#!/usr/bin/env python3
import argparse, json, os, queue, subprocess, sys, threading, time

MAX_SIDE_PHOTO, MAX_SIDE_VIDEO = 4096, 1920
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi")
VETO_KEEP = 0.7


def session(model, threads=None, copies=1):
    from rembg import new_session
    if threads:
        os.environ["OMP_NUM_THREADS"] = str(threads)
    made = [new_session(model) for _ in range(copies)]
    os.environ.pop("OMP_NUM_THREADS", None)
    return made


def colour(bg):
    return None if bg == "transparent" else tuple(int(bg[i:i + 2], 16) for i in (0, 2, 4))


def levels(low, high):
    import numpy as np
    return np.clip((np.arange(256, dtype=np.float32) - low) * 255 / (high - low), 0, 255).astype(np.uint8)


# isnet keeps floor reflections on some video frames and they flicker. u2netp is too coarse to draw
# the edge but doesnt make that mistake, so it only gets to veto
def veto(mask, coarse, keep=VETO_KEEP):
    import cv2
    h, w = mask.shape
    reach = max(3, int(0.012 * max(w, h))) | 1
    brush = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (reach, reach))
    near = cv2.GaussianBlur(cv2.dilate((coarse > 60).astype("uint8") * 255, brush), (0, 0), reach / 3)
    agreed = (mask.astype("uint16") * near // 255).astype("uint8")
    return agreed if int(agreed.sum()) >= keep * int(mask.sum()) else mask


def step(text):
    print(f"\r{text}...".ljust(32), end="", file=sys.stderr, flush=True)


def cut_photo(src, out, bg="transparent", model="birefnet-general", glasses=True):
    import numpy as np
    from PIL import Image, ImageOps
    from rembg import remove
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    if max(im.size) > MAX_SIDE_PHOTO:
        im.thumbnail((MAX_SIDE_PHOTO, MAX_SIDE_PHOTO), Image.LANCZOS)
    step("loading model")
    s = session(model, min(os.cpu_count() or 4, 8))[0]
    step("removing background")
    alpha = np.asarray(remove(im, session=s, only_mask=True).convert("L"))
    step("cleaning edges")
    alpha = levels(8, 245)[alpha]
    rgb = np.asarray(im).copy()
    if glasses:
        try:
            import cv2
            from glasses import see_through
            alpha = see_through(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), alpha)
        except Exception as e:
            print(f"glasses step skipped: {e!r}", file=sys.stderr)
    try:
        # edge pixels still carry the old background's colour, this works out the subject's own
        from pymatting import estimate_foreground_ml
        edge = (alpha > 0) & (alpha < 255)
        if edge.any():
            own = estimate_foreground_ml(rgb / 255.0, alpha / 255.0)
            rgb[edge] = (np.clip(own[edge], 0, 1) * 255).astype(np.uint8)
    except ImportError:
        pass
    rgb[alpha == 0] = 0
    cut = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
    fill = colour(bg)
    if fill is None and out.lower().endswith((".jpg", ".jpeg")):
        fill = (255, 255, 255)
    if fill is None:
        cut.save(out)
    else:
        flat = Image.new("RGB", cut.size, fill)
        flat.paste(cut, mask=cut.split()[3])
        flat.save(out)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:stream_side_data=rotation:stream_tags=rotate:format=duration",
                          "-of", "json", path], capture_output=True, text=True, timeout=60)
    d = json.loads(out.stdout or "{}")
    if not d.get("streams"):
        sys.exit("no video in that file")
    s = d["streams"][0]
    num, den = (s.get("r_frame_rate") or "30/1").split("/")
    turn = 0
    for side in s.get("side_data_list", []):
        turn = int(side.get("rotation", turn))
    turn = int((s.get("tags") or {}).get("rotate", turn))
    w, h = int(s["width"]), int(s["height"])
    if abs(turn) % 180 == 90:
        w, h = h, w
    return w, h, float(num) / float(den or 1), float(d.get("format", {}).get("duration") or 0)


def cut_video(src, out, bg="00b140", sessions=None, second=True):
    import numpy as np
    from PIL import Image
    from rembg import remove
    w, h, fps, seconds = probe(src)
    fps = min(fps if 1 <= fps <= 120 else 30, 30)
    scale = min(1, MAX_SIDE_VIDEO / max(w, h))
    w, h = max(2, int(w * scale) // 2 * 2), max(2, int(h * scale) // 2 * 2)
    total = max(1, int(seconds * fps))
    fill = colour(bg)
    cores = os.cpu_count() or 4
    each = min(4, cores)
    n = sessions or max(1, cores // each)
    step("loading models")
    pool = list(zip(session("isnet-general-use", each, n), session("u2netp", each, n) if second else [None] * n))

    decode = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={fps:.3f},scale={w}:{h}", "-f", "rawvideo",
                               "-pix_fmt", "rgb24", "pipe:1"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if fill is None:
        pix = "rgba"
        codec = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "32", "-deadline", "realtime", "-cpu-used", "6",
                 "-row-mt", "1", "-auto-alt-ref", "0", "-c:a", "libopus", "-b:a", "128k"]
    else:
        pix = "rgb24"
        codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                 "-movflags", "+faststart"]
    encode = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix, "-s", f"{w}x{h}", "-r", f"{fps:.3f}",
                               "-i", "pipe:0", "-i", src, "-map", "0:v:0", "-map", "1:a:0?", *codec, out],
                              stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    size = w * h * 3
    lut = levels(40, 215)
    todo, done = queue.Queue(maxsize=n * 3), {}
    ready = threading.Condition()
    failed = []

    def cut_frames(pair):
        first, coarse = pair
        while True:
            item = todo.get()
            if item is None:
                return
            i, raw = item
            try:
                frame = Image.frombuffer("RGB", (w, h), raw, "raw", "RGB", 0, 1)
                mask = lut[np.asarray(remove(frame, session=first, only_mask=True).resize((w, h), Image.BILINEAR), dtype=np.uint8)]
                if coarse is not None:
                    mask = veto(mask, np.asarray(remove(frame, session=coarse, only_mask=True).resize((w, h), Image.BILINEAR), dtype=np.uint8))
                pixels = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
                if fill is None:
                    result = np.dstack([pixels * (mask > 0)[..., None], mask]).tobytes()
                else:
                    a = mask.astype(np.uint16)[..., None]
                    result = ((pixels * a + np.array(fill, dtype=np.uint16) * (255 - a) + 127) // 255).astype(np.uint8).tobytes()
            except Exception as e:
                failed.append(e)
                result = None
            with ready:
                done[i] = result
                ready.notify_all()

    workers = [threading.Thread(target=cut_frames, args=(p,), daemon=True) for p in pool]
    for t in workers:
        t.start()

    def read_frames():
        i = 0
        while True:
            raw = decode.stdout.read(size)
            if len(raw) < size:
                break
            todo.put((i, raw))
            i += 1
        for _ in workers:
            todo.put(None)
        with ready:
            done[-1] = i
            ready.notify_all()

    threading.Thread(target=read_frames, daemon=True).start()
    written, started = 0, time.time()
    try:
        while True:
            with ready:
                while written not in done and not (-1 in done and written >= done[-1]):
                    ready.wait(timeout=1)
                if written not in done:
                    break
                frame = done.pop(written)
            if frame is None:
                raise failed[0]
            encode.stdin.write(frame)
            written += 1
            rate = written / (time.time() - started)
            print(f"\r{written}/{max(total, written)} frames  {rate:.1f}/s  {max(total - written, 0) / rate / 60:.1f} min left ", end="", file=sys.stderr)
        encode.stdin.close()
        err = encode.stderr.read().decode("utf-8", "replace")[-400:]
        if encode.wait() != 0:
            sys.exit("ffmpeg: " + err)
    finally:
        for p in (decode, encode):
            if p.poll() is None:
                p.kill()
            p.wait()
    print(file=sys.stderr)
    if not written:
        sys.exit("could not read that video")


def main():
    ap = argparse.ArgumentParser(description="remove the background from a photo or a video")
    ap.add_argument("file")
    ap.add_argument("-o", "--out")
    ap.add_argument("--bg", default=None, help="transparent or a hex colour like ffffff (photo: transparent, video: 00b140)")
    ap.add_argument("--model", default="birefnet-general", help="photo model, any rembg name (isnet-general-use is the fast one)")
    ap.add_argument("--no-glasses", action="store_true")
    ap.add_argument("--no-veto", action="store_true", help="video: skip the second model, a bit faster")
    a = ap.parse_args()
    if not os.path.isfile(a.file):
        sys.exit(f"no such file: {a.file}")
    stem = os.path.splitext(a.file)[0]
    video = a.file.lower().endswith(VIDEO_EXT)
    bg = (a.bg or ("00b140" if video else "transparent")).lower().lstrip("#")
    if bg != "transparent" and (len(bg) != 6 or any(c not in "0123456789abcdef" for c in bg)):
        sys.exit("--bg is transparent or 6 hex digits")
    started = time.time()
    if video:
        out = a.out or f"{stem}-no-bg.{'webm' if bg == 'transparent' else 'mp4'}"
        cut_video(a.file, out, bg, second=not a.no_veto)
    else:
        out = a.out or f"{stem}-no-bg.png"
        cut_photo(a.file, out, bg, a.model, glasses=not a.no_glasses)
    print("\r" + " " * 32 + "\r", end="", file=sys.stderr)
    print(f"{out}  {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()

import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

data, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
res = json.load(open(f"{data}/results.json"))
picked = json.load(open(f"{data}/set.json"))
COLS = [("original", None), ("u2net", "u2net"), ("isnet", "isnet-general-use"), ("birefnet lite", "birefnet-general-lite"),
        ("birefnet", "birefnet-general"), ("truth", "mask")]
GREEN = (0, 177, 64)
INK, PAPER = (235, 235, 235), (18, 18, 20)
FONT = next(p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Helvetica.ttc") if os.path.isfile(p))


def font(size):
    return ImageFont.truetype(FONT, size)


def on_green(im, alpha):
    flat = Image.new("RGB", im.size, GREEN)
    flat.paste(im, mask=alpha)
    return flat


def window(name, share=0.42):
    gt = np.asarray(Image.open(f"{data}/mask/{name}.png").convert("L"), dtype=np.float32)
    wrong = sum(np.abs(np.asarray(Image.open(f"{data}/pred/{m}/{name}.png").convert("L"), dtype=np.float32) - gt)
                for m in ("isnet-general-use", "birefnet-general"))
    h, w = gt.shape
    side = int(share * min(h, w))
    s = np.pad(wrong, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    step = max(1, side // 8)
    best = max(((s[y + side, x + side] - s[y, x + side] - s[y + side, x] + s[y, x], x, y)
                for y in range(0, h - side + 1, step) for x in range(0, w - side + 1, step)))
    return (best[1], best[2], best[1] + side, best[2] + side)


def tiles(name, zoom):
    im = Image.open(f"{data}/image/{name}.jpg").convert("RGB")
    box = window(name) if zoom else None
    made = []
    for label, src in COLS:
        if src is None:
            t = im
        else:
            folder = f"{data}/mask" if src == "mask" else f"{data}/pred/{src}"
            t = on_green(im, Image.open(f"{folder}/{name}.png").convert("L"))
            if src != "mask":
                label += f"  {res['accuracy'][src]['per'][name]:.1f}"
        made.append((label, t.crop(box) if box else t))
    return made


def grid(rows, across, tile, path):
    pad, cap = tile // 30, tile // 8
    f = font(max(11, tile // 16))
    cells = []
    for label, t in (c for r in rows for c in r):
        t = t.copy()
        t.thumbnail((tile, tile), Image.LANCZOS)
        cells.append((label, t))
    lines = [cells[i:i + across] for i in range(0, len(cells), across)]
    heights = [max(t.height for _, t in line) for line in lines]
    sheet = Image.new("RGB", (across * tile + (across + 1) * pad, sum(heights) + len(lines) * (cap + pad) + pad), PAPER)
    d = ImageDraw.Draw(sheet)
    y = pad
    for line, high in zip(lines, heights):
        for i, (label, t) in enumerate(line):
            x = pad + i * (tile + pad)
            sheet.paste(t, (x + (tile - t.width) // 2, y + (high - t.height) // 2))
            d.text((x + 2, y + high + cap // 5), label, fill=INK, font=f)
        y += high + cap + pad
    sheet.save(path, quality=88)
    print(path, sheet.size)


gap = {n: res["accuracy"]["u2net"]["per"][n] + res["accuracy"]["isnet-general-use"]["per"][n] - 2 * res["accuracy"]["birefnet-general"]["per"][n]
       for n in picked}
names = sys.argv[3:]
if not names:
    for cat in ("animal", "portrait", "furniture", "plant"):
        names.append(max((n for n in picked if picked[n] == cat), key=gap.get))
print(names)
rows = [tiles(n.rstrip("+"), n.endswith("+")) for n in names]
grid(rows, len(COLS), 360, f"{out}/models-wide.jpg")
grid([[r[0], r[2], r[4]] for r in rows], 3, 420, f"{out}/models-tall.jpg")

import json, os, statistics, sys
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bgremove import levels, veto

data = sys.argv[1]
picked = json.load(open(f"{data}/set.json"))
names = sorted(picked)
cats = sorted(set(picked.values()), key=lambda c: -sum(v == c for v in picked.values()))
models = [m for m in ("birefnet-general", "birefnet-massive", "bria-rmbg", "birefnet-general-lite", "birefnet-portrait", "isnet-general-use",
                      "u2net", "silueta", "u2net_human_seg", "u2netp") if os.path.isfile(f"{data}/pred/{m}.json")]


def read(path):
    return np.asarray(Image.open(path).convert("L"))


def score(pred, gt):
    p, g = pred.astype(np.float32) / 255, gt.astype(np.float32) / 255
    solid = (gt > 127).astype(np.uint8)
    r = max(2, round(0.01 * max(gt.shape)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    band = (cv2.dilate(solid, k) != cv2.erode(solid, k)) | ((gt > 0) & (gt < 255))
    a, b = pred > 127, gt > 127
    return {"err": float(np.abs(p - g).mean()) * 100, "edge": float(np.abs(p - g)[band].mean()) * 100 if band.any() else 0.0,
            "iou": float((a & b).sum() / max(1, (a | b).sum())) * 100}


rows = {}


def add(label, get):
    per = [score(get(n), read(f"{data}/mask/{n}.png")) for n in names]
    row = {k: round(statistics.mean(s[k] for s in per), 2) for k in ("err", "edge", "iou")}
    row["worst"] = round(max(s["err"] for s in per), 1)
    for c in cats:
        row[c] = round(statistics.mean(s["err"] for s, n in zip(per, names) if picked[n] == c), 2)
    row["per"] = {n: round(s["err"], 2) for s, n in zip(per, names)}
    rows[label] = row
    print(label, {k: v for k, v in row.items() if k != "per"}, flush=True)


for m in models:
    add(m, lambda n, m=m: read(f"{data}/pred/{m}/{n}.png"))
    cleaned = [score(levels(8, 245)[read(f"{data}/pred/{m}/{n}.png")], read(f"{data}/mask/{n}.png"))["err"] for n in names]
    rows[m]["clean"] = round(statistics.mean(cleaned), 2)
if "birefnet-general" in models:
    add("birefnet-general + levels", lambda n: levels(8, 245)[read(f"{data}/pred/birefnet-general/{n}.png")])
if "isnet-general-use" in models and "u2netp" in models:
    add("isnet + levels", lambda n: levels(40, 215)[read(f"{data}/pred/isnet-general-use/{n}.png")])
    for keep in (0.4, 0.7, 0.85, 0.95):
        add(f"isnet + levels + veto {keep}", lambda n, keep=keep: veto(levels(40, 215)[read(f"{data}/pred/isnet-general-use/{n}.png")],
                                                                      read(f"{data}/pred/u2netp/{n}.png"), keep))

speed = {}
for m in models:
    d = json.load(open(f"{data}/pred/{m}.json"))
    onnx = os.path.join(os.path.expanduser(os.environ.get("U2NET_HOME", "~/.u2net")), "models", m, m + ".onnx")
    speed[m] = {"seconds": round(statistics.median(d["times"]), 2), "load": d["load"], "ram_mb": d["rss_mb"],
                "file_mb": round(os.path.getsize(onnx) / 1e6) if os.path.isfile(onnx) else 0}


def lines(path):
    return [json.loads(x) for x in open(path)] if os.path.isfile(path) else []


json.dump({"images": len(names), "categories": {c: sum(v == c for v in picked.values()) for c in cats}, "accuracy": rows, "speed": speed,
           "threads": lines(f"{data}/threads.jsonl"), "video": lines(f"{data}/video.jsonl")}, open(f"{data}/results.json", "w"), indent=1)

print("\n| model | error % | after levels | edge error % | IoU % | worst image |\n|---|---|---|---|---|---|")
for m in models:
    r = rows[m]
    print(f"| {m} | {r['err']:.2f} | {r['clean']:.2f} | {r['edge']:.1f} | {r['iou']:.1f} | {r['worst']:.1f} |")
print("\n| model | seconds | RAM | download |\n|---|---|---|---|")
for m in models:
    s = speed[m]
    print(f"| {m} | {s['seconds']} | {s['ram_mb'] / 1024:.1f} GB | {s['file_mb']} MB |")
print("\n| model | " + " | ".join(f"{c} ({sum(v == c for v in picked.values())})" for c in cats) + " |\n|---|" + "---|" * len(cats))
for m in models:
    print(f"| {m} | " + " | ".join(f"{rows[m][c]:.2f}" for c in cats) + " |")
print("\n| | error % | edge error % | IoU % | worst image |\n|---|---|---|---|---|")
for label in rows:
    if label not in models or label in ("birefnet-general", "isnet-general-use"):
        r = rows[label]
        print(f"| {label} | {r['err']:.2f} | {r['edge']:.1f} | {r['iou']:.1f} | {r['worst']:.1f} |")

rng = np.random.default_rng(0)
print("\nerror of a minus error of b, 95% interval from resampling the images, and on how many images a is better")
for a, b in (("birefnet-general-lite", "birefnet-general"), ("birefnet-portrait", "birefnet-general"), ("birefnet-massive", "birefnet-general"),
             ("bria-rmbg", "birefnet-general"), ("isnet-general-use", "birefnet-general"), ("u2net", "isnet-general-use"),
             ("isnet + levels + veto 0.4", "isnet + levels"), ("isnet + levels + veto 0.85", "isnet + levels")):
    if a in rows and b in rows:
        d = np.array([rows[a]["per"][n] - rows[b]["per"][n] for n in names])
        lo, hi = np.percentile([d[rng.integers(0, len(d), len(d))].mean() for _ in range(10000)], [2.5, 97.5])
        print(f"{a} vs {b}: {d.mean():+.2f} [{lo:+.2f}, {hi:+.2f}]  better on {int((d < 0).sum())}/{len(d)}")

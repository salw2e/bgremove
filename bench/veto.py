# python bench/veto.py <folder of video frames>
# no ground truth for video frames, so birefnet is the reference here
import os, sys
import numpy as np
from PIL import Image
from rembg import remove

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bgremove import levels, session, veto

folder = sys.argv[1]
isnet, small, ref = session("isnet-general-use")[0], session("u2netp")[0], session("birefnet-general")[0]
keeps = (None, 0.4, 0.7, 0.85, 0.95)
total = {k: [] for k in keeps}
for name in sorted(f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg"))):
    im = Image.open(os.path.join(folder, name)).convert("RGB")
    mask = lambda s: np.asarray(remove(im, session=s, only_mask=True).convert("L").resize(im.size, Image.BILINEAR))
    a, coarse, r = levels(40, 215)[mask(isnet)], mask(small), levels(8, 245)[mask(ref)].astype(np.float32)
    line = []
    for k in keeps:
        out = (a if k is None else veto(a, coarse, k)).astype(np.float32)
        extra, lost = np.clip(out - r, 0, None).sum() / r.sum() * 100, np.clip(r - out, 0, None).sum() / r.sum() * 100
        total[k].append((extra, lost))
        line.append(f"{extra:5.1f}/{lost:4.1f}")
    print(f"{name:14s}", "  ".join(line), flush=True)
print("\n| veto | kept by mistake % | lost by mistake % |\n|---|---|---|")
for k in keeps:
    e, l = (sum(x[i] for x in total[k]) / len(total[k]) for i in (0, 1))
    print(f"| {'off' if k is None else k} | {e:.1f} | {l:.1f} |")

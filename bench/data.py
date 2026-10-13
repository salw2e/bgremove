import io, json, os, random, sys
import pyarrow.parquet as pq
from PIL import Image

src, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(f"{out}/image", exist_ok=True)
os.makedirs(f"{out}/mask", exist_ok=True)
rows = pq.read_table(src).to_pylist()
by = {}
for r in rows:
    name = os.path.splitext(r["image_name"])[0]
    Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB").save(f"{out}/image/{name}.jpg", quality=95)
    Image.open(io.BytesIO(r["mask"]["bytes"])).convert("L").save(f"{out}/mask/{name}.png")
    by.setdefault(r["category"], []).append(name)
random.seed(0)
picked = {}
for cat, names in sorted(by.items()):
    k = max(1, round(n * len(names) / len(rows)))
    for name in random.sample(sorted(names), k):
        picked[name] = cat
json.dump(picked, open(f"{out}/set.json", "w"), indent=0)
print(len(rows), "images,", len(picked), "picked", {c: sum(v == c for v in picked.values()) for c in by})

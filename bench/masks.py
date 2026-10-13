import json, os, resource, sys, time

model, data, threads = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ""
if threads:
    os.environ["OMP_NUM_THREADS"] = threads
from PIL import Image
from rembg import new_session, remove

names = sorted(json.load(open(f"{data}/set.json")))
out = f"{data}/pred/{model}"
os.makedirs(out, exist_ok=True)
t = time.time()
s = new_session(model)
load = time.time() - t
times = []
for name in names:
    im = Image.open(f"{data}/image/{name}.jpg").convert("RGB")
    t = time.time()
    mask = remove(im, session=s, only_mask=True)
    times.append(round(time.time() - t, 3))
    mask.convert("L").resize(im.size, Image.BILINEAR).save(f"{out}/{name}.png")
    print(model, name, im.size, times[-1], flush=True)
json.dump({"model": model, "threads": threads or "all", "load": round(load, 2), "times": times,
           "rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024}, open(f"{out}.json", "w"))

import json, os, resource, sys, time

model, data, threads = sys.argv[1], sys.argv[2], sys.argv[3]
os.environ["OMP_NUM_THREADS"] = threads
from PIL import Image
from rembg import new_session, remove

names = sorted(json.load(open(f"{data}/set.json")))[:4]
s = new_session(model)
times = []
for i, name in enumerate(names):
    im = Image.open(f"{data}/image/{name}.jpg").convert("RGB")
    t = time.time()
    remove(im, session=s, only_mask=True)
    if i:
        times.append(time.time() - t)
row = {"model": model, "threads": int(threads), "seconds": round(sorted(times)[len(times) // 2], 2),
       "rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024}
print(json.dumps(row), flush=True)
open(f"{data}/threads.jsonl", "a").write(json.dumps(row) + "\n")

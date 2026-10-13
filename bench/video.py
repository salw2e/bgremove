import json, os, sys, threading, time

data, n, per, veto = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] == "veto"
os.environ["OMP_NUM_THREADS"] = str(per)
from PIL import Image
from rembg import new_session, remove

name = sorted(json.load(open(f"{data}/set.json")))[0]
im = Image.open(f"{data}/image/{name}.jpg").convert("RGB").resize((1280, 720))
a = [new_session("isnet-general-use") for _ in range(n)]
b = [new_session("u2netp") for _ in range(n)] if veto else None
frames = max(4, 96 // n)


def work(i):
    for _ in range(frames):
        remove(im, session=a[i], only_mask=True)
        if veto:
            remove(im, session=b[i], only_mask=True)


for i in range(n):
    remove(im, session=a[i], only_mask=True)
ts = [threading.Thread(target=work, args=(i,)) for i in range(n)]
t = time.time()
[x.start() for x in ts]
[x.join() for x in ts]
row = {"sessions": n, "threads_each": per, "veto": veto, "fps": round(n * frames / (time.time() - t), 2)}
print(json.dumps(row), flush=True)
open(f"{data}/video.jsonl", "a").write(json.dumps(row) + "\n")

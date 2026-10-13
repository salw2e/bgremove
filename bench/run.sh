#!/bin/sh
# sh bench/run.sh <data dir>   (after bench/data.py)
set -e
d=$1
for m in u2netp silueta u2net u2net_human_seg isnet-general-use birefnet-general-lite birefnet-general birefnet-portrait birefnet-massive bria-rmbg; do
  [ -f $d/pred/$m.json ] || python bench/masks.py $m $d
done
rm -f $d/threads.jsonl $d/video.jsonl
for m in u2netp isnet-general-use birefnet-general-lite birefnet-general; do
  for t in 1 2 4 8 16 24; do python bench/threads.py $m $d $t; done
done
for g in "1 24" "2 12" "4 6" "6 4" "8 3" "12 2" "24 1"; do
  python bench/video.py $d $g plain
  python bench/video.py $d $g veto
done
echo done

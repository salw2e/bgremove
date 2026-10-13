# the numbers

## what you need

ram matters more than cores

| | ram | 12 MP photo, start to finish |
|---|---|---|
| default (birefnet) | 16 GB. one photo peaked at 9.6 GB so 12 can work | 15 s |
| `--model birefnet-general-lite` | 12 GB, peaked at 8 | 11 s |
| `--model isnet-general-use` | 4 GB, peaked at 1.6 | 4.5 s |

that time includes loading the model and writing the png. the model alone, seconds per photo by number of threads:

| threads | 1 | 2 | 4 | 8 | 16 | 24 |
|---|---|---|---|---|---|---|
| birefnet | 27.3 | 14.0 | 8.8 | 6.7 | 7.0 | 9.1 |
| birefnet lite | 10.5 | 6.1 | 4.5 | 3.9 | 4.0 | 4.9 |
| isnet | 2.6 | 1.2 | 0.65 | 0.41 | 0.42 | 0.52 |
| u2netp | 0.38 | 0.19 | 0.12 | 0.09 | 0.09 | 0.15 |

4 cores gets most of the speed, 8 is the fastest, and all 24 threads is slower than 8, so the script never uses more than 8 for a photo. ram is the same 14 GB at 1 thread or 24

so what id get: 4 cores + 16 GB for photos. on a 2 core / 4 GB vps only isnet fits

video is slow on cpu whatever you do. 2.9 frames a second on 24 threads, so a 14 second 720p clip took 2 minutes and a 10 second 1080p clip 1 min 50. ram is about 2 GB per 4 cores (12.6 GB on this box). on 4 cores expect a bit over 1 frame a second

no gpu numbers, i dont have one

## which model

rembg ships a lot of models and i wanted to know which one is actually best, so i ran 10 of them on 100 photos from [AIM-500](https://github.com/JizhiziLi/AIM) (people, animals, furniture, plants, toys, glass) where somebody drew the true cutout by hand, and compared

why AIM-500: birefnet's readme lists what the general weights were trained on and it includes the test halves of the usual benchmarks (DUTS, HRSOD, P3M), so scoring it on those is scoring it on photos it has already seen. AIM-500 is not on that list. for bria and birefnet-massive i dont know what they saw

- error = how far the predicted transparency is from the true one, averaged over every pixel. 0 is perfect
- edge error = same thing but only near the outline, where hair and fur are
- worst = the error on the one photo it did worst on

| model | error % | edge error % | worst % | sec per photo | ram | download | licence |
|---|---|---|---|---|---|---|---|
| birefnet-portrait | 0.56 | 3.8 | 4.8 | 9.1 | 13.6 GB | 973 MB | MIT |
| **birefnet-general** | 0.62 | 4.0 | 4.0 | 9.2 | 13.6 GB | 973 MB | MIT |
| bria-rmbg | 0.68 | 4.6 | 7.1 | 9.2 | 13.5 GB | 1024 MB | non commercial |
| birefnet-general-lite | 0.79 | 5.0 | 6.8 | 5.5 | 12.1 GB | 224 MB | MIT |
| birefnet-massive | 2.39 | 9.9 | 32.8 | 9.1 | 13.7 GB | 973 MB | MIT |
| **isnet-general-use** | 3.42 | 11.2 | 24.2 | 0.56 | 1.7 GB | 179 MB | Apache 2.0 |
| u2net | 3.99 | 13.4 | 24.2 | 0.26 | 1.1 GB | 176 MB | Apache 2.0 |
| silueta | 4.29 | 13.8 | 24.4 | 0.57 | 0.8 GB | 44 MB | Apache 2.0 |
| u2netp | 4.94 | 14.3 | 40.5 | 0.09 | 0.7 GB | 5 MB | Apache 2.0 |
| u2net_human_seg | 5.60 | 19.2 | 38.7 | 0.25 | 1.1 GB | 176 MB | Apache 2.0 |

bold = what this repo uses (birefnet-general for photos, isnet for video). seconds and ram here are at 24 threads over all 100 photos in one process, thats why they are higher than the table above

<picture>
  <source media="(min-width: 768px)" srcset="models-wide.jpg">
  <img src="models-tall.jpg" width="100%" alt="same four photos cut by u2net, isnet, birefnet lite and birefnet next to the truth">
</picture>

the number under each one is its error on that photo. these are the photos where the models disagree the most, not typical ones

what came out of it

- the three best (birefnet portrait, general, bria) are basically the same. portrait beats general on 82 of 100 photos but by 0.05, and after the cleanup step below its 0.52 vs 0.53. i expected the portrait one to be bad at animals and chairs and it isnt
- bria is as good but you cant use it commercially without paying, so no
- lite is a little worse (+0.18) and takes 40% less time. the download is 4x smaller but it still wants 12 GB of ram, so it doesnt help a small machine
- massive is worse than general on all 100 photos and drops big parts of the subject on a few. dont
- the old fast ones (isnet, u2net) have 5 to 6 times the error, and its not rough edges, its whole pieces of the subject going missing, like the rhino and the dress above. isnet vs u2net is too close to call on 100 photos
- u2net_human_seg is only ok on people (1.83) and birefnet is still way better there (0.35)
- glass and other see through stuff is the hardest for every model

error by kind of photo:

| model | animal (40) | portrait (20) | plant (15) | furniture (9) | toy (7) | transparent (7) | fruit (2) |
|---|---|---|---|---|---|---|---|
| birefnet-portrait | 0.38 | 0.31 | 0.69 | 0.66 | 0.53 | 2.01 | 0.42 |
| birefnet-general | 0.47 | 0.35 | 0.74 | 0.66 | 0.63 | 1.87 | 0.52 |
| bria-rmbg | 0.49 | 0.37 | 0.75 | 0.71 | 0.63 | 2.48 | 0.62 |
| birefnet-general-lite | 0.61 | 0.39 | 0.87 | 0.73 | 0.67 | 3.05 | 0.59 |
| birefnet-massive | 1.99 | 1.71 | 1.24 | 0.77 | 0.92 | 13.08 | 0.76 |
| isnet-general-use | 3.77 | 3.67 | 1.71 | 1.09 | 1.26 | 10.25 | 0.68 |
| u2net | 3.42 | 4.81 | 3.75 | 3.00 | 1.50 | 10.05 | 1.01 |
| silueta | 3.91 | 5.28 | 3.78 | 3.27 | 1.56 | 9.67 | 1.21 |
| u2netp | 5.82 | 5.20 | 3.28 | 2.71 | 1.41 | 10.09 | 1.44 |
| u2net_human_seg | 4.07 | 1.83 | 6.64 | 15.44 | 9.63 | 7.11 | 2.53 |

"basically the same" and "too close to call" are from resampling the 100 photos 10000 times, the script prints the intervals. every per photo number is in [results.json](results.json)

## what it does after the model

the model output is not used as is

**levels.** the models leave the background 1 or 2% there and the subject 97% there, and you see both on a new background. everything nearly empty is pushed to empty and nearly solid to solid. birefnet 0.62 -> 0.53, better on 92 of 100 photos. isnet 3.42 -> 3.24

**edge colour.** a half transparent pixel on the outline still has half of the old background's colour in it, so somebody who stood at a red wall gets red hair tips. pymatting works out what colour the subject alone was. no number for this one, the test set has no true colours

**glasses.** every model treats a lens as solid, so in a photo taken at an angle the wall stays visible through the bit of lens that sticks out past the face. `glasses.py` finds the face, labels its parts, and clears lens pixels that are outside the face and next to removed background. no number for this either: AIM-500 hides faces, so its only checked by eye on 14 photos

**veto (video).** isnet on some frames keeps the reflection on the floor under the subject, and not on the next frame, so it flickers. u2netp is too coarse to cut with but doesnt make that mistake, so its mask is used as a veto: isnet's mask only counts near where u2netp also saw something. on 8 frames from a clip that flickers, with birefnet as the reference:

| | kept by mistake % |
|---|---|
| isnet alone | 6.0 |
| with veto | 0.8 |

but it costs on normal photos. my first version dropped anything u2netp didnt see as long as 40% of the mask survived, and on the 100 photos that made isnet worse, 3.24 -> 4.19, because u2netp misses real parts of people. now the veto is skipped unless 70% survives: same 0.8 on the flicker frames, 3.24 -> 3.49 on photos. still a cost, and 8 frames from one clip is not much, so `--no-veto` turns it off (3.4 frames a second instead of 2.9)

## video speed

copies of the model x threads each, frames per second at 720p:

| copies x threads | isnet | isnet + veto |
|---|---|---|
| 1 x 24 | 1.9 | 1.5 |
| 2 x 12 | 2.6 | 2.2 |
| 4 x 6 | 3.2 | 2.7 |
| 6 x 4 | 3.4 | 2.9 |
| 8 x 3 | 3.5 | 3.0 |
| 12 x 2 | 3.4 | 3.0 |

one copy with all the threads is the slowest way to do it. the script runs one copy per 4 cores. 24 x 1 ran out of memory (24 copies of the model)

## run it yourself

```
pip install pyarrow
# test-00000-of-00001.parquet from https://huggingface.co/datasets/nobg/AIM-500
python bench/data.py test-00000-of-00001.parquet data 100
sh bench/run.sh data        # about 2 hours, wants 16 GB free
python bench/score.py data
python bench/sheet.py data study
python bench/veto.py some/folder/of/frames
```

everything here was measured on one box: ryzen 9 7900 (12 cores / 24 threads), 64 GB, no gpu, python 3.12, rembg 2.0.85, onnxruntime 1.31. it was doing other things at the same time so read the timings as give or take 10%

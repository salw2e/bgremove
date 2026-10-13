# bgremove

removes the background from a photo or a video on a normal cpu, no gpu. its the thing behind https://justsal.xyz/bgremove

```
pip install -r requirements.txt
python bgremove.py photo.jpg
python bgremove.py clip.mp4
```

you get `photo-no-bg.png` (transparent) and `clip-no-bg.mp4` (on green so any editor can key it out). video needs ffmpeg installed. first run downloads the models, about 1.2 GB, after that it works offline

```
python bgremove.py photo.jpg --bg ffffff                 # white instead of transparent
python bgremove.py photo.jpg --model isnet-general-use   # for small machines, a lot rougher
python bgremove.py clip.mp4 --bg transparent             # webm with alpha, iphones cant play it
python bgremove.py clip.mp4 -o out.mp4
```

<picture>
  <source media="(min-width: 768px)" srcset="study/cut-wide.jpg">
  <img src="study/cut-tall.jpg" width="100%" alt="before and after: lion, hair in the wind, teddy bear">
</picture>

## what you need

| | ram | one 12 MP photo |
|---|---|---|
| default (birefnet) | 16 GB | 15 s |
| `--model birefnet-general-lite` | 12 GB | 11 s |
| `--model isnet-general-use` | 4 GB | 4.5 s |

4 cores is enough and more than 8 doesnt help. video is slow, about 3 frames a second on 24 threads. no gpu numbers, i dont have one

## which model

i ran 10 of them on 100 photos that have a hand drawn cutout. birefnet is off by 0.6%, isnet (the best of the fast ones) by 3.4%, and its not rough edges, its whole pieces of the subject going missing. tables and pictures are in [study](study/)

## todo

- [ ] gpu numbers
- [ ] transparent video that iphones play
- [ ] the http worker that runs this behind the site

## thanks

[rembg](https://github.com/danielgatis/rembg), [BiRefNet](https://github.com/ZhengPeng7/BiRefNet), [DIS / isnet](https://github.com/xuebinqin/DIS), [U-2-Net](https://github.com/xuebinqin/U-2-Net), [pymatting](https://github.com/pymatting/pymatting), [face-parsing](https://github.com/yakhyo/face-parsing), [YuNet](https://github.com/opencv/opencv_zoo), and [AIM-500](https://github.com/JizhiziLi/AIM) for the test photos (the pictures above are from it)

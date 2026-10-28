# bgremove

Removes the background from photos and videos. Runs on CPU.

```
pip install -r requirements.txt
python bgremove.py photo.jpg
python bgremove.py clip.mp4
```

Video needs ffmpeg. The first run downloads about 1.2 GB of models.

```
python bgremove.py photo.jpg --bg ffffff
python bgremove.py photo.jpg --model isnet-general-use
```

<picture>
  <source media="(min-width: 768px)" srcset="study/cut-wide.jpg">
  <img src="study/cut-tall.jpg" width="100%" alt="before and after">
</picture>

| Model | RAM | 12 MP photo |
|---|---|---|
| birefnet-general (default) | 16 GB | 15 s |
| isnet-general-use | 4 GB | 4.5 s |

Comparison of 10 models is in [study](study/). Built on [rembg](https://github.com/danielgatis/rembg).

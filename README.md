# bgremove

removes the background from a photo or a video, on a normal cpu, no gpu. its the thing behind https://justsal.xyz/bgremove

```
pip install -r requirements.txt
python bgremove.py photo.jpg
python bgremove.py clip.mp4
```

photo comes out as `photo-no-bg.png` (transparent), video as `clip-no-bg.mp4` on green. video needs ffmpeg installed

first run downloads the models (about 1.2 GB), after that its offline

```
python bgremove.py photo.jpg --bg ffffff            # white instead of transparent
python bgremove.py photo.jpg --model isnet-general-use   # 10x faster, rougher edges
python bgremove.py clip.mp4 --bg transparent        # webm with alpha (iphones cant play it)
python bgremove.py clip.mp4 -o out.mp4
```

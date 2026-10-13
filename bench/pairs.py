# python bench/pairs.py out.jpg <across> photo.jpg photo-no-bg.png [more pairs]
import sys
from PIL import Image

out, across, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
tile, pad = 420, 12
tiles = []
for before, after in zip(files[::2], files[1::2]):
    a, b = Image.open(before).convert("RGB"), Image.open(after).convert("RGBA")
    board = Image.new("RGB", b.size, (255, 255, 255))
    px = board.load()
    for y in range(0, b.height, 24):
        for x in range(0, b.width, 24):
            if (x // 24 + y // 24) % 2:
                board.paste((216, 216, 216), (x, y, x + 24, y + 24))
    board.paste(b, mask=b.split()[3])
    for t in (a, board):
        side = min(t.size)
        tiles.append(t.crop(((t.width - side) // 2, (t.height - side) // 2, (t.width + side) // 2, (t.height + side) // 2)).resize((tile, tile), Image.LANCZOS))
lines = -(-len(tiles) // across)
sheet = Image.new("RGB", (across * tile + (across + 1) * pad, lines * tile + (lines + 1) * pad), (18, 18, 20))
for i, t in enumerate(tiles):
    sheet.paste(t, (pad + (i % across) * (tile + pad), pad + (i // across) * (tile + pad)))
sheet.save(out, quality=88)
print(out, sheet.size)

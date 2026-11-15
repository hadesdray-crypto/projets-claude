"""Extrait des images d'un GIF pour le contrôle visuel : python3 extraire.py <gif> <n> [x0 y0 x1 y1]
Écrit apercu/<nom>-NNN.png (agrandi) et une planche apercu/<nom>-planche.png."""
import os
import sys
from PIL import Image, ImageSequence, ImageDraw

gif, n = sys.argv[1], int(sys.argv[2])
box = tuple(int(v) for v in sys.argv[3:7]) if len(sys.argv) >= 7 else None
nom = os.path.basename(gif)[:-4]
os.makedirs('apercu', exist_ok=True)
im = Image.open(gif)
frames = [f.convert('RGB') for f in ImageSequence.Iterator(im)]
idx = [round(k * (len(frames) - 1) / (n - 1)) for k in range(n)]
vig = []
for k in idx:
    f = frames[k]
    if box:
        f = f.crop(box)
    f = f.resize((f.width * 2, f.height * 2), Image.NEAREST) if f.width < 500 else f
    f.save('apercu/%s-%03d.png' % (nom, k))
    vig.append((k, f))
cols = 4 if n > 8 else 2
w, h = vig[0][1].size
rows = (len(vig) + cols - 1) // cols
P = Image.new('RGB', (cols * w, rows * h))
for j, (k, f) in enumerate(vig):
    d = ImageDraw.Draw(f)
    d.text((4, 4), str(k), fill=(255, 255, 0))
    P.paste(f, ((j % cols) * w, (j // cols) * h))
P.save('apercu/%s-planche.png' % nom)
print(len(frames), idx, P.size)

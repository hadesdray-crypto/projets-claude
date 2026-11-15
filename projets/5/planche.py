"""Planche de contrôle : python3 planche.py <nom> i1,i2,... [sortie] — assemble des images du rendu (4 par ligne)."""
import sys
from PIL import Image, ImageDraw
nom, idx = sys.argv[1], [int(x) for x in sys.argv[2].split(',')]
out = sys.argv[3] if len(sys.argv) > 3 else '/tmp/planche.png'
c = 4 if len(idx) > 4 else len(idx); l = (len(idx) + c - 1) // c
w = Image.new('RGB', (480 * c, 360 * l))
for k, i in enumerate(idx):
    im = Image.open('/tmp/rendu/%s/i%04d.png' % (nom, i)).convert('RGB').crop((40, 20, 520, 380))
    ImageDraw.Draw(im).text((6, 4), 'image %d' % i, fill=(255, 255, 0))
    w.paste(im, (480 * (k % c), 360 * (k // c)))
w.save(out)

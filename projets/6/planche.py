"""Assemble des images d'aperçu d'un GIF en une planche : python3 planche.py <numéro> <i1> <i2> ... (sortie apercu/planche-N.png)"""
import sys
from PIL import Image
n = sys.argv[1]
ims = [Image.open('apercu/%s-%03d.png' % (n, int(i))) for i in sys.argv[2:]]
w, h = ims[0].size
cols = 2
rows = (len(ims) + 1) // 2
pl = Image.new('RGB', (w * cols, h * rows))
for k, im in enumerate(ims):
    pl.paste(im, ((k % cols) * w, (k // cols) * h))
pl.save('apercu/planche-%s.png' % n)

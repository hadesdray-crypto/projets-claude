"""Retire du calque « corps » le liseré clair (couleur du décor d'origine) qui entoure Thomas :
invisible sur le décor de départ, il devient un halo bleu clair dès que Thomas se couche
devant le sol sombre. On pèle, couche par couche (3 fois), les pixels du bord dont la couleur
est proche du décor et claire. À lancer une seule fois (le fichier calques/corps.png est modifié)."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
fond = np.array(Image.open('decor/fond.png').convert('RGB')).astype(int)
im = np.array(Image.open('calques/corps.png').convert('RGBA'))
a = im[..., 3] > 0
d = np.abs(im[..., :3].astype(int) - fond).sum(2)
clair = im[..., :3].astype(int).sum(2) > 330
bleute = im[..., 2].astype(int) >= im[..., 0].astype(int) - 4
retire_total = 0
for _ in range(3):
    bord = a & ~ndi.binary_erosion(a)
    cible = bord & (d < 30) & clair & bleute
    retire_total += int(cible.sum())
    a = a & ~cible
im[..., 3] = np.where(a, im[..., 3], 0)
Image.fromarray(im).save('calques/corps.png')
print('pixels retirés :', retire_total)

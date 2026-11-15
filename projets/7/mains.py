"""Planche des 4 formes de main : python3 mains.py  ->  mains.png (agrandie 8 fois)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import moteur7 as m

FORMES = [('ouverte', 0.0), ('relâchée', 0.40), ('saisissante', 0.72), ('fermée', 1.0)]


def main_seule(f, ang=0.0, taille=None):
    taille = taille or m.CFG['main']['taille']
    cadre = np.full((90, 90, 3), (118, 150, 160), np.float32)
    W = np.array([30.0, 45.0])
    paume, pouce, doigts = m.formes_main(W, ang, f, taille)
    r = m.CFG['rayons']
    peau = (m.CFG['peau']['clair'], m.CFG['peau']['moyen'], m.CFG['peau']['sombre'])
    t = m.Toile(0, 0, 90, 90)
    avant = lambda x, y: m.sdf_cone(x, y, (-10, 45), tuple(W), r['coude'], r['poignet'])
    t.peindre(lambda x, y: np.minimum.reduce([avant(x, y), paume(x, y), pouce(x, y)]), peau, m.CFG['trait'])
    t.nettoyer()
    t.poser(cadre)
    f2 = m.Toile(0, 0, 90, 90)
    f2.peindre(lambda x, y: np.minimum.reduce([g(x, y) for g in doigts]), peau, m.CFG['trait'])
    s2 = np.sort(np.stack([g(f2.X, f2.Y) for g in doigts]), axis=0)
    f2.rgb[(s2[0] < 0) & (s2[1] < 0) & (s2[1] - s2[0] < m.TX * 0.9)] = np.array(m.CFG['trait'], np.float32)
    f2.a &= ~(paume(f2.X, f2.Y) < -m.TX)
    f2.nettoyer()
    f2.poser(cadre)
    return np.clip(cadre, 0, 255).astype(np.uint8)


def planche(sortie='mains.png'):
    Z = 8
    ims = [Image.fromarray(main_seule(f)).resize((90 * Z, 90 * Z), Image.NEAREST) for _, f in FORMES]
    W = Image.new('RGB', (len(ims) * 90 * Z, 90 * Z + 40), (20, 22, 18))
    d = ImageDraw.Draw(W)
    fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
    for k, ((nom, f), im) in enumerate(zip(FORMES, ims)):
        W.paste(im, (k * 90 * Z, 40))
        d.text((k * 90 * Z + 20, 6), '%d. %s' % (k + 1, nom), font=fnt, fill=(235, 235, 200))
    W.save(sortie)


if __name__ == '__main__':
    planche()

"""Fabrique les GIF de la demande 7 : python3 fabriquer7.py amplitude | joie | mange
Réutilise le GIF et les panneaux de projets/6 (fabriquer.py)."""
import json
import os
import sys

import numpy as np
from PIL import Image

import moteur7
import amplitude
sys.path.insert(0, moteur7.P6)
import fabriquer as fab6  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
FPS = 30
CFG = {
    'joie': {'fichier': 'joie-avant-apres.gif', 'avant': 'g2_apres', 'apres': 's7_g2_apres', 't0': 0.0, 'duree': 3.0},
    'mange': {'fichier': 'mange-avant-apres.gif', 'avant': 'mange', 'apres': 's7_mange', 't0': 3.0, 'duree': 3.6},
}


class Decale:
    """Rendu qui commence à t0 : on simule les images avant t0 (ressorts) sans les garder."""

    def __init__(self, rendu, t0):
        self.r, self.n0 = rendu, int(round(t0 * FPS))

    def demarrer(self):
        self.r.demarrer()
        for i in range(self.n0):
            self.r.scene.image(i / FPS, FPS)

    def image(self, i):
        sc = self.r.scene
        im = sc.image((self.n0 + i) / FPS, FPS)
        return np.clip(np.round(im), 0, 255).astype(np.uint8)


def avant_apres(nom):
    c = CFG[nom]
    n = int(round(c['duree'] * FPS))
    cotes = []
    for cle, fichier in (('avant', 'scene.json'), ('apres', 'scene7.json')):
        r = moteur7.Rendu7(c[cle], None, FPS, fichier)
        d = Decale(r, c['t0'])
        d.demarrer()
        cotes.append(d)
    images, yeux = [], {'avant': [], 'apres': []}
    for i in range(n):
        pan = []
        for cle, d, col in zip(('avant', 'apres'), cotes, ((230, 190, 120), (140, 235, 140))):
            img = d.image(i)
            sc = d.r.scene
            dd = sc.dernier
            yeux[cle].append(fab6.produire.compter_yeux(img, dd['rect_thomas'], [dd['rect_gant'], dd['rect_morceau'], dd.get('rect_bulle')]))
            pan.append(fab6.panneau(img, 'avant' if cle == 'avant' else 'après', col))
        w = pan[0].width
        comp = Image.new('RGB', (w * 2 + 4, pan[0].height), (16, 18, 14))
        comp.paste(pan[0], (0, 0))
        comp.paste(pan[1], (w + 4, 0))
        images.append(comp)
    sortie = os.path.join(ICI, c['fichier'])
    info = fab6.ecrire_gif(images, sortie)
    res = {'fichier': c['fichier'], 'images': n, 'octets': os.path.getsize(sortie), **info,
           'yeux_avant_images_pas_2': [i for i, v in enumerate(yeux['avant']) if v != 2],
           'yeux_apres_images_pas_2': [i for i, v in enumerate(yeux['apres']) if v != 2]}
    print(json.dumps(res, ensure_ascii=False))
    return res


def gif_amplitude():
    fab6.LIMITE = 6_500_000      # pas de limite de taille demandée pour ce GIF
    r = amplitude.RenduAmp()
    r.demarrer()
    images = []
    for i in range(int(amplitude.DUREE * FPS)):
        im = r.image(i)
        a = Image.fromarray(im[60:380, 0:340]).resize((850, 800), Image.NEAREST)
        images.append(a)
    sortie = os.path.join(ICI, 'amplitude-bras.gif')
    info = fab6.ecrire_gif(images, sortie)
    res = {'fichier': 'amplitude-bras.gif', 'images': len(images), 'octets': os.path.getsize(sortie), **info}
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    a = sys.argv[1]
    if a == 'amplitude':
        gif_amplitude()
    else:
        avant_apres(a)

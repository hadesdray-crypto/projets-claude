"""Produit les 4 GIF de la démo, mesure le temps de calcul et vérifie le décor.

Lancer : python3 produire_gifs.py
Sorties : 01-repos-vivant.gif ... 04-transition-sommeil.gif, mesures.json,
          verification/ (images extraites des GIF pour contrôle visuel).
"""
import json
import os
import platform
import time

import numpy as np
from PIL import Image

from moteur import Scene, chemin

IPS = 12.5            # images par seconde (80 ms par image, valeur exacte en GIF)
DUREE = 8.0           # secondes, boucle
N = int(IPS * DUREE)


def scenario_repos(s):
    s.jouer('thomas', 'repos')
    s.jouer('mouches', 'mouches')


def scenario_frotter(s):
    scenario_repos(s)
    s.declencher('frotter_la_tete', 1.5)


def scenario_os(s):
    scenario_repos(s)
    s.declencher('donner_un_os', 1.0)


def scenario_sommeil(s):
    scenario_repos(s)
    # endormissement à 0,5 s, sommeil, puis réveil doux pour que la boucle soit continue
    s.jouer('thomas', 'pose_sommeil', t0=0.5, fin=5.5)


GIFS = [
    ('01-repos-vivant.gif', scenario_repos),
    ('02-frotter-la-tete.gif', scenario_frotter),
    ('03-donner-un-os.gif', scenario_os),
    ('04-transition-sommeil.gif', scenario_sommeil),
]


def palette_commune(fond, images, rect):
    """Une seule palette pour tout le GIF : un pixel fixe garde le même indice
    dans toutes les images, donc le décor reste identique pixel pour pixel.
    La zone animée compte davantage dans le choix des couleurs (yeux, chair, os)."""
    x, y, w, h = rect
    morceaux = [im[y:y + h, x:x + w] for im in images]
    bande = np.concatenate(morceaux, axis=1)
    lignes = []
    for i in range(0, bande.shape[1], fond.shape[1]):
        m = bande[:, i:i + fond.shape[1]]
        if m.shape[1] < fond.shape[1]:
            m = np.pad(m, ((0, 0), (0, fond.shape[1] - m.shape[1]), (0, 0)), mode='edge')
        lignes.append(m)
    pile = np.concatenate([fond] + lignes, axis=0)
    return Image.fromarray(pile).quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                                          kmeans=3, dither=Image.Dither.NONE)


def main():
    os.makedirs(chemin('verification'), exist_ok=True)
    mesures = {'machine': f'{platform.processor() or platform.machine()} ({os.cpu_count()} cœurs), Python {platform.python_version()}',
               'ips': IPS, 'images_par_gif': N, 'gifs': {}}
    for nom, scenario in GIFS:
        s = Scene()
        scenario(s)
        s.image(0.0)                          # première image (chargements, caches)
        images, temps, pixels, rects = [], [], [], []
        for i in range(N):
            t = i / IPS
            t0 = time.perf_counter()
            cadre = s.image(t)
            temps.append(time.perf_counter() - t0)
            pixels.append(sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in s.sales))
            rects.append(list(s.sales))
            images.append(np.clip(np.round(cadre), 0, 255).astype(np.uint8))
        pal = palette_commune(np.round(s.fond).astype(np.uint8), images[::12], s.objets['thomas'].rect)
        frames = [Image.fromarray(im).quantize(palette=pal, dither=Image.Dither.NONE) for im in images]
        frames[0].save(chemin(nom), save_all=True, append_images=frames[1:], duration=int(1000 / IPS),
                       loop=0, optimize=False, disposal=1)

        # --- vérifications sur le GIF relu
        g = Image.open(chemin(nom))
        fond_q = np.asarray(Image.fromarray(np.round(s.fond).astype(np.uint8))
                            .quantize(palette=pal, dither=Image.Dither.NONE).convert('RGB'))
        n_lu, ecarts_decor = 0, 0
        for i in range(g.n_frames):
            g.seek(i)
            im = np.asarray(g.convert('RGB'))
            masque = np.ones(im.shape[:2], bool)
            for x0, y0, x1, y1 in rects[i]:
                masque[y0:y1, x0:x1] = False
            ecarts_decor += int((im[masque] != fond_q[masque]).any(1).sum())
            if i in (0, 20, 37, 50, 62, 75, 87):
                Image.fromarray(im).save(chemin('verification', f'{nom[:2]}-image{i:03d}.png'))
            n_lu += 1
        g.seek(0)
        ms = np.array(temps) * 1000
        mesures['gifs'][nom] = {
            'images': n_lu, 'duree_s': n_lu / IPS, 'taille': list(g.size),
            'taille_fichier_Mo': round(os.path.getsize(chemin(nom)) / 1e6, 2),
            'ms_par_image_moyenne': round(float(ms.mean()), 2),
            'ms_par_image_max': round(float(ms.max()), 2),
            'ms_par_image_min': round(float(ms.min()), 2),
            'pixels_recalcules_moyenne': int(np.mean(pixels)),
            'part_image_recalculee': round(float(np.mean(pixels)) / (640 * 480), 3),
            'pixels_hors_zones_animees_differents_du_decor': ecarts_decor,
        }
        print(nom, mesures['gifs'][nom])
    with open(chemin('mesures.json'), 'w', encoding='utf-8') as f:
        json.dump(mesures, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()

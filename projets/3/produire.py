"""Produit le film « Thomas mange » et les mesures de contrôle.

Sorties (dans ce dossier) :
  thomas-mange.mp4   H.264, 640x480, 24 i/s, 13 s, boucle
  thomas-mange.gif   même film en GIF (palette commune)
  cle-1.png … cle-6.png  images clés extraites du film
  mesures.json       temps de calcul, pixels du décor modifiés, continuité,
                     contact morceau/bouche, comptage des yeux
Lancer : python3 produire.py   (ffmpeg doit être installé)
"""
import io
import json
import math
import os
import subprocess
import tempfile
import time

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import moteur

ICI = os.path.dirname(os.path.abspath(__file__))
FPS = 24
CLES = [  # (fichier, instant en secondes, ce que montre l'image)
    ('cle-1.png', 0.50, 'repos'),
    ('cle-2.png', 2.96, 'le gant dépose le morceau'),
    ('cle-3.png', 4.75, 'la main saisit le morceau'),
    ('cle-4.png', 6.17, 'le morceau à la bouche (morsure)'),
    ('cle-5.png', 6.04, 'mâchoire ouverte'),
    ('cle-6.png', 10.25, 'avalé (renflement dans le cou, plus rien dans la main)'),
]


def compter_yeux(img, rect_gant):
    """Compte les taches claires de type « blanc d'œil » (crème ou blanc, pas les
    reflets vert clair du crâne) de plus de 40 pixels dans le rectangle de Thomas, hors gant. Les dents et les reflets sont
    plus petits. Attendu : 2 (l'œil de la tête et l'œil pendant)."""
    x0, y0, x1, y1 = 95, 35, 365, 345
    sub = img[y0:y1, x0:x1].astype(np.int32)
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    clair = (r > 205) & (g > 185) & (b > 130) & (r >= g - 4) & (r - g < 45)   # crème ou blanc, pas vert clair
    if rect_gant is not None:
        gx0, gy0, gx1, gy1 = rect_gant
        clair[max(gy0 - y0, 0):max(gy1 - y0, 0), max(gx0 - x0, 0):max(gx1 - x0, 0)] = False
    lab, n = ndi.label(ndi.binary_closing(clair, iterations=1))
    tailles = ndi.sum(clair, lab, range(1, n + 1))
    return int(sum(1 for t in tailles if t >= 40))


def main():
    scene = moteur.Scene(sequence='thomas_mange')
    seq = scene.sequence
    n = int(round(seq.duree * FPS))
    fond = np.round(scene.fond).astype(np.uint8)
    th = scene.thomas
    dossier = tempfile.mkdtemp()
    temps = []
    hors_zones = []
    sauts = []          # par image : déplacement maximal d'un point depuis l'image précédente
    par_passage = {}
    contact = []
    yeux = []
    prec = None
    cle_idx = {int(round(t * FPS)): (f, t, d) for f, t, d in CLES}
    t_pre = time.perf_counter()
    scene.prechauffer(FPS)
    t_pre = time.perf_counter() - t_pre
    for i in range(n + 1):           # image n = image 0 de la boucle suivante (contrôle de la jonction)
        t = i / FPS
        t0 = time.perf_counter()
        img = scene.image(t, FPS)
        dt = time.perf_counter() - t0
        im8 = np.clip(np.round(img), 0, 255).astype(np.uint8)
        d = scene.dernier
        if i < n:
            temps.append(dt)
            Image.fromarray(im8).save(os.path.join(dossier, 'i%04d.png' % i))
        # 1. décor : pixels différents du décor fixe hors des rectangles animés
        hors = np.ones(fond.shape[:2], bool)
        for (x0, y0, x1, y1) in d['sales']:
            hors[y0:y1, x0:x1] = False
        hors_zones.append(int((np.abs(im8.astype(int) - fond).sum(2)[hors] > 0).sum()))
        # 2. continuité : points suivis (articulations, sommets du bras, morceau, œil, gant)
        sq = d['squelette']
        sommets = th.transforme_sommets(sq, th.couches(d['parametres'], scene.parametres('thomas', t)[1]))
        pts = {'epaule': sq['E'], 'coude': sq['C'], 'poignet': sq['P'],
               'bout_des_doigts': th.point_main(d['parametres'], sq, [16, 2]),
               'oeil_pendant': d['oeil'], 'morceau': d['morceau'], 'gant': d['gant']}
        # champ du corps (déformation des pixels du corps et du visage)
        ch = th.champ(th.couches(d['parametres'], scene.parametres('thomas', t)[1]), th.boite_corps)[0]
        if prec is not None:
            sauts_i = {}
            for k, v in pts.items():
                if v is None or prec['pts'].get(k) is None or (k == 'gant' and (v[1] is None or v[1] < -60)):
                    continue
                sauts_i[k] = float(np.hypot(*(np.array(v, float) - np.array(prec['pts'][k], float))))
            sauts_i['sommets_du_bras'] = float(np.hypot(*(sommets - prec['sommets']).T).max())
            sauts_i['pixels_du_corps'] = float(np.hypot(*(ch - prec['champ']).transpose(2, 0, 1)).max())
            nom, cle_k = max(sauts_i.items(), key=lambda kv: kv[1])
            a, b, u = seq.pose_courante('thomas', (i - 0.5) / FPS)
            passage = '%s -> %s' % (a, b) if b else a
            sauts.append({'image': i, 't': round(t, 3), 'max': round(cle_k, 3), 'point': nom,
                          'detail': {k: round(v, 2) for k, v in sauts_i.items()}, 'passage': passage})
            pp = par_passage.setdefault(passage, {'max': 0.0, 'point': '', 'images': 0})
            pp['images'] += 1
            if cle_k > pp['max']:
                pp['max'], pp['point'] = round(cle_k, 3), nom
        prec = {'pts': {k: (None if v is None else np.array(v, float)) for k, v in pts.items()},
                'sommets': sommets, 'champ': ch}
        # 3. contact morceau / bouche : pixels du morceau posés sur l'intérieur de la bouche
        recouvre = float((d['alpha_morceau'] * d['bouche']).sum())
        contact.append(round(recouvre, 1))
        # 4. yeux
        rg = None
        if d['gant'][1] is not None and d['gant'][1] > -60:
            gx, gy = d['gant']
            rg = (int(gx - 48), 0, int(gx + 48), int(gy + 40))
        yeux.append(compter_yeux(im8, rg))
        if i in cle_idx:
            f, tc, desc = cle_idx[i]
            Image.fromarray(im8).save(os.path.join(ICI, f))
        if i == 0:
            premiere = im8.copy()
        if i == n:
            jonction = float(np.abs(im8.astype(int) - premiere.astype(int)).max())

    # --- film MP4 (H.264) et GIF
    mp4 = os.path.join(ICI, 'thomas-mange.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(dossier, 'i%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'slow',
                    '-movflags', '+faststart', mp4], check=True)
    gif = os.path.join(ICI, 'thomas-mange.gif')
    couleurs = 256
    while True:
        pal = os.path.join(dossier, 'palette.png')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(dossier, 'i%04d.png'),
                        '-vf', 'palettegen=max_colors=%d:stats_mode=full' % couleurs, pal], check=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(dossier, 'i%04d.png'),
                        '-i', pal, '-lavfi', 'paletteuse=dither=none:diff_mode=rectangle', '-loop', '0', gif], check=True)
        taille = os.path.getsize(gif)
        if taille <= 8 * 1024 * 1024 or couleurs <= 32:
            break
        couleurs //= 2

    # --- repli « images précalculées » : poids réel des rectangles de Thomas
    x, y, w, h = th.rect
    poids_png = 0
    for i in range(0, n):
        im = Image.open(os.path.join(dossier, 'i%04d.png' % i)).crop((x, y, x + w, y + h)).quantize(256)
        b = io.BytesIO()
        im.save(b, 'PNG', optimize=False)
        poids_png += b.tell()

    t_ms = np.array(temps) * 1000
    mesures = {
        'images': n, 'images_par_seconde': FPS, 'duree_s': seq.duree,
        'prechauffage_ressorts_s': round(t_pre, 3),
        'temps_ms': {'moyenne': round(float(t_ms.mean()), 1), 'mediane': round(float(np.median(t_ms)), 1),
                     'pire': round(float(t_ms.max()), 1), 'meilleur': round(float(t_ms.min()), 1)},
        'pixels_decor_modifies_hors_zones': {'total': int(sum(hors_zones)), 'max_par_image': int(max(hors_zones))},
        'jonction_boucle_ecart_max_niveau': jonction,
        'saut_max_par_image_px': max(s['max'] for s in sauts),
        'saut_max_par_passage': par_passage,
        'sauts_par_image': sauts,
        'contact_bouche_pixels': contact,
        'yeux_par_image': yeux,
        'gif': {'couleurs': couleurs, 'octets': os.path.getsize(gif)},
        'mp4': {'octets': os.path.getsize(mp4)},
        'repli_precalcul': {'rectangle': [w, h], 'images': n,
                            'octets_rgba_brut': n * w * h * 4, 'octets_palette_256_brut': n * w * h,
                            'octets_png_256_couleurs_mesure': poids_png},
        'cles': [{'fichier': f, 't': t, 'image': int(round(t * FPS)), 'montre': dsc} for f, t, dsc in CLES],
    }
    with open(os.path.join(ICI, 'mesures.json'), 'w', encoding='utf-8') as f:
        json.dump(mesures, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in mesures.items() if k not in ('sauts_par_image', 'contact_bouche_pixels', 'yeux_par_image', 'saut_max_par_passage')}, ensure_ascii=False, indent=1))
    print('images extraites dans', dossier)


if __name__ == '__main__':
    main()

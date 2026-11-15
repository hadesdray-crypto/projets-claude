"""Produit les films et les mesures de contrôle.

  python3 produire.py mange            une séquence : <nom>.mp4, <nom>-cle-1..4.png
  python3 produire.py mange caresse    plusieurs
  python3 produire.py journee          le film assemblé thomas-journee.mp4
  python3 produire.py tout             les cinq séquences puis le film
Sorties : MP4 H.264 640x480 à 30 i/s, 4 images clés PNG par séquence, un GIF allégé
de la séquence « mange », et mesures.json (une entrée par séquence, mise à jour).
ffmpeg doit être installé. Les images sont gardées dans /tmp/rendu/<nom>/.
"""
import json
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import moteur

ICI = os.path.dirname(os.path.abspath(__file__))
FPS = 30
JOURNEE = ['mange', 'caresse', 'joie', 'dort', 'reveil']
CLES = {   # instants (s) des 4 images clés de chaque séquence
    'mange': [(2.65, 'le gant dépose le morceau'), (4.59, 'la main saisit le morceau'),
              (6.26, 'le morceau est dans la bouche ouverte'), (8.0, 'il avale : renflement dans le cou, morceau entamé')],
    'caresse': [(1.2, 'le gant arrive'), (2.5, 'frisson sous la caresse'), (4.0, 'yeux mi-clos, sourire'), (6.0, 'le gant repart')],
    'joie': [(0.95, 'élan'), (1.2, 'saut, bras levés'), (3.5, 'bras en l\'air, bouche ouverte'), (5.9, 'les bras redescendent')],
    'dort': [(1.6, 'bâillement'), (3.6, 'accroupi'), (4.6, 'il s\'allonge'), (7.6, 'endormi, bulle Zzz')],
    'reveil': [(0.5, 'endormi'), (3.3, 'il se redresse'), (5.9, 'étirement'), (7.6, 'retour au repos')],
}


def compter_yeux(img, rect_thomas, exclus):
    """Compte les taches « blanc d'œil » (crème ou blanc) d'au moins 40 pixels dans
    la boîte de Thomas, hors gant et bulle. Les dents et les reflets sont plus
    petits. Attendu : 2 (œil de la tête + œil pendant), 1 si la paupière est fermée."""
    x0, y0, x1, y1 = rect_thomas
    sub = img[y0:y1, x0:x1].astype(np.int32)
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    clair = (r > 205) & (g > 185) & (b > 130) & (r >= g - 4) & (r - g < 45)
    for ex in exclus:
        if ex:
            clair[max(ex[1] - y0, 0):max(ex[3] - y0, 0), max(ex[0] - x0, 0):max(ex[2] - x0, 0)] = False
    lab, n = ndi.label(ndi.binary_closing(clair, iterations=1))
    tailles = ndi.sum(clair, lab, range(1, n + 1))
    return int(sum(1 for t in tailles if t >= 40))


def rendre(nom, sequence, boucle):
    """Calcule toutes les images, les enregistre et renvoie les mesures."""
    scene = moteur.Scene(sequence=sequence)
    seq = scene.sequence
    n = int(round(seq.duree * FPS))
    fond = np.round(scene.fond).astype(np.uint8)
    th = scene.thomas
    dossier = os.path.join('/tmp/rendu', nom)
    os.makedirs(dossier, exist_ok=True)
    for f in os.listdir(dossier):
        os.remove(os.path.join(dossier, f))
    t_pre = time.perf_counter()
    scene.prechauffer(FPS)
    t_pre = time.perf_counter() - t_pre
    temps, hors_zones, sauts, yeux, contact, surface = [], [], [], [], [], []
    aires = {}
    os_ecart = 0.0
    par_passage = {}
    surf_zone = []
    prec = None
    jonction = None
    longueurs0 = {b: o['longueur'] for b, o in th.os.items() if 'longueur' in o and b not in ('tronc',)}
    enfants = {'bras': 'avant_bras', 'avant_bras': 'main', 'cuisse_g': 'tibia_g', 'tibia_g': 'pied_g',
               'cuisse_d': 'tibia_d', 'tibia_d': 'pied_d', 'bras2': 'avant_bras2'}
    for i in range(n + 1):           # image n = image 0 de la boucle suivante (contrôle de la jonction)
        t = i / FPS
        t0 = time.perf_counter()
        img = scene.image(t, FPS)
        dt = time.perf_counter() - t0
        im8 = np.clip(np.round(img), 0, 255).astype(np.uint8)
        d = scene.dernier
        et = d['etat']
        if i < n:
            temps.append(dt)
            Image.fromarray(im8).save(os.path.join(dossier, 'i%04d.png' % i))
            # 1. décor : pixels différents du décor fixe hors des rectangles animés
            hors = np.ones(fond.shape[:2], bool)
            aire_zone = 0
            for (x0, y0, x1, y1) in d['sales']:
                hors[y0:y1, x0:x1] = False
            hors_zones.append(int((np.abs(im8.astype(int) - fond).sum(2)[hors] > 0).sum()))
            surf_zone.append(int((~hors).sum()))
            yeux.append(compter_yeux(im8, d['rect_thomas'], [d['rect_gant'], d['rect_morceau'], d.get('rect_bulle')]))
            contact.append(round(d['contact_bouche'], 1))
            surface.append(round(d['surface_morceau'], 1))
            for k, v in d['aires'].items():
                a = aires.setdefault(k, [1e9, -1e9])
                a[0], a[1] = min(a[0], v), max(a[1], v)
            # longueurs d'os : distance entre deux articulations, comparée au repos
            for b, e in enfants.items():
                os_ecart = max(os_ecart, abs(float(np.linalg.norm(et['J'][e] - et['J'][b])) -
                                             float(np.linalg.norm(th.os[e]['pivot'] + et['dec'][e] - th.os[b]['pivot']))))
        # 2. continuité : articulations, bout des doigts, œil, morceau, gant, sommets, pixels du corps
        pts = {'articulation ' + b: et['J'][b] for b in th.ordre}
        pts['bout des doigts'] = th.point_main(et, [16, 2])
        pts['œil pendant'] = d['oeil']
        pts['morceau'] = d['morceau']
        pts['gant'] = d['gant']
        sommets = {c['nom']: th.sommets(c, et) for c in th.calques if 'chaine' in c}
        ch = th.champ(d['couches'], th.boite_corps)[0]
        if prec is not None:
            s_i = {}
            for k, v in pts.items():
                if v is None or prec['pts'].get(k) is None:
                    continue
                s_i[k] = float(np.hypot(*(np.array(v, float) - prec['pts'][k])))
            for k, v in sommets.items():
                s_i['sommets ' + k] = float(np.hypot(*(v - prec['sommets'][k]).T).max())
            s_i['pixels du visage (zones)'] = float(np.hypot(*(ch - prec['champ']).transpose(2, 0, 1)).max())
            thomas_ = {k: v for k, v in s_i.items() if k not in ('gant', 'morceau')}
            pt_t, v_t = max(thomas_.items(), key=lambda kv: kv[1])
            s_, tl, _ = seq.locale((i - 0.5) / FPS)
            a, b, u = s_.pose_courante('thomas', tl)
            passage = '%s : %s -> %s' % (s_.nom, a, b) if b else '%s : %s' % (s_.nom, a)
            sauts.append({'image': i, 't': round(t, 3), 'thomas': round(v_t, 2), 'point': pt_t,
                          'gant': round(s_i.get('gant', 0.0), 2), 'morceau': round(s_i.get('morceau', 0.0), 2),
                          'oeil': round(s_i.get('œil pendant', 0.0), 2), 'passage': passage})
            pp = par_passage.setdefault(passage, {'thomas_max': 0.0, 'point': '', 'gant_max': 0.0, 'morceau_max': 0.0, 'images': 0})
            pp['images'] += 1
            if v_t > pp['thomas_max']:
                pp['thomas_max'], pp['point'] = round(v_t, 2), pt_t
            pp['gant_max'] = max(pp['gant_max'], round(s_i.get('gant', 0.0), 2))
            pp['morceau_max'] = max(pp['morceau_max'], round(s_i.get('morceau', 0.0), 2))
        prec = {'pts': {k: (None if v is None else np.array(v, float)) for k, v in pts.items()},
                'sommets': sommets, 'champ': ch}
        if i == 0:
            premiere = im8.copy()
        if i == n:
            jonction = float(np.abs(im8.astype(int) - premiere.astype(int)).max())
            jonction_moy = float(np.abs(im8.astype(int) - premiere.astype(int)).mean())
    # sauts : un point qui se déplace plus de 2,5 fois plus que la moyenne des deux images voisines (et de plus de 3 px)
    v = [s['thomas'] for s in sauts]
    brusques = [sauts[k]['image'] for k in range(1, len(v) - 1)
                if v[k] > 3.0 and v[k] > 2.5 * (v[k - 1] + v[k + 1]) / 2]
    # surface du morceau avant et après chaque morsure
    morsures = []
    for k in range(1, len(surface)):
        pass
    paliers = []
    for k, s in enumerate(surface):
        if s > 0 and (not paliers or abs(paliers[-1][1] - s) > 12):
            paliers.append([k, s])
    t_ms = np.array(temps) * 1000
    mesures = {
        'images': n, 'images_par_seconde': FPS, 'duree_s': seq.duree, 'boucle': boucle,
        'prechauffage_ressorts_s': round(t_pre, 2),
        'temps_ms': {'moyenne': round(float(t_ms.mean()), 1), 'mediane': round(float(np.median(t_ms)), 1),
                     'pire': round(float(t_ms.max()), 1), 'meilleur': round(float(t_ms.min()), 1)},
        'zone_animee_pixels': {'moyenne': int(np.mean(surf_zone)), 'max': int(max(surf_zone)), 'image_entiere': 640 * 480},
        'pixels_decor_modifies_hors_zones': {'total': int(sum(hors_zones)), 'max_par_image': int(max(hors_zones))},
        'jonction_fin_debut': {'ecart_max_niveau': jonction, 'ecart_moyen_niveau': round(jonction_moy, 4),
                               'deplacement_thomas_px': sauts[-1]['thomas']},
        'deplacement_max_par_image_px': {'thomas': max(s['thomas'] for s in sauts), 'gant': max(s['gant'] for s in sauts),
                                         'morceau': max(s['morceau'] for s in sauts), 'oeil_pendant': max(s['oeil'] for s in sauts)},
        'sauts_brusques_images': brusques,
        'ecart_max_longueur_os_px': round(os_ecart, 6),
        'rapport_surface_maillage_min_max': {k: [round(a[0], 4), round(a[1], 4)] for k, a in aires.items()},
        'yeux': {'images_a_2': yeux.count(2), 'images_a_1': yeux.count(1), 'images_a_0': yeux.count(0),
                 'images_a_3_ou_plus': sum(1 for y in yeux if y >= 3),
                 'images_pas_2': [k for k, y in enumerate(yeux) if y != 2]},
        'morceau': {'surface_px_par_palier': [{'image': k, 'surface_px': s} for k, s in paliers],
                    'contact_bouche_max_px': max(contact) if contact else 0,
                    'images_avec_contact': [k for k, c in enumerate(contact) if c > 20]},
        'par_passage': par_passage,
        'par_image': sauts,
        'surface_morceau_par_image': surface,
        'contact_bouche_par_image': contact,
    }
    return mesures, dossier, n


def encoder(dossier, mp4):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(dossier, 'i%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '15', '-preset', 'slow', '-r', str(FPS),
                    '-movflags', '+faststart', mp4], check=True)


def gif_allege(dossier, gif, limite=8 * 1024 * 1024):
    """GIF à 15 i/s ; on baisse le nombre de couleurs tant qu'il dépasse la limite."""
    couleurs = 128
    while True:
        pal = os.path.join(dossier, 'palette.png')
        src = ['-framerate', str(FPS), '-i', os.path.join(dossier, 'i%04d.png')]
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + src +
                       ['-vf', 'fps=15,palettegen=max_colors=%d:stats_mode=full' % couleurs, pal], check=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + src + ['-i', pal, '-lavfi',
                        'fps=15[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle', '-loop', '0', gif], check=True)
        if os.path.getsize(gif) <= limite or couleurs <= 16:
            break
        couleurs //= 2
    os.remove(pal)
    return {'couleurs': couleurs, 'images_par_seconde': 15, 'octets': os.path.getsize(gif)}


def main():
    demandes = sys.argv[1:] or ['tout']
    if demandes == ['tout']:
        demandes = JOURNEE + ['journee']
    fichier = os.path.join(ICI, 'mesures.json')
    tout = json.load(open(fichier, encoding='utf-8')) if os.path.exists(fichier) else {}
    for nom in demandes:
        if nom == 'journee':
            mesures, dossier, n = rendre('journee', JOURNEE, True)
            mp4 = os.path.join(ICI, 'thomas-journee.mp4')
            for k in ('par_image', 'surface_morceau_par_image', 'contact_bouche_par_image'):
                mesures.pop(k)
            mesures['sequences'] = JOURNEE
        else:
            boucle = moteur.Sequence(nom).boucle
            mesures, dossier, n = rendre(nom, nom, boucle)
            mp4 = os.path.join(ICI, nom + '.mp4')
            mesures['cles'] = []
            for k, (t, desc) in enumerate(CLES[nom], 1):
                i = int(round(t * FPS))
                f = '%s-cle-%d.png' % (nom, k)
                Image.open(os.path.join(dossier, 'i%04d.png' % i)).save(os.path.join(ICI, f))
                mesures['cles'].append({'fichier': f, 't': t, 'image': i, 'montre': desc})
            if nom == 'mange':
                mesures['gif'] = gif_allege(dossier, os.path.join(ICI, 'mange.gif'))
        encoder(dossier, mp4)
        mesures['mp4'] = {'fichier': os.path.basename(mp4), 'octets': os.path.getsize(mp4)}
        tout[nom] = mesures
        with open(fichier, 'w', encoding='utf-8') as f:
            json.dump(tout, f, ensure_ascii=False, indent=1)
        resume = {k: v for k, v in mesures.items() if k not in ('par_image', 'par_passage', 'surface_morceau_par_image', 'contact_bouche_par_image')}
        print(nom, json.dumps(resume, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()

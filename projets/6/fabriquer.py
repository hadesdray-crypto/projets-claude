"""Fabrique un GIF « avant / après » : python3 fabriquer.py <numéro>
Lit gifs.json (une entrée par GIF : séquences avant/après, effets globaux, durée),
rend les deux versions à 30 i/s, les place côte à côte avec une étiquette, écrit le GIF,
les images de contrôle (apercu/) et les mesures (mesures.json)."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import effets

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, effets.P5)
import produire  # noqa: E402  (compter_yeux)

FPS = 30
RECADRE = (0, 20, 400, 450)      # zone de la scène gardée (Thomas, gant, morceau)
ECHELLE = 0.8
BANDEAU = 26
LIMITE = 2_400_000                 # sous 2,5 Mo même en mégaoctets décimaux


def police(taille):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', None):
        try:
            return ImageFont.truetype(f, taille) if f else ImageFont.load_default(taille)
        except Exception:
            pass


def panneau(img, etiquette, couleur):
    x0, y0, x1, y1 = RECADRE
    im = Image.fromarray(img[y0:y1, x0:x1])
    im = im.resize((int((x1 - x0) * ECHELLE), int((y1 - y0) * ECHELLE)), Image.BOX)
    out = Image.new('RGB', (im.width, im.height + BANDEAU), (16, 18, 14))
    out.paste(im, (0, BANDEAU))
    d = ImageDraw.Draw(out)
    d.text((out.width // 2, BANDEAU // 2), etiquette, font=police(17), fill=couleur, anchor='mm')
    return out


def yeux(rendu, img):
    d = rendu.scene.dernier
    return produire.compter_yeux(img, d['rect_thomas'], [d['rect_gant'], d['rect_morceau'], d.get('rect_bulle')])


def main(num):
    cfg = [g for g in json.load(open(os.path.join(ICI, 'gifs.json'), encoding='utf-8')) if g['numero'] == num][0]
    n = int(round(cfg['duree'] * FPS))
    cotes = []
    for cle in ('avant', 'apres'):
        c = cfg[cle]
        r = effets.Rendu(c['sequence'], c.get('effets'), fps=FPS)
        if r.sequence.duree and abs(r.sequence.duree * FPS - (n - sum(g[1] for g in r.gels))) > 0.51:
            print('ATTENTION %s : durée séquence %.3f s, attendu %.3f s' % (cle, r.sequence.duree, (n - sum(g[1] for g in r.gels)) / FPS))
        r.demarrer()
        cotes.append(r)
    paires, mes = [], {'avant': {'yeux': [], 'decor_px': []}, 'apres': {'yeux': [], 'decor_px': []}}
    for i in range(n + 1):             # n+1 : la dernière sert au contrôle de jonction, pas au GIF
        pan = []
        for cle, r, col in zip(('avant', 'apres'), cotes, ((230, 190, 120), (140, 235, 140))):
            img = r.image(i)
            glob = r.marques[i]
            if i < n:
                mes[cle]['yeux'].append(yeux(r, img) if True else 0)
                hors = np.ones(img.shape[:2], bool)
                for (x0, y0, x1, y1) in r.rects:
                    hors[y0:y1, x0:x1] = False
                dif = int((np.abs(img.astype(int) - r.fond).sum(2)[hors] > 0).sum())
                mes[cle]['decor_px'].append(None if ('flash' in glob or 'secousse' in glob or 'miettes' in glob) else dif)
            pan.append(panneau(img, cfg['etiquettes'][cle] if 'etiquettes' in cfg else cle, col))
        w = pan[0].width
        comp = Image.new('RGB', (w * 2 + 4, pan[0].height), (16, 18, 14))
        comp.paste(pan[0], (0, 0))
        comp.paste(pan[1], (w + 4, 0))
        paires.append(comp)
    images = paires[:n]
    jonction = float(np.abs(np.asarray(paires[n]).astype(int) - np.asarray(paires[0]).astype(int)).mean())
    os.makedirs(os.path.join(ICI, 'apercu'), exist_ok=True)
    for k in sorted({0, n // 8, n // 4, 3 * n // 8, n // 2, 5 * n // 8, 3 * n // 4, 7 * n // 8} | set(cfg.get('apercu', []))):
        images[k].save(os.path.join(ICI, 'apercu', '%d-%03d.png' % (num, k)))
    sortie = os.path.join(ICI, cfg['fichier'])
    info = ecrire_gif(images, sortie)
    ent = {'fichier': cfg['fichier'], 'images': n, 'images_par_seconde': FPS, 'duree_s': cfg['duree'],
           'dimensions': list(images[0].size), 'octets': os.path.getsize(sortie), **info,
           'jonction_fin_debut_ecart_moyen_niveau': round(jonction, 3),
           'effets_globaux': {k: [i for i, m in cotes[1].marques.items() if k in m and i < n] for k in ('gel', 'flash', 'secousse', 'miettes')}}
    for cle in ('avant', 'apres'):
        y = mes[cle]['yeux']
        d = [v for v in mes[cle]['decor_px'] if v is not None]
        ent[cle] = {'yeux_images_a_2': y.count(2), 'yeux_images_pas_2': [i for i, v in enumerate(y) if v != 2],
                    'decor_modifie_hors_zones_px_max': max(d) if d else 0,
                    'images_sans_effet_global_comptees': len(d)}
    f = os.path.join(ICI, 'mesures.json')
    tout = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    tout[str(num)] = ent
    json.dump(tout, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(ent, ensure_ascii=False, indent=1))


def ecrire_gif(images, sortie):
    """Palette commune (pas de scintillement). Les pixels identiques à l'image précédente sont
    transparents (le GIF garde l'ancien) : le fichier est bien plus petit. On réduit les couleurs
    tant que le fichier dépasse 2,5 Mo."""
    cible = [images[k] for k in range(0, len(images), max(1, len(images) // 12))]
    mont = Image.new('RGB', (images[0].width, images[0].height * len(cible)))
    for k, im in enumerate(cible):
        mont.paste(im, (0, k * images[0].height))
    for coul in (200, 128, 96, 64, 48, 32):
        pal = mont.quantize(colors=coul, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        plein = [np.asarray(im.quantize(palette=pal, dither=Image.Dither.NONE)) for im in images]
        trames = []
        for k, a in enumerate(plein):
            a2 = a.copy()
            if k:
                a2[a == plein[k - 1]] = 255
            im = Image.fromarray(a2, 'P')
            im.putpalette(pal.getpalette()[:768])
            im.info['transparency'] = 255
            trames.append(im)
        trames[0].save(sortie, save_all=True, append_images=trames[1:], duration=[(30, 30, 40)[k % 3] for k in range(len(trames))],
                       loop=0, optimize=False, disposal=1, transparency=255)
        if os.path.getsize(sortie) <= LIMITE:
            return {'couleurs': coul, 'methode': 'pixels inchangés transparents'}
    return {'couleurs': coul, 'depasse_limite': True}


if __name__ == '__main__':
    main(int(sys.argv[1]))

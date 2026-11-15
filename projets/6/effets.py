"""Effets d'animation ajoutés pour la demande 6, SANS toucher au moteur de projets/5.

Ce module fait trois choses :
  1. il fait chercher les poses, séquences et recettes d'abord dans projets/6, puis dans projets/5 ;
  2. il ajoute au moteur une courbe de recette : « ressort » (oscillation amortie qui part d'instants donnés) ;
  3. il applique des effets GLOBAUX décrits en JSON (recettes/effets_*.json) autour du rendu du moteur :
       tenue / hit_stop (gel du temps), flash (éclair), secousse (décalage de l'image entière),
       miettes (petits morceaux projetés), pas_de_temps (rendu « sur 2 » ou « sur 3 »).
Les autres effets (micro_vie, squash_stretch, overshoot) sont de simples recettes « couches » du moteur.
"""
import json
import math
import os

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
P5 = os.path.join(os.path.dirname(ICI), '5')

import sys  # noqa: E402
sys.path.insert(0, P5)
import moteur  # noqa: E402


def _chemin(*p):
    for base in (ICI, P5):
        f = os.path.join(base, *p)
        if os.path.exists(f):
            return f
    return os.path.join(P5, *p)


moteur.chemin = _chemin

_courbe_origine = moteur.courbe_periodique


def _courbe(nom, t, duree, phase, c):
    if nom == 'ressort':
        # oscillation amortie : exp(-amortissement * d) * sin(2 pi * frequence * d), d = temps depuis l'instant.
        # Périodique (la queue de la période précédente se prolonge au début) : la boucle reste propre.
        f = ((t / duree + phase) % 1.0) * duree
        s = 0.0
        for inst in c.get('instants', [0.0]):
            d = f - inst
            if d < 0:
                d += duree
            s += math.exp(-c.get('amortissement', 6.0) * d) * math.sin(2 * math.pi * c.get('frequence', 4.0) * d)
        return s
    return _courbe_origine(nom, t, duree, phase, c)


moteur.courbe_periodique = _courbe


def lire_effets(nom):
    if not nom:
        return []
    with open(_chemin('recettes', nom + '.json'), encoding='utf-8') as f:
        return json.load(f)['effets']


class Rendu:
    """Rend un film image par image (30 i/s) pour une séquence et ses effets globaux.
    Les images de sortie portent l'indice i ; le temps d'animation est i/30 moins les images gelées."""

    def __init__(self, sequence, effets=None, fps=30):
        self.fps = fps
        self.effets = lire_effets(effets)
        self.scene = moteur.Scene(sequence=sequence)
        self.sequence = self.scene.sequence
        self.gels = [(int(round(e['a'] * fps)), int(e['images'])) for e in self.effets if e['type'] in ('hit_stop', 'tenue')]
        self.pas = next((int(e['images_par_pose']) for e in self.effets if e['type'] == 'pas_de_temps'), 1)
        self.fond = np.round(self.scene.fond).astype(np.uint8)
        self.derniere = None
        self.marques = {}           # indice -> liste d'effets globaux actifs sur cette image
        self.fenetre_anim = None

    def _index_anim(self, i):
        """Indice d'image d'animation et drapeau « gelée »."""
        gele = 0
        for d, n in self.gels:
            if i >= d + n:
                gele += n
            elif i >= d:
                return d - sum(nn for dd, nn in self.gels if dd < d), True
        return i - gele, False

    def demarrer(self):
        self.scene.prechauffer(self.fps if self.pas == 1 else self.fps / self.pas)
        self.deja = None

    def image(self, i):
        j, gele = self._index_anim(i)
        actifs = []
        if gele and self.derniere is not None:
            base = self.derniere
            actifs.append('gel')
        else:
            if self.pas > 1 and j % self.pas != 0 and self.derniere is not None:
                base = self.derniere
            else:
                t = (j // self.pas * self.pas) / self.fps
                im = self.scene.image(t, self.fps / self.pas if self.pas > 1 else self.fps)
                base = np.clip(np.round(im), 0, 255).astype(np.uint8)
                self.rects = list(self.scene.sales)
            self.derniere = base
        out = base.copy()
        out, glob = self._post(out, i)
        self.marques[i] = actifs + glob
        return out

    # ------------------------------------------------ effets globaux
    def _post(self, img, i):
        glob = []
        for e in self.effets:
            if 'a' not in e:
                continue
            d = int(round(e['a'] * self.fps))
            k = i - d
            if e['type'] == 'flash' and 0 <= k < e['images']:
                a = e.get('opacite', 0.8) * (1.0 - k / e['images'] * e.get('declin', 0.4))
                col = np.array(e.get('couleur', [255, 255, 255]), np.float32)
                img = np.round(img.astype(np.float32) * (1 - a) + col * a).astype(np.uint8)
                glob.append('flash')
            elif e['type'] == 'secousse' and 0 <= k < e['images']:
                f = 1.0 - k / e['images']          # s'éteint
                ph = k * e.get('rythme', 2.4)
                dx = int(round(e.get('amplitude_x', 4) * f * math.sin(ph * math.pi + 0.5)))
                dy = int(round(e.get('amplitude_y', 4) * f * math.sin(ph * math.pi * 1.3 + 1.1)))
                img = _decaler(img, dx, dy)
                glob.append('secousse')
            elif e['type'] == 'miettes' and 0 <= k < e['duree_images']:
                _miettes(img, e, k, self.scene.pal)
                glob.append('miettes')
        return img, glob


def _decaler(img, dx, dy):
    """Décale l'image entière en répétant le bord (pas de bande noire)."""
    h, w = img.shape[:2]
    p = max(abs(dx), abs(dy))
    if p == 0:
        return img
    gr = np.pad(img, ((p, p), (p, p), (0, 0)), mode='edge')
    return gr[p - dy:p - dy + h, p - dx:p - dx + w].copy()


def _miettes(img, e, k, pal):
    """Petits carrés de chair projetés depuis (x, y), tirés avec une graine fixe."""
    rng = np.random.RandomState(e.get('graine', 7))
    n = e.get('nombre', 6)
    h, w = img.shape[:2]
    for q in range(n):
        ang = math.radians(e.get('angle', -60) + rng.uniform(-e.get('ouverture', 55), e.get('ouverture', 55)))
        v = rng.uniform(e.get('vitesse_min', 3.0), e.get('vitesse_max', 7.0))
        tai = int(rng.choice(e.get('tailles', [4, 4, 6])))
        col = pal[e.get('couleurs', ['viande_clair', 'viande_moyen', 'viande_vif'])[q % len(e.get('couleurs', [0, 0, 0]))]]
        x = e['x'] + v * math.cos(ang) * k
        y = e['y'] + v * math.sin(ang) * k + 0.5 * e.get('gravite', 0.7) * k * k
        x0, y0 = int(round(x)), int(round(y))
        if 0 <= x0 < w - tai and 0 <= y0 < h - tai:
            img[y0:y0 + tai, x0:x0 + tai] = pal['trait_rouge']
            img[y0 + 1:y0 + tai - 1, x0 + 1:x0 + tai - 1] = col

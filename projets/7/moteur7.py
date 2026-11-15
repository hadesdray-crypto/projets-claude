"""Bras de Thomas pour la demande 7, SANS modifier le moteur de projets/5.

Le moteur (projets/5/moteur.py) et les effets (projets/6/effets.py) sont réutilisés tels quels.
Ce module ajoute :
  - la recherche des fichiers dans projets/7, puis projets/6, puis projets/5 ;
  - la classe Thomas7 : même squelette et même rendu du corps et des jambes, mais les deux bras
    (haut du bras, avant-bras, manche, main) sont dessinés par le code, en pixel art, à partir des
    positions des articulations calculées par le squelette (donc longueurs d'os constantes) ;
  - la classe Scene7 qui utilise Thomas7 et scene7.json.
Réglages : bras.json (rayons, couleurs, formes de main), scene7.json (os, épaules).
"""
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage as ndi

ICI = os.path.dirname(os.path.abspath(__file__))
P6 = os.path.join(os.path.dirname(ICI), '6')
P5 = os.path.join(os.path.dirname(ICI), '5')
sys.path.insert(0, P6)
import effets  # noqa: E402  (ajoute la courbe « ressort » et cherche dans projets/6)
import moteur  # noqa: E402


def _chemin(*p):
    for base in (ICI, P6, P5):
        f = os.path.join(base, *p)
        if os.path.exists(f):
            return f
    return os.path.join(P5, *p)


moteur.chemin = _chemin
effets._chemin = _chemin

CFG = json.load(open(os.path.join(ICI, 'bras.json'), encoding='utf-8'))
TX = int(CFG['texel'])
LUM = moteur.LUMIERE


# ---------------------------------------------------------------- toile en texels alignés sur l'écran
class Toile:
    """Grille de texels de 2 pixels alignée sur les pixels de l'écran (bords nets, pas de lissage).
    On y peint des formes données par des distances signées, en aplats : un contour d'un texel,
    ton clair côté lumière, ton sombre côté opposé, ton moyen ailleurs."""

    def __init__(self, x0, y0, x1, y1):
        x0, y0 = int(math.floor(x0)) // TX * TX, int(math.floor(y0)) // TX * TX
        x1, y1 = (int(math.ceil(x1)) + TX - 1) // TX * TX, (int(math.ceil(y1)) + TX - 1) // TX * TX
        self.x0, self.y0 = x0, y0
        nx, ny = (x1 - x0) // TX, (y1 - y0) // TX
        self.X = (x0 + (np.arange(nx) + 0.5) * TX)[None, :].repeat(ny, 0).astype(np.float32)
        self.Y = (y0 + (np.arange(ny) + 0.5) * TX)[:, None].repeat(nx, 1).astype(np.float32)
        self.rgb = np.zeros((ny, nx, 3), np.float32)
        self.a = np.zeros((ny, nx), bool)

    def peindre(self, f, tons, trait, ep=TX, bande=(5.0, 5.0)):
        sd = f(self.X, self.Y)
        dedans = sd < 0
        if not dedans.any():
            return dedans
        clair, moyen, sombre = (np.array(c, np.float32) for c in tons)
        vl = f(self.X + bande[0] * LUM[0], self.Y + bande[0] * LUM[1])
        vo = f(self.X - bande[1] * LUM[0], self.Y - bande[1] * LUM[1])
        coul = np.empty(sd.shape + (3,), np.float32)
        coul[:] = moyen
        coul[vl > -ep] = clair
        coul[vo > -ep] = sombre
        coul[sd > -ep] = np.array(trait, np.float32)
        self.rgb[dedans] = coul[dedans]
        self.a |= dedans
        return dedans

    def trait(self, f, couleur):
        m = f(self.X, self.Y) < 0
        m &= self.a
        self.rgb[m] = np.array(couleur, np.float32)

    def nettoyer(self):
        """Pixel art propre : plus aucun texel isolé, plus aucun trou d'un texel."""
        a = self.a
        lab, n = ndi.label(a, structure=np.ones((3, 3)))
        if n:
            taille = ndi.sum(a, lab, range(1, n + 1))
            for k in np.nonzero(taille < 3)[0]:
                a[lab == k + 1] = False
        trous = ndi.binary_fill_holes(a) & ~a
        lab, n = ndi.label(trous)
        for k in range(1, n + 1):
            m = lab == k
            if m.sum() <= 2:
                a[m] = True
                vois = ndi.binary_dilation(m, iterations=2) & a & ~m
                if vois.any():
                    self.rgb[m] = self.rgb[vois].mean(0)

    def poser(self, cadre):
        if not self.a.any():
            return None
        H, W = cadre.shape[:2]
        m = self.a.repeat(TX, 0).repeat(TX, 1)
        c = self.rgb.repeat(TX, 0).repeat(TX, 1)
        x0, y0 = self.x0, self.y0
        h, w = m.shape
        sx0, sy0 = max(0, -x0), max(0, -y0)
        ex, ey = min(w, W - x0), min(h, H - y0)
        if ex <= sx0 or ey <= sy0:
            return None
        zone = cadre[y0 + sy0:y0 + ey, x0 + sx0:x0 + ex]
        mm = m[sy0:ey, sx0:ex]
        zone[mm] = c[sy0:ey, sx0:ex][mm]
        return (x0 + sx0, y0 + sy0, x0 + ex, y0 + ey)


def sdf_cone(px, py, a, b, ra, rb):
    """Capsule dont le rayon varie linéairement de ra (en a) à rb (en b)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy + 1e-9
    h = np.clip(((px - a[0]) * dx + (py - a[1]) * dy) / L2, 0, 1)
    return np.hypot(px - a[0] - h * dx, py - a[1] - h * dy) - (ra + (rb - ra) * h)


def _niveau(f, formes):
    """Paramètres de main interpolés entre les formes (ouverte, relâchée, saisissante, fermée)."""
    cles = sorted(formes.values(), key=lambda s: s['f'])
    f = min(max(f, cles[0]['f']), cles[-1]['f'])
    for i in range(len(cles) - 1):
        a, b = cles[i], cles[i + 1]
        if a['f'] <= f <= b['f']:
            u = (f - a['f']) / (b['f'] - a['f'] + 1e-9)
            u = u * u * (3 - 2 * u)
            doigts = [[a['doigts'][k][j] * (1 - u) + b['doigts'][k][j] * u for j in range(3)] for k in range(3)]
            pouce = [a['pouce'][j] * (1 - u) + b['pouce'][j] * u for j in range(2)]
            return doigts, pouce
    return cles[-1]['doigts'], cles[-1]['pouce']


def formes_main(P, ang, f, taille=1.0):
    """Main en repère local (u vers les doigts, v de côté), centrée sur le poignet P et tournée de
    ang degrés. Renvoie (palette : liste de fonctions pour la paume et le pouce,
    doigts : liste de fonctions). Les doigts raccourcissent en se courbant."""
    doigts_p, pouce_p = _niveau(f, CFG['main']['formes'])
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    k = taille

    def loc(px, py):
        dx, dy = px - P[0], py - P[1]
        return (c * dx + s * dy) / k, (-s * dx + c * dy) / k

    larg = 1.0 - 0.18 * min(f / 0.4, 1.0) * (1 if f < 0.4 else 0)    # (la paume reste la même)
    paume_u0, paume_u1 = -4.0, 15.0 - 3.0 * max(0.0, f - 0.7)

    def paume(px, py):
        u, v = loc(px, py)
        # trapèze arrondi : poignet étroit, dos de la main large
        w0, w1 = 9.5, 12.0
        t = np.clip((u - paume_u0) / (paume_u1 - paume_u0), 0, 1)
        demi = w0 + (w1 - w0) * t
        qx = np.abs(v) - demi + 3.0
        qy = np.abs(u - (paume_u0 + paume_u1) / 2) - (paume_u1 - paume_u0) / 2 + 3.0
        d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - 3.0
        return d * k

    # pouce : deux phalanges parties du côté « haut » (v < 0)
    a0 = pouce_p[0]
    ca = pouce_p[1]
    p0 = (4.0, -9.0)
    e1 = (math.cos(math.radians(a0)), math.sin(math.radians(a0)))
    l1, l2 = 8.0, 6.5 - 1.5 * (ca / 62)
    m1 = (p0[0] + e1[0] * l1, p0[1] + e1[1] * l1)
    a1 = a0 + ca
    m2 = (m1[0] + math.cos(math.radians(a1)) * l2, m1[1] + math.sin(math.radians(a1)) * l2)

    def pouce(px, py):
        u, v = loc(px, py)
        return np.minimum(sdf_cone(u, v, p0, m1, 4.4, 3.8), sdf_cone(u, v, m1, m2, 3.8, 3.4)) * k

    # doigts : trois doigts de deux phalanges, courbés d'un angle k1 puis k2
    doigts = []
    for i, ((ecart, c1, c2), (bu, bv)) in enumerate(zip(doigts_p, ((14.0, -8.2), (15.0, 0.2), (14.0, 8.6)))):
        raccourci = 1.0 - 0.34 * (c1 / 90.0)
        la, lb = 9.2 * raccourci, 7.4 * raccourci
        dep = (bu, bv)
        d1 = ecart + c1 * 0.35 * (1 if i != 0 else 0.6)
        q1 = (dep[0] + la * math.cos(math.radians(d1)), dep[1] + la * math.sin(math.radians(d1)))
        d2 = ecart + c1 * 0.35 + c2 * 0.55
        q2 = (q1[0] + lb * math.cos(math.radians(d2)), q1[1] + lb * math.sin(math.radians(d2)))
        doigts.append(lambda px, py, a=dep, b=q1, cc=q2:
                      np.minimum(sdf_cone(*loc(px, py), a, b, 4.6, 4.1), sdf_cone(*loc(px, py), b, cc, 4.1, 3.5)) * k)
    return paume, pouce, doigts


def moteur_sd(f, toile):
    return f(toile.X, toile.Y)


class Thomas7(moteur.Thomas):
    """Thomas de projets/5 dont les bras sont remplacés par des bras dessinés par le code."""

    def __init__(self, objet, palette):
        super().__init__(objet, palette)
        self.cfg = CFG
        self.dernier_bras = {}

    # ------------------------------------------------ géométrie des bras
    def articulations(self, etat, cle):
        a = CFG['bras'][cle]['os']
        S, E, W = (etat['J'][o] for o in a)
        return np.array(S), np.array(E), np.array(W)

    def _formes_bras(self, S, E, W, cle):
        r = CFG['rayons']
        rs, re_, rw = r['epaule'], r['coude'], r['poignet']
        haut = lambda px, py: sdf_cone(px, py, S, E, rs, re_)
        avant = lambda px, py: sdf_cone(px, py, E, W, re_, rw)
        return haut, avant

    def dessiner_bras(self, cadre, p, etat, cle, morceau=None, info=None):
        """Dessine un bras complet. Ordre : bras + paume (un seul contour), manche, pli du coude,
        puis (si le bras tient quelque chose) l'objet, puis les doigts."""
        cfg = CFG['bras'][cle]
        S, E, W = self.articulations(etat, cle)
        osn = cfg['os']
        ang = self.os[osn[1]]['angle0'] + etat['A'][osn[2]]       # direction de l'avant-bras (degrés)
        fer = p.get(cfg['fermeture'], cfg['defaut_fermeture'])
        paume, pouce, doigts = formes_main(W, ang, fer, CFG['main']['taille'])
        haut, avant = self._formes_bras(S, E, W, cle)
        peau = (CFG['peau']['clair'], CFG['peau']['moyen'], CFG['peau']['sombre'])
        man = (CFG['manche']['clair'], CFG['manche']['moyen'], CFG['manche']['sombre'])
        trait = CFG['trait']
        r = CFG['rayons']
        marge = 52
        pts = np.array([S, E, W])
        x0, y0 = pts.min(0) - marge
        x1, y1 = pts.max(0) + marge
        dos = Toile(x0, y0, x1, y1)
        fin = Toile(x0, y0, x1, y1)
        # 1. peau : haut du bras + avant-bras + paume + pouce, d'un seul bloc
        dos.peindre(lambda x, y: np.minimum.reduce([haut(x, y), avant(x, y), paume(x, y), pouce(x, y)]), peau, trait)
        # 2. pli propre à l'intérieur du coude (plus le coude est plié, plus il est marqué)
        d1 = (E - S) / (np.linalg.norm(E - S) + 1e-9)
        d2 = (W - E) / (np.linalg.norm(W - E) + 1e-9)
        pli = math.degrees(math.acos(float(np.clip(d1 @ d2, -1, 1))))
        if pli > 18:
            b = d2 - d1
            nb = np.linalg.norm(b)
            if nb > 1e-6:
                b = b / nb
                lon = r['coude'] * (0.35 + 0.6 * min(pli / 110.0, 1.0))
                A0 = E + b * (r['coude'] * 0.18)
                A1 = E + b * lon
                dos.trait(lambda x, y: moteur.sdf_capsule(x, y, A0[0], A0[1], A1[0], A1[1], 0.9), trait)
        # 3. manche déchirée qui suit le haut du bras
        Ls = CFG['manche_longueur']
        e = E - S
        n_e = np.linalg.norm(e)
        u = e / n_e
        nv = np.array([-u[1], u[0]])
        sur = CFG['manche_surplus']
        rs, re_ = r['epaule'] + sur, r['coude'] + sur * 0.5

        def manche(x, y):
            t = ((x - S[0]) * u[0] + (y - S[1]) * u[1])
            v = ((x - S[0]) * nv[0] + (y - S[1]) * nv[1])
            rr = rs + (re_ - rs) * np.clip(t / n_e, 0, 1)
            lat = np.abs(v) - rr
            # bord bas déchiré : escalier de 2 texels de période irrégulière
            zig = 7.0 * (np.abs(((v + 40) / 9.0) % 2.0 - 1.0)) - 3.5 + 2.0 * np.sin(v * 0.6 + (1.7 if cle == 'avant' else 0.3))
            fin_t = n_e * Ls + zig
            d_cap = np.hypot(np.maximum(-t, 0), np.maximum(lat, 0)) + np.minimum(np.maximum(-t, lat), 0)
            d_bas = t - fin_t
            return np.maximum(np.where(t < 0, np.hypot(x - S[0], y - S[1]) - rs, lat), d_bas)
        dm = dos.peindre(manche, man, trait)
        # taches de la chemise (comme le gilet de Thomas) : texels fixes dans le repère de l'écran
        iu, iv = np.floor(dos.X / (3 * TX)), np.floor(dos.Y / (2 * TX))
        h = np.modf(np.sin(iu * 12.9898 + iv * 78.233) * 43758.5453)[0] % 1.0
        coeur = dm & (moteur_sd(manche, dos) < -TX)
        dos.rgb[coeur & (h < 0.22)] = np.array([102, 108, 78], np.float32)
        dos.rgb[coeur & (h > 0.86)] = np.array([96, 88, 68], np.float32)
        dos.nettoyer()
        r1 = dos.poser(cadre)
        rects = [r1]
        # 4. ce que le bras tient, entre la paume et les doigts
        if morceau is not None:
            rects.append(morceau(cadre, 1.0 - (info['levres'] if info is not None else 0.0)))
        # 5. doigts (par-dessus)
        fin.peindre_union = None
        sd = lambda x, y: np.minimum.reduce([f(x, y) for f in doigts])
        fin.peindre(sd, peau, trait)
        # trait d'un texel entre deux doigts qui se touchent
        allsd = [f(fin.X, fin.Y) for f in doigts]
        s2 = np.sort(np.stack(allsd), axis=0)
        entre = (s2[0] < 0) & (s2[1] < 0) & (s2[1] - s2[0] < TX * 0.9)
        fin.rgb[entre] = np.array(trait, np.float32)
        # la base des doigts est cachée par la paume : on garde seulement ce qui dépasse
        fin.a &= ~(paume(fin.X, fin.Y) < -TX)          # la base des doigts se fond dans la paume (pas de trait)
        fin.nettoyer()
        rects.append(fin.poser(cadre))
        return moteur.union(rects)

    # ------------------------------------------------ rendu
    def rendre(self, cadre, p, couches, etat, ressorts, morceau=None):
        H, W = cadre.shape[:2]
        rects = []
        info = {'bouche': np.zeros((H, W), np.float32), 'levres': np.zeros((H, W), np.float32), 'aires': {}}
        tige_devant = p.get('physique.tige_devant', 0.0) >= 0.5
        for c in self.calques:
            nom = c['nom']
            if 'chaine' in c:
                rects.append(self._calque_chaine(c, cadre, couches, etat, info, H, W))
            elif nom == 'tige':
                if not tige_devant:
                    rects.append(self._tige(cadre, ressorts, p))
            elif nom == 'bras7':
                self.dernier_bras = {}
                rects.append(self.dessiner_bras(cadre, p, etat, 'arriere', None, info))
                rects.append(self.dessiner_bras(cadre, p, etat, 'avant', morceau, info))
        if tige_devant:
            rects.append(self._tige(cadre, ressorts, p))
        return moteur.union(rects), info

    def _calque_chaine(self, c, cadre, couches, etat, info, H, W):
        """Calque à maillage (corps, jambes) : identique à moteur.Thomas.rendre."""
        nom = c['nom']
        if nom == 'corps':
            img = self.couleurs(self.corps, couches)
            x0, y0, x1, y1 = self.boite_corps
            ch = self.champ(couches, self.boite_corps)
            qx, qy = self.inverser(self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1], ch)
            tex = moteur.echantillonner(img, qx, qy)
        else:
            tex = c['tex']
        D = self.sommets(c, etat)
        T = c['tris']
        ox, oy = c['org']
        if np.abs(D - c['V']).max() < 1e-4:
            rect = moteur.composer(cadre, tex[..., :4], ox, oy)
            if nom == 'corps' and rect:
                a0, b0, a1, b1 = rect
                info['bouche'][b0:b1, a0:a1] = tex[b0 - oy:b1 - oy, a0 - ox:a1 - ox, 4]
                info['levres'][b0:b1, a0:a1] = tex[b0 - oy:b1 - oy, a0 - ox:a1 - ox, 5]
            return rect
        res = moteur.rasteriser(D, c['V'] - [ox, oy], T, H, W)
        if res is None:
            return None
        X0, Y0, qx, qy, couvert = res
        r = moteur.echantillonner(tex, qx, qy) * couvert[..., None]
        Y1, X1 = Y0 + qx.shape[0], X0 + qx.shape[1]
        zone = cadre[Y0:Y1, X0:X1]
        zone[:] = r[..., :3] + zone * (1 - r[..., 3:4])
        if nom == 'corps':
            info['bouche'][Y0:Y1, X0:X1] = r[..., 4]
            info['levres'][Y0:Y1, X0:X1] = r[..., 5]
            ys, xs = np.nonzero(r[..., 3] > 0)
            if len(ys):
                return (X0 + int(xs.min()), Y0 + int(ys.min()), X0 + int(xs.max()) + 1, Y0 + int(ys.max()) + 1)
            return None
        return (X0, Y0, X1, Y1)


class Scene7(moteur.Scene):
    def __init__(self, fichier='scene7.json', sequence=None):
        super().__init__(fichier, sequence)
        self.thomas = Thomas7(self.objets['thomas'], self.pal)


class Rendu7(effets.Rendu):
    """Comme effets.Rendu (projets/6) mais sur la scène de projets/7 (ou une autre : fichier)."""

    def __init__(self, sequence, effets_=None, fps=30, fichier='scene7.json'):
        self.fps = fps
        self.effets = effets.lire_effets(effets_)
        self.scene = Scene7(fichier, sequence) if fichier == 'scene7.json' else moteur.Scene(fichier, sequence)
        self.sequence = self.scene.sequence
        self.gels = [(int(round(e['a'] * fps)), int(e['images'])) for e in self.effets if e['type'] in ('hit_stop', 'tenue')]
        self.pas = next((int(e['images_par_pose']) for e in self.effets if e['type'] == 'pas_de_temps'), 1)
        self.fond = np.round(self.scene.fond).astype(np.uint8)
        self.derniere = None
        self.marques = {}
        self.fenetre_anim = None

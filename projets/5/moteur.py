"""Moteur d'animation par zones, version 3 (la journée de Thomas le zombie).

Principe (inchangé) :
  - le décor est fixe ; à chaque image on remet le décor seulement dans les
    rectangles dessinés à l'image précédente, puis on recalcule les rectangles
    des objets animés (Thomas, gant, morceau, mouches, bulle, poussières, reflet) ;
  - un objet devient animé par son composant « animable » (scene.json) ;
  - le mouvement vient de cartes de zones (niveaux de gris, sous-pixel) et d'un squelette ;
  - tout est donnée : poses (poses/*.json), séquences (sequences/*.json),
    recettes (recettes/*.json), actions (actions.json) ;
  - le moteur calcule seul l'entre-deux (courbes douces, spline d'Hermite monotone).

Nouveau dans la version 3 :
  - squelette complet (bassin, tronc, cou, deux jambes, deux bras) ; chaque calque
    est un maillage de triangles déformé par « rotation progressive » le long de
    sa chaîne d'os (le volume est conservé aux articulations, pas de torsion) ;
  - jambes posées par cinématique inverse (les pieds restent où la pose les met) ;
  - bouche à deux niveaux : intérieur et lèvres ; un objet tenu passe entre les deux ;
  - objets dessinés par le code en « texels » de 2 pixels, aplats de la palette de
    Thomas, contour sombre de 2 pixels, aucun dégradé (passe de style) ;
  - plusieurs séquences enchaînées sur une même ligne de temps (classe Enchainement).
Bibliothèques : numpy, scipy, Pillow (libres).
"""
import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ICI = os.path.dirname(os.path.abspath(__file__))
LUMIERE = (-0.42, -0.91)          # direction d'où vient la lumière (haut gauche), comme sur Thomas
TEXEL = 2.0                       # taille d'un « pixel » du dessin d'origine, en pixels d'écran


def chemin(*p):
    return os.path.join(ICI, *p)


def lire_json(p):
    with open(chemin(p), encoding='utf-8') as f:
        return json.load(f)


# ================================================================ courbes
def lissage(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def lissage_v(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def facilite(nom, u):
    """Courbes de passage d'une pose à la suivante (u de 0 à 1)."""
    u = min(max(u, 0.0), 1.0)
    if nom == 'lineaire':
        return u
    if nom == 'doux':                       # accélération puis décélération douces
        return u * u * u * (u * (6 * u - 15) + 10)
    if nom == 'entree':                     # démarre doucement, finit vite
        return u * u * u
    if nom == 'sortie':                     # démarre vite, finit doucement
        return 1 - (1 - u) ** 3
    if nom == 'chute':                      # chute libre (accélération constante)
        return u * u
    if nom == 'rebond':                     # dépasse un peu puis revient
        return 1 - math.cos(u * math.pi * 1.5) * math.exp(-4.5 * u) if u < 1 else 1.0
    raise ValueError('courbe inconnue : ' + nom)


def courbe_periodique(nom, t, duree, phase, c):
    """Courbes des recettes (périodiques, période « duree »)."""
    if nom == 'constante':
        return 1.0
    x = t / duree + phase
    if nom == 'sinus':
        return math.sin(2 * math.pi * x)
    if nom == 'sinus_positif':
        return 0.5 - 0.5 * math.cos(2 * math.pi * x)
    if nom == 'souffle':                    # inspiration plus courte que l'expiration
        f = x - math.floor(x)
        k = c.get('inspire', 0.4)
        return (0.5 - 0.5 * math.cos(math.pi * f / k)) if f < k else (0.5 + 0.5 * math.cos(math.pi * (f - k) / (1 - k)))
    if nom == 'bruit':
        return (math.sin(2 * math.pi * x) * 0.55 + math.sin(2 * math.pi * (3 * x + 0.31)) * 0.3
                + math.sin(2 * math.pi * (7 * x + 0.67)) * 0.15)
    if nom == 'clignement':                 # instants irréguliers (en secondes) dans la période
        largeur = c.get('largeur', 0.2)
        f = (x - math.floor(x)) * duree
        for inst in c.get('instants', [0.0]):
            if 0 <= f - inst < largeur:
                return math.sin(math.pi * (f - inst) / largeur)
        return 0.0
    raise ValueError('courbe inconnue : ' + nom)


# ================================================================ poses et séquences
def aplatir(d, prefixe=''):
    """{"zones": {"machoire": 0.5}} -> {"zones.machoire": 0.5}"""
    out = {}
    for k, v in d.items():
        if k in ('nom', 'description'):
            continue
        cle = prefixe + k
        if isinstance(v, dict):
            out.update(aplatir(v, cle + '.'))
        else:
            out[cle] = v
    return out


def charger_pose(nom):
    return aplatir(lire_json(os.path.join('poses', nom + '.json')))


class Piste:
    """Une suite de clés (poses) pour un objet. Chaque entrée :
       {"pose": nom | "valeurs": {...}, "duree": s, "courbe": nom, "tenir": s}
       « duree » = temps du passage depuis la clé précédente, « tenir » = arrêt
       sur la pose. Les paramètres absents d'une pose gardent leur valeur."""

    def __init__(self, entrees):
        self.cles = []
        courant = {}
        t = 0.0
        for i, e in enumerate(entrees):
            vals = charger_pose(e['pose']) if 'pose' in e else {}
            vals.update(aplatir(e.get('valeurs', {})))
            courant = {**courant, **vals}
            t += e.get('duree', 0.0) if i > 0 else 0.0
            arrivee = t
            t += e.get('tenir', 0.0)
            self.cles.append({'arrivee': arrivee, 'depart': t, 'courbe': e.get('courbe', 'spline'),
                              'v': dict(courant), 'nom': e.get('pose', e.get('nom', '?'))})
        self.duree = t
        noms = set()
        for c in self.cles:
            noms |= set(c['v'])
        for c in self.cles:                 # une valeur posée plus tard vaut aussi avant
            for n in noms:
                if n not in c['v']:
                    c['v'][n] = next(k['v'][n] for k in self.cles if n in k['v'])
        self.noms = noms
        self.pentes = {n: self._pentes(n) for n in noms if self._numerique(n)}

    def _numerique(self, n):
        v = self.cles[0]['v'][n]
        return isinstance(v, (int, float)) or (isinstance(v, list) and all(isinstance(x, (int, float)) for x in v))

    def _pentes(self, n):
        """Pente à chaque clé pour la spline d'Hermite monotone (Fritsch-Carlson) :
        nulle si la pose est tenue, si c'est un extrémum ou si le passage voisin
        n'est pas une spline ; sinon moyenne harmonique des pentes voisines,
        ce qui donne un mouvement continu à travers les poses intermédiaires."""
        K = self.cles
        vals = [np.atleast_1d(np.array(k['v'][n], np.float64)) for k in K]
        res = []
        for i in range(len(K)):
            m = np.zeros_like(vals[i])
            if 0 < i < len(K) - 1 and K[i]['depart'] == K[i]['arrivee'] \
                    and K[i]['courbe'] == 'spline' and K[i + 1]['courbe'] == 'spline':
                d0 = (vals[i] - vals[i - 1]) / max(K[i]['arrivee'] - K[i - 1]['depart'], 1e-6)
                d1 = (vals[i + 1] - vals[i]) / max(K[i + 1]['arrivee'] - K[i]['depart'], 1e-6)
                ok = d0 * d1 > 0
                m = np.where(ok, 2.0 / (1.0 / np.where(ok, d0, 1) + 1.0 / np.where(ok, d1, 1)), 0.0)
            res.append(m)
        return res

    def valeurs(self, t):
        K = self.cles
        if t <= K[0]['arrivee']:
            return dict(K[0]['v']), 0, 0.0
        for i in range(len(K) - 1):
            a, b = K[i], K[i + 1]
            if t < a['depart']:
                return dict(a['v']), i, 0.0
            if t < b['arrivee']:
                T = b['arrivee'] - a['depart']
                u = (t - a['depart']) / T
                out = {}
                for n in self.noms:
                    va, vb = a['v'][n], b['v'][n]
                    if n not in self.pentes:          # texte (attache…) : change à l'arrivée
                        out[n] = va
                        continue
                    A, B = np.array(va, np.float64), np.array(vb, np.float64)
                    if b['courbe'] == 'spline':
                        h00 = 2 * u ** 3 - 3 * u ** 2 + 1
                        h10 = u ** 3 - 2 * u ** 2 + u
                        h01 = -2 * u ** 3 + 3 * u ** 2
                        h11 = u ** 3 - u ** 2
                        m0 = self.pentes[n][i].reshape(A.shape)
                        m1 = self.pentes[n][i + 1].reshape(A.shape)
                        r = h00 * A + h10 * T * m0 + h01 * B + h11 * T * m1
                    else:
                        r = A + (B - A) * facilite(b['courbe'], u)
                    out[n] = r.tolist() if isinstance(va, list) else float(r)
                return out, i, u
        return dict(K[-1]['v']), len(K) - 1, 0.0


class Sequence:
    def __init__(self, nom):
        d = lire_json(os.path.join('sequences', nom + '.json'))
        self.nom = nom
        self.d = d
        self.pistes = {o: Piste(e) for o, e in d['pistes'].items()}
        self.duree = d.get('duree') or max(p.duree for p in self.pistes.values())
        self.recettes = d.get('recettes', {})
        self.boucle = bool(d.get('boucle'))

    def locale(self, t):
        """(séquence, temps local, début) pour un temps global."""
        if self.boucle:
            return self, t % self.duree, t - (t % self.duree)
        return self, min(max(t, 0.0), self.duree), 0.0

    def valeurs(self, objet, tl):
        p = self.pistes.get(objet)
        return {} if p is None else p.valeurs(tl)[0]

    def pose_courante(self, objet, tl):
        p = self.pistes[objet]
        v, i, u = p.valeurs(tl)
        return p.cles[i]['nom'], (p.cles[i + 1]['nom'] if i + 1 < len(p.cles) else None), u


class Enchainement:
    """Plusieurs séquences jouées l'une après l'autre sur une même ligne de temps
    (le film de la journée). La dernière pose de l'une est la première de la suivante."""

    def __init__(self, noms):
        self.seqs = [Sequence(n) for n in noms]
        self.debuts = [0.0]
        for s in self.seqs[:-1]:
            self.debuts.append(self.debuts[-1] + s.duree)
        self.duree = self.debuts[-1] + self.seqs[-1].duree
        self.nom = '+'.join(noms)
        self.boucle = True

    def locale(self, t):
        tm = t % self.duree
        for s, d in zip(reversed(self.seqs), reversed(self.debuts)):
            if tm >= d:
                return s, min(tm - d, s.duree), t - (tm - d)
        return self.seqs[0], 0.0, t


# ================================================================ outils image
def echantillonner(img, qx, qy):
    """Lecture bilinéaire (sous-pixel) de img (h,w,c) aux positions qx,qy ; 0 hors image."""
    coords = np.array([qy, qx], dtype=np.float32)
    canaux = [ndi.map_coordinates(img[..., c], coords, order=1, mode='constant', cval=0.0, prefilter=False)
              for c in range(img.shape[2])]
    return np.stack(canaux, -1)


def composer(cadre, rgba_pm, x0, y0):
    """Pose un RGBA prémultiplié (float) en (x0, y0) ; renvoie le rectangle touché."""
    h, w = rgba_pm.shape[:2]
    H, W = cadre.shape[:2]
    a0, b0 = max(x0, 0), max(y0, 0)
    a1, b1 = min(x0 + w, W), min(y0 + h, H)
    if a0 >= a1 or b0 >= b1:
        return None
    part = rgba_pm[b0 - y0:b1 - y0, a0 - x0:a1 - x0]
    zone = cadre[b0:b1, a0:a1]
    zone[:] = part[..., :3] + zone * (1 - part[..., 3:4])
    return (a0, b0, a1, b1)


def coller_sous_pixel(cadre, sprite_pm, x, y, opacite=1.0):
    h, w = sprite_pm.shape[:2]
    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - ix, y - iy
    s = np.zeros((h + 1, w + 1, 4), np.float32)
    s[:h, :w] += sprite_pm * (1 - fx) * (1 - fy)
    s[:h, 1:] += sprite_pm * fx * (1 - fy)
    s[1:, :w] += sprite_pm * (1 - fx) * fy
    s[1:, 1:] += sprite_pm * fx * fy
    return composer(cadre, s * opacite, ix, iy)


def charger_rgba(p):
    a = np.asarray(Image.open(chemin(p)).convert('RGBA')).astype(np.float32)
    a[..., 3] /= 255.0
    a[..., :3] *= a[..., 3:4]
    return a


def charger_gris(p):
    return np.asarray(Image.open(chemin(p)).convert('L')).astype(np.float32) / 255.0


def rot(a_deg):
    a = math.radians(a_deg)
    return math.cos(a), math.sin(a)


def tourner(px, py, a_deg):
    c, s = rot(a_deg)
    return c * px - s * py, s * px + c * py


def union(rects):
    rects = [r for r in rects if r]
    if not rects:
        return None
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


# ---------------------------------------------------------------- champs de distance
def sdf_capsule(px, py, ax, ay, bx, by, r):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy + 1e-9
    h = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1)
    return np.hypot(px - ax - h * dx, py - ay - h * dy) - r


def sdf_ellipse(px, py, cx, cy, rx, ry):
    return (np.hypot((px - cx) / rx, (py - cy) / ry) - 1) * min(rx, ry)


def sdf_boite(px, py, cx, cy, hx, hy, r=0.0):
    qx, qy = np.abs(px - cx) - hx + r, np.abs(py - cy) - hy + r
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


# ---------------------------------------------------------------- passe de style « pixel art »
class Texels:
    """Petite toile en texels de 2 pixels, dans un repère local (u, v) en pixels.
    On y peint des formes (champs de distance) en aplats : contour sombre d'un
    texel, ton clair du côté de la lumière, ton sombre du côté opposé, ton moyen
    ailleurs. Aucun dégradé. La toile est ensuite posée dans l'image avec une
    position et un angle au sous-pixel, comme les pixels de Thomas."""

    def __init__(self, u0, v0, u1, v1, angle_monde=0.0):
        self.u0, self.v0 = u0, v0
        nu = int(math.ceil((u1 - u0) / TEXEL))
        nv = int(math.ceil((v1 - v0) / TEXEL))
        self.V, self.U = np.mgrid[0:nv, 0:nu].astype(np.float32)
        self.U = u0 + (self.U + 0.5) * TEXEL
        self.V = v0 + (self.V + 0.5) * TEXEL
        self.rgb = np.zeros((nv, nu, 3), np.float32)
        self.a = np.zeros((nv, nu), np.float32)
        # la lumière vient du haut gauche du monde : on l'exprime dans le repère local
        self.lx, self.ly = tourner(LUMIERE[0], LUMIERE[1], -angle_monde)

    def peindre(self, f, tons, trait, ep=TEXEL, bande=(4.0, 3.0), contour=True, grain=0.0):
        """f(U, V) -> distance signée (px). tons = (clair, moyen, sombre).
        grain : part des texels du ton moyen remplacés par de petites taches
        claires ou sombres (peau marbrée de Thomas), fixes dans le repère local."""
        sd = f(self.U, self.V)
        dedans = sd < 0
        if not dedans.any():
            return dedans
        clair, moyen, sombre = (np.array(c, np.float32) for c in tons)
        vers_lumiere = f(self.U + bande[0] * self.lx, self.V + bande[0] * self.ly)
        vers_ombre = f(self.U - bande[1] * self.lx, self.V - bande[1] * self.ly)
        coul = np.empty(sd.shape + (3,), np.float32)
        coul[:] = moyen
        if grain > 0:
            iu, iv = np.floor((self.U + 0.37 * self.V) / (3 * TEXEL)), np.floor(self.V / (2 * TEXEL))
            h = np.modf(np.sin(iu * 12.9898 + iv * 78.233) * 43758.5453)[0] % 1.0
            coul[h < grain] = clair
            coul[h > 1 - grain] = sombre
        coul[vers_lumiere > -ep] = clair
        coul[vers_ombre > -ep] = sombre
        if contour:
            coul[sd > -ep] = np.array(trait, np.float32)
        self.rgb[dedans] = coul[dedans]
        self.a[dedans] = 1.0
        return dedans

    def peindre_union(self, formes, tons, trait, ep=TEXEL, bande=(4.0, 3.0), grain=0.0):
        """Plusieurs formes voisines (des doigts) peintes d'un bloc : un seul contour
        autour de l'ensemble, et un trait d'un texel entre deux formes qui se touchent."""
        dedans = self.peindre(lambda u, v: np.minimum.reduce([f(u, v) for f in formes]), tons, trait, ep, bande, grain=grain)
        if len(formes) > 1:
            sd = np.sort(np.stack([f(self.U, self.V) for f in formes]), axis=0)
            entre = dedans & (sd[1] - sd[0] < TEXEL * 0.55) & (sd[1] < 0)
            self.aplat(entre, trait)
        return dedans

    def aplat(self, masque, couleur):
        self.rgb[masque] = np.array(couleur, np.float32)
        self.a[masque] = 1.0

    def effacer(self, masque):
        self.a[masque] = 0.0

    def surface(self):
        return float(self.a.sum()) * TEXEL * TEXEL

    def poser(self, cadre, x, y, angle, masque=None, opacite=1.0):
        """Pose la toile : son origine locale (0, 0) va en (x, y), tournée de « angle ».
        masque : image (H, W) qui multiplie l'opacité (ce qui est caché). Renvoie
        (rectangle, alpha monde dans ce rectangle)."""
        if self.a.max() <= 0:
            return None, None
        t = int(TEXEL)
        tex = np.dstack([self.rgb * self.a[..., None], self.a]).repeat(t, 0).repeat(t, 1)
        h, w = tex.shape[:2]
        coins = [(self.u0, self.v0), (self.u0 + w, self.v0), (self.u0, self.v0 + h), (self.u0 + w, self.v0 + h)]
        cx = [x + tourner(u, v, angle)[0] for u, v in coins]
        cy = [y + tourner(u, v, angle)[1] for u, v in coins]
        H, W = cadre.shape[:2]
        x0, x1 = max(int(math.floor(min(cx))) - 1, 0), min(int(math.ceil(max(cx))) + 2, W)
        y0, y1 = max(int(math.floor(min(cy))) - 1, 0), min(int(math.ceil(max(cy))) + 2, H)
        if x0 >= x1 or y0 >= y1:
            return None, None
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        c, s = rot(angle)
        dx, dy = gx - x, gy - y
        u = c * dx + s * dy - self.u0 - 0.5
        v = -s * dx + c * dy - self.v0 - 0.5
        r = echantillonner(tex, u, v) * opacite
        if masque is not None:
            r = r * masque[y0:y1, x0:x1, None]
        zone = cadre[y0:y1, x0:x1]
        zone[:] = r[..., :3] + zone * (1 - r[..., 3:4])
        return (x0, y0, x1, y1), r[..., 3]


# ---------------------------------------------------------------- maillages
def grille(x0, y0, x1, y1, pas, plein=None):
    """Grille de triangles sur le rectangle (monde). plein : masque (H, W) des
    pixels à couvrir (les carreaux vides sont ignorés)."""
    nx = int(math.ceil((x1 - x0) / pas)) + 1
    ny = int(math.ceil((y1 - y0) / pas)) + 1
    vx = x0 + np.arange(nx) * pas
    vy = y0 + np.arange(ny) * pas
    VX, VY = np.meshgrid(vx, vy)
    tris = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            if plein is not None:
                cx0, cy0 = int(vx[i]), int(vy[j])
                if not plein[max(cy0, 0):cy0 + int(pas) + 1, max(cx0, 0):cx0 + int(pas) + 1].any():
                    continue
            v00, v10 = j * nx + i, j * nx + i + 1
            v01, v11 = (j + 1) * nx + i, (j + 1) * nx + i + 1
            tris.append((v00, v10, v11))
            tris.append((v00, v11, v01))
    return np.stack([VX.ravel(), VY.ravel()], 1).astype(np.float64), np.array(tris, np.int32)


def rasteriser(D, S, tris, H, W):
    """Pour chaque pixel couvert par les triangles déformés D, la position source
    (interpolée depuis S). Les triangles sont pris dans l'ordre : le dernier gagne.
    Renvoie (x0, y0, qx, qy, couvert) sur la boîte englobante, ou None."""
    A, B, C = D[tris[:, 0]], D[tris[:, 1]], D[tris[:, 2]]
    xmin = np.floor(np.minimum(np.minimum(A[:, 0], B[:, 0]), C[:, 0])).astype(int)
    xmax = np.ceil(np.maximum(np.maximum(A[:, 0], B[:, 0]), C[:, 0])).astype(int)
    ymin = np.floor(np.minimum(np.minimum(A[:, 1], B[:, 1]), C[:, 1])).astype(int)
    ymax = np.ceil(np.maximum(np.maximum(A[:, 1], B[:, 1]), C[:, 1])).astype(int)
    X0, Y0 = max(int(xmin.min()), 0), max(int(ymin.min()), 0)
    X1, Y1 = min(int(xmax.max()) + 1, W), min(int(ymax.max()) + 1, H)
    if X0 >= X1 or Y0 >= Y1:
        return None
    den = (B[:, 1] - C[:, 1]) * (A[:, 0] - C[:, 0]) + (C[:, 0] - B[:, 0]) * (A[:, 1] - C[:, 1])
    ok = np.abs(den) > 1e-9
    den = np.where(ok, den, 1.0)
    taille = np.maximum(xmax - xmin, ymax - ymin) + 1
    qx = np.full((Y1 - Y0, X1 - X0), -100.0, np.float32)
    qy = np.full((Y1 - Y0, X1 - X0), -100.0, np.float32)
    w = X1 - X0
    lots = []
    petits = taille <= 10
    if petits.any():
        lots.append(np.nonzero(petits)[0])
    for i in np.nonzero(~petits)[0]:
        lots.append(np.array([i]))
    lin_t, sx_t, sy_t, ord_t = [], [], [], []
    for idx in lots:
        K = int(taille[idx].max())
        off = np.arange(K)
        px = (xmin[idx, None, None] + off[None, None, :]).astype(np.float32) + 0 * off[None, :, None]
        py = (ymin[idx, None, None] + off[None, :, None]).astype(np.float32) + 0 * off[None, None, :]
        a_, b_, c_ = A[idx], B[idx], C[idx]
        ex = px - c_[:, 0, None, None]
        ey = py - c_[:, 1, None, None]
        dd = den[idx, None, None]
        l1 = ((b_[:, 1] - c_[:, 1])[:, None, None] * ex + (c_[:, 0] - b_[:, 0])[:, None, None] * ey) / dd
        l2 = ((c_[:, 1] - a_[:, 1])[:, None, None] * ex + (a_[:, 0] - c_[:, 0])[:, None, None] * ey) / dd
        l3 = 1 - l1 - l2
        dedans = (l1 >= -1e-4) & (l2 >= -1e-4) & (l3 >= -1e-4) & ok[idx, None, None]
        dedans &= (px >= X0) & (px < X1) & (py >= Y0) & (py < Y1)
        k_i, j_i, i_i = np.nonzero(dedans)
        if len(k_i) == 0:
            continue
        L1, L2, L3 = l1[k_i, j_i, i_i], l2[k_i, j_i, i_i], l3[k_i, j_i, i_i]
        t = idx[k_i]
        sa, sb, sc = S[tris[t, 0]], S[tris[t, 1]], S[tris[t, 2]]
        sx_t.append(L1 * sa[:, 0] + L2 * sb[:, 0] + L3 * sc[:, 0])
        sy_t.append(L1 * sa[:, 1] + L2 * sb[:, 1] + L3 * sc[:, 1])
        lin_t.append((py[k_i, j_i, i_i].astype(int) - Y0) * w + (px[k_i, j_i, i_i].astype(int) - X0))
        ord_t.append(t)
    if not lin_t:
        return None
    lin = np.concatenate(lin_t)
    sx = np.concatenate(sx_t)
    sy = np.concatenate(sy_t)
    o = np.argsort(np.concatenate(ord_t), kind='stable')        # ordre des triangles : le dernier gagne
    lin, sx, sy = lin[o], sx[o], sy[o]
    _, dernier = np.unique(lin[::-1], return_index=True)
    dernier = len(lin) - 1 - dernier
    qx.flat[lin[dernier]] = sx[dernier]
    qy.flat[lin[dernier]] = sy[dernier]
    return X0, Y0, qx, qy, qx > -50


# ================================================================ Thomas (objet animable à squelette complet)
class Thomas:
    def __init__(self, objet, palette):
        d = objet['animable']
        self.def_ = d
        self.pal = palette
        self.nom = objet['nom']
        x, y, w, h = objet['rect']                 # toile de repos du calque « corps »
        self.rect = (x, y, w, h)
        self.ox, self.oy = x, y
        sl = (slice(y, y + h), slice(x, x + w))
        corps = charger_rgba(d['calques']['corps'])[sl]
        bouche = charger_gris(d['masques']['bouche'])[sl]
        levres = charger_gris(d['masques']['levres'])[sl]
        self.corps = np.dstack([corps, bouche, levres]).astype(np.float32)
        self.oeil = charger_rgba(d['calques']['oeil_pendant'])
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.gx, self.gy = gx, gy
        ys, xs = np.nonzero(self.corps[..., 3] > 0)
        self.boite_corps = (max(int(xs.min()) - 16, 0), max(int(ys.min()) - 16, 0),
                            min(int(xs.max()) + 17, w), min(int(ys.max()) + 17, h))
        self.zones = {}
        for nom, z in d['zones'].items():
            z = dict(z)
            if 'carte' in z:
                pm = charger_gris(z['carte'])
                z['poids_monde'] = pm
                z['poids'] = pm[sl]
                ys, xs = np.nonzero(z['poids'] > 0)
                z['boite'] = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
            self.zones[nom] = z
        self.parametres = d['parametres']
        self.main = d['main']
        self.tige = d['tige']
        # --- squelette
        sq = d['squelette']
        self.os = {}
        self.ordre = []
        for o in sq['os']:
            o = dict(o)
            o['pivot'] = np.array(o['pivot'], np.float64)
            if 'vers' in o:
                v = np.array(o['vers'], np.float64) - o['pivot']
                o['axe'] = v / np.linalg.norm(v)
                o['longueur'] = float(np.linalg.norm(v))
                o['angle0'] = math.degrees(math.atan2(v[1], v[0]))
            self.os[o['nom']] = o
            self.ordre.append(o['nom'])
        self.jambes = sq['jambes']
        for j in self.jambes:
            H0, K0, A0 = (self.os[j[k]]['pivot'] for k in ('cuisse', 'tibia', 'pied'))
            j['l1'] = float(np.linalg.norm(K0 - H0))
            j['l2'] = float(np.linalg.norm(A0 - K0))
            j['a_t0'] = math.degrees(math.atan2(*(K0 - H0)[::-1]))
            j['a_s0'] = math.degrees(math.atan2(*(A0 - K0)[::-1]))
        self.a_f0 = self.os['avant_bras']['angle0']
        # --- calques à maillage
        self.calques = []
        for c in d['dessin']:
            c = dict(c)
            if 'chaine' in c:
                self._preparer_calque(c)
            self.calques.append(c)
        self.par_nom = {c['nom']: c for c in self.calques}

    # ------------------------------------------------ maillage et poids d'un calque
    def _preparer_calque(self, c):
        pas = float(c.get('pas', 4))
        if c['nom'] == 'corps':                       # toute la toile de repos (les zones déplacent les pixels)
            x0, y0, x1, y1 = self.boite_corps
            V, tris = grille(self.ox + x0, self.oy + y0, self.ox + x1, self.oy + y1, pas)
            c['org'] = (self.ox + x0, self.oy + y0)
            c['tex'] = None
        else:
            img = charger_rgba(c['image'])
            ys, xs = np.nonzero(img[..., 3] > 0)
            bx0, by0, bx1, by1 = int(xs.min()) - 2, int(ys.min()) - 2, int(xs.max()) + 3, int(ys.max()) + 3
            c['tex'] = img[by0:by1, bx0:bx1].copy()
            c['org'] = (bx0, by0)
            plein = ndi.binary_dilation(img[..., 3] > 0, iterations=2)
            V, tris = grille(bx0, by0, bx1, by1, pas, plein)
        chaine = c['chaine']
        W = np.ones((len(V), len(chaine)), np.float64)
        regles = c.get('poids', {})
        for k in range(1, len(chaine)):
            o = self.os[chaine[k]]
            regle = regles.get(chaine[k])
            if regle == 1:
                continue
            if isinstance(regle, str):               # carte de poids
                carte = charger_gris(regle)
                W[:, k] = ndi.map_coordinates(carte, [V[:, 1], V[:, 0]], order=1, mode='nearest')
            else:                                    # fondu le long de l'os, centré sur l'articulation
                f = float(o.get('fondu', 6.0))
                s = (V - o['pivot']) @ o['axe']
                W[:, k] = lissage_v((s + f) / (2 * f))
            W[:, k] = np.minimum(W[:, k], W[:, k - 1])
        c['V'], c['W'] = V, W
        # ordre de dessin : les parties les plus loin dans la chaîne passent devant
        prof = W[tris].sum(2).mean(1)
        c['tris'] = tris[np.argsort(prof, kind='stable')]
        A, B, Cc = V[c['tris'][:, 0]], V[c['tris'][:, 1]], V[c['tris'][:, 2]]
        c['aire0'] = float(np.abs((B[:, 0] - A[:, 0]) * (Cc[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (Cc[:, 0] - A[:, 0])).sum() / 2)

    # ------------------------------------------------ paramètres -> couches de zones
    def couches(self, p, recettes):
        out = []
        for nom, liens in self.parametres.items():
            v = p.get(nom, 0.0)
            if not isinstance(v, (int, float)) or v == 0:
                continue
            for zone, effet, facteur in liens:
                out.append((zone, effet, v * facteur))
        out += recettes
        return out

    def champ(self, couches, boite):
        x0, y0, x1, y1 = boite
        gx, gy = self.gx[y0:y1, x0:x1] + self.ox, self.gy[y0:y1, x0:x1] + self.oy
        fx = np.zeros_like(gx)
        fy = np.zeros_like(gy)
        for zn, effet, v in couches:
            z = self.zones.get(zn)
            if z is None or 'poids' not in z or abs(v) < 1e-6:
                continue
            w = z['poids'][y0:y1, x0:x1]
            self._effet(fx, fy, gx, gy, w, z, effet, v)
        return np.dstack([fx, fy]), x0, y0

    @staticmethod
    def _bosse(z, v):
        """Renflement qui descend le long du cou : centre et force (0 → 1 puis 1 → 2…)."""
        p = v - math.floor(v)
        if not (0 < p < 1):
            return None
        (ax, ay), (bx, by) = z['de'], z['a']
        return ax + (bx - ax) * p, ay + (by - ay) * p, math.sin(math.pi * p) ** 0.6

    @staticmethod
    def _effet(fx, fy, gx, gy, w, z, effet, v):
        if effet == 'deplacement_x':
            fx += w * v
        elif effet == 'deplacement_y':
            fy += w * v
        elif effet == 'rotation':
            px, py = z['pivot']
            ca, sa = rot(v)
            dx, dy = gx - px, gy - py
            fx += w * ((ca - 1) * dx - sa * dy)
            fy += w * (sa * dx + (ca - 1) * dy)
        elif effet == 'echelle':
            px, py = z['pivot']
            fx += w * v * (gx - px)
            fy += w * v * (gy - py)
        elif effet == 'renflement':
            b = Thomas._bosse(z, v)
            if b is not None:
                cx, cy, f = b
                dx, dy = gx - cx, gy - cy
                g = np.exp(-(dx * dx + dy * dy) / z['rayon'] ** 2) * f
                # la peau gonfle autour du centre (loupe) et pousse vers l'avant
                fx += w * g * (z['amplitude'] * z['direction'][0] + z['loupe'] * dx)
                fy += w * g * (z['amplitude'] * z['direction'][1] + z['loupe'] * dy)

    def deplacement_point(self, couches, x, y):
        """Où va le point (x, y) du corps (champ avant), et rotation locale du corps."""
        def F(px, py):
            gx = np.array([[px]], np.float32)
            gy = np.array([[py]], np.float32)
            fx = np.zeros_like(gx)
            fy = np.zeros_like(gy)
            for zn, effet, v in couches:
                z = self.zones.get(zn)
                if z is None or 'poids_monde' not in z or abs(v) < 1e-6:
                    continue
                pm = z['poids_monde']
                ix, iy = int(px), int(py)
                ax, ay = px - ix, py - iy
                w = (pm[iy, ix] * (1 - ax) * (1 - ay) + pm[iy, ix + 1] * ax * (1 - ay)
                     + pm[iy + 1, ix] * (1 - ax) * ay + pm[iy + 1, ix + 1] * ax * ay)
                self._effet(fx, fy, gx, gy, np.float32(w), z, effet, v)
            return float(fx[0, 0]), float(fy[0, 0])
        dx, dy = F(x, y)
        e = 2.0
        rx1, ry1 = F(x + e, y)
        rx0, ry0 = F(x - e, y)
        sx1, sy1 = F(x, y + e)
        sx0, sy0 = F(x, y - e)
        r = 0.5 * ((ry1 - ry0) / (2 * e) - (sx1 - sx0) / (2 * e))
        return dx, dy, math.degrees(r)

    @staticmethod
    def inverser(px, py, champ):
        F, ox, oy = champ
        qx, qy = px, py
        for _ in range(4):
            d = echantillonner(F, qx - ox, qy - oy)
            qx, qy = px - d[..., 0], py - d[..., 1]
        return qx, qy

    def couches_tronc(self, couches):
        porteuses = self.def_['squelette'].get('zones_porteuses')
        return couches if porteuses is None else [c for c in couches if c[0] in porteuses]

    # ------------------------------------------------ squelette
    def resoudre(self, p, couches):
        """Paramètres de la pose -> état du squelette : angle local et décalage de
        chaque os, puis position (J) et angle (A) dans le monde. Les longueurs
        d'os ne changent jamais : seuls des angles sont calculés."""
        ct = self.couches_tronc(couches)
        th, dec = {}, {}
        for b in self.ordre:
            o = self.os[b]
            th[b] = float(p.get('squelette.' + o['angle'], 0.0)) if o.get('angle') else 0.0
            dec[b] = np.zeros(2)
            if o.get('suit_champ'):                  # l'épaule suit la respiration et le balancement
                dx, dy, r = self.deplacement_point(ct, *o['pivot'])
                dec[b] = np.array([dx, dy])
                th[b] += r
        rac = self.ordre[0]
        th[rac] = float(p.get('squelette.racine', 0.0))
        dec[rac] = np.array([p.get('squelette.racine_x', 0.0), p.get('squelette.racine_y', 0.0)], np.float64)
        # jambes : cinématique inverse à deux os, les pieds vont où la pose les met
        J0r = self.os[rac]['pivot']
        avant = np.array(tourner(1.0, 0.0, th[rac]))
        for j in self.jambes:
            H0, A0 = self.os[j['cuisse']]['pivot'], self.os[j['pied']]['pivot']
            Hm = J0r + dec[rac] + np.array(tourner(*(H0 - J0r), th[rac]))
            cible = A0 + [p.get('squelette.%s_x' % j['pied'], 0.0), p.get('squelette.%s_y' % j['pied'], 0.0)]
            dv = cible - Hm
            l1, l2 = j['l1'], j['l2']
            L = min(max(float(np.linalg.norm(dv)), abs(l1 - l2) + 0.5), l1 + l2 - 0.02)
            base = math.degrees(math.atan2(dv[1], dv[0]))
            ouv = math.degrees(math.acos(min(max((l1 * l1 + L * L - l2 * l2) / (2 * l1 * L), -1.0), 1.0)))
            meilleur = None
            for s in (1, -1):
                a_t = base + s * ouv
                K = Hm + l1 * np.array(rot(a_t))
                note = float((K - Hm) @ avant)
                if meilleur is None or note > meilleur[0]:
                    meilleur = (note, a_t, K)
            _, a_t, K = meilleur
            Am = Hm + dv / max(np.linalg.norm(dv), 1e-9) * L
            a_s = math.degrees(math.atan2(Am[1] - K[1], Am[0] - K[0]))
            n180 = lambda a: (a + 180.0) % 360.0 - 180.0
            th[j['cuisse']] = n180(a_t - j['a_t0'] - th[rac])
            th[j['tibia']] = n180((a_s - j['a_s0']) - (a_t - j['a_t0']))
            th[j['pied']] = n180(p.get('squelette.' + j['pied'], 0.0) - (a_s - j['a_s0']))
        J, A = {}, {}
        for b in self.ordre:
            o = self.os[b]
            par = o['parent']
            if par is None:
                A[b] = th[b]
                J[b] = o['pivot'] + dec[b]
            else:
                A[b] = A[par] + th[b]
                J[b] = J[par] + np.array(tourner(*(o['pivot'] + dec[b] - self.os[par]['pivot']), A[par]))
        return {'theta': th, 'dec': dec, 'J': J, 'A': A}

    def point_os(self, etat, os_, pt):
        """Point attaché rigidement à un os (coordonnées de repos) -> monde."""
        return etat['J'][os_] + np.array(tourner(*(np.array(pt, np.float64) - self.os[os_]['pivot']), etat['A'][os_]))

    def _progressif(self, P, chaine, W, etat):
        """Rotation progressive : chaque sommet tourne autour de chaque articulation
        de sa chaîne d'une fraction (son poids) de l'angle. Volume conservé."""
        P = P.copy()
        th, dec = etat['theta'], etat['dec']
        for k in range(len(chaine) - 1, 0, -1):
            b = chaine[k]
            J0 = self.os[b]['pivot']
            w = W[:, k]
            a = np.radians(w * th[b])
            c, s = np.cos(a), np.sin(a)
            qx, qy = P[:, 0] - J0[0], P[:, 1] - J0[1]
            P[:, 0] = J0[0] + w * dec[b][0] + c * qx - s * qy
            P[:, 1] = J0[1] + w * dec[b][1] + s * qx + c * qy
        b = chaine[0]
        J0 = self.os[b]['pivot']
        c, s = rot(th[b])
        qx, qy = P[:, 0] - J0[0], P[:, 1] - J0[1]
        return np.stack([J0[0] + dec[b][0] + c * qx - s * qy, J0[1] + dec[b][1] + s * qx + c * qy], 1)

    def sommets(self, c, etat):
        return self._progressif(c['V'], c['chaine'], c['W'], etat)

    def point_corps(self, etat, couches, x, y):
        """Point du calque « corps » (tête comprise) -> monde : zones puis squelette."""
        dx, dy, _ = self.deplacement_point(couches, x, y)
        c = self.par_nom['corps']
        W = np.ones((1, len(c['chaine'])))
        regles = c.get('poids', {})
        for k in range(1, len(c['chaine'])):
            o = self.os[c['chaine'][k]]
            regle = regles.get(c['chaine'][k])
            if isinstance(regle, str):
                W[0, k] = self.zones_carte(regle)[int(round(y)), int(round(x))]
            elif regle != 1:
                f = float(o.get('fondu', 6.0))
                W[0, k] = lissage(((np.array([x, y]) - o['pivot']) @ o['axe'] + f) / (2 * f))
            W[0, k] = min(W[0, k], W[0, k - 1])
        return self._progressif(np.array([[x + dx, y + dy]], np.float64), c['chaine'], W, etat)[0]

    def zones_carte(self, fichier):
        if not hasattr(self, '_cartes'):
            self._cartes = {}
        if fichier not in self._cartes:
            self._cartes[fichier] = charger_gris(fichier)
        return self._cartes[fichier]

    def point_main(self, etat, local):
        """Point exprimé dans le repère de la main (x vers les doigts) -> monde."""
        k = self.main.get('taille', 1.0)
        wx, wy = tourner(local[0] * k, local[1] * k, self.a_f0 + etat['A']['main'])
        return etat['J']['main'] + [wx, wy]

    # ------------------------------------------------ couleurs (paupière, renflement du cou)
    def couleurs(self, img, couches):
        out = None
        for zn, effet, v in couches:
            if effet not in ('paupiere', 'renflement') or abs(v) < 1e-4:
                continue
            z = self.zones[zn]
            if effet == 'renflement':
                b = self._bosse(z, v)
                if b is None:
                    continue
                if out is None:
                    out = img.copy()
                cx, cy, f = b
                x0, y0, x1, y1 = z['boite']
                dx = self.gx[y0:y1, x0:x1] + self.ox - cx
                dy = self.gy[y0:y1, x0:x1] + self.oy - cy
                r = z['rayon'] * (0.55 + 0.45 * f)
                d = np.hypot(dx, dy * 0.85)
                part = out[y0:y1, x0:x1]
                a = part[..., 3:4]
                masque = (z['poids'][y0:y1, x0:x1] > 0.5) & (a[..., 0] > 0.5)
                # bosse en aplats : reflet du côté de la lumière, peau tendue, croissant d'ombre dessous
                bosse = masque & (d < r)
                eclat = bosse & (np.hypot(dx - LUMIERE[0] * r * 0.35, dy - LUMIERE[1] * r * 0.35) < r * 0.45)
                ombre = masque & (d >= r) & (d < r + TEXEL) & (dx * LUMIERE[0] + dy * LUMIERE[1] < r * 0.25)
                for m, coul in ((bosse, self.pal['peau_clair']), (eclat, self.pal['peau_eclat']),
                                (ombre, self.pal['peau_sombre'])):
                    part[..., :3][m] = np.array(coul, np.float32)
                continue
            if out is None:
                out = img.copy()
            self.paupiere(out, z, min(max(v, 0.0), 1.0))
        return img if out is None else out

    def paupiere(self, img, z, k):
        """Paupière en aplats : peau, bande d'ombre et trait sombre au bord."""
        cx, cy = z['centre'][0] - self.ox, z['centre'][1] - self.oy
        r = z['rayon']
        x0, x1 = int(cx - r - 2), int(cx + r + 3)
        y0, y1 = int(cy - r - 2), int(cy + r + 3)
        sx, sy = self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1]
        dedans = np.clip(r + 0.5 - np.hypot(sx - cx, sy - cy), 0, 1)
        # la paupière du haut descend jusqu'aux trois quarts, celle du bas monte : fermé = une fente sombre
        bord = cy - r + 2 * r * k * 0.74
        bas = cy + r - 2 * r * k * 0.26
        couvre = np.maximum(np.clip(bord - sy + 0.5, 0, 1), np.clip(sy - bas + 0.5, 0, 1)) * dedans
        peau = np.array(z['couleur'], np.float32)
        ton = np.where((bord - sy < 3.0)[..., None], np.array(self.pal['peau_moyen'], np.float32), peau)
        haut = (np.hypot(sx - cx + 2.5, sy - cy + 3.5) < r * 0.5) & (bord - sy >= 3.0)
        ton = np.where(haut[..., None], np.array(self.pal['peau_eclat'], np.float32), ton)
        trait = np.clip(1.5 - np.abs(sy - bord), 0, 1) * dedans * min(k * 6, 1.0)
        part = img[y0:y1, x0:x1]
        a = part[..., 3:4]
        rgb = part[..., :3]
        rgb[:] = rgb + (ton * a - rgb) * couvre[..., None]
        rgb[:] = rgb + (np.array(self.pal['trait'], np.float32) * a - rgb) * trait[..., None]

    # ------------------------------------------------ rendu
    def rendre(self, cadre, p, couches, etat, ressorts, morceau=None):
        """Dessine Thomas dans le cadre. morceau : fonction qui dessine ce qu'il
        tient (entre la paume et les doigts, et entre l'intérieur de la bouche et
        les lèvres). Renvoie le rectangle touché et des informations de contrôle."""
        H, W = cadre.shape[:2]
        rects = []
        info = {'bouche': np.zeros((H, W), np.float32), 'levres': np.zeros((H, W), np.float32), 'aires': {}}
        for c in self.calques:
            nom = c['nom']
            if 'chaine' in c:
                if nom == 'corps':
                    # corps : déformation par zones (champ inversé, lecture sous-pixel)…
                    img = self.couleurs(self.corps, couches)
                    x0, y0, x1, y1 = self.boite_corps
                    ch = self.champ(couches, self.boite_corps)
                    qx, qy = self.inverser(self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1], ch)
                    tex = echantillonner(img, qx, qy)
                else:
                    tex = c['tex']
                D = self.sommets(c, etat)             # … puis squelette
                T = c['tris']
                A_, B_, C_ = D[T[:, 0]], D[T[:, 1]], D[T[:, 2]]
                info['aires'][nom] = float(np.abs((B_[:, 0] - A_[:, 0]) * (C_[:, 1] - A_[:, 1]) - (B_[:, 1] - A_[:, 1]) * (C_[:, 0] - A_[:, 0])).sum() / 2) / c['aire0']
                ox, oy = c['org']
                if np.abs(D - c['V']).max() < 1e-4:   # calque immobile : simple copie
                    r = tex
                    rect = composer(cadre, tex[..., :4], ox, oy)
                    if nom == 'corps' and rect:
                        a0, b0, a1, b1 = rect
                        info['bouche'][b0:b1, a0:a1] = tex[b0 - oy:b1 - oy, a0 - ox:a1 - ox, 4]
                        info['levres'][b0:b1, a0:a1] = tex[b0 - oy:b1 - oy, a0 - ox:a1 - ox, 5]
                    rects.append(rect)
                    continue
                res = rasteriser(D, c['V'] - [ox, oy], T, H, W)
                if res is None:
                    continue
                X0, Y0, qx, qy, couvert = res
                r = echantillonner(tex, qx, qy) * couvert[..., None]
                Y1, X1 = Y0 + qx.shape[0], X0 + qx.shape[1]
                zone = cadre[Y0:Y1, X0:X1]
                zone[:] = r[..., :3] + zone * (1 - r[..., 3:4])
                if nom == 'corps':
                    info['bouche'][Y0:Y1, X0:X1] = r[..., 4]
                    info['levres'][Y0:Y1, X0:X1] = r[..., 5]
                    ys, xs = np.nonzero(r[..., 3] > 0)
                    if len(ys):
                        rects.append((X0 + int(xs.min()), Y0 + int(ys.min()), X0 + int(xs.max()) + 1, Y0 + int(ys.max()) + 1))
                else:
                    rects.append((X0, Y0, X1, Y1))
            elif nom == 'tige':
                rects.append(self._tige(cadre, ressorts, p))
            elif nom == 'main':
                dos, devant = self._main(etat, p.get('squelette.main_fermeture', 0.5))
                P = etat['J']['main']
                ang = self.a_f0 + etat['A']['main']
                rects.append(dos.poser(cadre, P[0], P[1], ang)[0])
                if morceau is not None:
                    rects.append(morceau(cadre, 1.0 - info['levres']))
                rects.append(devant.poser(cadre, P[0], P[1], ang)[0])
        return union(rects), info

    def _main(self, etat, fermeture):
        """Main dessinée par le code dans le style de Thomas (texels, aplats de sa
        palette, contour sombre de même épaisseur), attachée au poignet. Deux
        toiles : dos (paume, pouce) et devant (doigts)."""
        ang = self.a_f0 + etat['A']['main']
        pal = self.pal
        tons = (pal['bras_clair'], pal['bras_moyen'], pal['bras_sombre'])
        dos = Texels(-16, -30, 42, 30, ang)
        devant = Texels(-16, -30, 42, 30, ang)
        f = fermeture
        dos.peindre(lambda u, v: sdf_capsule(u, v, -8, 0.5, 10, 0.5, 10.6), tons, pal['trait'], grain=0.09)
        dos.effacer(dos.U < -1.0)                     # coupe nette au poignet : la paume prolonge l'avant-bras
        a1 = -62 + 80 * f
        ex, ey = tourner(9.5, 0, a1)
        dos.peindre(lambda u, v: sdf_capsule(u, v, 7.0, -9.0, 7.0 + ex, -9.0 + ey, 4.2), tons, pal['trait'])
        # doigts vus de dessus : en se fermant ils raccourcissent (ils s'enroulent vers
        # la paume) et se serrent, au lieu de tourner à plat
        doigts = []
        for i, (bu, bv, l1, l2) in enumerate(((12.0, -7.4, 8.0, 6.5), (13.0, 0.4, 8.6, 6.8), (12.0, 8.0, 7.4, 6.0))):
            k1 = 4 + 20 * f
            k2 = 6 + 26 * f
            e1 = tourner(l1 * (1 - 0.45 * f), 0, k1)
            m_ = (bu + e1[0], bv + e1[1])
            e2 = tourner(l2 * (1 - 0.8 * f), 0, k1 + k2)
            c_ = (m_[0] + e2[0], m_[1] + e2[1])
            doigts.append(lambda u, v, a=(bu, bv), b=m_, c=c_: np.minimum(sdf_capsule(u, v, a[0], a[1], b[0], b[1], 4.4),
                                                                          sdf_capsule(u, v, b[0], b[1], c[0], c[1], 4.1)))
        devant.peindre_union(doigts, tons, pal['trait'])
        return dos, devant

    def _tige(self, cadre, etat, p):
        """Tige (courbe de Bézier) de l'orbite à l'œil pendant, puis l'œil. Aplats."""
        t = self.tige
        A = np.array(etat['ancre'])
        X = np.array(etat['oeil'])
        V = np.array(etat['vitesse_oeil'])
        r_oe = t['rayon_oeil']
        haut = X + (A - X) / max(np.linalg.norm(A - X), 1e-6) * (r_oe - 1.5)
        ctrl = (A + haut) / 2 + np.array(t.get('courbure', [0.0, 0.0])) + np.array([0.0, 0.18 * np.linalg.norm(haut - A)]) - V * 0.012
        x0 = int(min(A[0], X[0], ctrl[0])) - 14
        y0 = int(min(A[1], X[1], ctrl[1])) - 14
        x1 = int(max(A[0], X[0], ctrl[0])) + 15
        y1 = int(max(A[1], X[1], ctrl[1])) + 15
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
        sd = np.full(gx.shape, 1e9, np.float32)
        n = 10
        pts = [(1 - s) ** 2 * A + 2 * (1 - s) * s * ctrl + s * s * haut for s in np.linspace(0, 1, n + 1)]
        for i in range(n):
            sd = np.minimum(sd, sdf_capsule(gx, gy, *pts[i], *pts[i + 1], t['epaisseur']))
        cov = np.clip(0.5 - sd, 0, 1)
        coeur = np.clip(-sd - 1.3 + 0.5, 0, 1)
        coul = np.array(self.pal['rose_tige'], np.float32) * coeur[..., None] + np.array(self.pal['trait_rouge'], np.float32) * (1 - coeur[..., None])
        rect = composer(cadre, np.dstack([coul * cov[..., None], cov]), x0, y0)
        # l'œil : pixels d'origine, rotation légère (il « regarde ») + position sous-pixel
        ang = p.get('zones.oeil_pendant_regard', 0.0)
        sp = self.oeil
        h, w = sp.shape[:2]
        if abs(ang) > 0.05:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            cx, cy = (w - 1) / 2, (h - 1) / 2
            ux, uy = tourner(xx - cx, yy - cy, -ang)
            sp = echantillonner(sp, ux + cx, uy + cy)
        r2 = coller_sous_pixel(cadre, sp, X[0] - (w - 1) / 2, X[1] - (h - 1) / 2)
        return union([rect, r2])


# ================================================================ objets dessinés par le code
class Gant:
    """Gant de laboratoire (et manche de blouse) dessiné par le code, en aplats.
    Paramètres : x, y (bout des doigts), angle, ouverture (0 = pince fermée),
    paume (0 = pince qui tient, 1 = main à plat qui caresse)."""

    def __init__(self, d, pal):
        self.d = d
        self.pal = pal

    def dessiner(self, cadre, p):
        x, y = p.get('x', 0.0), p.get('y', -300.0)
        if y < -80:
            return None
        ang = p.get('angle', 0.0)
        o = p.get('ouverture', 0.0)
        paume = p.get('paume', 0.0)
        k = self.d.get('taille', 1.0)
        pal = self.pal
        blanc = (pal['blanc_oeil'], pal['gant_moyen'], pal['gant_sombre'])
        trait = pal['trait']
        haut = -(y + 80)
        T = Texels(-36, min(haut, -80), 36, 14, ang)
        # manche de blouse qui monte hors de l'image, puis revers du gant
        T.peindre(lambda u, v: sdf_boite(u, v, 2, -656, 15, 600, 2), blanc, trait, bande=(6.0, 6.0))
        T.peindre(lambda u, v: sdf_boite(u, v, 2, -52, 15, 6, 3), blanc, trait)
        if paume < 0.5:
            # paume, un doigt replié, puis la pince pouce + index
            T.peindre(lambda u, v: sdf_capsule(u, v, 2, -35, 2, -20, 12.5), blanc, trait)
            T.peindre(lambda u, v: sdf_capsule(u, v, 11.5, -19, 14.0 + 3 * o, -8.5 + 1.5 * o, 4.8), blanc, trait)
            T.peindre(lambda u, v: sdf_capsule(u, v, -9.5, -22, -5.5 - 9 * o, -3.0 - 1.5 * o, 4.8), blanc, trait)
            T.peindre(lambda u, v: sdf_capsule(u, v, 5, -19, 4.0 + 8 * o, -2.0 - 1.5 * o, 4.8), blanc, trait)
        else:
            # main à plat : pouce écarté, paume large, quatre doigts serrés vers le bas
            T.peindre(lambda u, v: sdf_capsule(u, v, -12, -27, -19, -14, 4.3), blanc, trait)
            T.peindre(lambda u, v: sdf_boite(u, v, 2, -31, 13.5, 12, 8), blanc, trait)
            doigts = []
            for i, (du, lg) in enumerate(((-8.5, 15.0), (-1.5, 18.0), (5.5, 17.0), (12.5, 13.0))):
                ecart = (i - 1.5) * (0.8 + 1.2 * o)
                doigts.append(lambda u, v, du=du, lg=lg, ecart=ecart: sdf_capsule(u, v, du, -20, du + ecart, -20 + lg, 4.2))
            T.peindre_union(doigts, blanc, trait)
        return T.poser(cadre, x, y, ang)[0]


class Morceau:
    """Morceau de chair crue dessiné par le code (texels, aplats, contour sombre).
    Objet animable : position, angle, écrasement, bouchées. Chaque bouchée retire
    un vrai morceau : la surface (en pixels) est mesurable à chaque image."""

    def __init__(self, d, pal):
        self.d = d
        self.pal = pal

    def toile(self, p, etat, ang):
        d = self.d
        pal = self.pal
        e = p.get('ecrasement', 0.0) + etat.get('tremble', 0.0)
        ex, ey = 1 + e, 1 / (1 + e)
        rx, ry = d['rayons']
        T = Texels(-rx - 6, -ry - 6, rx + 6, ry + 12, ang)
        n_b = p.get('bouchees', 0.0)

        def forme(u, v):
            u, v = u / ex, v / ey
            th = np.arctan2(v, u)
            rr = 1 + 0.07 * np.sin(2 * th + 0.6) + 0.05 * np.sin(5 * th + 2.0) + 0.04 * np.sin(9 * th + 4.1)
            n4 = (np.abs(u / rx) ** 2.6 + np.abs(v / ry) ** 2.6) ** (1 / 2.6)
            return (n4 / rr - 1) * min(rx, ry)

        def mordu(u, v):
            """Distance à la partie déjà mangée (négatif = mangé) : bord en dents de scie."""
            sd = np.full(u.shape, 1e9, np.float32)
            for k_, (bx, br) in enumerate(d['bouchees']):
                f = min(max(n_b - k_, 0.0), 1.0)
                if f > 0:
                    dent = 1.3 * np.sin(v * 1.15 + k_ * 1.7)
                    sd = np.minimum(sd, (u - (bx + dent)) + (1 - f) * (br + 4.0))
            return sd

        tons = (pal['viande_clair'], pal['viande_moyen'], pal['viande_sombre'])
        dedans = T.peindre(lambda u, v: np.maximum(forme(u, v), -mordu(u, v)), tons, pal['trait_rouge'])
        # marbrures de gras et reflet : petits aplats nets
        gras = dedans & (forme(T.U, T.V) < -3.2) & (np.sin(0.62 * T.V + 1.5 * np.sin(0.4 * T.U + 2.0) + 1.0) > 0.82)
        T.aplat(gras & (mordu(T.U, T.V) > 3.5), pal['gras'])
        reflet = dedans & (np.hypot(T.U + rx * 0.45, T.V + ry * 0.4) < 2.3) & (mordu(T.U, T.V) > 3.5)
        T.aplat(reflet, pal['gras'])
        # chair à vif le long de la morsure
        md = mordu(T.U, T.V)
        T.aplat(dedans & (md > TEXEL) & (md < 2 * TEXEL + 0.5) & (forme(T.U, T.V) < -TEXEL), pal['viande_vif'])
        # filaments qui pendent (un texel de large), balancés par le mouvement
        bal = etat.get('balancement', 0.0)
        bas_u, bas_v = tourner(0.0, 1.0, -ang)
        for i, (fu, fl) in enumerate(d['filaments']):
            au, av = fu, ry * 0.75
            if mordu(np.float32(au), np.float32(av)) < 2.0:
                continue
            lg = fl * (1.0 + 0.0 * i)
            bu, bv = au + bas_u * lg - bas_v * bal * fl * 0.6, av + bas_v * lg + bas_u * bal * fl * 0.6
            fil = (sdf_capsule(T.U, T.V, au, av, bu, bv, 0.9) < 0) & ~dedans
            T.aplat(fil, pal['viande_moyen'])
        return T

    def dessiner(self, cadre, p, etat, cx, cy, ang, masque=None):
        T = self.toile(p, etat, ang)
        rect, alpha = T.poser(cadre, cx, cy, ang, masque)
        return rect, alpha, T.surface()


class Mouches:
    """Mouches : chacune a sa trajectoire (boucles, crochets, pauses), périodique."""

    def __init__(self, d):
        self.d = d
        m = charger_rgba('decor/mouche.png')
        lum = m[..., :3].sum(2) / np.maximum(m[..., 3], 1e-3) / 3
        self.mouche = m
        self.sans_ailes = m * (1 - ((lum > 150) & (m[..., 3] > 0)))[..., None]

    def positions(self, t, p, cible):
        T = self.d['duree']
        ag = p.get('agitation', 0.0)
        at = p.get('attraction', 0.0)
        res = []
        for i, v in enumerate(self.d['vols']):
            cx, cy, rx, ry, nx, ny, ph = v[:7]
            boucle, n_b, pause = (v[7:] + [0, 0, 0])[:3] if len(v) > 7 else (0, 0, 0)
            a = 2 * math.pi * (t / T + ph)
            # l'allure varie : elle ralentit presque jusqu'à l'arrêt puis repart
            a2 = a + pause * math.sin(a)
            x = cx + rx * math.sin(nx * a2) + 0.35 * rx * math.sin(3 * nx * a2 + 1.1)
            y = cy + ry * math.sin(ny * a2 + 0.7) + 0.25 * ry * math.sin(2 * ny * a2 + 2.3)
            x += boucle * math.cos(n_b * a + i)            # petites boucles serrées
            y += boucle * 0.7 * math.sin(n_b * a + i)
            x += ag * 9 * math.sin(2 * math.pi * (t * 3.0 + i * 0.37))
            y += ag * 7 * math.sin(2 * math.pi * (t * 2.25 + i * 0.61))
            if cible is not None and at > 0:
                k = at * self.d['attirees'][i]
                ox, oy = 13 * math.cos(a * 2 + i), 9 * math.sin(a * 2 + i) - 10
                x += (cible[0] + ox - x) * k
                y += (cible[1] + oy - y) * k
            res.append((x, y))
        return res

    def dessiner(self, cadre, t, p, cible, fps):
        rects = []
        for i, (x, y) in enumerate(self.positions(t, p, cible)):
            sp = self.mouche if (int(round(t * fps)) + i) % 2 == 0 else self.sans_ailes
            h, w = sp.shape[:2]
            r = coller_sous_pixel(cadre, sp, x - w / 2, y - h / 2)
            if r:
                rects.append(r)
        return rects


class Bulle:
    """Bulle « Zzz » du sommeil (texels, aplats) : deux petites bulles puis la
    grande avec les lettres. Paramètre « taille » de 0 (rien) à 1 (complète)."""

    def __init__(self, d, pal):
        self.d = d
        self.pal = pal

    def dessiner(self, cadre, p, x, y, t):
        k = p.get('taille', 0.0)
        if k < 0.08:
            return None
        pal = self.pal
        blanc = (pal['blanc_oeil'], pal['blanc_oeil'], pal['gant_moyen'])
        flot = 1.5 * math.sin(2 * math.pi * t / 4.0)
        T = Texels(-12, -66, 52, 6, 0.0)
        if k > 0.08:
            T.peindre(lambda u, v: sdf_ellipse(u, v, 0, -2, 3.2, 3.2), blanc, pal['trait'])
        if k > 0.35:
            T.peindre(lambda u, v: sdf_ellipse(u, v, 6, -13 + 0.5 * flot, 5.2, 4.6), blanc, pal['trait'])
        if k > 0.65:
            cy = -40 + flot
            T.peindre(lambda u, v: sdf_ellipse(u, v, 24, cy, 23, 17), blanc, pal['trait'], bande=(4.0, 4.0))
            # lettres Z en texels (un grand, un petit) ; le petit clignote lentement
            lettres = [(12, cy - 9, 8, 1.0)]
            if math.sin(2 * math.pi * t / 2.0) > -0.3:
                lettres.append((29, cy + 0, 5, 1.0))
            for (lu, lv, n, _) in lettres:
                iu = np.floor((T.U - lu) / TEXEL)
                iv = np.floor((T.V - lv) / TEXEL)
                dans = (iu >= 0) & (iu < n) & (iv >= 0) & (iv < n)
                z = dans & ((iv <= 1) | (iv >= n - 2) | (np.abs(iu + iv - (n - 1)) <= 1))
                T.aplat(z, pal['trait'])
        return T.poser(cadre, x, y, 0.0)[0]


class Poussieres:
    """Petites poussières claires qui dérivent lentement (un texel chacune)."""

    def __init__(self, d, pal):
        self.d = d
        self.coul = np.array(pal['blanc_oeil'], np.float32)

    def dessiner(self, cadre, t):
        T = self.d['duree']
        rects = []
        for i, (cx, cy, rx, ry, nx, ny, ph) in enumerate(self.d['grains']):
            a = 2 * math.pi * (t / T + ph)
            x = cx + rx * math.sin(nx * a) + 3 * math.sin(3 * a + i)
            y = cy + ry * math.sin(ny * a + 1.3 * i)
            if math.sin(2 * a + 2.1 * i) < -0.55:      # elle sort de la lumière
                continue
            sp = np.zeros((2, 2, 4), np.float32)
            op = self.d.get('opacite', 0.55)
            sp[..., :3] = self.coul * op
            sp[..., 3] = op
            r = coller_sous_pixel(cadre, sp, x, y)
            if r:
                rects.append(r)
        return rects


class Reflet:
    """Reflet léger qui glisse sur la vitre : deux bandes obliques en escalier
    (texels), très peu opaques. Seul son rectangle est recalculé."""

    def __init__(self, d):
        self.d = d

    def dessiner(self, cadre, t):
        d = self.d
        f = (t / d['duree'] + d.get('phase', 0.0)) % 1.0
        if f > d['passage']:
            return None
        u = f / d['passage']
        x0, x1 = d['x']
        xc = x0 + (x1 - x0) * u
        y0, y1 = d['y']
        op = d['opacite'] * math.sin(math.pi * u) ** 0.5
        if op < 0.01:
            return None
        pente = d['pente']
        hauteur = y1 - y0
        bx0, bx1 = int(xc - 8), int(xc + pente * hauteur + 30)
        bx0, bx1 = max(bx0, d['bornes'][0]), min(bx1, d['bornes'][1])
        if bx0 >= bx1:
            return None
        gy, gx = np.mgrid[y0:y1, bx0:bx1].astype(np.float32)
        gxq = np.floor(gx / TEXEL) * TEXEL
        gyq = np.floor(gy / TEXEL) * TEXEL
        s = gxq - xc - (y1 - gyq) * pente                 # position en travers de la bande
        bande = ((s >= 0) & (s < d['largeurs'][0])) | ((s >= d['largeurs'][0] + 6) & (s < d['largeurs'][0] + 6 + d['largeurs'][1]))
        a = bande.astype(np.float32) * op
        zone = cadre[y0:y1, bx0:bx1]
        zone[:] = zone + (np.array(d['couleur'], np.float32) - zone) * a[..., None]
        return (bx0, y0, bx1, y1)


# ================================================================ scène
class Scene:
    def __init__(self, fichier='scene.json', sequence=None):
        d = lire_json(fichier)
        self.d = d
        self.pal = lire_json(d['palette'])
        self.pal.update(d.get('couleurs', {}))
        self.fond = np.asarray(Image.open(chemin(d['fond'])).convert('RGB')).astype(np.float32)
        self.objets = {o['nom']: o for o in d['objets']}
        self.thomas = Thomas(self.objets['thomas'], self.pal)
        self.gant = Gant(self.objets['gant']['animable']['dessin'], self.pal)
        self.morceau = Morceau(self.objets['morceau']['animable']['dessin'], self.pal)
        self.mouches = Mouches(self.objets['mouches']['animable'])
        self.bulle = Bulle(self.objets['bulle']['animable'], self.pal)
        self.poussieres = Poussieres(self.objets['poussieres']['animable'], self.pal)
        self.reflet = Reflet(self.objets['reflet']['animable'])
        self.actions = lire_json('actions.json')
        self.sequence = None
        if sequence:
            self.jouer(sequence)
        self.recettes = {}
        self.cadre = self.fond.copy()
        self.sales = []
        self.etat = None
        self.dernier = {}

    def jouer(self, sequence):
        """sequence : un nom, ou une liste de noms à enchaîner."""
        self.sequence = Enchainement(sequence) if isinstance(sequence, (list, tuple)) else Sequence(sequence)
        self.etat = None

    def declencher(self, nom_action):
        """Action du joueur -> zone touchée -> séquence et recettes jouées ensemble."""
        a = self.actions[nom_action]
        self.jouer(a['sequence'])
        if 'recettes' in a:
            self.sequence.recettes = a['recettes']

    def recette(self, nom):
        if nom not in self.recettes:
            self.recettes[nom] = lire_json(os.path.join('recettes', nom + '.json'))
        return self.recettes[nom]

    # ------------------------------------------------ valeurs à l'instant t
    def parametres(self, objet, t):
        seq, tl, _ = self.sequence.locale(t)
        p = seq.valeurs(objet, tl)
        zones = []
        for nom in seq.recettes.get(objet, []):
            for c in self.recette(nom)['couches']:
                v = c.get('amplitude', 1.0) * courbe_periodique(c.get('courbe', 'constante'), t, c.get('duree', 1.0), c.get('phase', 0.0), c)
                if 'module' in c:                # intensité réglée par un paramètre de la pose
                    v *= p.get(c['module'], c.get('module_defaut', 1.0))
                if 'parametre' in c:
                    p[c['parametre']] = p.get(c['parametre'], 0.0) + v
                else:
                    zones.append((c['zone'], c['effet'], v))
        return p, zones

    def etat_thomas(self, t):
        pt, zt = self.parametres('thomas', t)
        couches = self.thomas.couches(pt, zt)
        return pt, zt, couches, self.thomas.resoudre(pt, couches)

    def _morceau_brut(self, t, att):
        """Position et angle (monde) du morceau pour un mode d'attache donné."""
        pm, _ = self.parametres('morceau', t)
        if att == 'main':
            pt, zt, couches, et = self.etat_thomas(t)
            pos = self.thomas.point_main(et, pt.get('attaches.prise_main', [15, 2]))
            ang = pm.get('angle_main', 0.0) + self.thomas.a_f0 + et['A']['main']
            du, dv = pm.get('tenue', [0.0, 0.0])          # où les doigts tiennent le morceau
            return pos + np.array(tourner(du, dv, ang)), ang
        if att == 'gant':
            pg, _ = self.parametres('gant', t)
            dx, dy = pm.get('decalage', [0, 8])
            ox, oy = tourner(dx, dy, pg.get('angle', 0.0))
            return np.array([pg['x'] + ox, pg['y'] + oy]), pm.get('angle', 0.0) + pg.get('angle', 0.0)
        return np.array([pm.get('x', -100.0), pm.get('y', -100.0)]), pm.get('angle', 0.0)

    def morceau_monde(self, t):
        """Quand l'attache change (gant -> libre -> main), l'écart éventuel entre
        l'ancienne et la nouvelle position est résorbé en douceur (0,25 s)."""
        pm, _ = self.parametres('morceau', t)
        att = pm.get('attache', 'libre')
        pos, ang = self._morceau_brut(t, att)
        seq, tl, _ = self.sequence.locale(t)
        piste = seq.pistes['morceau']
        D = 0.25
        for i in range(1, len(piste.cles)):
            k = piste.cles[i]
            avant = piste.cles[i - 1]['v'].get('attache')
            if k['v'].get('attache') != avant and 0 <= tl - k['arrivee'] < D:
                ts = t - (tl - k['arrivee'])
                p_old, a_old = self._morceau_brut(ts, avant)
                p_new, a_new = self._morceau_brut(ts, k['v'].get('attache'))
                f = 1 - lissage((tl - k['arrivee']) / D)
                pos = pos + (p_old - p_new) * f
                ang = ang + ((a_old - a_new + 180.0) % 360.0 - 180.0) * f
        return pos, ang

    def morceau_visible(self, t):
        seq, tl, _ = self.sequence.locale(t)
        if 'morceau' not in seq.pistes:
            return False, {}
        pm, _ = self.parametres('morceau', t)
        return pm.get('visible', 1) > 0.5, pm

    # ------------------------------------------------ mouvement secondaire (ressorts amortis)
    def _etat_initial(self):
        tg = self.thomas.tige
        return {'oeil': np.array(tg['oeil_repos'], np.float64), 'v_oeil': np.zeros(2), 'ancre': list(tg['ancre']),
                'cheveux': 0.0, 'v_cheveux': 0.0, 'cible_cheveux': 0.0,
                'tremble': 0.0, 'v_tremble': 0.0, 'pos_m': None, 'vit_m': np.zeros(2),
                'balancement': 0.0, 'v_bal': 0.0}

    def _pas(self, t, dt):
        th = self.thomas
        tg = th.tige
        pt, zt, couches, et = self.etat_thomas(t)
        e = self.etat
        A = th.point_corps(et, couches, *tg['ancre'])
        visible, pm = self.morceau_visible(t)
        pos_m = self.morceau_monde(t)[0] if visible else None
        pg, _ = self.parametres('gant', t)
        gant = np.array([pg['x'], pg['y'] - 14.0]) if pg.get('y', -300) > -80 else None
        sol = pt.get('physique.sol_oeil', 1e9)
        n = 8
        h = dt / n
        L0 = tg['longueur']
        main = th.point_main(et, [8, 0])
        C_, P_ = et['J']['avant_bras'], et['J']['main']
        for _ in range(n):
            X, V = e['oeil'], e['v_oeil']
            d = X - A
            L = max(np.linalg.norm(d), 1e-6)
            F = np.array([0.0, tg['gravite']])
            F -= tg['raideur'] * (L - L0) * d / L
            F -= tg['amortissement'] * V
            # la main, le morceau et le gant poussent l'œil s'ils passent tout près
            for q, rq in ((main, 21.0), (pos_m, 20.0), (gant, 22.0), ('avant_bras', 20.0)):
                if q is None:
                    continue
                if isinstance(q, str):        # le point le plus proche sur l'avant-bras
                    ab = P_ - C_
                    q = C_ + ab * min(max(float((X - C_) @ ab) / float(ab @ ab), 0.0), 1.0)
                dq = X - q
                lq = np.linalg.norm(dq)
                if lq < rq:     # contact doux : force qui croît progressivement
                    F += dq / max(lq, 1e-3) * (rq - lq) ** 2 * 18.0
            if X[1] > sol:      # l'œil repose sur le sol : appui doux et frottement
                F[1] -= (X[1] - sol) * 900.0 + V[1] * 30.0
                F[0] -= V[0] * 14.0
            V = V + F * h
            e['oeil'] = X + V * h
            e['v_oeil'] = V
        e['ancre'] = A.tolist()
        # cheveux : suivent la rotation de la tête avec retard
        cible = (pt.get('zones.tete_rotation', 0.0) + pt.get('squelette.cou', 0.0) + pt.get('squelette.tronc', 0.0)
                 + pt.get('squelette.racine', 0.0) + sum(v for z, ef, v in zt if z == 'tete' and ef == 'rotation'))
        k, c = 140.0, 11.0
        acc = k * (cible - e['cheveux']) - c * e['v_cheveux']
        e['v_cheveux'] += acc * dt
        e['cheveux'] += e['v_cheveux'] * dt
        e['cible_cheveux'] = cible
        # morceau : tremblement (écrasement) et filaments, poussés par l'accélération
        if pos_m is not None and e['pos_m'] is not None:
            v_new = (pos_m - e['pos_m']) / dt
            acc_m = (v_new - e['vit_m']) / dt
            e['vit_m'] = v_new
        else:
            acc_m = np.zeros(2)
            e['vit_m'] = np.zeros(2)
        acc_m = np.clip(acc_m, -6000, 6000)
        e['pos_m'] = pos_m
        a1 = -260.0 * e['tremble'] - 14.0 * e['v_tremble'] + acc_m[1] * 0.00004
        e['v_tremble'] += a1 * dt
        e['tremble'] += e['v_tremble'] * dt
        a2 = -90.0 * e['balancement'] - 7.0 * e['v_bal'] - acc_m[0] * 0.0012
        e['v_bal'] += a2 * dt
        e['balancement'] = float(np.clip(e['balancement'] + e['v_bal'] * dt, -1.2, 1.2))

    def prechauffer(self, fps, t0=0.0):
        """Met les ressorts dans l'état qu'ils ont au début du film. Séquence en
        boucle : on simule une boucle entière (la jonction est alors continue).
        Sinon : on laisse les ressorts se poser sur la première pose."""
        self.etat = self._etat_initial()
        if self.sequence.boucle:
            n = int(round(self.sequence.duree * fps))
            for i in range(n):
                self._pas(t0 + i / fps, 1.0 / fps)
        else:
            for i in range(int(4 * fps)):
                self._pas(t0, 1.0 / fps)

    def image(self, t, fps=30):
        """Calcule l'image au temps t (float32 640x480x3). Les appels doivent se
        suivre dans le temps (les ressorts avancent d'une image à l'autre)."""
        if self.etat is None:
            self.prechauffer(fps)
        self._pas(t, 1.0 / fps)
        e = self.etat
        th = self.thomas
        cadre = self.cadre
        # 1. on remet le décor fixe uniquement là où on avait dessiné
        for (x0, y0, x1, y1) in self.sales:
            cadre[y0:y1, x0:x1] = self.fond[y0:y1, x0:x1]
        sales = []
        pt, zt, _, _ = self.etat_thomas(t)
        zt = zt + [('cheveux', 'rotation', float(np.clip((e['cheveux'] - e['cible_cheveux']) * 1.6, -14, 14)))]
        couches = th.couches(pt, zt)
        et = th.resoudre(pt, couches)
        visible, pm = self.morceau_visible(t)
        pos_m, ang_m = self.morceau_monde(t) if visible else (None, 0.0)
        if pos_m is not None:
            e['cible_mouches'] = pos_m
        etat_m = {'tremble': e['tremble'], 'balancement': e['balancement']}
        en_main = visible and pm.get('attache') == 'main'
        suivi = {'alpha': None, 'rect': None, 'surface': 0.0}

        def dessiner_morceau(cadre_, masque=None):
            r, a, s = self.morceau.dessiner(cadre_, pm, etat_m, pos_m[0], pos_m[1], ang_m, masque)
            suivi.update(alpha=a, rect=r, surface=s)
            return r

        # 2. Thomas : seule sa boîte englobante est recalculée
        ressorts = {'ancre': e['ancre'], 'oeil': e['oeil'].tolist(), 'vitesse_oeil': e['v_oeil'].tolist()}
        rect_t, info = th.rendre(cadre, pt, couches, et, ressorts, dessiner_morceau if en_main else None)
        sales.append(rect_t)
        # 3. morceau libre ou tenu par le gant, gant (par-dessus)
        if visible and not en_main:
            sales.append(dessiner_morceau(cadre))
        pg, _ = self.parametres('gant', t)
        rect_g = self.gant.dessiner(cadre, pg)
        sales.append(rect_g)
        # 4. bulle du sommeil, mouches, poussières, reflet sur la vitre
        pb, _ = self.parametres('bulle', t)
        if pb.get('taille', 0.0) > 0.08:
            tete = th.point_corps(et, couches, *self.bulle.d['attache'])
            sales.append(self.bulle.dessiner(cadre, pb, tete[0] + pb.get('dx', 0.0), tete[1] + pb.get('dy', 0.0), t))
        pmo, _ = self.parametres('mouches', t)
        sales += self.mouches.dessiner(cadre, t, pmo, e.get('cible_mouches'), fps)
        sales += self.poussieres.dessiner(cadre, t)
        sales.append(self.reflet.dessiner(cadre, t))
        self.sales = [r for r in sales if r]
        # informations pour le contrôle
        contact = 0.0
        if suivi['alpha'] is not None and suivi['rect'] is not None:
            x0, y0, x1, y1 = suivi['rect']
            contact = float((suivi['alpha'] * info['bouche'][y0:y1, x0:x1]).sum())
        self.dernier = {'sales': list(self.sales), 'etat': et, 'morceau': pos_m, 'contact_bouche': contact,
                        'surface_morceau': suivi['surface'] if visible else 0.0, 'oeil': e['oeil'].copy(),
                        'parametres': pt, 'couches': couches, 'aires': info['aires'], 'rect_thomas': rect_t,
                        'rect_gant': rect_g, 'rect_morceau': suivi['rect'], 'gant': (pg.get('x'), pg.get('y')) if pg.get('y', -300) > -80 else None}
        return cadre

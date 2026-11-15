"""Moteur d'animation par zones, version 2 (Thomas le zombie mange).

Principe (inchangé depuis la version 1) :
  - le décor est fixe ; à chaque image on remet le décor seulement dans les
    rectangles dessinés à l'image précédente, puis on recalcule les rectangles
    des objets animés (Thomas, le gant, le morceau de chair, les mouches) ;
  - un objet devient animé par son composant « animable » (scene.json) ;
  - le mouvement vient de cartes de zones (niveaux de gris) et d'un squelette ;
  - tout est donnée : poses (poses/*.json), séquences (sequences/*.json),
    recettes (recettes/*.json), actions (actions.json).

Nouveau :
  - une POSE est un fichier JSON réutilisable (angles du squelette, état des zones,
    points d'attache) ; une SÉQUENCE est une liste de poses avec, pour chaque
    passage, une durée et une courbe. Le moteur calcule seul l'entre-deux
    (courbes douces ou spline d'Hermite monotone) : aucune image intermédiaire
    n'est posée à la main ;
  - bras à 3 articulations (épaule, coude, poignet) : maillage de triangles
    déformé par mélange linéaire des os (skinning), longueurs d'os constantes ;
  - mouvement secondaire par ressorts amortis (œil pendant, cheveux, morceau de chair).
Bibliothèques : numpy, Pillow (libres).
"""
import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ICI = os.path.dirname(os.path.abspath(__file__))


def chemin(*p):
    return os.path.join(ICI, *p)


def lire_json(p):
    with open(chemin(p), encoding='utf-8') as f:
        return json.load(f)


# ================================================================ courbes
def lissage(x):
    x = min(max(x, 0.0), 1.0)
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
    if nom == 'bruit':
        return (math.sin(2 * math.pi * x) * 0.55 + math.sin(2 * math.pi * (3 * x + 0.31)) * 0.3
                + math.sin(2 * math.pi * (7 * x + 0.67)) * 0.15)
    if nom == 'clignement':
        largeur = c.get('largeur', 0.22) / duree
        f = x - math.floor(x)
        return math.sin(math.pi * f / largeur) if f < largeur else 0.0
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

    def valeurs(self, objet, t):
        p = self.pistes.get(objet)
        if p is None:
            return {}
        return p.valeurs(t % self.duree if self.d.get('boucle') else t)[0]

    def pose_courante(self, objet, t):
        p = self.pistes[objet]
        v, i, u = p.valeurs(t % self.duree)
        return p.cles[i]['nom'], (p.cles[i + 1]['nom'] if i + 1 < len(p.cles) else None), u


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


def rot(a_deg):
    a = math.radians(a_deg)
    return math.cos(a), math.sin(a)


def tourner(px, py, a_deg):
    c, s = rot(a_deg)
    return c * px - s * py, s * px + c * py


# ---------------------------------------------------------------- dessin par champs de distance
def sdf_capsule(px, py, ax, ay, bx, by, r):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy + 1e-9
    h = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1)
    return np.hypot(px - ax - h * dx, py - ay - h * dy) - r


def sdf_ellipse(px, py, cx, cy, rx, ry):
    return (np.hypot((px - cx) / rx, (py - cy) / ry) - 1) * min(rx, ry)


def peindre(rgb, a, sdf, coul_fond, coul_trait, trait=1.2, ombre=None):
    """Ajoute une forme (champ de distance sdf) avec un contour sombre, par-dessus
    (rgb, a) non prémultipliés. ombre : facteur de luminosité par pixel."""
    cov = np.clip(0.5 - sdf, 0, 1)
    interieur = np.clip(-sdf - trait + 0.5, 0, 1)
    c = np.clip(np.array(coul_fond, np.float32) * (1 if ombre is None else ombre[..., None]), 0, 255)
    coul = c * interieur[..., None] + np.array(coul_trait, np.float32) * (1 - interieur[..., None])
    rgb[:] = coul * cov[..., None] + rgb * (1 - cov[..., None])
    a[:] = cov + a * (1 - cov)


# ================================================================ Thomas (objet animable à squelette)
class Thomas:
    def __init__(self, objet):
        d = objet['animable']
        self.def_ = d
        self.nom = objet['nom']
        x, y, w, h = objet['rect']
        self.rect = (x, y, w, h)
        self.ox, self.oy = x, y
        sl = (slice(y, y + h), slice(x, x + w))
        fond = np.asarray(Image.open(chemin(d['derriere'])).convert('RGB')).astype(np.float32)
        self.derriere = fond[sl].copy()
        self.corps = charger_rgba(d['calques']['corps'])[sl].copy()
        self.bras = charger_rgba(d['calques']['bras'])[sl].copy()
        self.oeil = charger_rgba(d['calques']['oeil_pendant'])
        # masque de l'intérieur de la bouche (sert au contrôle « le morceau touche la bouche »)
        rgb = self.corps[..., :3] / np.maximum(self.corps[..., 3:4], 1e-3)
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        bx_, by_, brx, bry = d['bouche']
        dans = np.hypot((gx + x - bx_) / brx, (gy + y - by_) / bry) < 1
        rouge = (rgb[..., 0] > rgb[..., 1] + 15) & (rgb.mean(2) < 120)
        self.corps = np.dstack([self.corps, (dans & rouge).astype(np.float32)])
        self.gx, self.gy = gx, gy
        ys, xs = np.nonzero(self.corps[..., 3] > 0)
        self.boite_corps = (max(int(xs.min()) - 16, 0), max(int(ys.min()) - 16, 0),
                            min(int(xs.max()) + 17, w), min(int(ys.max()) + 17, h))
        self.zones = {}
        for nom, z in d['zones'].items():
            z = dict(z)
            if 'carte' in z:
                z['poids'] = np.asarray(Image.open(chemin(z['carte'])).convert('L')).astype(np.float32)[sl] / 255.0
                ys, xs = np.nonzero(z['poids'] > 0)
                z['boite'] = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
                z['poids_monde'] = np.asarray(Image.open(chemin(z['carte'])).convert('L')).astype(np.float32) / 255.0
            self.zones[nom] = z
        self.parametres = d['parametres']
        sq = d['squelette']
        self.E0 = np.array(sq['epaule'], np.float64)
        self.C0 = np.array(sq['coude'], np.float64)
        self.P0 = np.array(sq['poignet'], np.float64)
        self.l1 = float(np.linalg.norm(self.C0 - self.E0))
        self.l2 = float(np.linalg.norm(self.P0 - self.C0))
        self.a_u0 = math.degrees(math.atan2(*(self.C0 - self.E0)[::-1]))
        self.a_f0 = math.degrees(math.atan2(*(self.P0 - self.C0)[::-1]))
        self.main = d['main']
        self.tige = d['tige']
        tx0, ty0, tx1, ty1 = self.main.get('texture', [244, 252, 278, 270])
        bt = self.bras[ty0 - y:ty1 - y, tx0 - x:tx1 - x]
        lum = bt[..., :3].mean(2) / np.maximum(bt[..., 3], 1e-3)
        self.grain = np.clip(lum / np.median(lum), 0.75, 1.25).astype(np.float32)
        self._maillage()

    # ------------------------------------------------ maillage du bras (pose de repos)
    def _maillage(self):
        a = self.bras[..., 3]
        ys, xs = np.nonzero(a > 0)
        pas = 3.0
        x0, y0 = xs.min() - 3, ys.min() - 3
        nx = int((xs.max() + 4 - x0) / pas) + 2
        ny = int((ys.max() + 4 - y0) / pas) + 2
        vx = x0 + np.arange(nx) * pas
        vy = y0 + np.arange(ny) * pas
        VX, VY = np.meshgrid(vx, vy)
        tris = []
        from scipy import ndimage as ndi
        plein = ndi.binary_dilation(a > 0, iterations=2)
        for j in range(ny - 1):
            for i in range(nx - 1):
                cx0, cy0 = int(vx[i]), int(vy[j])
                bloc = plein[max(cy0, 0):cy0 + int(pas) + 1, max(cx0, 0):cx0 + int(pas) + 1]
                if bloc.any():
                    v00, v10 = j * nx + i, j * nx + i + 1
                    v01, v11 = (j + 1) * nx + i, (j + 1) * nx + i + 1
                    tris.append((v00, v10, v11))
                    tris.append((v00, v11, v01))
        self.tris = np.array(tris, np.int32)
        V = np.stack([VX.ravel(), VY.ravel()], 1) + [self.ox, self.oy]     # monde
        self.V = V
        # poids : corps (haut de la manche, collé à l'épaule), bras, avant-bras
        E, C, P = self.E0, self.C0, self.P0

        def dist_seg(p, a, b):
            ab = b - a
            h = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
            return np.linalg.norm(p - a - h[:, None] * ab, axis=1)
        du, df = dist_seg(V, E, C), dist_seg(V, C, P)
        wf = 1 / (1 + np.exp(-(du - df) / 2.5))
        sq = self.def_['squelette']
        wb = 1 - np.clip((V[:, 1] - sq['attache_haut']) / sq['attache_fondu'], 0, 1)
        wb = wb * wb * (3 - 2 * wb) * (1 - wf)
        self.W = np.stack([wb, (1 - wb) * (1 - wf) + 0 * wb, wf], 1)
        self.W[:, 1] = 1 - self.W[:, 0] - self.W[:, 2]
        # ordre de dessin : avant-bras devant le haut du bras
        prof = self.W[self.tris, 2].mean(1)
        self.tris = self.tris[np.argsort(prof, kind='stable')]

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
            p = v - math.floor(v)              # 0→1 puis 1→2 : une déglutition chacun
            if 0 < p < 1:
                (ax, ay), (bx, by) = z['de'], z['a']
                cx, cy = ax + (bx - ax) * p, ay + (by - ay) * p
                bosse = np.exp(-((gx - cx) ** 2 + (gy - cy) ** 2) / z['rayon'] ** 2) * math.sin(math.pi * p) * z['amplitude']
                fx += w * bosse * z['direction'][0]
                fy += w * bosse * z['direction'][1]

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

    # ------------------------------------------------ squelette (cinématique directe)
    def couches_tronc(self, couches):
        porteuses = self.def_['squelette'].get('zones_porteuses')
        return couches if porteuses is None else [c for c in couches if c[0] in porteuses]

    def squelette(self, p, couches):
        dx, dy, r = self.deplacement_point(self.couches_tronc(couches), *self.E0)
        E = self.E0 + [dx, dy]
        a_u = r + p.get('squelette.epaule', 0.0)
        a_f = a_u + p.get('squelette.coude', 0.0)
        a_h = a_f + p.get('squelette.poignet', 0.0)
        C = E + np.array(tourner(*(self.C0 - self.E0), a_u))
        P = C + np.array(tourner(*(self.P0 - self.C0), a_f - 0.0))
        return {'E': E, 'C': C, 'P': P, 'a_u': a_u, 'a_f': a_f, 'a_h': a_h,
                'dir_main': self.a_f0 + a_h}

    def point_main(self, p, sq, local):
        """Point exprimé dans le repère de la main (x vers les doigts) -> monde."""
        k = self.main.get('taille', 1.0)
        lx, ly = local[0] * k, local[1] * k
        wx, wy = tourner(lx, ly, sq['dir_main'])
        return sq['P'] + [wx, wy]

    # ------------------------------------------------ couleurs (paupières)
    def couleurs(self, img, couches):
        out = None
        for zn, effet, v in couches:
            if effet not in ('paupiere', 'renflement') or abs(v) < 1e-4:
                continue
            z = self.zones[zn]
            if effet == 'renflement':
                # reflet qui descend avec le renflement (la peau tendue accroche la lumière)
                p = v - math.floor(v)
                if not (0 < p < 1) or not z.get('eclat'):
                    continue
                if out is None:
                    out = img.copy()
                (ax, ay), (bx, by) = z['de'], z['a']
                cx, cy = ax + (bx - ax) * p - self.ox, ay + (by - ay) * p - self.oy
                x0, y0, x1, y1 = z['boite']
                gx, gy = self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1]
                bosse = np.exp(-((gx - cx) ** 2 + (gy - cy) ** 2) / z['rayon'] ** 2) * math.sin(math.pi * p)
                part = out[y0:y1, x0:x1]
                k = 1 + z['eclat'] * bosse * z['poids'][y0:y1, x0:x1]
                part[..., :3] = np.minimum(part[..., :3] * k[..., None], 255 * part[..., 3:4])
                continue
            if out is None:
                out = img.copy()
            self.paupiere(out, z, min(max(v, 0.0), 1.0))
        return img if out is None else out

    def paupiere(self, img, z, k):
        cx, cy = z['centre'][0] - self.ox, z['centre'][1] - self.oy
        r = z['rayon']
        x0, x1 = int(cx - r - 2), int(cx + r + 3)
        y0, y1 = int(cy - r - 2), int(cy + r + 3)
        sx, sy = self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1]
        dedans = np.clip(r + 0.5 - np.hypot(sx - cx, sy - cy), 0, 1)
        bord = cy - r + 2 * r * k
        couvre = np.clip(bord - sy + 0.5, 0, 1) * dedans
        bombe = np.exp(-((sx - cx) ** 2 + (sy - (cy - 0.45 * r)) ** 2) / (0.75 * r) ** 2)
        ombre = (0.86 + 0.24 * bombe) * np.clip(1 - 0.25 * np.clip(1.5 - (bord - sy) / 2.5, 0, 1), 0.7, 1)
        peau = np.array(z['couleur'], np.float32)
        cil = np.array([40, 48, 30], np.float32)
        trait = np.clip(1.4 - np.abs(sy - bord), 0, 1) * dedans * min(k * 6, 1.0)
        part = img[y0:y1, x0:x1]
        a = part[..., 3:4]
        rgb = part[..., :3]
        rgb[:] = rgb + ((peau * ombre[..., None]) * a - rgb) * couvre[..., None]
        rgb[:] = rgb + (cil * a - rgb) * trait[..., None]

    # ------------------------------------------------ rendu
    def rendre(self, p, couches, etat, morceau=None):
        """Calcule le rectangle de Thomas. morceau : fonction qui dessine la chair
        tenue en main (entre la paume et les doigts). Renvoie l'image et des infos."""
        sortie = self.derriere.copy()
        info = {}
        # 1. corps : déformation par zones (champ inversé, lecture sous-pixel)
        img = self.couleurs(self.corps, couches)
        boite = self.boite_corps
        ch = self.champ(couches, boite)
        x0, y0, x1, y1 = boite
        qx, qy = self.inverser(self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1], ch)
        rendu = echantillonner(img, qx, qy)
        zone = sortie[y0:y1, x0:x1]
        zone[:] = rendu[..., :3] + zone * (1 - rendu[..., 3:4])
        bouche = np.zeros(sortie.shape[:2], np.float32)
        bouche[y0:y1, x0:x1] = rendu[..., 4]
        info['bouche'] = bouche
        # 2. tige et œil pendant (mouvement secondaire) : devant le visage, derrière le bras
        self._tige(sortie, etat, p)
        # 3. bras : maillage déformé (skinning linéaire) puis main dessinée
        sq = self.squelette(p, couches)
        info['squelette'] = sq
        self._dessiner_bras(sortie, sq, couches)
        fermeture = p.get('squelette.main_fermeture', 0.5)
        dos, devant = self._main(sq, fermeture)
        self._poser(sortie, dos)
        if morceau is not None:
            morceau(sortie, self.ox, self.oy)
        self._poser(sortie, devant)
        info['ancre_tige'] = etat['ancre']
        return sortie, info

    def _poser(self, sortie, calque):
        if calque is None:
            return
        rgba, x0, y0 = calque
        composer(sortie, rgba, x0 - self.ox, y0 - self.oy)

    def transforme_sommets(self, sq, couches):
        V = self.V
        E, C = sq['E'], sq['C']
        cu, su = rot(sq['a_u'])
        cf, sf = rot(sq['a_f'])
        du = V - self.E0
        Tu = E + np.stack([cu * du[:, 0] - su * du[:, 1], su * du[:, 0] + cu * du[:, 1]], 1)
        df = V - self.C0
        Tf = C + np.stack([cf * df[:, 0] - sf * df[:, 1], sf * df[:, 0] + cf * df[:, 1]], 1)
        # le haut de la manche suit le corps (champ des zones au sommet)
        Tb = V.copy()
        haut = self.W[:, 0] > 1e-4
        if haut.any():
            ch = self.champ(self.couches_tronc(couches), self.boite_corps)
            F, ox, oy = ch
            d = echantillonner(F, (V[haut, 0] - self.ox - ox).astype(np.float32),
                               (V[haut, 1] - self.oy - oy).astype(np.float32))
            Tb[haut] = V[haut] + d
        W = self.W
        return W[:, :1] * Tb + W[:, 1:2] * Tu + W[:, 2:3] * Tf

    def _dessiner_bras(self, sortie, sq, couches):
        D = self.transforme_sommets(sq, couches) - [self.ox, self.oy]
        S = self.V - [self.ox, self.oy]
        H, W = sortie.shape[:2]
        qx = np.full((H, W), -100.0, np.float32)
        qy = np.full((H, W), -100.0, np.float32)
        # rastérisation des triangles : chaque pixel de sortie reçoit sa position source
        T = self.tris
        A, B, Cc = D[T[:, 0]], D[T[:, 1]], D[T[:, 2]]
        SA, SB, SC = S[T[:, 0]], S[T[:, 1]], S[T[:, 2]]
        xmin = np.floor(np.minimum(np.minimum(A[:, 0], B[:, 0]), Cc[:, 0])).astype(int)
        xmax = np.ceil(np.maximum(np.maximum(A[:, 0], B[:, 0]), Cc[:, 0])).astype(int)
        ymin = np.floor(np.minimum(np.minimum(A[:, 1], B[:, 1]), Cc[:, 1])).astype(int)
        ymax = np.ceil(np.maximum(np.maximum(A[:, 1], B[:, 1]), Cc[:, 1])).astype(int)
        den = (B[:, 1] - Cc[:, 1]) * (A[:, 0] - Cc[:, 0]) + (Cc[:, 0] - B[:, 0]) * (A[:, 1] - Cc[:, 1])
        ok = np.abs(den) > 1e-9
        den = np.where(ok, den, 1.0)
        # tous les triangles d'un coup : chaque triangle teste une grille K x K de pixels
        K = int(max((xmax - xmin).max(), (ymax - ymin).max())) + 1
        off = np.arange(K)
        px = (xmin[:, None, None] + off[None, None, :]).astype(np.float32) + 0 * off[None, :, None]
        py = (ymin[:, None, None] + off[None, :, None]).astype(np.float32) + 0 * off[None, None, :]
        b0 = (B[:, 1] - Cc[:, 1])[:, None, None]
        b1 = (Cc[:, 0] - B[:, 0])[:, None, None]
        c0 = (Cc[:, 1] - A[:, 1])[:, None, None]
        c1 = (A[:, 0] - Cc[:, 0])[:, None, None]
        ex = px - Cc[:, 0, None, None]
        ey = py - Cc[:, 1, None, None]
        dd = den[:, None, None]
        l1 = (b0 * ex + b1 * ey) / dd
        l2 = (c0 * ex + c1 * ey) / dd
        l3 = 1 - l1 - l2
        dedans = (l1 >= -1e-4) & (l2 >= -1e-4) & (l3 >= -1e-4) & ok[:, None, None]
        dedans &= (px >= 0) & (px < W) & (py >= 0) & (py < H)
        k_i, j_i, i_i = np.nonzero(dedans)          # ordre croissant des triangles : le dernier gagne
        L1, L2, L3 = l1[k_i, j_i, i_i], l2[k_i, j_i, i_i], l3[k_i, j_i, i_i]
        sx = L1 * SA[k_i, 0] + L2 * SB[k_i, 0] + L3 * SC[k_i, 0]
        sy = L1 * SA[k_i, 1] + L2 * SB[k_i, 1] + L3 * SC[k_i, 1]
        X = px[k_i, j_i, i_i].astype(int)
        Y = py[k_i, j_i, i_i].astype(int)
        lin = Y * W + X
        # dernière écriture par pixel (le triangle le plus en avant)
        _, dernier = np.unique(lin[::-1], return_index=True)
        dernier = len(lin) - 1 - dernier
        qx.flat[lin[dernier]] = sx[dernier]
        qy.flat[lin[dernier]] = sy[dernier]
        couvert = qx > -50
        ys, xs = np.nonzero(couvert)
        if len(ys) == 0:
            return
        b0, b1, a0, a1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        r = echantillonner(self.bras, qx[b0:b1, a0:a1], qy[b0:b1, a0:a1]) * couvert[b0:b1, a0:a1, None]
        zone = sortie[b0:b1, a0:a1]
        zone[:] = r[..., :3] + zone * (1 - r[..., 3:4])

    def _main(self, sq, fermeture):
        """Main dessinée par le code (champ de distance), attachée au poignet.
        Renvoie deux calques : dos (paume, pouce) et devant (doigts)."""
        m = self.main
        P = sq['P']
        ang = sq['dir_main']
        R = 30
        x0, y0 = int(P[0]) - R, int(P[1]) - R
        gy, gx = np.mgrid[y0:y0 + 2 * R, x0:x0 + 2 * R].astype(np.float32)
        # repère de la main : u vers les doigts, v côté paume
        c, s = rot(ang)
        dx, dy = gx + 0.5 - P[0], gy + 0.5 - P[1]
        k = m.get('taille', 1.0)
        u = (c * dx + s * dy) / k
        v = (-s * dx + c * dy) / k
        clair, moyen, sombre, trait = (np.array(m[k], np.float32) for k in ('clair', 'moyen', 'sombre', 'trait'))
        gh, gw = self.grain.shape
        grain = self.grain[(np.floor(v * 0.9).astype(int) + 4) % gh, (np.floor(u * 1.1).astype(int) + 40) % gw]
        res = []
        for couche in ('dos', 'devant'):
            rgb = np.zeros(gx.shape + (3,), np.float32)
            a = np.zeros(gx.shape, np.float32)
            if couche == 'dos':
                # paume : capsule épaisse depuis le poignet
                sd = sdf_capsule(u, v, -2, 0.5, 8.5, 0.5, 6.4)
                ombre = (1.0 + 0.10 * np.clip(-v / 6, -1, 1)) * grain
                peindre(rgb, a, sd, moyen, trait, 1.3, ombre)
                # pouce (côté dos, se replie vers la paume quand la main se ferme)
                a1 = -55 + 70 * fermeture
                bx, by = 6.0, -5.0
                ex, ey = tourner(6.5, 0, a1)
                peindre(rgb, a, sdf_capsule(u, v, bx, by, bx + ex, by + ey, 2.3), clair, trait, 1.1)
            else:
                # trois doigts (style pixel art), deux phalanges qui s'enroulent
                for i, off in enumerate((-3.6, 0.2, 3.9)):
                    k1 = 8 + 72 * fermeture + 4 * i * fermeture
                    k2 = 10 + 75 * fermeture
                    ax, ay = 9.0, off
                    e1 = tourner(5.2 - 0.4 * i, 0, k1)
                    bx, by = ax + e1[0], ay + e1[1]
                    e2 = tourner(4.2 - 0.3 * i, 0, k1 + k2)
                    cx, cy = bx + e2[0], by + e2[1]
                    sd = np.minimum(sdf_capsule(u, v, ax, ay, bx, by, 2.0), sdf_capsule(u, v, bx, by, cx, cy, 1.8))
                    coul = clair if i == 0 else (moyen if i == 1 else sombre * 1.15)
                    peindre(rgb, a, sd, coul, trait, 1.0, grain)
            if a.max() <= 0:
                res.append(None)
                continue
            res.append((np.dstack([rgb, a]), x0, y0))
        return res

    def _tige(self, sortie, etat, p):
        """Tige (courbe de Bézier) de l'orbite à l'œil pendant, puis l'œil."""
        t = self.tige
        A = np.array(etat['ancre'])
        X = np.array(etat['oeil'])
        V = np.array(etat['vitesse_oeil'])
        r_oe = t['rayon_oeil']
        haut = X + (A - X) / max(np.linalg.norm(A - X), 1e-6) * (r_oe - 1.5)
        ctrl = A + np.array(t.get('courbure', [0.0, 0.0])) + np.array([0.0, 0.42 * np.linalg.norm(haut - A)]) - V * 0.012
        x0 = int(min(A[0], X[0], ctrl[0])) - 14
        y0 = int(min(A[1], X[1], ctrl[1])) - 14
        x1 = int(max(A[0], X[0], ctrl[0])) + 15
        y1 = int(max(A[1], X[1], ctrl[1])) + 15
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
        sd = np.full(gx.shape, 1e9, np.float32)
        n = 10
        pts = [(1 - s) ** 2 * A + 2 * (1 - s) * s * ctrl + s * s * haut for s in np.linspace(0, 1, n + 1)]
        for i in range(n):
            ep = t['epaisseur'] * (1.0 - 0.25 * i / n)
            sd = np.minimum(sd, sdf_capsule(gx, gy, *pts[i], *pts[i + 1], ep))
        rgb = np.zeros(gx.shape + (3,), np.float32)
        a = np.zeros(gx.shape, np.float32)
        ombre = 1.0 + 0.12 * np.clip((gx - (A[0] + X[0]) / 2) / 3, -1, 1)
        peindre(rgb, a, sd, t['couleur'], t['trait'], 0.9, ombre)
        composer(sortie, np.dstack([rgb, a]), x0 - self.ox, y0 - self.oy)
        # l'œil : pixels d'origine, rotation légère (il « regarde ») + position sous-pixel
        ang = p.get('zones.oeil_pendant_regard', 0.0)
        sp = self.oeil
        h, w = sp.shape[:2]
        if abs(ang) > 0.05:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            cx, cy = (w - 1) / 2, (h - 1) / 2
            ux, uy = tourner(xx - cx, yy - cy, -ang)
            sp = echantillonner(sp, ux + cx, uy + cy)
        coller_sous_pixel(sortie, sp, X[0] - self.ox - (w - 1) / 2, X[1] - self.oy - (h - 1) / 2)


# ================================================================ objets dessinés par le code
class Gant:
    """Gant blanc de laboratoire (et manche de blouse) dessiné par le code.
    Paramètres : x, y (point de pince), angle, ouverture (0 = pince fermée)."""

    def __init__(self, d):
        self.d = d

    def dessiner(self, cadre, p):
        x, y = p.get('x', 0.0), p.get('y', -200.0)
        if y < -60:
            return None
        ang = p.get('angle', 0.0)
        o = p.get('ouverture', 0.0)
        d = self.d
        k = d.get('taille', 1.0)
        x0, y0 = int(x - 30 * k) - 30, 0
        x1, y1 = int(x + 31 * k) + 30, int(y + 16 * k)
        if y1 <= 0:
            return None
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
        c, s = rot(-ang)
        dx, dy = gx - x, gy - y
        u = (c * dx - s * dy) / k       # repère du gant : v vers le bas (vers les doigts)
        v = (s * dx + c * dy) / k
        rgb = np.zeros(gx.shape + (3,), np.float32)
        a = np.zeros(gx.shape, np.float32)
        blanc, ombre_c, trait = (np.array(d[k], np.float32) for k in ('blanc', 'ombre', 'trait'))
        blouse = np.array(d['blouse'], np.float32)
        # manche de blouse qui monte hors de l'image
        peindre(rgb, a, sdf_capsule(u, v, 1.5, -400, 1.5, -36, 11.5), blouse, trait, 1.0,
                1.0 - 0.10 * np.clip(u / 11, -1, 1))
        # revers du gant
        peindre(rgb, a, sdf_capsule(u, v, -6.5, -31, 9.5, -31, 4.2), blanc * 0.97, trait, 1.1)
        # paume
        sh = 1.0 - 0.14 * np.clip(u / 9, -1, 1)
        peindre(rgb, a, sdf_capsule(u, v, 1.5, -24, 1.5, -12, 8.2), blanc, trait, 1.2, sh)
        # doigts repliés (majeur, annulaire) à l'arrière
        peindre(rgb, a, sdf_capsule(u, v, 6.5, -12, 8.0 + 2 * o, -5 + o, 2.4), ombre_c, trait, 1.0)
        # pouce et index : la pince (s'ouvre avec « ouverture »)
        peindre(rgb, a, sdf_capsule(u, v, -6.0, -14, -3.0 - 6 * o, -1.5 - 1 * o, 2.5), blanc, trait, 1.0)
        peindre(rgb, a, sdf_capsule(u, v, 3.5, -12, 1.8 + 6 * o, -0.5 - 1 * o, 2.4), blanc * 0.98, trait, 1.0)
        return composer(cadre, np.dstack([rgb, a]), x0, y0)


class Morceau:
    """Morceau de viande crue dessiné par le code (pixel art, tons rosés et rouges,
    petits filaments). Objet animable : position, angle, écrasement, bouchées."""

    def __init__(self, d):
        self.d = d
        rng = np.random.default_rng(7)
        self.bruit = rng.uniform(0, 2 * math.pi, 6)

    def rgba(self, p, etat, cx, cy):
        """Image RGBA prémultipliée du morceau centré en (cx, cy) (monde)."""
        d = self.d
        ang = p.get('angle', 0.0)
        e = p.get('ecrasement', 0.0) + etat.get('tremble', 0.0)
        sx, sy = 1 + e, 1 / (1 + e)
        R = 22
        x0, y0 = int(cx) - R, int(cy) - R
        gy, gx = np.mgrid[y0:y0 + 2 * R, x0:x0 + 2 * R].astype(np.float32) + 0.5
        c, s = rot(-ang)
        dx, dy = gx - cx, gy - cy
        u = (c * dx - s * dy) / sx
        v = (s * dx + c * dy) / sy
        rx, ry = d['rayons']
        th = np.arctan2(v, u)
        b = self.bruit
        rr = 1 + 0.05 * np.sin(2 * th + b[0]) + 0.035 * np.sin(5 * th + b[1]) + 0.03 * np.sin(9 * th + b[2])
        n4 = (np.abs(u / rx) ** 3 + np.abs(v / ry) ** 3) ** (1 / 3)      # bloc aux coins arrondis
        sd = (n4 / rr - 1) * min(rx, ry)
        # bouchées : disques retirés (côté bouche), qui grandissent pendant la morsure
        n_b = p.get('bouchees', 0.0)
        sd_b = np.full(gx.shape, 1e9, np.float32)
        for k, cercles in enumerate(d['bouchees']):
            f = min(max(n_b - k, 0.0), 1.0)
            if f > 0:
                for (bx, by, br) in cercles:      # un grand cercle + petites traces de dents
                    # la bouchée entre par le bord (comme des dents qui se referment)
                    cxb = bx - (1 - f) * (br + 6.0) * (1 if bx <= 0 else -1)
                    sd_b = np.minimum(sd_b, np.hypot(u - cxb, v - by) - br)
        sd = np.maximum(sd, -sd_b)
        cov = np.clip(0.5 - sd, 0, 1)
        # couleurs : rouge au bord, rose au centre, reflet, marbrures de gras
        prof = np.floor(np.clip(-sd / 5.0, 0, 1) * 3.0 + 0.5) / 3.0       # aplats (pixel art)
        rouge, rose, gras, trait, coupe = (np.array(d[k], np.float32) for k in ('rouge', 'rose', 'gras', 'trait', 'coupe'))
        coul = rouge + (rose - rouge) * prof[..., None]
        reflet = np.clip(1 - np.hypot(u + rx * 0.35, v + ry * 0.45) / 4.0, 0, 1)
        coul = coul + (np.array([250, 190, 195], np.float32) - coul) * (0.55 * reflet)[..., None]
        marbre = np.clip((np.sin(0.55 * v + 1.4 * np.sin(0.35 * u + b[3])) - 0.86) * 5, 0, 1) * (prof > 0.3)
        coul = coul + (gras - coul) * (0.55 * marbre)[..., None]
        # chair à vif sur le bord des bouchées
        vif = np.clip(1.8 - np.abs(sd_b), 0, 1) * (sd_b < 3)
        coul = coul + (coupe - coul) * vif[..., None]
        bordure = np.clip(1.2 + sd, 0, 1) * (1 - vif)
        coul = coul + (trait - coul) * bordure[..., None]
        a = cov
        rgb = coul
        # filaments qui pendent (suivent le mouvement avec retard)
        bal = etat.get('balancement', 0.0)
        gx_l, gy_l = tourner(0.0, 1.0, -ang)            # « vers le bas » dans le repère du morceau
        px_l, py_l = -gy_l, gx_l
        if n_b < 1.95:
            for i, (fu, fl) in enumerate(d['filaments']):
                ax_ = gx_l * ry * 0.8 + px_l * fu
                ay_ = gy_l * ry * 0.8 + py_l * fu
                # le filament part avec une bouchée si son point d'attache est mangé
                mange = False
                for k, cercles in enumerate(d['bouchees']):
                    f = min(max(n_b - k, 0.0), 1.0)
                    for (bx, by, br) in cercles:
                        cxb = bx - (1 - f) * (br + 6.0) * (1 if bx <= 0 else -1)
                        if f > 0 and math.hypot(ax_ - cxb, ay_ - by) < br + 1:
                            mange = True
                if mange:
                    continue
                lat = bal * fl * 0.6 + 0.8 * math.sin(i * 2.1)
                bx_ = ax_ + gx_l * fl + px_l * lat
                by_ = ay_ + gy_l * fl + py_l * lat
                sdf = sdf_capsule(u, v, ax_, ay_, bx_, by_, 0.55)
                cf = np.clip(0.5 - sdf / 0.8, 0, 1) * 0.85
                na = a + cf * (1 - a)
                rgb = (rgb * a[..., None] + np.array(d['filament'], np.float32) * (cf * (1 - a))[..., None]) / np.maximum(na, 1e-6)[..., None]
                a = na
        if a.max() <= 0:
            return None
        return np.dstack([rgb * a[..., None], a]), x0, y0


# ================================================================ mouches
class Mouches:
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
        for i, (cx, cy, rx, ry, nx, ny, ph) in enumerate(self.d['vols']):
            a = 2 * math.pi * (t / T + ph)
            x = cx + rx * math.sin(nx * a) + 0.35 * rx * math.sin(3 * nx * a + 1.1)
            y = cy + ry * math.sin(ny * a + 0.7)
            # agitation : petits crochets rapides ; attraction : vers le morceau
            x += ag * 9 * math.sin(2 * math.pi * (t * 3.1 + i * 0.37))
            y += ag * 7 * math.sin(2 * math.pi * (t * 2.3 + i * 0.61))
            if cible is not None and at > 0:
                k = at * self.d['attirees'][i]
                ox, oy = 13 * math.cos(a * 2 + i), 9 * math.sin(a * 2 + i) - 10
                x += (cible[0] + ox - x) * k
                y += (cible[1] + oy - y) * k
            res.append((x, y))
        return res

    def dessiner(self, cadre, t, p, cible):
        rects = []
        for i, (x, y) in enumerate(self.positions(t, p, cible)):
            sp = self.mouche if (int(t * 24) + i) % 2 == 0 else self.sans_ailes
            h, w = sp.shape[:2]
            r = coller_sous_pixel(cadre, sp, x - w / 2, y - h / 2)
            if r:
                rects.append(r)
        return rects


# ================================================================ scène
class Scene:
    def __init__(self, fichier='scene.json', sequence=None):
        d = lire_json(fichier)
        self.d = d
        self.fond = np.asarray(Image.open(chemin(d['fond'])).convert('RGB')).astype(np.float32)
        self.objets = {o['nom']: o for o in d['objets']}
        self.thomas = Thomas(self.objets['thomas'])
        self.gant = Gant(self.objets['gant']['animable']['dessin'])
        self.morceau = Morceau(self.objets['morceau']['animable']['dessin'])
        self.mouches = Mouches(self.objets['mouches']['animable'])
        self.actions = lire_json('actions.json')
        self.sequence = Sequence(sequence) if sequence else None
        self.recettes = {}
        self.cadre = self.fond.copy()
        self.sales = []
        self.etat = None
        self.t_sim = None
        self.dernier = {}

    def declencher(self, nom_action):
        """Action du joueur -> zone touchée -> séquence et recettes jouées ensemble."""
        a = self.actions[nom_action]
        self.sequence = Sequence(a['sequence'])
        if 'recettes' in a:
            self.sequence.recettes = a['recettes']
        self.etat = None

    def recette(self, nom):
        if nom not in self.recettes:
            self.recettes[nom] = lire_json(os.path.join('recettes', nom + '.json'))
        return self.recettes[nom]

    # ------------------------------------------------ valeurs à l'instant t
    def parametres(self, objet, t):
        p = self.sequence.valeurs(objet, t) if self.sequence else {}
        zones = []
        tl = t % self.sequence.duree if self.sequence else t
        for nom in (self.sequence.recettes.get(objet, []) if self.sequence else []):
            for c in self.recette(nom)['couches']:
                v = c.get('amplitude', 1.0) * courbe_periodique(c.get('courbe', 'constante'), tl, c.get('duree', 1.0), c.get('phase', 0.0), c)
                if 'module' in c:                # intensité réglée par un paramètre de la pose
                    v *= p.get(c['module'], 1.0)
                if 'parametre' in c:
                    p[c['parametre']] = p.get(c['parametre'], 0.0) + v
                else:
                    zones.append((c['zone'], c['effet'], v))
        return p, zones

    def _morceau_brut(self, t, att):
        """Position et angle (monde) du morceau pour un mode d'attache donné."""
        pm, _ = self.parametres('morceau', t)
        if att == 'main':
            pt, zt = self.parametres('thomas', t)
            sq = self.thomas.squelette(pt, self.thomas.couches(pt, zt))
            pos = self.thomas.point_main(pt, sq, pt.get('attaches.prise_main', [16, 2]))
            return pos, pm.get('angle_main', 0.0) + sq['dir_main']
        if att == 'gant':
            pg, _ = self.parametres('gant', t)
            dx, dy = pm.get('decalage', [0, 8])
            ox, oy = tourner(dx, dy, pg.get('angle', 0.0))
            return np.array([pg['x'] + ox, pg['y'] + oy]), pm.get('angle', 0.0) + pg.get('angle', 0.0)
        return np.array([pm.get('x', -100.0), pm.get('y', -100.0)]), pm.get('angle', 0.0)

    def morceau_monde(self, t):
        """Quand l'attache change (gant -> libre -> main), l'écart éventuel entre
        l'ancienne et la nouvelle position est résorbé en douceur (0,2 s)."""
        pm, _ = self.parametres('morceau', t)
        att = pm.get('attache', 'libre')
        pos, ang = self._morceau_brut(t, att)
        piste = self.sequence.pistes['morceau']
        tm = t % self.sequence.duree
        for i in range(1, len(piste.cles)):
            k = piste.cles[i]
            avant = piste.cles[i - 1]['v'].get('attache')
            if k['v'].get('attache') != avant and 0 <= tm - k['arrivee'] < 0.2:
                ts = t - (tm - k['arrivee'])
                p_old, a_old = self._morceau_brut(ts, avant)
                p_new, a_new = self._morceau_brut(ts, k['v'].get('attache'))
                f = 1 - lissage((tm - k['arrivee']) / 0.2)
                pos = pos + (p_old - p_new) * f
                ang = ang + ((a_old - a_new + 180.0) % 360.0 - 180.0) * f
        return pos, ang

    # ------------------------------------------------ mouvement secondaire (ressorts amortis)
    def _etat_initial(self):
        tg = self.thomas.tige
        return {'oeil': np.array(tg['oeil_repos'], np.float64), 'v_oeil': np.zeros(2),
                'cheveux': 0.0, 'v_cheveux': 0.0, 'cible_cheveux': 0.0,
                'tremble': 0.0, 'v_tremble': 0.0, 'pos_m': None, 'vit_m': np.zeros(2),
                'balancement': 0.0, 'v_bal': 0.0}

    def _pas(self, t, dt):
        th = self.thomas
        tg = th.tige
        pt, zt = self.parametres('thomas', t)
        couches = th.couches(pt, zt)
        e = self.etat
        dx, dy, r = th.deplacement_point(couches, *tg['ancre'])
        A = np.array(tg['ancre']) + [dx, dy]
        sq = th.squelette(pt, couches)
        pm, _ = self.parametres('morceau', t)
        pos_m = self.morceau_monde(t)[0] if pm.get('visible', 1) > 0.5 else None
        n = 8
        h = dt / n
        L0 = tg['longueur']
        for _ in range(n):
            X, V = e['oeil'], e['v_oeil']
            d = X - A
            L = max(np.linalg.norm(d), 1e-6)
            F = np.array([0.0, tg['gravite']])
            F -= tg['raideur'] * (L - L0) * d / L
            F -= tg['amortissement'] * V
            # la main et le morceau poussent l'œil s'ils passent tout près
            for q, rq in ((th.point_main(pt, sq, [8, 0]), 16.0), (pos_m, 18.0)):
                if q is None:
                    continue
                dq = X - q
                lq = np.linalg.norm(dq)
                if lq < rq:     # contact doux : force qui croît progressivement
                    F += dq / max(lq, 1e-3) * (rq - lq) ** 2 * 18.0
            V = V + F * h
            e['oeil'] = X + V * h
            e['v_oeil'] = V
        e['ancre'] = A.tolist()
        # cheveux : suivent la rotation de la tête avec retard
        cible = pt.get('zones.tete_rotation', 0.0) + sum(v for z, ef, v in zt if z == 'tete' and ef == 'rotation')
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

    def prechauffer(self, fps):
        """Simule une boucle entière avant de filmer : l'état des ressorts au début
        du film est alors celui de la fin de boucle (boucle continue)."""
        self.etat = self._etat_initial()
        self.etat['ancre'] = self.thomas.tige['ancre']
        D = self.sequence.duree
        n = int(round(D * fps))
        for i in range(n):
            self._pas(i / fps, 1.0 / fps)
        self.t_sim = 0.0

    def image(self, t, fps=24):
        """Calcule l'image au temps t (float32 640x480x3). Les appels doivent se
        suivre dans le temps (les ressorts avancent d'une image à l'autre)."""
        if self.etat is None:
            self.prechauffer(fps)
        self._pas(t, 1.0 / fps)
        e = self.etat
        th = self.thomas
        # 1. on remet le décor fixe uniquement là où on avait dessiné
        for (x0, y0, x1, y1) in self.sales:
            self.cadre[y0:y1, x0:x1] = self.fond[y0:y1, x0:x1]
        sales = []
        pt, zt = self.parametres('thomas', t)
        zt = zt + [('cheveux', 'rotation', (e['cheveux'] - e['cible_cheveux']) * 1.6)]
        couches = th.couches(pt, zt)
        pm, _ = self.parametres('morceau', t)
        sq = th.squelette(pt, couches)
        visible = pm.get('visible', 1) > 0.5
        pos_m, ang_m = self.morceau_monde(t) if visible else (None, 0.0)
        if pos_m is not None:
            e['cible_mouches'] = pos_m
        etat_m = {'tremble': e['tremble'], 'balancement': e['balancement']}
        img_m = self.morceau.rgba({**pm, 'angle': ang_m}, etat_m, *pos_m) if visible else None
        en_main = visible and pm.get('attache') == 'main'
        rects_m = []

        def dessiner_morceau(sortie, ox, oy):
            if img_m is not None:
                rgba, x0, y0 = img_m
                composer(sortie, rgba, x0 - ox, y0 - oy)

        # 2. Thomas : seul son rectangle est recalculé
        etat_t = {'ancre': e['ancre'], 'oeil': e['oeil'].tolist(), 'vitesse_oeil': e['v_oeil'].tolist()}
        img_t, info = th.rendre(pt, couches, etat_t, dessiner_morceau if en_main else None)
        x, y, w, h = th.rect
        self.cadre[y:y + h, x:x + w] = img_t
        sales.append((x, y, x + w, y + h))
        # 3. morceau libre ou tenu par le gant, gant, mouches (par-dessus)
        if img_m is not None and not en_main:
            r = composer(self.cadre, *img_m)
            if r:
                sales.append(r)
                rects_m.append(r)
        pg, _ = self.parametres('gant', t)
        r = self.gant.dessiner(self.cadre, pg)
        if r:
            sales.append(r)
        pmo, _ = self.parametres('mouches', t)
        sales += self.mouches.dessiner(self.cadre, t, pmo, e.get('cible_mouches'))
        self.sales = sales
        # informations pour le contrôle
        bouche = np.zeros(self.cadre.shape[:2], np.float32)
        bouche[y:y + h, x:x + w] = info['bouche']
        alpha_m = np.zeros(self.cadre.shape[:2], np.float32)
        if img_m is not None:
            rgba, x0, y0 = img_m
            a = np.zeros(rgba.shape[:2] + (4,), np.float32)
            a[..., 3] = rgba[..., 3]
            a[..., 0] = rgba[..., 3]
            composer(alpha_m[..., None].repeat(3, 2), a, x0, y0)
            vide = np.zeros(alpha_m.shape + (3,), np.float32)
            composer(vide, a, x0, y0)
            alpha_m = vide[..., 0]
        self.dernier = {'sales': list(sales), 'squelette': sq, 'morceau': pos_m, 'bouche': bouche,
                        'alpha_morceau': alpha_m, 'oeil': e['oeil'].copy(), 'parametres': pt,
                        'gant': (pg.get('x'), pg.get('y'))}
        return self.cadre

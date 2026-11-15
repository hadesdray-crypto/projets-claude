"""Moteur d'animation par zones (démo Thomas le zombie).

Principe :
  - le décor est une image fixe, copiée une seule fois ; à chaque image on ne
    recalcule que les rectangles des objets animés (et des particules) ;
  - un objet devient animé en recevant un composant « animable » (scene.json) :
    calques découpés + cartes de zones (niveaux de gris) ;
  - une animation est une recette JSON : liste de couches
    {zone, effet, amplitude, duree, courbe, phase, debut, fin, attaque, relache} ;
    le moteur additionne les couches de toutes les recettes actives, rien de plus.
Bibliothèques : numpy, Pillow (libres).
"""
import json
import math
import os

import numpy as np
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))


def chemin(*p):
    return os.path.join(ICI, *p)


def lire_json(p):
    with open(chemin(p), encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------- courbes
def lissage(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def courbe(nom, t, duree, phase, couche):
    """Valeur de la courbe au temps t (secondes). Toutes sont périodiques de
    période « duree », sauf « constante »."""
    if nom == 'constante':
        return 1.0
    x = t / duree + phase
    if nom == 'sinus':
        return math.sin(2 * math.pi * x)
    if nom == 'sinus_positif':                       # 0 → 1 → 0
        return 0.5 - 0.5 * math.cos(2 * math.pi * x)
    if nom == 'bruit':                               # bruit doux et périodique
        return (math.sin(2 * math.pi * x) * 0.55 + math.sin(2 * math.pi * (3 * x + 0.31)) * 0.3
                + math.sin(2 * math.pi * (7 * x + 0.67)) * 0.15)
    if nom == 'clignement':                          # fermeture brève une fois par période
        largeur = couche.get('largeur', 0.24) / duree
        f = x - math.floor(x)
        return math.sin(math.pi * f / largeur) if f < largeur else 0.0
    raise ValueError('courbe inconnue : ' + nom)


def enveloppe(t, c):
    """Entrée et sortie progressives d'une couche (attaque / relâche)."""
    debut = c.get('debut', 0.0)
    if t < debut:
        return 0.0
    att = c.get('attaque', 0.0)
    e = 1.0 if att <= 0 else lissage((t - debut) / att)
    fin = c.get('fin')
    if fin is not None:
        rel = c.get('relache', 0.0)
        if t >= fin + rel:
            return 0.0
        if t > fin:
            e *= 1.0 - (lissage((t - fin) / rel) if rel > 0 else 1.0)
    return e


def valeur(c, t):
    return c.get('amplitude', 1.0) * enveloppe(t, c) * courbe(
        c.get('courbe', 'constante'), t, c.get('duree', 1.0), c.get('phase', 0.0), c)


# ---------------------------------------------------------------- outils image
def echantillonner(img, qx, qy):
    """Lecture bilinéaire (sous-pixel) de img (h,w,c) aux positions qx,qy ; 0 hors image."""
    h, w = img.shape[:2]
    x0 = np.floor(qx).astype(np.int32)
    y0 = np.floor(qy).astype(np.int32)
    fx = (qx - x0)[..., None].astype(np.float32)
    fy = (qy - y0)[..., None].astype(np.float32)
    out = 0
    for dy, wy in ((0, 1 - fy), (1, fy)):
        for dx, wx in ((0, 1 - fx), (1, fx)):
            xi = x0 + dx
            yi = y0 + dy
            ok = ((xi >= 0) & (xi < w) & (yi >= 0) & (yi < h))[..., None]
            v = img[np.clip(yi, 0, h - 1), np.clip(xi, 0, w - 1)]
            out = out + v * (wx * wy * ok)
    return out


def coller_sous_pixel(cadre, sprite_pm, x, y, opacite=1.0):
    """Pose un sprite (RGBA prémultiplié, float) à une position non entière :
    décalage bilinéaire, donc glissement doux. Retourne le rectangle touché."""
    h, w = sprite_pm.shape[:2]
    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - ix, y - iy
    s = np.zeros((h + 1, w + 1, 4), np.float32)
    s[:h, :w] += sprite_pm * (1 - fx) * (1 - fy)
    s[:h, 1:] += sprite_pm * fx * (1 - fy)
    s[1:, :w] += sprite_pm * (1 - fx) * fy
    s[1:, 1:] += sprite_pm * fx * fy
    s *= opacite
    H, W = cadre.shape[:2]
    x0, y0, x1, y1 = max(ix, 0), max(iy, 0), min(ix + w + 1, W), min(iy + h + 1, H)
    if x0 >= x1 or y0 >= y1:
        return None
    part = s[y0 - iy:y1 - iy, x0 - ix:x1 - ix]
    zone = cadre[y0:y1, x0:x1]
    zone[:] = part[..., :3] + zone * (1 - part[..., 3:4])
    return (x0, y0, x1, y1)


def charger_rgba(p):
    a = np.asarray(Image.open(chemin(p)).convert('RGBA')).astype(np.float32)
    a[..., 3] /= 255.0
    a[..., :3] *= a[..., 3:4]                       # prémultiplié
    return a


# ---------------------------------------------------------------- objet animable
class Animable:
    """Composant ajoutable à n'importe quel objet de la scène."""

    def __init__(self, objet, defn):
        self.nom = objet['nom']
        x, y, w, h = objet['rect']
        self.rect = (x, y, w, h)
        sl = (slice(y, y + h), slice(x, x + w))
        fond = np.asarray(Image.open(chemin(defn.get('derriere', 'decor/fond.png'))).convert('RGB')).astype(np.float32)
        self.derriere = fond[sl].copy()
        self.calques = []
        calques = defn.get('calques') or [{'nom': 'entier', 'image': None, 'ordre': 0}]
        for c in calques:
            if c.get('image'):
                img = charger_rgba(c['image'])[sl].copy()
            else:                                   # objet de décor sans découpe : tout le rectangle
                img = np.dstack([self.derriere, np.ones(self.derriere.shape[:2], np.float32)])
            ys, xs = np.nonzero(img[..., 3] > 0)
            boite = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
            self.calques.append({**c, 'img': img, 'boite': boite})
        self.calques.sort(key=lambda c: c.get('ordre', 0))
        self.zones = {}
        for nom, z in defn.get('zones', {}).items():
            z = dict(z)
            if 'carte' in z:
                z['poids'] = np.asarray(Image.open(chemin(z['carte'])).convert('L')).astype(np.float32)[sl] / 255.0
                ys, xs = np.nonzero(z['poids'] > 0)
                z['boite'] = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
            for k in ('pivot', 'centre'):
                if k in z:
                    z[k] = (z[k][0] - x, z[k][1] - y)   # coordonnées locales au rectangle
            self.zones[nom] = z
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.gx, self.gy = gx, gy

    # -- champ de déplacement d'un calque (somme pondérée des couches de géométrie),
    #    calculé seulement sur la boîte (x0, y0, x1, y1) en coordonnées locales
    def champ(self, nom_calque, couches, boite):
        x0, y0, x1, y1 = boite
        gx, gy = self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1]
        fx = np.zeros_like(gx)
        fy = np.zeros_like(gy)
        actif = False
        for zn, effet, v, c in couches:
            z = self.zones[zn]
            if z.get('type') == 'calque' or 'poids' not in z or z.get('calque', 'corps') != nom_calque:
                continue
            if abs(v) < 1e-5:
                continue
            w = z['poids'][y0:y1, x0:x1]
            if effet == 'deplacement_x':
                fx += w * v
            elif effet == 'deplacement_y':
                fy += w * v
            elif effet == 'rotation':
                px, py = z['pivot']
                a = math.radians(v)
                ca, sa = math.cos(a) - 1, math.sin(a)
                dx, dy = gx - px, gy - py
                fx += w * (ca * dx - sa * dy)
                fy += w * (sa * dx + ca * dy)
            elif effet in ('echelle', 'echelle_x', 'echelle_y'):
                px, py = z['pivot']
                if effet != 'echelle_y':
                    fx += w * v * (gx - px)
                if effet != 'echelle_x':
                    fy += w * v * (gy - py)
            else:
                continue
            actif = True
        return (np.dstack([fx, fy]), x0, y0) if actif else None

    @staticmethod
    def inverser(px, py, champ):
        """Le champ dit où va chaque pixel source ; on cherche, pour chaque
        pixel de sortie, d'où il vient (point fixe, 3 passes, sous-pixel)."""
        F, ox, oy = champ
        qx, qy = px, py
        for _ in range(3):
            d = echantillonner(F, qx - ox, qy - oy)
            qx, qy = px - d[..., 0], py - d[..., 1]
        return qx, qy

    def couleurs(self, img, nom_calque, couches):
        """Effets de couleur, appliqués aux pixels du calque avant déformation
        (ils suivent donc le mouvement). Seuls les pixels de la zone changent."""
        out = None
        for zn, effet, v, c in couches:
            z = self.zones[zn]
            if z.get('calque', 'corps') != nom_calque or abs(v) < 1e-4:
                continue
            if effet not in ('luminosite', 'lueur', 'teinte', 'paupiere'):
                continue
            if out is None:
                out = img.copy()
            if effet == 'paupiere':
                self.paupiere(out, z, min(max(v, 0.0), 1.0))
                continue
            x0, y0, x1, y1 = z['boite']
            part = out[y0:y1, x0:x1]
            w = z['poids'][y0:y1, x0:x1, None]
            a = part[..., 3:4]
            if effet == 'luminosite':
                part[..., :3] *= 1 + w * v
            elif effet == 'lueur':
                part[..., :3] += w * v * 255 * a
            elif effet == 'teinte':
                coul = np.array(c['couleur'], np.float32)
                part[..., :3] += (coul * a - part[..., :3]) * w * v
            np.clip(part[..., :3], 0, 255 * a, out=part[..., :3])
        return img if out is None else out

    def paupiere(self, img, z, k):
        """Paupière qui descend sur un œil rond : bord net mais sous-pixel."""
        cx, cy = z['centre']
        r = z['rayon']
        x0, x1 = int(cx - r - 2), int(cx + r + 3)
        y0, y1 = int(cy - r - 2), int(cy + r + 3)
        sx, sy = self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1]
        dedans = np.clip(r + 0.5 - np.hypot(sx - cx, sy - cy), 0, 1)
        bord = cy - r + 2 * r * k                      # position du bord de la paupière
        couvre = np.clip(bord - sy + 0.5, 0, 1) * dedans
        # relief : bombé clair au centre de la paupière, plus sombre vers le bord
        bombe = np.exp(-((sx - cx) ** 2 + (sy - (cy - 0.45 * r)) ** 2) / (0.75 * r) ** 2)
        ombre = (0.86 + 0.24 * bombe) * np.clip(1 - 0.25 * np.clip(1.5 - (bord - sy) / 2.5, 0, 1), 0.7, 1)
        peau = np.array(z['couleur'], np.float32)
        cil = np.array(z.get('couleur_bord', [40, 48, 30]), np.float32)
        trait = np.clip(1.4 - np.abs(sy - bord), 0, 1) * dedans * min(k * 6, 1.0)
        part = img[y0:y1, x0:x1]
        a = part[..., 3:4]
        rgb = part[..., :3]
        rgb[:] = rgb + ((peau * ombre[..., None]) * a - rgb) * couvre[..., None]
        rgb[:] = rgb + (cil * a - rgb) * trait[..., None]

    def borner(self, x0, y0, x1, y1):
        h, w = self.gx.shape
        return (max(int(math.floor(x0)), 0), max(int(math.floor(y0)), 0),
                min(int(math.ceil(x1)), w), min(int(math.ceil(y1)), h))

    def rendre(self, couches):
        """Calcule le rectangle de l'objet pour l'instant donné."""
        sortie = self.derriere.copy()
        transfo = {}
        for cal in self.calques:
            nom = cal['nom']
            img = self.couleurs(cal['img'], nom, couches)
            bx0, by0, bx1, by1 = cal['boite']
            parent = cal.get('parent')
            if not parent:
                # calque racine : déformation par zones seulement
                boite = self.borner(bx0 - 16, by0 - 16, bx1 + 16, by1 + 16)
                ch = self.champ(nom, couches, boite)
                transfo[nom] = ch
                if ch is None:
                    rendu, boite = img, (0, 0, img.shape[1], img.shape[0])
                    x0, y0, x1, y1 = boite
                else:
                    x0, y0, x1, y1 = boite
                    qx, qy = self.inverser(self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1], ch)
                    rendu = echantillonner(img, qx, qy)
            else:
                # calque enfant : transformation rigide (rotation autour du pivot +
                # translation) + mouvement du parent au point d'attache + zones locales
                zc = self.zones[nom]
                cx, cy = zc['pivot']
                ang, tx, ty = 0.0, 0.0, 0.0
                for zn, effet, v, c in couches:
                    if zn != nom:
                        continue
                    if effet == 'rotation':
                        ang += v
                    elif effet == 'deplacement_x':
                        tx += v
                    elif effet == 'deplacement_y':
                        ty += v
                pch = transfo.get(parent)
                if pch is not None:
                    dx, dy, rot = self.mouvement_au_point(pch, cx, cy)
                    tx, ty, ang = tx + dx, ty + dy, ang + rot
                a = math.radians(ang)
                ca, sa = math.cos(a), math.sin(a)
                # boîte de destination : coins de la boîte source transformés
                coins = [(bx0 - 4, by0 - 4), (bx1 + 4, by0 - 4), (bx0 - 4, by1 + 4), (bx1 + 4, by1 + 4)]
                xs = [ca * (u - cx) - sa * (v - cy) + cx + tx for u, v in coins]
                ys = [sa * (u - cx) + ca * (v - cy) + cy + ty for u, v in coins]
                x0, y0, x1, y1 = self.borner(min(xs), min(ys), max(xs) + 1, max(ys) + 1)
                if x0 >= x1 or y0 >= y1:
                    continue
                ux = self.gx[y0:y1, x0:x1] - cx - tx
                uy = self.gy[y0:y1, x0:x1] - cy - ty
                qx, qy = ca * ux + sa * uy + cx, -sa * ux + ca * uy + cy
                ch = self.champ(nom, couches, self.borner(bx0 - 6, by0 - 6, bx1 + 6, by1 + 6))
                if ch is not None:
                    qx, qy = self.inverser(qx, qy, ch)
                rendu = echantillonner(img, qx, qy)
            zone = sortie[y0:y1, x0:x1]
            sortie[y0:y1, x0:x1] = rendu[..., :3] + zone * (1 - rendu[..., 3:4])
        return sortie

    @staticmethod
    def mouvement_au_point(champ, x, y):
        F, ox, oy = champ
        ix, iy = int(round(x)) - ox, int(round(y)) - oy
        fx, fy = F[..., 0], F[..., 1]
        dx, dy = float(fx[iy, ix]), float(fy[iy, ix])
        # rotation locale estimée par les dérivées du champ
        rot = 0.5 * ((fy[iy, ix + 2] - fy[iy, ix - 2]) / 4 - (fx[iy + 2, ix] - fx[iy - 2, ix]) / 4)
        return dx, dy, math.degrees(rot)


# ---------------------------------------------------------------- particules
def lettre_z(echelle):
    motif = ["11111", "00011", "00110", "01100", "11111"]
    m = np.array([[c == '1' for c in l] for l in motif], np.float32)
    m = np.kron(m, np.ones((echelle, echelle), np.float32))
    m = np.pad(m, 1)
    contour = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            contour = np.maximum(contour, np.roll(np.roll(m, dy, 0), dx, 1))
    rgba = np.zeros(m.shape + (4,), np.float32)
    rgba[..., :3] = np.where(m[..., None] > 0, [245, 248, 250], [30, 36, 40])
    rgba[..., 3] = np.maximum(m, contour)
    rgba[..., :3] *= rgba[..., 3:4]
    return rgba


def anneau(rayon):
    n = int(rayon * 2 + 4)
    y, x = np.mgrid[0:n, 0:n] - (n - 1) / 2
    d = np.hypot(x, y)
    a = np.clip(1.2 - np.abs(d - rayon), 0, 1) * 0.9
    rgba = np.zeros((n, n, 4), np.float32)
    rgba[..., :3] = 255
    rgba[..., 3] = a
    rgba[..., :3] *= a[..., None]
    return rgba


class Particules:
    def __init__(self):
        m = charger_rgba('decor/mouche.png')
        lum = m[..., :3].sum(2) / np.maximum(m[..., 3], 1e-3) / 3
        self.mouche = m
        self.mouche_sans_ailes = m * (1 - ((lum > 150) & (m[..., 3] > 0)))[..., None]
        self.z = {1: lettre_z(2), 2: lettre_z(3)}
        self.anneau = anneau(7)

    def dessiner(self, cadre, couche, v, t):
        """v = intensité (0..1) issue de l'enveloppe ; renvoie les rectangles touchés."""
        effet = couche['effet']
        rects = []
        if v <= 0.002:
            return rects
        if effet == 'mouches':
            T = couche['duree']
            for i, m in enumerate(couche['vols']):
                cx, cy, rx, ry, nx, ny, ph = m
                a = 2 * math.pi * (t / T + ph)
                x = cx + rx * math.sin(nx * a) + 0.35 * rx * math.sin(3 * nx * a + 1.1)
                y = cy + ry * math.sin(ny * a + 0.7)
                # battement d'ailes : pixels d'ailes allumés / éteints
                sp = self.mouche if (int(t * 25) + i) % 2 == 0 else self.mouche_sans_ailes
                h, w = sp.shape[:2]
                r = coller_sous_pixel(cadre, sp, x - w / 2, y - h / 2)
                if r:
                    rects.append(r)
        elif effet == 'zzz':
            T = couche['duree']
            x0, y0 = couche['origine']
            n = couche.get('nombre', 3)
            for i in range(n):
                f = (t / T + i / n) % 1.0
                montee = couche.get('hauteur', 40) * f
                x = x0 + 10 * f + 3 * math.sin(2 * math.pi * (f * 1.5 + i * 0.3))
                y = y0 - montee
                op = min(f / 0.2, 1.0) * min((1 - f) / 0.3, 1.0) * v
                sp = self.z[1 if f < 0.45 else 2]
                h, w = sp.shape[:2]
                r = coller_sous_pixel(cadre, sp, x - w / 2, y - h / 2, op)
                if r:
                    rects.append(r)
        elif effet == 'curseur':
            T = couche['duree']
            (ax, ay), (bx, by) = couche['de'], couche['a']
            f = 0.5 - 0.5 * math.cos(2 * math.pi * t / T)
            x, y = ax + (bx - ax) * f, ay + (by - ay) * f
            h, w = self.anneau.shape[:2]
            r = coller_sous_pixel(cadre, self.anneau, x - w / 2, y - h / 2, v)
            if r:
                rects.append(r)
        return rects


EFFETS_PARTICULES = ('mouches', 'zzz', 'curseur')


# ---------------------------------------------------------------- scène
class Scene:
    def __init__(self, fichier='scene.json'):
        d = lire_json(fichier)
        self.fond = np.asarray(Image.open(chemin(d['fond'])).convert('RGB')).astype(np.float32)
        self.objets = {}
        for o in d['objets']:
            if o.get('animable') is not None:
                # objet sans rectangle (ex. les mouches) : seulement des particules
                self.objets[o['nom']] = Animable(o, o['animable']) if 'rect' in o else None
        self.actions = lire_json('actions.json')
        self.particules = Particules()
        self.actives = []                 # (objet, recette, t0, fin_forcee)
        self.cadre = self.fond.copy()
        self.sales = []                   # rectangles modifiés à l'image précédente

    def recette(self, nom):
        return lire_json(os.path.join('recettes', nom + '.json'))

    def jouer(self, objet, nom_recette, t0=0.0, fin=None):
        self.actives.append((objet, self.recette(nom_recette), t0, fin))

    def declencher(self, nom_action, t0):
        """Action du joueur → zone touchée → recettes déclenchées ensemble."""
        a = self.actions[nom_action]
        for r in a['recettes']:
            self.jouer(a['objet'], r, t0, a.get('duree'))

    def couches_actives(self, objet, t):
        res = []
        for (o, rec, t0, fin) in self.actives:
            if o != objet:
                continue
            tl = t - t0
            if tl < 0:
                continue
            for c in rec['couches']:
                if fin is not None and 'fin' not in c:
                    c = {**c, 'fin': fin}
                res.append((c['zone'], c['effet'], valeur(c, tl), c, tl))
        return res

    def image(self, t):
        """Calcule l'image au temps t (float32 640x480x3)."""
        # 1. on remet le décor fixe uniquement là où on avait dessiné
        for (x0, y0, x1, y1) in self.sales:
            self.cadre[y0:y1, x0:x1] = self.fond[y0:y1, x0:x1]
        sales = []
        # 2. objets animés : seul leur rectangle est recalculé
        for nom, obj in self.objets.items():
            if obj is None:
                continue
            couches = self.couches_actives(nom, t)
            geo = [(z, e, v, c) for (z, e, v, c, tl) in couches if e not in EFFETS_PARTICULES]
            x, y, w, h = obj.rect
            self.cadre[y:y + h, x:x + w] = obj.rendre(geo)
            sales.append((x, y, x + w, y + h))
        # 3. particules par-dessus
        for nom in self.objets:
            for (z, e, v, c, tl) in self.couches_actives(nom, t):
                if e in EFFETS_PARTICULES:
                    sales += self.particules.dessiner(self.cadre, c, enveloppe(tl, c), tl)
        self.sales = sales
        return self.cadre

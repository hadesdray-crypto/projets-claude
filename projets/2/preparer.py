"""Préparation unique des données à partir de l'image d'entrée.

Produit (dans ce dossier) :
  decor/fond.png            décor fixe 640x480 (mouches d'origine effacées)
  objets/thomas_derriere.png mur reconstruit derrière Thomas (visible seulement
                            là où un calque s'écarte de sa place d'origine)
  calques/*.png             calques RGBA de Thomas (corps, bras droit, œil pendant)
  zones/*.png               cartes de zones en niveaux de gris (clair = bouge)
  decor/mouche.png          sprite de mouche (RGBA) pris dans l'image
Lancer : python3 preparer.py
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ICI = os.path.dirname(os.path.abspath(__file__))
ENTREE = os.path.join(ICI, '..', 'demo-zombie', 'entrees', '03-zombie.png')
X0, Y0, L, H = 330, 250, 640, 480          # cadrage dans l'image d'origine (taille native, sans rééchelle)
MOUCHES = [(498, 322), (645, 300), (750, 383), (698, 432), (403, 450)]  # coordonnées d'origine


def sauver(arr, chemin, mode=None):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    Image.fromarray(arr, mode).save(chemin, optimize=True)


def boucher_par_lignes(img, trou):
    """Remplit les pixels « trou » ligne par ligne par interpolation entre les
    voisins valides de gauche et de droite (le mur a des rayures horizontales)."""
    out = img.copy()
    for y in range(img.shape[0]):
        ligne = trou[y]
        if not ligne.any():
            continue
        xs = np.arange(img.shape[1])
        bons = ~ligne
        if bons.sum() < 2:
            continue
        for c in range(3):
            out[y, ligne, c] = np.interp(xs[ligne], xs[bons], img[y, bons, c])
    return out


def segmenter_thomas(c):
    """Silhouette de Thomas : tout ce qui n'est pas la couleur du mur, dans un cadre."""
    m = np.zeros((H, L), bool)
    x0, y0, x1, y1 = 100, 40, 380, 360
    sub = c[y0:y1, x0:x1]
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    lum = sub.mean(2)
    mur = (b > r + 4) & (np.abs(b - g) < 22) & (lum > 90)
    mur = ndi.binary_opening(mur, iterations=1)
    fg = ~mur
    lab, n = ndi.label(fg)
    tailles = ndi.sum(fg, lab, range(1, n + 1))
    fgm = lab == (np.argmax(tailles) + 1)
    trous = ndi.binary_fill_holes(fgm) & ~fgm
    tl, tn = ndi.label(trous)
    ts = ndi.sum(trous, tl, range(1, tn + 1))
    for i, s in enumerate(ts):
        if s < 150:
            fgm |= tl == (i + 1)
    # cheveux fins : pixels sombres proches de la tête et reliés au corps
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    tete = ((xx - (255 - x0)) ** 2 / 80 ** 2 + (yy - (130 - y0)) ** 2 / 85 ** 2) < 1
    # mèche = pixel nettement différent du mur environnant (médiane locale)
    mur_local = ndi.median_filter(sub, size=(9, 9, 1))
    sombre = ((lum < 110) & ~mur) | ((np.abs(sub - mur_local).sum(2) > 45) & (lum < 140))
    lab2, _ = ndi.label(fgm | (sombre & tete))
    fgm = lab2 == lab2[fgm][0]
    # bouts de mèches en pointillés : croissance pas à pas vers les pixels voisins
    pointilles = (np.abs(sub - mur_local).sum(2) > 30) & tete
    carre = np.ones((3, 3), bool)
    for _ in range(6):
        fgm |= ndi.binary_dilation(fgm, structure=carre, iterations=3) & pointilles
    m[y0:y1, x0:x1] = fgm
    return m


def lissage(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def main():
    src = np.asarray(Image.open(ENTREE).convert('RGB')).astype(np.float32)
    c = src[Y0:Y0 + H, X0:X0 + L].copy()
    yy, xx = np.mgrid[0:H, 0:L].astype(np.float32)

    # --- sprite de mouche (prise sur la mouche en (645,300)) puis effacement des mouches
    mx, my = 645 - X0, 300 - Y0
    boite = c[my - 9:my + 7, mx - 10:mx + 10]
    fond_local = np.median(np.concatenate([boite[0], boite[-1]]), axis=0)
    dist = np.abs(boite - fond_local).sum(2)
    alpha = np.clip((dist - 25) / 40, 0, 1)
    sprite = np.dstack([boite, alpha * 255]).astype(np.uint8)
    sauver(sprite, os.path.join(ICI, 'decor', 'mouche.png'), 'RGBA')

    trou = np.zeros((H, L), bool)
    for (x, y) in MOUCHES:
        x, y = x - X0, y - Y0
        trou[y - 10:y + 8, x - 11:x + 11] = True
    # seuls les pixels qui diffèrent du mur sont effacés
    fond = boucher_par_lignes(c, trou & (ndi.binary_dilation(
        (np.abs(c - ndi.median_filter(c, size=(15, 15, 1))).sum(2) > 30), iterations=2)))
    sauver(np.round(fond).astype(np.uint8), os.path.join(ICI, 'decor', 'fond.png'))

    # --- Thomas : silhouette, calques, mur derrière
    fg = segmenter_thomas(fond)
    region = (xx >= 118) & (xx < 345) & (yy < 338)
    # bas du corps (jambes) reste dans le décor fixe : coupure à y=312 sauf l'os (x>218)
    region &= (yy < 312) | (xx > 218)
    sil = fg & region
    # retire les fines rayures horizontales du mur collées au corps (sous la tête)
    ouvert = ndi.binary_opening(sil, structure=np.ones((5, 1), bool))
    sil = np.where(yy > 130, ouvert, sil)
    sil &= ~((xx >= 290) & (yy >= 300))      # coin du cercueil
    # ne garder que les morceaux reliés (corps, bras+os, œil) : retire les bouts de décor
    # (morceaux comptés avec un voisinage élargi : les mèches en pointillés restent)
    lab, n = ndi.label(ndi.binary_dilation(sil, structure=np.ones((3, 3), bool), iterations=3))
    tailles = ndi.sum(sil, lab, range(1, n + 1))
    sil = sil & np.isin(lab, [i + 1 for i, t in enumerate(tailles) if t > 400])

    # bras droit + os : à droite de l'épaule (x>218), sous l'œil pendant
    zone_bras = ((xx > 218) & (yy >= 240)) | ((xx > 300) & (yy >= 200))
    rampe = np.clip((xx - 218) / 5.0, 0, 1)             # fondu doux à l'épaule
    bras = sil & zone_bras
    lab, n = ndi.label(bras)
    tailles = ndi.sum(bras, lab, range(1, n + 1))
    bras = lab == (np.argmax(tailles) + 1)
    sil = sil & ~(zone_bras & ~bras)
    # liseré : les pixels clairs d'anticrénelage autour des contours (mèches de
    # cheveux surtout) doivent bouger avec Thomas, sinon ils restent en « fantôme »
    sil_l = ndi.binary_dilation(sil, iterations=2) & region
    # reconstruction du mur : on n'interpole qu'à partir de pixels « mur »
    # (un reste sombre au bord tracerait sinon une ligne dans la reconstruction)
    mur_local = ndi.median_filter(fond, size=(9, 9, 1))
    pas_mur = np.abs(fond - mur_local).sum(2) > 30
    trou = ndi.binary_dilation(sil_l, iterations=1) | (ndi.binary_dilation(sil_l, iterations=6) & pas_mur)
    bouche = boucher_par_lignes(fond, trou)
    # dans ce liseré, on garde les pixels qui diffèrent du mur reconstruit sans être
    # plus sombres (halo d'anticrénelage) ; les rayures sombres du mur restent au décor.
    # Le premier pixel autour du contour est toujours gardé ; autour des cheveux
    # (y <= 130, pas de rayures), on garde tout le liseré.
    ecart = (fond - bouche).sum(2)
    garde = (sil | (ndi.binary_dilation(sil) & region) | (sil_l & (yy <= 130))
             | (sil_l & (np.abs(ecart) > 24) & (ecart > -15)))
    bras = ndi.binary_dilation(bras, iterations=2) & zone_bras & garde
    a_bras = bras * rampe
    # œil pendant : tige + globe sous l'œil exorbité
    zone_oeil = (xx >= 266) & (xx <= 296) & (yy >= 169) & (yy <= 226)
    a_oeil = (garde & zone_oeil).astype(np.float32)
    # corps : le reste (garde la racine du bras jusqu'à x=223 pour le fondu)
    a_corps = (garde & ~(zone_bras & (xx > 223)) & ~zone_oeil).astype(np.float32)

    couvert = (a_bras > 0) | (a_oeil > 0) | (a_corps > 0)
    derriere = np.where(couvert[..., None], bouche, fond)   # hors calques : décor intact
    sauver(np.round(derriere).astype(np.uint8), os.path.join(ICI, 'objets', 'thomas_derriere.png'))
    for nom, a in [('corps', a_corps), ('bras_droit', a_bras), ('oeil_pendant', a_oeil)]:
        rgba = np.dstack([fond, a * 255])
        sauver(np.round(rgba).astype(np.uint8), os.path.join(ICI, 'calques', nom + '.png'), 'RGBA')

    # --- cartes de zones (niveaux de gris, 255 = mouvement complet)
    def ellipse(cx, cy, rx, ry):
        return (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1).astype(np.float32)

    def flou(m, s):
        return ndi.gaussian_filter(m, s)

    zones = {}
    # tête (avec cheveux), nulle sous le cou
    zones['tete'] = flou(ellipse(258, 118, 100, 95), 4) * (1 - lissage((yy - 186) / 26))
    # haut du corps : 1 au-dessus des épaules, 0 à la taille
    zones['haut_du_corps'] = 1 - lissage((yy - 230) / 75)
    zones['ventre'] = flou(ellipse(178, 272, 38, 26), 5)
    # mâchoire : moitié basse de la bouche et menton
    m = ellipse(229, 190, 28, 14) * (yy > 179)
    zones['machoire'] = flou(m, 2.5)
    zones['coin_bouche_gauche'] = flou(ellipse(210, 175, 4, 4), 2.5)
    zones['coin_bouche_droit'] = flou(ellipse(252, 172, 4, 4), 2.5)
    zones['bave'] = flou(ellipse(232, 185, 16, 2), 1.0) * sil
    zones['main'] = flou(ellipse(285, 270, 17, 15), 3)
    for nom, z in zones.items():
        z = z / max(z.max(), 1e-6)
        sauver(np.round(z * 255).astype(np.uint8), os.path.join(ICI, 'zones', nom + '.png'), 'L')

    # couleur de paupière : peau moyenne au-dessus de chaque œil
    for nom, (cx, cy, r) in {'oeil_gauche': (246.5, 124, 12), 'oeil_exorbite': (286, 156, 12.5)}.items():
        anneau = (np.hypot(xx - cx, yy - cy) > r + 3) & (np.hypot(xx - cx, yy - cy) < r + 7) & (yy < cy) & sil
        coul = fond[anneau]
        coul = coul[coul.mean(1) > 70]
        print(nom, 'couleur paupière', np.round(coul.mean(0)).astype(int).tolist())
    print('pixels de Thomas :', int(sil.sum()))


if __name__ == '__main__':
    main()

"""Préparation unique des données à partir de l'image d'entrée (version 3).

Thomas est découpé en entier (squelette complet) ; le décor ne contient plus Thomas.
Produit (dans ce dossier) :
  decor/fond.png              décor fixe 640x480 SANS Thomas (mur et sol reconstruits)
  decor/mouche.png            sprite de mouche pris dans l'image
  calques/corps.png           tronc + tête + bassin, SANS bras, SANS os, SANS l'œil
                              exorbité en trop ni la tige (dessinée par le moteur)
  calques/manche.png          manche (haut du bras avant)
  calques/avant_bras.png      avant-bras avant (la main est dessinée par le moteur)
  calques/bras_arriere.png    bras arrière entier avec sa main (prolongé sous le gilet)
  calques/jambe_g.png, jambe_d.png   jambes et pieds (prolongés sous le bassin)
  calques/oeil_pendant.png    le petit œil au bout de la tige (pixels d'origine)
  zones/*.png                 cartes de zones en niveaux de gris (clair = bouge),
                              dont bouche.png (intérieur de la bouche) et levres.png
  palette.json                couleurs relevées sur Thomas (passe de style)
Lancer : python3 preparer.py
"""
import json
from PIL import ImageDraw
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ICI = os.path.dirname(os.path.abspath(__file__))
ENTREE = os.path.join(ICI, '..', 'demo-zombie', 'entrees', '03-zombie.png')
X0, Y0, L, H = 330, 250, 640, 480          # cadrage dans l'image d'origine (taille réelle)
MOUCHES = [(498, 322), (645, 300), (750, 383), (698, 432), (403, 450)]  # coordonnées d'origine

OEIL_EN_TROP = (285.0, 157.0, 16.0)        # œil exorbité au bord du visage : retiré
ORBITE = (277.0, 160.0)                    # d'où sort la tige
OEIL_PENDANT = (280.5, 212.5, 10.5)        # petit œil au bout de la tige : gardé
# nouveau bord de la tête là où était l'œil en trop (x, y)
BORD_TETE = [(305, 132), (303, 143), (298, 153), (289, 162), (277, 169), (264, 176)]
BOUCHE = (229, 176, 24, 16)                # ellipse qui contient l'intérieur de la bouche
BAS_DU_CORPS = 306                         # sous cette ligne, le bassin appartient aux jambes
LIGNE_SOL = 351                            # sous cette ligne, le décor reconstruit est du sol
# contours tracés à la main (coordonnées du cadre 640x480), contour noir compris
BRAS_ARRIERE = [(123, 229), (150.5, 229), (150.5, 284), (149.5, 285), (149.5, 342), (147, 352), (124, 352),
                (110, 348), (104, 336), (106, 322), (116, 312), (123, 302)]
JAMBE_G = [(149, 288), (186, 288), (186, 326), (187, 362), (184, 376), (180, 390), (187, 404), (188, 430),
           (128, 431), (125, 416), (131, 402), (140, 394), (137, 384), (141, 368), (148, 352)]
JAMBE_D = [(186, 288), (225, 288), (227, 326), (231, 340), (231, 354), (228, 372), (226, 384), (223, 392),
           (238, 398), (252, 407), (253, 420), (196, 422), (194, 404), (196, 392), (191, 376), (191, 362),
           (193, 350), (193, 326), (186, 326)]


def sauver(arr, chemin, mode=None):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    Image.fromarray(arr, mode).save(chemin, optimize=True)


def boucher_par_lignes(img, trou, sources=None):
    """Remplit les pixels « trou » ligne par ligne (le mur a des rayures horizontales).
    sources : masque des pixels qui peuvent servir de modèle (par exemple ceux qui
    ont la couleur du mur) ; s'il y en a trop peu sur une ligne, tous servent."""
    out = img.copy()
    xs = np.arange(img.shape[1])
    for y in range(img.shape[0]):
        ligne = trou[y]
        if not ligne.any():
            continue
        bons = ~ligne
        if sources is not None and (bons & sources[y]).sum() >= 20:
            bons = bons & sources[y]
        if bons.sum() < 2:
            continue
        for c in range(3):
            out[y, ligne, c] = np.interp(xs[ligne], xs[bons], img[y, bons, c])
    return out


def diffuser(img, trou, connu, iterations=400):
    """Remplissage doux d'un trou à partir des pixels connus voisins (diffusion)."""
    out = img.copy()
    poids = connu.astype(np.float32)
    acc = out * poids[..., None]
    for _ in range(iterations):
        s = ndi.uniform_filter(acc, size=(3, 3, 1))
        p = ndi.uniform_filter(poids, size=3)
        rempli = trou & (p > 1e-4)
        acc[rempli] = s[rempli] / p[rempli][:, None]
        poids = np.where(trou, np.maximum(poids, (p > 1e-4).astype(np.float32)), poids)
        acc = np.where(trou[..., None], acc * poids[..., None], acc)
    res = np.where(poids[..., None] > 0, acc / np.maximum(poids, 1e-6)[..., None], img)
    out[trou] = res[trou]
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
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    tete = ((xx - (255 - x0)) ** 2 / 80 ** 2 + (yy - (130 - y0)) ** 2 / 85 ** 2) < 1
    mur_local = ndi.median_filter(sub, size=(9, 9, 1))
    sombre = ((lum < 110) & ~mur) | ((np.abs(sub - mur_local).sum(2) > 45) & (lum < 140))
    lab2, _ = ndi.label(fgm | (sombre & tete))
    fgm = lab2 == lab2[fgm][0]
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

    # --- mouches : sprite puis effacement
    mx, my = 645 - X0, 300 - Y0
    boite = c[my - 9:my + 7, mx - 10:mx + 10]
    fond_local = np.median(np.concatenate([boite[0], boite[-1]]), axis=0)
    alpha = np.clip((np.abs(boite - fond_local).sum(2) - 25) / 40, 0, 1)
    sauver(np.dstack([boite, alpha * 255]).astype(np.uint8), os.path.join(ICI, 'decor', 'mouche.png'), 'RGBA')
    trou = np.zeros((H, L), bool)
    for (x, y) in MOUCHES:
        x, y = x - X0, y - Y0
        trou[y - 10:y + 8, x - 11:x + 11] = True
    fond = boucher_par_lignes(c, trou & ndi.binary_dilation(
        (np.abs(c - ndi.median_filter(c, size=(15, 15, 1))).sum(2) > 30), iterations=2))
    sauver(np.round(fond).astype(np.uint8), os.path.join(ICI, 'decor', 'fond.png'))

    # --- silhouette complète de Thomas (comme la version 1)
    fg = segmenter_thomas(fond)
    region = (xx >= 118) & (xx < 345) & (yy < 338)
    region &= (yy < 312) | (xx > 218)
    sil = fg & region
    ouvert = ndi.binary_opening(sil, structure=np.ones((5, 1), bool))
    sil = np.where(yy > 130, ouvert, sil)
    sil &= ~((xx >= 290) & (yy >= 300))
    lab, n = ndi.label(ndi.binary_dilation(sil, structure=np.ones((3, 3), bool), iterations=3))
    tailles = ndi.sum(sil, lab, range(1, n + 1))
    sil = sil & np.isin(lab, [i + 1 for i, t in enumerate(tailles) if t > 400])

    # liseré d'anticrénelage (cheveux surtout), comme en version 1
    sil_l = ndi.binary_dilation(sil, iterations=2) & region
    mur_local = ndi.median_filter(fond, size=(9, 9, 1))
    pas_mur = np.abs(fond - mur_local).sum(2) > 30
    trou_mur = ndi.binary_dilation(sil_l, iterations=1) | (ndi.binary_dilation(sil_l, iterations=6) & pas_mur)
    mur = boucher_par_lignes(fond, trou_mur)
    ecart = (fond - mur).sum(2)
    garde = (sil | (ndi.binary_dilation(sil) & region) | (sil_l & (yy <= 130))
             | (sil_l & (np.abs(ecart) > 24) & (ecart > -15)))

    r, g, b = fond[..., 0], fond[..., 1], fond[..., 2]
    lum = fond.mean(2)
    # --- l'os : tons crème / rosés, plus son contour sombre ; aucun os ne reste
    boite_os = (xx >= 245) & (xx <= 336) & (yy >= 204) & (yy <= 322)
    os_coeur = boite_os & (r > g + 4) & (lum > 105) & ~((g > r) & (lum < 160))
    os_coeur = ndi.binary_closing(os_coeur, iterations=2) & boite_os
    peau = (g > r + 6) & (lum > 55)
    os_m = (ndi.binary_dilation(os_coeur, iterations=3) & boite_os & ~peau) | os_coeur

    # --- œil en trop + tige + œil pendant : retirés du corps
    ox, oy, orr = OEIL_EN_TROP
    retire_oeil = (np.hypot(xx - ox, yy - oy) <= orr) | (np.hypot((xx - 270.5) / 4.5, (yy - 155) / 13) <= 1) | ((xx >= 265) & (xx <= 296) & (yy >= 160) & (yy <= 228))
    retire_oeil &= garde
    # nouveau bord de la tête : x_bord(y)
    by = np.array([p[1] for p in BORD_TETE], np.float32)
    bx = np.array([p[0] for p in BORD_TETE], np.float32)
    x_bord = np.interp(yy, by, bx, left=400, right=-1)
    dedans_tete = (xx < x_bord) & (yy >= by[0]) & (yy <= by[-1] + 4)
    joue = retire_oeil & dedans_tete
    # avant-bras : de la sortie de la manche (x>=222) jusqu'au poignet (x<284)
    avant_bras = garde & (xx >= 222) & (xx < 284) & (yy >= 238) & (yy <= 286) & ~os_m
    lab, n = ndi.label(avant_bras)
    tailles = ndi.sum(avant_bras, lab, range(1, n + 1))
    avant_bras = lab == (np.argmax(tailles) + 1)
    avant_bras &= ~((r > g + 2) & (lum > 60) & (xx > 262))      # restes roses de l'os au poignet
    avant_bras &= ~((xx > 271) & (yy > 271))                    # doigts de l'ancienne main (sous le poignet)
    avant_bras &= ~((b > r + 4) & (lum > 90))                   # liseré couleur du mur
    main_m = garde & (xx >= 280) & (yy >= 238) & (yy <= 300)        # main d'origine (serre l'os) : retirée
    # manche (recouvre le haut du bras) : bande sous l'épaule
    manche = garde & (xx >= 209) & (xx <= 238) & (yy >= 194) & (yy <= 264) & ~avant_bras
    # dans la manche, seuls les pixels à droite du pli du gilet (x>=211) suivent le bras
    bras_m = avant_bras | manche

    # --- calque du bras (manche + avant-bras), pose de repos
    rampe_haut = lissage((yy - 194) / 4.0)
    a_bras = bras_m * rampe_haut
    # --- corps : tout le reste, moins le bras, l'os, la main, l'œil en trop, la tige
    corps_m = garde & ~bras_m & ~os_m & ~main_m & ~retire_oeil & ~((xx >= 240) & (yy >= 203))
    img_corps = fond.copy()
    a_corps = corps_m.astype(np.float32)

    # joue reconstruite là où était l'œil en trop : peau diffusée + contour sombre
    tete_connue = corps_m & (np.hypot(xx - ox, yy - oy) < 34) & (lum > 60) & (g > r)
    zone_j = joue | (ndi.binary_dilation(joue, iterations=1) & corps_m & ~tete_connue)
    ref = fond[(xx >= 278) & (xx <= 298) & (yy >= 112) & (yy <= 138) & (g > r + 8) & (lum > 90)]
    peau_tete = np.median(ref, axis=0)
    img_corps = diffuser(img_corps, zone_j, tete_connue & (g > r + 8), 120)
    img_corps = np.where(zone_j[..., None], 0.35 * img_corps + 0.65 * peau_tete, img_corps)
    # texture de peau : détails fins repris du crâne juste au-dessus (30 px plus haut)
    detail = fond - ndi.uniform_filter(fond, size=(5, 5, 1))
    img_corps = np.where(zone_j[..., None], img_corps + 0.8 * np.roll(detail, 30, axis=0), img_corps)
    # bande d'ombre le long du nouveau bord, comme sur le reste du crâne
    ombre_b = np.clip((x_bord - xx) / 5.0, 0, 1)
    img_corps = np.where(zone_j[..., None], img_corps * (0.78 + 0.22 * ombre_b[..., None]), img_corps)
    contour = np.clip(1.6 - np.abs(xx - x_bord), 0, 1) * dedans_tete
    sombre = np.array([34, 44, 28], np.float32)
    img_corps = np.where(zone_j[..., None], img_corps * (1 - contour[..., None]) + sombre * contour[..., None], img_corps)
    a_corps = np.where(joue, 1.0, a_corps)
    # orbite vide d'où sort la tige
    qx, qy = ORBITE
    d_orb = np.hypot((xx - qx) / 3.2, (yy - qy) / 3.6)
    cou_orb = np.clip((1.0 - d_orb) * 5, 0, 1)
    fondo = np.array([62, 22, 26], np.float32) * (0.7 + 0.3 * np.clip(d_orb, 0, 1))[..., None]
    bord_o = np.clip(1 - np.abs(d_orb - 1.0) * 4.5, 0, 1)
    img_corps = img_corps * (1 - cou_orb[..., None]) + fondo * cou_orb[..., None]
    img_corps = img_corps * (1 - bord_o[..., None]) + sombre * bord_o[..., None]
    a_corps = np.maximum(a_corps, np.maximum(cou_orb, bord_o) * dedans_tete)

    # torse caché sous la manche : visible seulement quand le bras s'écarte.
    # Texture du gilet reprise 20 px plus à gauche, nouveau bord sombre à x≈227.
    sous = manche & (xx < 228)
    decale = np.roll(fond, 20, axis=1)
    img_corps = np.where(sous[..., None], decale, img_corps)
    bord_t = sous & (xx >= 225)
    img_corps = np.where(bord_t[..., None], sombre, img_corps)
    a_corps = np.where(sous, 1.0, a_corps)

    # ------------------------------------------------------------ version 3 : corps entier
    def polygone(pts):
        im = Image.new('L', (L, H), 0)
        ImageDraw.Draw(im).polygon([tuple(p) for p in pts], fill=255)
        return np.asarray(im) > 0

    mur_c = (b > r + 4) & (np.abs(b - g) < 22) & (lum > 90)          # couleur du mur
    beige = (r >= g - 3) & (lum > 60)                                # tissu du gilet
    # --- bras arrière (à gauche de l'image) avec sa main
    p_bras2 = polygone(BRAS_ARRIERE) & ~mur_c
    p_bras2 &= ~(beige & (yy < 244))
    lab, n = ndi.label(p_bras2)
    p_bras2 = lab == (np.argmax(ndi.sum(p_bras2, lab, range(1, n + 1))) + 1)
    p_bras2 = ndi.binary_fill_holes(p_bras2)
    img_b2 = fond.copy()
    a_b2 = p_bras2.astype(np.float32)
    # prolongement caché sous le gilet (jusqu'à l'épaule) : copie de la peau du bras
    dec = 26
    for y in range(236, 205, -1):
        libre = a_b2[y] == 0
        src_ok = p_bras2[y + dec] & (xx[y] >= 127) & (xx[y] <= 149)
        pose = libre & src_ok
        img_b2[y, pose] = fond[y + dec, pose]
        a_b2[y, pose] = 1.0
    # --- jambes et pieds
    p_jg = polygone(JAMBE_G)
    p_jd = polygone(JAMBE_D) & ~p_jg
    for pj in (p_jg, p_jd):
        pj &= ~(mur_c & (yy > 318) & (xx >= 184) & (xx <= 196))
    # --- corps : on retire le bras arrière et ce qui est sous la ceinture basse
    corps_m &= ~p_bras2
    corps_m &= ~(polygone(BRAS_ARRIERE) & mur_c)
    a_corps = np.where(p_bras2 | (polygone(BRAS_ARRIERE) & mur_c), 0.0, a_corps)
    bas = yy >= BAS_DU_CORPS
    a_corps = np.where(bas & (xx < 232), 0.0, a_corps)
    corps_m &= ~(bas & (xx < 232))

    # --- décor sans Thomas : mur reconstruit par lignes, sol par copie en miroir
    tout = ((a_bras > 0) | (a_corps > 0) | ndi.binary_dilation(os_m, iterations=3) | main_m | retire_oeil
            | garde | p_bras2 | p_jg | p_jd)
    tout2 = ndi.binary_dilation(tout, iterations=3)
    tout2 |= (xx >= 245) & (xx <= 318) & (yy >= 200) & (yy <= 322) & pas_mur
    src_mur = mur_c & (xx < 300)
    mur = boucher_par_lignes(fond, trou_mur | tout2, src_mur)
    decor = np.where(tout2[..., None], mur, fond)
    sol = decor.copy()
    for y in range(LIGNE_SOL, H):
        ligne = tout2[y]
        if not ligne.any():
            continue
        xs_ = np.nonzero(np.diff(np.concatenate([[0], ligne.astype(np.int8), [0]])))[0]
        for a_, b_ in zip(xs_[0::2], xs_[1::2]):
            nb = b_ - a_
            i = np.arange(nb)
            gauche = np.clip(a_ - 1 - i, 0, L - 1)
            droite = np.clip(b_ + (nb - 1 - i), 0, L - 1)
            t = lissage((i + 0.5) / nb)[:, None]
            sol[y, a_:b_] = fond[y, gauche] * (1 - t) + fond[y, droite] * t
    decor = np.where((tout2 & (yy >= LIGNE_SOL))[..., None], sol, decor)
    sauver(np.round(decor).astype(np.uint8), os.path.join(ICI, 'decor', 'fond.png'))
    a_manche = (manche * rampe_haut).astype(np.float32)
    a_avant = avant_bras.astype(np.float32)
    calques = [('corps', img_corps, a_corps), ('manche', fond, a_manche), ('avant_bras', fond, a_avant),
               ('bras_arriere', img_b2, a_b2), ('jambe_g', fond, p_jg.astype(np.float32)),
               ('jambe_d', fond, p_jd.astype(np.float32))]
    for nom, im, a in calques:
        sauver(np.round(np.dstack([np.clip(im, 0, 255), a * 255])).astype(np.uint8),
               os.path.join(ICI, 'calques', nom + '.png'), 'RGBA')
    # contrôle : les calques recomposés au repos (sans main ni tige) par-dessus le décor
    recompose = decor.copy()
    for nom in ('jambe_d', 'jambe_g', 'bras_arriere', 'corps', 'manche', 'avant_bras'):
        im, a = next((i, al) for n_, i, al in calques if n_ == nom)
        recompose = recompose * (1 - a[..., None]) + np.clip(im, 0, 255) * a[..., None]
    sauver(np.round(recompose).astype(np.uint8), '/tmp/v/recompose.png')
    # intérieur de la bouche et lèvres (le morceau passe entre les deux)
    bx_, by_, brx, bry = BOUCHE
    rgb_c = img_corps
    dans_b = np.hypot((xx - bx_) / brx, (yy - by_) / bry) < 1
    interieur = dans_b & (rgb_c[..., 0] > rgb_c[..., 1] + 15) & (rgb_c.mean(2) < 120) & (a_corps > 0)
    plein = ndi.binary_fill_holes(ndi.binary_closing(interieur, iterations=3))
    levres = ndi.binary_dilation(plein, iterations=5) & ~interieur & (a_corps > 0)
    sauver((interieur * 255).astype(np.uint8), os.path.join(ICI, 'zones', 'bouche.png'), 'L')
    sauver((levres * 255).astype(np.uint8), os.path.join(ICI, 'zones', 'levres.png'), 'L')
    # palette relevée sur Thomas (passe de style des objets dessinés par le code)
    def mediane(m):
        return np.round(np.median(fond[m], axis=0)).astype(int).tolist()
    peau = avant_bras & (g > r + 10)
    lp = lum[peau]
    q = np.percentile(lp, [25, 60, 88])
    oe = (np.hypot(xx - OEIL_PENDANT[0], yy - OEIL_PENDANT[1]) < 8)
    pal = {
        'peau_sombre': mediane(peau & (lum < q[0])),
        'peau_moyen': mediane(peau & (lum >= q[0]) & (lum < q[1])),
        'peau_clair': mediane(peau & (lum >= q[1]) & (lum < q[2])),
        'peau_eclat': mediane(peau & (lum >= q[2])),
        'trait': mediane(garde & (lum < 30)),
        'blanc_oeil': mediane(oe & (lum > 190)),
        'creme_ombre': mediane(oe & (lum > 120) & (lum <= 190)),
        'chair_sombre': mediane(interieur & (lum < 55)),
        'chair': mediane(interieur & (lum >= 55)),
        'rose_tige': mediane((xx >= 268) & (xx <= 284) & (yy >= 165) & (yy <= 200) & (r > g + 40) & (lum > 120)),
        'rose_sombre': mediane((xx >= 268) & (xx <= 284) & (yy >= 165) & (yy <= 200) & (r > g + 30) & (lum > 60) & (lum <= 120)),
        'gilet_clair': mediane(garde & beige & (lum > 150) & (xx < 200) & (yy > 180) & (yy < 280)),
        'gilet_moyen': mediane(garde & beige & (lum > 95) & (lum <= 150) & (xx < 200) & (yy > 180) & (yy < 280)),
    }
    with open(os.path.join(ICI, 'palette.json'), 'w', encoding='utf-8') as f:
        json.dump(pal, f, ensure_ascii=False, indent=1)
    print('palette', pal)
    # petit œil pendant (pixels d'origine), centré dans un carré 24x24
    ex, ey, er = OEIL_PENDANT
    x0, y0 = int(ex) - 12, int(ey) - 12
    morceau = fond[y0:y0 + 24, x0:x0 + 24]
    d = np.hypot(xx[y0:y0 + 24, x0:x0 + 24] - ex, yy[y0:y0 + 24, x0:x0 + 24] - ey)
    a_oe = np.clip(er + 0.5 - d, 0, 1) * garde[y0:y0 + 24, x0:x0 + 24]
    sauver(np.round(np.dstack([morceau, a_oe * 255])).astype(np.uint8),
           os.path.join(ICI, 'calques', 'oeil_pendant.png'), 'RGBA')

    # --- cartes de zones (niveaux de gris, 255 = mouvement complet)
    def ellipse(cx, cy, rx, ry):
        return (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1).astype(np.float32)

    flou = ndi.gaussian_filter
    zones = {}
    zones['tete'] = flou(ellipse(258, 118, 100, 95), 4) * (1 - lissage((yy - 186) / 26))
    zones['haut_du_corps'] = 1 - lissage((yy - 228) / 78)
    zones['poitrine'] = flou(ellipse(195, 245, 40, 30), 6)
    # mâchoire : bas du visage sous la ligne de la bouche, le pivot est à l'arrière (oreille)
    # transition douce (20 px) entre la lèvre du haut et la mâchoire : l'intérieur
    # de la bouche s'étire quand elle s'ouvre (pente du champ < 1, inversion stable)
    zones['machoire'] = flou(ellipse(230, 192, 38, 22), 2.0) * lissage((yy - 166) / 22)
    zones['joue_gauche'] = flou(ellipse(212, 170, 9, 9), 3)
    zones['joue_droite'] = flou(ellipse(258, 170, 8, 9), 3)
    zones['cou'] = flou(((xx >= 196) & (xx <= 226) & (yy >= 190) & (yy <= 246)).astype(np.float32), 2.5) * (a_corps > 0)
    # coins de la bouche (sourire)
    zones['coin_g'] = flou(ellipse(207, 174, 5, 5), 2.5)
    zones['coin_d'] = flou(ellipse(250, 173, 5, 5), 2.5)
    # cheveux : mèches hors du crâne, poids croissant avec la distance au crâne
    d_crane = np.hypot((xx - 250) / 52, (yy - 122) / 46)
    zones['cheveux'] = np.clip((d_crane - 1.0) / 0.35, 0, 1) * (yy < 125) * garde
    for nom, z in zones.items():
        z = z / max(z.max(), 1e-6)
        sauver(np.round(z * 255).astype(np.uint8), os.path.join(ICI, 'zones', nom + '.png'), 'L')
    anneau = (np.hypot(xx - 246.5, yy - 124) > 15) & (np.hypot(xx - 246.5, yy - 124) < 19) & (yy < 124) & sil
    coul = fond[anneau]
    coul = coul[coul.mean(1) > 70]
    print('couleur paupière', np.round(coul.mean(0)).astype(int).tolist())
    peau_bras = fond[avant_bras & (g > r + 10) & (lum > 80)]
    print('peau du bras (claire, moyenne, sombre)', np.percentile(peau_bras, [85, 50, 15], axis=0).round().astype(int).tolist())
    print('pixels : corps', int((a_corps > 0).sum()), 'os retirés', int(os_m.sum()))


if __name__ == '__main__':
    main()

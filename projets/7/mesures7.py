"""Mesures de la demande 7 : python3 mesures7.py  ->  mesures.json
Chaque image est rendue deux fois avec Thomas seul sur le décor : avec les bras et sans les bras ;
la différence donne le masque exact des bras (anciens : manche, avant-bras, bras arrière, main ;
nouveaux : calque « bras7 »). Même méthode avant et après."""
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

import moteur7
import amplitude

ICI = os.path.dirname(os.path.abspath(__file__))
FPS = 30
VIEUX = {'bras_arriere', 'manche', 'avant_bras', 'main'}
NOUVEAUX = {'bras7'}
OS = {'avant': ('bras', 'avant_bras', 'main'), 'arriere': ('bras2', 'avant_bras2', 'main2')}


AVANT_VIEUX = {'manche', 'avant_bras', 'main'}
ARRIERE_VIEUX = {'bras_arriere'}


def deux_rendus(sc, noms):
    """Renvoie (image, masque des deux bras, silhouette, état, masque bras avant, masque bras arrière)."""
    d, th, e = sc.dernier, sc.thomas, sc.etat
    ress = {'ancre': e['ancre'], 'oeil': e['oeil'].tolist(), 'vitesse_oeil': e['v_oeil'].tolist()}
    nouveau = isinstance(th, moteur7.Thomas7)

    def rendre(sans_avant, sans_arriere):
        B = sc.fond.copy()
        sauve = th.calques
        if nouveau:
            th.exclure = ({'avant'} if sans_avant else set()) | ({'arriere'} if sans_arriere else set())
        else:
            ex = (AVANT_VIEUX if sans_avant else set()) | (ARRIERE_VIEUX if sans_arriere else set())
            th.calques = [c for c in sauve if c['nom'] not in ex]
        th.rendre(B, d['parametres'], d['couches'], d['etat'], ress)
        th.calques = sauve
        if nouveau:
            th.exclure = set()
        return np.round(B)

    A = rendre(False, False)
    sans_av, sans_ar, sans = rendre(True, False), rendre(False, True), rendre(True, True)
    m_av = np.abs(A - sans_av).sum(2) > 12
    m_ar = np.abs(A - sans_ar).sum(2) > 12
    masque = np.abs(A - sans).sum(2) > 12
    sil = np.abs(A - sc.fond).sum(2) > 12
    return A, masque, sil, d['etat'], m_av, m_ar


def joints(etat, cle, vieux):
    o = OS[cle]
    J = etat['J']
    S, E = np.array(J[o[0]]), np.array(J[o[1]])
    W = np.array(J[o[2]]) if o[2] in J else None
    if W is None:                       # ancienne main arrière : pas d'os, le poignet est au bout de l'avant-bras
        return S, E, None
    return S, E, W


def epaisseur(masque, S, E, W):
    """Épaisseur du bras (px) perpendiculairement à l'os : 4 stations sur le bas du haut du bras (sous la manche), 5 sur l'avant-bras (hors main)."""
    segs = [(S, E, np.linspace(0.65, 0.92, 4)), (E, W, np.linspace(0.2, 0.7, 5))] if W is not None else [(S, E, np.linspace(0.65, 0.92, 4))]
    out = []
    for (a, b, stations) in segs:
        d = b - a
        L = np.linalg.norm(d)
        u = d / L
        n = np.array([-u[1], u[0]])
        vals = []
        for t in stations:
            p = a + d * t
            ts = np.arange(-30, 30.01, 0.5)
            xs = np.round(p[0] + n[0] * ts).astype(int)
            ys = np.round(p[1] + n[1] * ts).astype(int)
            ok = (xs >= 0) & (xs < masque.shape[1]) & (ys >= 0) & (ys < masque.shape[0])
            m = np.zeros(len(ts), bool)
            m[ok] = masque[ys[ok], xs[ok]]
            if not m.any():
                vals.append(0.0)
                continue
            i0 = np.argmin(np.abs(ts) + 1e6 * (~m))
            lo, hi = i0, i0
            while lo > 0 and m[lo - 1]:
                lo -= 1
            while hi < len(m) - 1 and m[hi + 1]:
                hi += 1
            vals.append((hi - lo + 1) * 0.5)
        out.append(vals)
    return out


def longueur_apparente(masque, S):
    """Plus long chemin DANS le masque (px) depuis l'épaule : longueur apparente du bras."""
    ys, xs = np.nonzero(masque)
    if len(ys) < 5:
        return 0.0
    idx = -np.ones(masque.shape, int)
    idx[ys, xs] = np.arange(len(ys))
    r, c, w = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        y2, x2 = ys + dy, xs + dx
        ok = (y2 < masque.shape[0]) & (x2 >= 0) & (x2 < masque.shape[1])
        j = np.full(len(ys), -1)
        j[ok] = idx[y2[ok], x2[ok]]
        k = j >= 0
        r += list(np.arange(len(ys))[k]); c += list(j[k]); w += [math.hypot(dy, dx)] * int(k.sum())
    G = coo_matrix((w + w, (r + c, c + r)), shape=(len(ys), len(ys))).tocsr()
    s0 = int(np.argmin((xs - S[0]) ** 2 + (ys - S[1]) ** 2))
    d = dijkstra(G, indices=s0)
    d = d[np.isfinite(d)]
    return float(d.max())


def isoles(sil, masque, etat, vieux):
    """Pixels isolés autour des bras : petits îlots (<= 3 px) de silhouette et trous (<= 3 px) dans la silhouette,
    dans une bande de 14 px autour de l'os des deux bras."""
    zone = ndi.binary_dilation(masque, iterations=14)
    lab, n = ndi.label(sil, structure=np.ones((3, 3)))
    nb = 0
    if n:
        t = ndi.sum(sil, lab, range(1, n + 1))
        petits = np.isin(lab, np.nonzero(t <= 3)[0] + 1)
        nb += int((petits & zone).sum())
    trous = ndi.binary_fill_holes(sil) & ~sil
    lab, n = ndi.label(trous)
    if n:
        t = ndi.sum(trous, lab, range(1, n + 1))
        petits = np.isin(lab, np.nonzero(t <= 3)[0] + 1)
        nb += int((petits & zone).sum())
    return nb


def jointures(A, masque, sil, etat, fond):
    """Aux 6 jointures : trous = pixels du décor visibles dans le disque de 6 px autour de l'articulation ;
    traits = pixels de contour (très sombres) dans le disque de 5 px (coupure ou pli visible sur l'articulation)."""
    res = {}
    gy, gx = np.mgrid[0:A.shape[0], 0:A.shape[1]]
    sombre = A.sum(2) < 75
    for cle in ('avant', 'arriere'):
        o = OS[cle]
        for nom, b in zip(('epaule', 'coude', 'poignet'), o):
            if b not in etat['J']:
                res[cle + '.' + nom] = None
                continue
            P = etat['J'][b]
            disque6 = (gx - P[0]) ** 2 + (gy - P[1]) ** 2 <= 36
            disque5 = (gx - P[0]) ** 2 + (gy - P[1]) ** 2 <= 25
            res[cle + '.' + nom] = {'trous': int((disque6 & ~sil).sum()), 'traits': int((disque5 & sombre).sum())}
    return res


def courir(rendu, noms, frames, vieux):
    sc = rendu.scene
    sortie = {}
    for i in range(max(frames) + 1):
        sc.image(i / FPS, FPS)
        if i not in frames:
            continue
        sortie[i] = deux_rendus(sc, noms)
    return sortie


def flexion(et, cle):
    o = OS[cle]
    S, E = np.array(et['J'][o[0]]), np.array(et['J'][o[1]])
    W = np.array(et['J'][o[2]]) if o[2] in et['J'] else None
    if W is None:
        return 0.0
    a, b = E - S, W - E
    return math.degrees(math.acos(np.clip(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9), -1, 1)))


def stats(v):
    v = [x for x in v if x > 0]
    if not v:
        return None
    return {'min': round(min(v), 1), 'max': round(max(v), 1), 'moyenne': round(float(np.mean(v)), 1),
            'ecart_max_pct': round(100 * (max(v) - min(v)) / float(np.mean(v)), 1)}


def main():
    sortie = {'methode': 'Voir le docstring de mesures7.py et le LISEZ-MOI.'}
    N = 90
    frames = list(range(N))
    # --- joie, avant et après (mêmes images)
    res = {}
    donnees = {}
    for cle, seq, fichier, noms in (('avant', 'g2_apres', 'scene.json', VIEUX), ('apres', 's7_g2_apres', 'scene7.json', NOUVEAUX)):
        r = moteur7.Rendu7(seq, None, FPS, fichier)
        r.demarrer()
        donnees[cle] = courir(r, noms, frames, None)
    # (a) épaisseur sur les 3 poses les plus pliées (d'après la flexion des os après)
    flex = {i: max(flexion(donnees['apres'][i][3], 'avant'), flexion(donnees['apres'][i][3], 'arriere')) for i in frames}
    choisies = sorted(sorted(frames, key=lambda i: -flex[i])[:40:13] + [sorted(frames, key=lambda i: -flex[i])[0]])[:4]
    ep = {}
    for i in choisies:
        ep[str(i)] = {}
        for cle in ('avant', 'apres'):
            A, m, sil, et, mav, mar = donnees[cle][i]
            ep[str(i)][cle] = {}
            for bras in ('avant', 'arriere'):
                S, E, W = joints(et, bras, None)
                prof = epaisseur(mav if bras == 'avant' else mar, S, E, W)
                ep[str(i)][cle][bras] = {'profil_haut_du_bras_px': prof[0], 'profil_avant_bras_px': prof[1] if len(prof) > 1 else None,
                                         'flexion_coude_deg': round(flexion(et, bras), 1),
                                         'ecart_haut': stats(prof[0]), 'ecart_avant_bras': stats(prof[1]) if len(prof) > 1 else None}
    sortie['a_epaisseur_poses_pliees_joie'] = ep
    # (b) jointures sur 90 images : somme et maximum
    jb = {}
    for cle in ('avant', 'apres'):
        tot = {}
        for i in frames:
            A, m, sil, et, mav, mar = donnees[cle][i]
            for k, v in jointures(A, m, sil, et, None).items():
                if v is None:
                    continue
                t = tot.setdefault(k, {'trous_total': 0, 'trous_max': 0, 'traits_total': 0, 'traits_max': 0})
                t['trous_total'] += v['trous']; t['trous_max'] = max(t['trous_max'], v['trous'])
                t['traits_total'] += v['traits']; t['traits_max'] = max(t['traits_max'], v['traits'])
        jb[cle] = tot
    sortie['b_jointures_joie_90_images'] = jb
    # (c) pixels isolés
    sortie['c_pixels_isoles_joie_90_images'] = {cle: {'total': sum(isoles(donnees[cle][i][2], donnees[cle][i][1], None, None) for i in frames),
                                                       'par_image_moyenne': round(sum(isoles(donnees[cle][i][2], donnees[cle][i][1], None, None) for i in frames) / N, 2)}
                                                 for cle in ('avant', 'apres')}
    # (d) longueur apparente
    d = {}
    for cle in ('avant', 'apres'):
        d[cle] = {}
        for bras in ('avant', 'arriere'):
            L = []
            for i in frames:
                A, m, sil, et, mav, mar = donnees[cle][i]
                S = joints(et, bras, None)[0]
                # masque du seul bras : composante la plus proche de l'épaule
                if flexion(et, bras) >= 50:
                    continue            # bras replié : le masque se recouvre, la mesure n'a plus de sens
                v = longueur_apparente(mav if bras == 'avant' else mar, S)
                if v > 0:
                    L.append(v)
            d[cle][bras] = {'images_comptees': len(L), 'min_px': round(min(L), 1), 'max_px': round(max(L), 1), 'moyenne_px': round(float(np.mean(L)), 1),
                            'ecart_pct': round(100 * (max(L) - min(L)) / float(np.mean(L)), 1)}
    sortie['d_longueur_apparente_joie_90_images'] = d
    # longueur des os (squelette) pendant le test d'amplitude
    ra = amplitude.RenduAmp()
    ra.demarrer()
    Ls = {'avant': [], 'arriere': []}
    ep2 = {}
    da = {}
    flexa = {}
    for i in range(120):
        ra.scene.image(i / FPS, FPS)
        A, m, sil, et, mav, mar = deux_rendus(ra.scene, NOUVEAUX)
        da[i] = (m, et, sil, A, mav, mar)
        for bras in Ls:
            S, E, W = joints(et, bras, None)
            Ls[bras].append(float(np.linalg.norm(E - S) + np.linalg.norm(W - E)))
    sortie['d_longueur_os_amplitude_120_images'] = {b: {'min_px': round(min(v), 3), 'max_px': round(max(v), 3),
                                                      'ecart_pct': round(100 * (max(v) - min(v)) / float(np.mean(v)), 4)} for b, v in Ls.items()}
    # épaisseur pendant l'amplitude : images de coude plié à 140° et 70°
    ep3 = {}
    for i in (45, 52, 60, 75):
        m, et, sil, A, mav, mar = da[i]
        ep3[str(i)] = {}
        for bras in ('avant', 'arriere'):
            S, E, W = joints(et, bras, None)
            prof = epaisseur(mav if bras == 'avant' else mar, S, E, W)
            ep3[str(i)][bras] = {'flexion_coude_deg': round(flexion(et, bras), 1), 'profil_haut_du_bras_px': prof[0], 'profil_avant_bras_px': prof[1],
                                 'ecart_haut': stats(prof[0]), 'ecart_avant_bras': stats(prof[1])}
    sortie['a_epaisseur_amplitude_apres'] = ep3
    # longueur apparente pendant l'amplitude
    la = {}
    for bras in ('avant', 'arriere'):
        L = []
        for i in range(0, 120, 2):
            m, et, sil, A, mav, mar = da[i]
            S = joints(et, bras, None)[0]
            if flexion(et, bras) >= 50:
                continue
            L.append(longueur_apparente(mav if bras == 'avant' else mar, S))
        la[bras] = {'images_comptees': len(L), 'min_px': round(min(L), 1), 'max_px': round(max(L), 1), 'ecart_pct': round(100 * (max(L) - min(L)) / float(np.mean(L)), 1)}
    sortie['d_longueur_apparente_amplitude_apres'] = la
    json.dump(sortie, open(os.path.join(ICI, 'mesures.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in sortie.items() if k[0] in 'bcd'}, ensure_ascii=False, indent=1)[:6000])


if __name__ == '__main__':
    main()

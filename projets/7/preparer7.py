"""Prépare les données de la demande 7 (à lancer une fois : python3 preparer7.py).

1. scene7.json : scène de projets/5 avec le nouveau squelette des bras
   (vraies épaules sur le tronc, os de 56 et 50 px, bras au repos pendants, os « main2 » pour la main arrière)
   et sans les anciens calques de bras (les bras sont dessinés par moteur7.py).
2. poses/n7_*.json : toutes les poses de projets/5 recalées pour le nouveau squelette. Pour chaque pose,
   la main (poignet) reste à la MÊME place que dans l'ancien dessin (cinématique inverse à deux os), et sa
   direction aussi : les mouvements existants (joie, mange, saisie, caresse) ne sont pas cassés.
3. sequences/s7_*.json : les séquences existantes réécrites avec les poses n7_.
"""
import glob
import json
import math
import os

ICI = os.path.dirname(os.path.abspath(__file__))
P5 = os.path.join(os.path.dirname(ICI), '5')
P6 = os.path.join(os.path.dirname(ICI), '6')

NEUF = {'bras': ((228, 222), (228, 278)), 'avant_bras': ((228, 278), (228, 328)), 'main': ((228, 328), None),
        'bras2': ((140, 220), (140, 276)), 'avant_bras2': ((140, 276), (140, 326)), 'main2': ((140, 326), None)}


def u(a):
    return (math.cos(math.radians(a)), math.sin(math.radians(a)))


def n180(a):
    return (a + 180.0) % 360.0 - 180.0


def scene():
    s = json.load(open(os.path.join(P5, 'scene.json'), encoding='utf-8'))
    t = s['objets'][0]['animable']
    anc = {o['nom']: o for o in t['squelette']['os']}
    vieux = {}
    for nom in ('bras', 'avant_bras', 'bras2', 'avant_bras2'):
        o = anc[nom]
        v = (o['vers'][0] - o['pivot'][0], o['vers'][1] - o['pivot'][1])
        vieux[nom] = {'pivot': tuple(o['pivot']), 'L': math.hypot(*v), 'dir0': math.degrees(math.atan2(v[1], v[0]))}
    for nom, (piv, vers) in NEUF.items():
        if nom == 'main2':
            t['squelette']['os'].append({'nom': 'main2', 'parent': 'avant_bras2', 'pivot': list(piv), 'angle': 'poignet2'})
            continue
        anc[nom]['pivot'] = list(piv)
        if vers:
            anc[nom]['vers'] = list(vers)
        else:
            anc[nom].pop('vers', None)
    anc['main']['pivot'] = list(NEUF['main'][0])
    t['dessin'] = [d for d in t['dessin'] if d['nom'] in ('jambe_d', 'jambe_g', 'corps', 'tige')]
    t['dessin'].insert(3, {'nom': 'bras7'})
    t['calques']['corps'] = 'calques/corps7.png'
    json.dump(s, open(os.path.join(ICI, 'scene7.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return vieux


def ik(S, L1, L2, T, E_vieux):
    dx, dy = T[0] - S[0], T[1] - S[1]
    d = min(max(math.hypot(dx, dy), abs(L1 - L2) + 0.5), L1 + L2 - 0.3)
    base = math.degrees(math.atan2(dy, dx))
    ouv = math.degrees(math.acos(max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)))))
    meilleur = None
    for sgn in (1, -1):
        a1 = base + sgn * ouv
        E = (S[0] + L1 * u(a1)[0], S[1] + L1 * u(a1)[1])
        dist = math.hypot(E[0] - E_vieux[0], E[1] - E_vieux[1])
        if meilleur is None or dist < meilleur[0]:
            meilleur = (dist, a1, E)
    _, a1, E = meilleur
    a2 = math.degrees(math.atan2(T[1] - E[1], T[0] - E[0]))
    return a1, a2


def recaler(d, vieux):
    q = d.get('squelette')
    if q is None:
        return d
    L1n, L2n = 56.0, 50.0
    for (e, c, p, bras, avant, Sn) in (('epaule', 'coude', 'poignet', 'bras', 'avant_bras', NEUF['bras'][0]),
                                       ('epaule2', 'coude2', 'poignet2', 'bras2', 'avant_bras2', NEUF['bras2'][0])):
        if e not in q:
            continue
        b, a = vieux[bras], vieux[avant]
        a1o = b['dir0'] + q[e]
        Eo = (b['pivot'][0] + b['L'] * u(a1o)[0], b['pivot'][1] + b['L'] * u(a1o)[1])
        a2o = a['dir0'] + q[e] + q.get(c, 0.0)
        To = (Eo[0] + a['L'] * u(a2o)[0], Eo[1] + a['L'] * u(a2o)[1])
        a1, a2 = ik(Sn, L1n, L2n, To, Eo)
        ep, co = n180(a1 - 90.0), n180(a2 - a1)
        if e == 'epaule':
            q[p] = n180((q[e] + q.get(c, 0.0) + q.get(p, 0.0)) - ep - co - 90.0)
        else:
            q[p] = 0.0
        q[e], q[c] = round(ep, 2), round(co, 2)
        q[p] = round(q[p], 2)
    return d


def main():
    vieux = scene()
    os.makedirs(os.path.join(ICI, 'poses'), exist_ok=True)
    os.makedirs(os.path.join(ICI, 'sequences'), exist_ok=True)
    noms = []
    for f in sorted(glob.glob(os.path.join(P5, 'poses', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        nom = os.path.basename(f)[:-5]
        d['nom'] = 'n7_' + nom
        d = recaler(d, vieux)
        json.dump(d, open(os.path.join(ICI, 'poses', 'n7_' + nom + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        noms.append(nom)
    print(len(noms), 'poses recalées')
    sources = {}
    for f in glob.glob(os.path.join(P5, 'sequences', '*.json')) + glob.glob(os.path.join(P6, 'sequences', '*.json')):
        sources[os.path.basename(f)[:-5]] = f
    for nom, f in sources.items():
        s = json.load(open(f, encoding='utf-8'))
        for piste in s['pistes'].values():
            for e in piste:
                if e.get('pose') in noms:
                    e['pose'] = 'n7_' + e['pose']
        s['nom'] = 's7_' + nom
        json.dump(s, open(os.path.join(ICI, 'sequences', 's7_' + nom + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(sources), 'séquences réécrites')


if __name__ == '__main__':
    main()

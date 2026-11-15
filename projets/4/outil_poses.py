"""Outil d'écriture des poses clés et des séquences (à lancer une fois ; le moteur
n'en a pas besoin : il lit seulement les fichiers JSON produits).

Poses : pour celles où la main doit atteindre un point précis (le morceau posé sur
le bord du cercueil, la bouche), on donne la cible de la main et sa direction ;
l'outil calcule par cinématique inverse à deux os les angles de l'épaule, du coude
et du poignet. Seuls des angles sont enregistrés : les longueurs d'os sont fixes.
Séquences : l'outil additionne les durées pour que les pistes (Thomas, gant,
morceau, mouches, bulle) tombent ensemble, puis écrit sequences/<nom>.json.
Une fois écrits, poses et séquences sont de simples fichiers JSON modifiables à la main.
Lancer : python3 outil_poses.py
"""
import json
import math
import os

import numpy as np

import moteur

ICI = os.path.dirname(os.path.abspath(__file__))
scene = moteur.lire_json('scene.json')
PAL = moteur.lire_json('palette.json')
TH = moteur.Thomas(next(o for o in scene['objets'] if o['nom'] == 'thomas'), PAL)
BOUCHE_AVANT = (249.0, 177.0)     # bord avant de l'intérieur de la bouche (Thomas regarde à droite)
PRISE = [15.0, 2.0]               # point de prise dans le repère de la main (entre les doigts)
SUR_LE_BORD = (303.0, 317.0)      # centre du morceau posé sur le bord du cercueil
TENUE = [-9.0, 0.0]               # le morceau dépasse des doigts vers la bouche (repère du morceau)

REPOS = {
    'squelette': {'racine': 0.0, 'racine_x': 0.0, 'racine_y': 0.0, 'tronc': 0.0, 'cou': 0.0,
                  'epaule': 0.0, 'coude': 0.0, 'poignet': 0.0, 'main_fermeture': 0.55,
                  'epaule2': 0.0, 'coude2': 0.0,
                  'pied_g_x': 0.0, 'pied_g_y': 0.0, 'pied_g': 0.0, 'pied_d_x': 0.0, 'pied_d_y': 0.0, 'pied_d': 0.0},
    'corps': {'inclinaison': 0.0, 'x': 0.0, 'y': 0.0, 'epaules': 0.0, 'poitrine': 0.0},
    'zones': {'tete_rotation': 0.0, 'tete_x': 0.0, 'tete_y': 0.0, 'machoire': 0.0, 'joues': 0.0, 'sourire': 0.0,
              'paupieres': 0.0, 'cou_deglutition': 0.0, 'oeil_pendant_regard': 0.0},
    'vie': {'eveil': 1.0, 'sommeil': 0.0, 'frisson': 0.0},
    'physique': {'sol_oeil': 2000.0},
    'attaches': {'prise_main': PRISE},
}
POSES = {}


def fusion(base, ajout):
    out = json.loads(json.dumps(base))
    for k, v in ajout.items():
        if isinstance(v, dict):
            out.setdefault(k, {}).update(v)
        else:
            out[k] = v
    return out


def etat_de(pose):
    p = moteur.aplatir(pose)
    c = TH.couches(p, [])
    return p, c, TH.resoudre(p, c)


def point(pose, x, y):
    """Point du corps (coordonnées de repos) -> monde, dans cette pose."""
    p, c, et = etat_de(pose)
    return TH.point_corps(et, c, x, y)


def norm180(a):
    return (a + 180.0) % 360.0 - 180.0


def ik(pose, cible, direction, fermeture):
    """Angles (épaule, coude, poignet) pour que le point de prise de la main
    soit en « cible » avec la main orientée selon « direction » (degrés)."""
    base_pose = fusion(pose, {'squelette': {'epaule': 0.0, 'coude': 0.0, 'poignet': 0.0}})
    p, c, et = etat_de(base_pose)
    E = et['J']['bras']
    a_parent = et['A']['bras']                      # angle du tronc + rotation locale du champ
    a_u0, a_f0 = TH.os['bras']['angle0'], TH.os['avant_bras']['angle0']
    l1, l2 = TH.os['bras']['longueur'], TH.os['avant_bras']['longueur']
    k = TH.main.get('taille', 1.0)
    px, py = moteur.tourner(PRISE[0] * k, PRISE[1] * k, direction)
    P = np.array(cible) - [px, py]
    d = P - E
    L = float(np.linalg.norm(d))
    portee = l1 + l2 - 0.6
    atteint = L <= portee
    L = min(max(L, abs(l1 - l2) + 0.5), portee)
    base = math.degrees(math.atan2(d[1], d[0]))
    A = math.degrees(math.acos((l1 * l1 + L * L - l2 * l2) / (2 * l1 * L)))
    meilleur = None
    for s in (1, -1):
        a_u = base + s * A                                  # angle absolu du haut du bras
        C = E + l1 * np.array([math.cos(math.radians(a_u)), math.sin(math.radians(a_u))])
        w = E + d / np.linalg.norm(d) * L
        a_f = math.degrees(math.atan2(w[1] - C[1], w[0] - C[0]))
        if norm180(a_f - a_u) <= 0:                         # le coude ne plie que dans un sens
            meilleur = (a_u, a_f)
    a_u, a_f = meilleur
    if not atteint:
        print('   attention : cible hors de portée, bras tendu au maximum')
    return {'epaule': round(norm180(a_u - a_u0 - a_parent), 2),
            'coude': round(norm180((a_f - a_f0) - (a_u - a_u0)), 2),
            'poignet': round(norm180(direction - a_f), 2), 'main_fermeture': fermeture}


def json_compact(d):
    lignes = ['{']
    items = list(d.items())
    for i, (k, v) in enumerate(items):
        fin = ',' if i < len(items) - 1 else ''
        lignes.append('  %s: %s%s' % (json.dumps(k), json.dumps(v, ensure_ascii=False), fin))
    lignes.append('}')
    return '\n'.join(lignes) + '\n'


def ecrire(nom, description, pose):
    d = {'nom': nom, 'description': description}
    d.update(pose)
    os.makedirs(os.path.join(ICI, 'poses'), exist_ok=True)
    with open(os.path.join(ICI, 'poses', nom + '.json'), 'w', encoding='utf-8') as f:
        f.write(json_compact(d))
    POSES[nom] = pose
    return pose


def entiere(nom, description, ajout):
    return ecrire(nom, description, fusion(REPOS, ajout))


def avec_bras(nom, description, ajout, cible, direction, fermeture):
    pose = fusion(REPOS, ajout)
    pose['squelette'].update(ik(pose, cible, direction, fermeture))
    return ecrire(nom, description, pose)


# ================================================================ séquences
class Piste:
    """Écrit une piste en additionnant les durées ; « marque » retient l'instant
    d'arrivée d'une clé pour caler les autres pistes dessus."""

    def __init__(self):
        self.e = []
        self.t = 0.0
        self.m = {}

    def cle(self, pose=None, duree=0.0, courbe='doux', tenir=0.0, valeurs=None, marque=None):
        e = {}
        if pose:
            e['pose'] = pose
        if valeurs:
            e['valeurs'] = valeurs
        if self.e:
            e['duree'] = round(duree, 4)
            e['courbe'] = courbe
            self.t += duree
        if marque:
            self.m[marque] = self.t
        if tenir:
            e['tenir'] = round(tenir, 4)
            self.t += tenir
        self.e.append(e)
        return self

    def jusqua(self, pose, t_fin, courbe='doux', valeurs=None):
        return self.cle(pose, t_fin - self.t, courbe, valeurs=valeurs)


def absolue(cles):
    """[(instant, valeurs, courbe)] -> entrées de piste (durées)."""
    out = []
    t_prec = 0.0
    for i, (t, v, courbe) in enumerate(cles):
        e = {'valeurs': v}
        if i == 0:
            if t > 0:
                e['tenir'] = round(t, 4)
        else:
            e['duree'] = round(t - t_prec, 4)
            e['courbe'] = courbe
        t_prec = t
        out.append(e)
    return out


def ecrire_sequence(nom, description, duree, pistes, boucle=True):
    d = {'nom': nom, 'description': description, 'duree': duree, 'boucle': boucle,
         'recettes': {'thomas': ['vie']}, 'pistes': pistes}
    lignes = ['{', '  "nom": %s,' % json.dumps(nom), '  "description": %s,' % json.dumps(description, ensure_ascii=False),
              '  "duree": %s,' % duree, '  "boucle": %s,' % json.dumps(boucle),
              '  "recettes": {"thomas": ["vie"]},', '  "pistes": {']
    noms = list(pistes)
    for i, n in enumerate(noms):
        lignes.append('    %s: [' % json.dumps(n))
        for j, e in enumerate(pistes[n]):
            lignes.append('      %s%s' % (json.dumps(e, ensure_ascii=False), ',' if j < len(pistes[n]) - 1 else ''))
        lignes.append('    ]%s' % (',' if i < len(noms) - 1 else ''))
    lignes += ['  }', '}']
    os.makedirs(os.path.join(ICI, 'sequences'), exist_ok=True)
    with open(os.path.join(ICI, 'sequences', nom + '.json'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lignes) + '\n')
    print('séquence', nom, ':', len(pistes['thomas']), 'clés pour Thomas,', len({e.get('pose') for e in pistes['thomas']}), 'poses différentes')


# ================================================================ A. Thomas mange
def poses_mange():
    entiere('repos', "Pose de repos de l'image d'origine : debout, bras le long du corps, main vide à demi fermée.", {})
    entiere('regard_gant', "Thomas lève la tête vers le gant qui arrive en haut à droite ; l'œil pendant se tourne aussi, le poids recule un peu.",
            {'squelette': {'racine_x': -1.0, 'tronc': -1.0}, 'corps': {'epaules': -0.6},
             'zones': {'tete_rotation': -8.0, 'tete_x': 1.0, 'machoire': 0.2, 'oeil_pendant_regard': 25.0}})
    entiere('regard_morceau', "La tête suit le morceau qui tombe et se baisse vers lui ; le buste se penche un peu.",
            {'squelette': {'racine_x': 1.0}, 'corps': {'inclinaison': 1.5},
             'zones': {'tete_rotation': 7.0, 'tete_x': 2.5, 'tete_y': 1.0, 'machoire': 0.3, 'oeil_pendant_regard': -20.0}})
    entiere('anticipation', "Tension avant le geste : recul du bassin, genoux qui plient un peu, épaules qui montent, inspiration, main qui s'ouvre.",
            {'squelette': {'racine_x': -2.5, 'racine_y': 2.0, 'tronc': -1.0, 'epaule': -8.0, 'coude': -12.0, 'poignet': -12.0,
                           'main_fermeture': 0.05, 'epaule2': -5.0},
             'corps': {'inclinaison': -1.5, 'epaules': -1.5, 'poitrine': 0.8},
             'zones': {'tete_rotation': 5.0, 'tete_x': 1.5, 'machoire': 0.35, 'oeil_pendant_regard': -20.0}})
    cz = {'squelette': {'racine_x': 1.5, 'racine_y': 1.0, 'epaule2': 4.0}, 'corps': {'inclinaison': 3.0, 'x': 1.0},
          'zones': {'tete_rotation': 7.0, 'tete_x': 2.0, 'machoire': 0.3, 'oeil_pendant_regard': -20.0}}
    avec_bras('bras_part', "Le bras part vers le morceau : l'épaule avance, le coude s'ouvre, la main reste ouverte.",
              cz, (290.0, 283.0), 22.0, 0.0)
    cz = {'squelette': {'racine_x': 3.5, 'racine_y': 2.5, 'epaule2': 9.0, 'coude2': -6.0}, 'corps': {'inclinaison': 6.0, 'x': 2.0, 'y': 0.5},
          'zones': {'tete_rotation': 8.0, 'tete_x': 2.5, 'tete_y': 0.5, 'machoire': 0.25, 'oeil_pendant_regard': -20.0}}
    avec_bras('bras_mi_chemin', "Bras à mi-chemin : le poids passe vers l'avant, le bras arrière part en contrepoids, la main descend vers le morceau.",
              cz, (299.0, 303.0), 45.0, 0.0)
    cz = {'squelette': {'racine_x': 5.0, 'racine_y': 4.0, 'epaule2': 12.0, 'coude2': -8.0},
          'corps': {'inclinaison': 8.5, 'x': 3.0, 'y': 1.5, 'epaules': 0.5},
          'zones': {'tete_rotation': 9.0, 'tete_x': 3.0, 'tete_y': 1.0, 'machoire': 0.15, 'oeil_pendant_regard': -25.0}}
    avec_bras('main_saisit', "La main ouverte arrive sur le morceau posé sur le bord du cercueil ; buste penché, genoux fléchis, bras presque tendu.",
              cz, SUR_LE_BORD, 58.0, 0.0)
    avec_bras('main_fermee', "Les doigts se referment sur le morceau (le morceau s'attache à la main).",
              cz, SUR_LE_BORD, 58.0, 1.0)
    cz = {'squelette': {'racine_x': 2.5, 'racine_y': 1.5, 'epaule2': 6.0, 'coude2': -4.0}, 'corps': {'inclinaison': 4.0, 'x': 1.5, 'epaules': -0.5},
          'zones': {'tete_rotation': 6.0, 'tete_x': 2.0, 'machoire': 0.3, 'oeil_pendant_regard': -10.0}}
    avec_bras('bras_leve', "Le morceau remonte : le buste se redresse, le coude se plie, le poignet tourne.",
              cz, (290.0, 262.0), -15.0, 1.0)
    cz = {'squelette': {'racine_x': 0.5, 'epaule2': 2.0}, 'corps': {'inclinaison': 1.5, 'x': 0.5},
          'zones': {'tete_rotation': 6.0, 'tete_x': 2.0, 'tete_y': 0.5, 'machoire': 0.2, 'oeil_pendant_regard': 0.0}}
    b = point(fusion(REPOS, cz), *BOUCHE_AVANT)
    avec_bras('bras_presque_bouche', "Bras presque à la bouche : coude plié contre le corps, le morceau à hauteur du menton, devant la bouche.",
              cz, (b[0] + 30.0, b[1] + 10.0), -100.0, 1.0)

    # trois bouchées : à chacune le morceau est plus court, la main vient donc plus près
    for i, (devant, dedans) in enumerate(((26.0, 14.0), (17.0, 5.0), (8.0, -5.0)), 1):
        cz = {'corps': {'inclinaison': 1.0}, 'zones': {'tete_rotation': 6.0, 'tete_x': 2.5, 'tete_y': 0.5, 'machoire': 0.25, 'oeil_pendant_regard': 10.0}}
        b = point(fusion(REPOS, cz), *BOUCHE_AVANT)
        avec_bras('main_bouche_%d' % i, "Bouchée %d : la main présente le morceau juste devant la bouche (d'après la pose « repas » de la planche)." % i,
                  cz, (b[0] + devant, b[1] + 3.0), -120.0, 1.0)
        cz = {'squelette': {'racine_x': -1.0, 'tronc': -1.5}, 'corps': {'inclinaison': 0.0, 'poitrine': 0.6},
              'zones': {'tete_rotation': 2.0, 'tete_x': 1.5, 'machoire': 1.0, 'oeil_pendant_regard': 10.0}}
        b = point(fusion(REPOS, fusion(cz, {'zones': {'machoire': 0.0}})), *BOUCHE_AVANT)
        avec_bras('bouche_ouverte_%d' % i, "Bouchée %d : la mâchoire s'ouvre grand, la tête se relève un peu (élan avant la morsure)." % i,
                  cz, (b[0] + devant - 3.0, b[1] + 4.0), -120.0, 1.0)
        cz = {'squelette': {'racine_x': 1.0, 'tronc': 1.0}, 'corps': {'inclinaison': 1.5},
              'zones': {'tete_rotation': 8.0, 'tete_x': 3.0, 'tete_y': 0.8, 'machoire': 0.85, 'oeil_pendant_regard': 10.0}}
        b = point(fusion(REPOS, fusion(cz, {'zones': {'machoire': 0.0}})), *BOUCHE_AVANT)
        avec_bras('dans_la_bouche_%d' % i, "Bouchée %d : la main pousse le morceau DANS la bouche encore ouverte (il passe derrière les lèvres et les dents)." % i,
                  cz, (b[0] + dedans, b[1] + 4.0), -120.0, 1.0)
        cz = {'squelette': {'racine_x': 1.0, 'tronc': 1.0}, 'corps': {'inclinaison': 1.5},
              'zones': {'tete_rotation': 8.5, 'tete_x': 3.0, 'tete_y': 1.0, 'machoire': -0.12, 'joues': 0.4, 'oeil_pendant_regard': 10.0}}
        avec_bras('morsure_%d' % i, "Bouchée %d : la mâchoire se referme d'un coup sur le morceau." % i,
                  cz, (b[0] + dedans, b[1] + 4.0), -120.0, 1.0)
        if i < 3:
            cz = {'corps': {'inclinaison': 1.0, 'x': 0.5},
                  'zones': {'tete_rotation': 6.0, 'tete_x': 2.0, 'tete_y': 0.5, 'machoire': 0.0, 'joues': 0.8, 'oeil_pendant_regard': 0.0}}
            b = point(fusion(REPOS, cz), *BOUCHE_AVANT)
            avec_bras('retire_%d' % i, "Après la bouchée %d : la main recule, on voit le morceau entamé ; les joues sont pleines." % i,
                      cz, (b[0] + 34.0 - 6.0 * i, b[1] + 16.0), -100.0, 1.0)
    # mastication : poses partielles (visage seulement) ; le bras garde sa position
    ecrire('mastication_1', "Mâchoire mi-ouverte, joues gonflées, tête qui plonge un peu.",
           {'zones': {'machoire': 0.6, 'joues': 1.0, 'tete_rotation': 7.5, 'tete_y': 0.8}})
    ecrire('mastication_2', "Mâchoire fermée, joues qui se vident, tête qui remonte.",
           {'zones': {'machoire': -0.1, 'joues': 0.3, 'tete_rotation': 5.5, 'tete_y': -0.2}})
    ecrire('mastication_3', "Mâchoire mi-ouverte décalée, joues pleines, tête un peu en avant.",
           {'zones': {'machoire': 0.5, 'joues': 1.0, 'tete_rotation': 6.5, 'tete_x': 3.5, 'tete_y': 0.5}})
    ecrire('avale_prepare', "Avant d'avaler : bouche fermée, menton rentré, tête qui remonte, épaules qui montent.",
           {'zones': {'machoire': -0.1, 'joues': 0.5, 'tete_rotation': 3.0, 'tete_y': -1.0}, 'corps': {'epaules': -1.0}})
    ecrire('avalement', "Il avale : la tête plonge, le renflement descend dans le cou (une unité de cou_deglutition par gorgée).",
           {'zones': {'machoire': -0.1, 'joues': 0.0, 'tete_rotation': 9.0, 'tete_y': 1.4}, 'corps': {'epaules': 0.6}})
    cz = {'corps': {'inclinaison': 1.0}, 'zones': {'tete_rotation': 6.0, 'tete_x': 2.0, 'joues': 0.9, 'oeil_pendant_regard': 0.0}}
    b = point(fusion(REPOS, cz), *BOUCHE_AVANT)
    avec_bras('menton', "Main vide restée sous le menton pendant qu'il mâche la dernière bouchée.",
              cz, (b[0] + 14.0, b[1] + 26.0), -85.0, 0.8)
    cz = {'squelette': {'racine_x': -1.5, 'tronc': -2.0, 'epaule2': -4.0},
          'corps': {'inclinaison': -1.0, 'x': -1.0, 'epaules': -1.6, 'poitrine': 1.9},
          'zones': {'tete_rotation': -4.5, 'tete_y': -0.5, 'machoire': 0.15, 'paupieres': 0.45, 'sourire': 0.6, 'oeil_pendant_regard': 0.0}}
    avec_bras('soulagement_inspire', "Satisfait, il inspire longuement : poitrine gonflée, épaules hautes, tête en arrière, yeux mi-clos ; le bras redescend.",
              cz, (290.0, 262.0), 15.0, 0.6)
    entiere('soulagement', "Long soupir : la poitrine se vide, les épaules retombent, les genoux mollissent, la tête s'affaisse, la main pend.",
            {'squelette': {'racine_x': 0.5, 'racine_y': 2.0, 'tronc': 1.0, 'epaule': 1.0, 'coude': 4.0, 'poignet': 12.0, 'main_fermeture': 0.45, 'epaule2': 2.0},
             'corps': {'inclinaison': 0.8, 'x': 0.5, 'epaules': 2.6, 'poitrine': -1.3},
             'zones': {'tete_rotation': 3.0, 'tete_y': 1.2, 'machoire': 0.25, 'paupieres': 0.5, 'sourire': 0.8}})


def sequence_mange():
    T = Piste()
    T.cle('repos', tenir=1.1)
    T.cle('regard_gant', 0.45, tenir=0.95)
    T.cle('regard_morceau', 0.5, marque='regarde')
    T.cle('anticipation', 0.42)
    T.cle('bras_part', 0.33, 'spline')
    T.cle('bras_mi_chemin', 0.3, 'spline')
    T.cle('main_saisit', 0.32, 'spline')
    T.cle('main_fermee', 0.22, 'doux', tenir=0.1, marque='saisi')
    T.cle('bras_leve', 0.42, 'spline')
    T.cle('bras_presque_bouche', 0.38, 'spline')
    deg = 0.0
    for i in (1, 2, 3):
        g = {'zones': {'cou_deglutition': deg}}
        T.cle('main_bouche_%d' % i, 0.3, 'doux', valeurs=g, marque='presente_%d' % i)
        T.cle('bouche_ouverte_%d' % i, 0.24, 'doux', valeurs=g)
        T.cle('dans_la_bouche_%d' % i, 0.2, 'doux', valeurs=g, marque='dedans_%d' % i, tenir=0.06)
        T.cle('morsure_%d' % i, 0.13, 'entree', valeurs=g, marque='mord_%d' % i, tenir=0.12)
        if i < 3:
            T.cle('retire_%d' % i, 0.3, 'doux', valeurs=g, marque='retire_%d' % i)
        else:
            T.cle('menton', 0.36, 'doux', valeurs=g)
        for m in (1, 2, 3, 2):
            T.cle('mastication_%d' % m, 0.16, 'doux', valeurs=g)
        T.cle('avale_prepare', 0.2, 'doux', valeurs=g)
        deg += 1.0
        T.cle('avalement', 0.55, 'doux', valeurs={'zones': {'cou_deglutition': deg}}, tenir=0.08, marque='avale_%d' % i)
    g = {'zones': {'cou_deglutition': deg}}
    T.cle('soulagement_inspire', 0.7, 'doux', valeurs=g)
    T.cle('soulagement', 0.75, 'doux', valeurs=g)
    assert T.t < 15.5, T.t
    T.jusqua('repos', 16.0, 'doux', valeurs=g)
    m = T.m
    print('   instants :', {k: round(v, 2) for k, v in m.items()})
    # le gant : au plus 15 px par image (30 i/s), départ et arrivée en douceur
    haut = {'x': 380.0, 'y': -110.0, 'angle': 9.0, 'ouverture': 0.0, 'paume': 0.0}
    bas = {'x': 322.0, 'y': 258.0, 'angle': 0.0, 'ouverture': 0.0}
    t_bas = m['regarde'] - 0.45
    gant = absolue([(t_bas - 1.7, haut, 'doux'), (t_bas, bas, 'doux'), (t_bas + 0.08, {}, 'doux'),
                    (t_bas + 0.26, {'ouverture': 1.0}, 'doux'), (t_bas + 0.5, {}, 'doux'),
                    (t_bas + 2.2, dict(haut, ouverture=0.3), 'doux')])
    t_lache = t_bas + 0.16
    morceau = absolue([
        (t_lache, {'visible': 1, 'attache': 'gant', 'decalage': [0.0, 9.0], 'x': 322.0, 'y': 267.0, 'angle': 0.0, 'angle_main': -48.0,
                   'tenue': [0.0, 0.0], 'ecrasement': 0.0, 'bouchees': 0.0}, 'doux'),
        (t_lache, {'attache': 'libre'}, 'doux'),
        (t_lache + 0.27, {'x': SUR_LE_BORD[0], 'y': SUR_LE_BORD[1], 'angle': 8.0}, 'chute'),
        (t_lache + 0.31, {'ecrasement': 0.3}, 'sortie'),
        (t_lache + 0.56, {'ecrasement': 0.0}, 'doux'),
        (m['saisi'], {}, 'doux'),
        (m['saisi'], {'attache': 'main'}, 'doux'),
        (m['presente_1'], {'angle_main': 120.0, 'tenue': TENUE}, 'doux'),
        (m['dedans_1'] + 0.06, {}, 'doux'), (m['mord_1'] + 0.02, {'bouchees': 1.0}, 'entree'),
        (m['dedans_2'] + 0.06, {}, 'doux'), (m['mord_2'] + 0.02, {'bouchees': 2.0}, 'entree'),
        (m['dedans_3'] + 0.06, {}, 'doux'), (m['mord_3'] + 0.02, {'bouchees': 3.0}, 'entree'),
        (m['mord_3'] + 0.02, {'visible': 0}, 'doux'),
    ])
    mouches = absolue([
        (t_bas - 1.2, {'agitation': 0.0, 'attraction': 0.0}, 'doux'),
        (t_bas - 0.4, {'agitation': 0.7}, 'doux'),
        (t_bas + 0.4, {'agitation': 1.0, 'attraction': 0.0}, 'doux'),
        (t_bas + 1.8, {'agitation': 0.35, 'attraction': 0.85}, 'doux'),
        (m['mord_3'], {}, 'doux'),
        (m['mord_3'] + 1.5, {'agitation': 0.8, 'attraction': 0.0}, 'doux'),
        (15.6, {'agitation': 0.0}, 'doux'),
    ])
    ecrire_sequence('mange', "Un gant de laboratoire apporte un morceau de chair crue ; Thomas le saisit, en mange trois bouchées "
                    "(le morceau entre dans la bouche et rapetisse à chaque morsure), avale, soupire et revient au repos. 16 s, boucle continue.",
                    16.0, {'thomas': T.e, 'gant': gant, 'morceau': morceau, 'mouches': mouches})


def main():
    poses_mange()
    sequence_mange()
    print(len(POSES), 'poses écrites')


if __name__ == '__main__':
    main()

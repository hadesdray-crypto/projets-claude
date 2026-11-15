"""Outil d'écriture des poses clés (à lancer une fois ; le moteur n'en a pas besoin).

Pour les poses où la main doit atteindre un point précis (le morceau posé sur le
bord du cercueil, la bouche), on donne la cible de la main et sa direction ; l'outil
calcule par cinématique inverse à deux os les angles de l'épaule, du coude et du
poignet, puis écrit le fichier poses/<nom>.json. Les longueurs d'os sont fixes :
seuls des angles sont enregistrés. Les autres poses sont écrites telles quelles.

La pose « repas » de la planche 10-zombie-animation.png (coude contre le corps,
avant-bras remonté, main devant la bouche, tête penchée vers la nourriture) sert
de cible à « main_bouche », recalée sur la taille de Thomas.
Lancer : python3 outil_poses.py
"""
import json
import math
import os

import numpy as np

import moteur

ICI = os.path.dirname(os.path.abspath(__file__))
scene = moteur.lire_json('scene.json')
TH = moteur.Thomas(next(o for o in scene['objets'] if o['nom'] == 'thomas'))
BOUCHE_AVANT = (247.0, 178.0)     # bord avant de l'intérieur de la bouche (Thomas regarde à droite)
PRISE = [16.0, 2.0]               # point de prise dans le repère de la main (bout des doigts)
SUR_LE_BORD = (303.0, 319.0)      # centre du morceau posé sur le bord du cercueil

REPOS = {
    'squelette': {'epaule': 0.0, 'coude': 0.0, 'poignet': 0.0, 'main_fermeture': 0.55},
    'corps': {'inclinaison': 0.0, 'x': 0.0, 'y': 0.0, 'epaules': 0.0, 'poitrine': 0.0},
    'zones': {'tete_rotation': 0.0, 'tete_x': 0.0, 'tete_y': 0.0, 'machoire': 0.0, 'joues': 0.0,
              'paupieres': 0.0, 'cou_deglutition': 0.0, 'oeil_pendant_regard': 0.0},
    'attaches': {'prise_main': PRISE},
}


def fusion(base, ajout):
    out = json.loads(json.dumps(base))
    for k, v in ajout.items():
        if isinstance(v, dict):
            out.setdefault(k, {}).update(v)
        else:
            out[k] = v
    return out


def couches_de(pose):
    return TH.couches(moteur.aplatir(pose), [])


def point(pose, x, y):
    dx, dy, _ = TH.deplacement_point(couches_de(pose), x, y)
    return np.array([x + dx, y + dy])


def norm180(a):
    return (a + 180.0) % 360.0 - 180.0


def ik(pose, cible, direction, fermeture):
    """Angles (épaule, coude, poignet) pour que le point de prise de la main
    soit en « cible » avec la main orientée selon « direction » (degrés)."""
    c = TH.couches_tronc(couches_de(pose))
    dx, dy, r = TH.deplacement_point(c, *TH.E0)
    E = TH.E0 + [dx, dy]
    k = TH.main.get('taille', 1.0)
    px, py = moteur.tourner(PRISE[0] * k, PRISE[1] * k, direction)
    P = np.array(cible) - [px, py]
    d = P - E
    L = float(np.linalg.norm(d))
    l1, l2 = TH.l1, TH.l2
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
        rel = norm180(a_f - a_u)
        if rel <= 0:                                        # le coude ne plie que dans un sens
            meilleur = (a_u, a_f)
    a_u, a_f = meilleur
    epaule = norm180(a_u - TH.a_u0 - r)
    coude = norm180((a_f - a_u) - (TH.a_f0 - TH.a_u0))
    poignet = norm180(direction - a_f)
    if not atteint:
        print('   attention : cible hors de portée, bras tendu au maximum')
    return {'epaule': round(epaule, 2), 'coude': round(coude, 2), 'poignet': round(poignet, 2),
            'main_fermeture': fermeture}


def ecrire(nom, description, pose, partielle=False):
    d = {'nom': nom, 'description': description}
    d.update(pose)
    os.makedirs(os.path.join(ICI, 'poses'), exist_ok=True)
    with open(os.path.join(ICI, 'poses', nom + '.json'), 'w', encoding='utf-8') as f:
        f.write(json_compact(d))
    print(nom, '(partielle)' if partielle else '')


def json_compact(d):
    lignes = ['{']
    items = list(d.items())
    for i, (k, v) in enumerate(items):
        fin = ',' if i < len(items) - 1 else ''
        lignes.append('  %s: %s%s' % (json.dumps(k), json.dumps(v, ensure_ascii=False), fin))
    lignes.append('}')
    return '\n'.join(lignes) + '\n'


def avec_bras(nom, description, corps_zones, cible, direction, fermeture):
    pose = fusion(REPOS, corps_zones)
    pose['squelette'] = ik(pose, cible, direction, fermeture)
    ecrire(nom, description, pose)
    return pose


def main():
    ecrire('repos', "Pose de repos de l'image d'origine : bras le long du corps, main vide à demi fermée.", REPOS)
    ecrire('regard_gant', "Thomas lève la tête vers le gant qui arrive en haut à droite ; l'œil pendant se tourne aussi.",
           fusion(REPOS, {'corps': {'epaules': -0.6}, 'zones': {'tete_rotation': -7.0, 'tete_x': 1.0, 'oeil_pendant_regard': 25.0}}))
    ecrire('regard_morceau', "La tête suit le morceau qui tombe et se baisse vers lui ; le buste se penche un peu.",
           fusion(REPOS, {'corps': {'inclinaison': 1.5}, 'zones': {'tete_rotation': 7.0, 'tete_x': 2.5, 'tete_y': 1.0, 'oeil_pendant_regard': -20.0}}))
    ecrire('anticipation', "Tension avant le geste : léger recul du buste, épaules qui montent, inspiration, main qui s'ouvre.",
           fusion(REPOS, {'squelette': {'epaule': -8.0, 'coude': -12.0, 'poignet': -12.0, 'main_fermeture': 0.05},
                          'corps': {'inclinaison': -2.0, 'x': -1.5, 'epaules': -1.5, 'poitrine': 0.8},
                          'zones': {'tete_rotation': 5.0, 'tete_x': 1.5, 'oeil_pendant_regard': -20.0}}))
    cz = {'corps': {'inclinaison': 3.0, 'x': 1.0}, 'zones': {'tete_rotation': 7.0, 'tete_x': 2.0, 'oeil_pendant_regard': -20.0}}
    avec_bras('bras_part', "Le bras part vers le morceau : l'épaule avance, le coude s'ouvre, la main reste ouverte.",
              cz, (290.0, 283.0), 22.0, 0.0)
    cz = {'corps': {'inclinaison': 6.0, 'x': 2.0, 'y': 0.5}, 'zones': {'tete_rotation': 8.0, 'tete_x': 2.5, 'tete_y': 0.5, 'oeil_pendant_regard': -20.0}}
    avec_bras('bras_mi_chemin', "Bras à mi-chemin : le poids passe vers l'avant, la main descend vers le morceau.",
              cz, (299.0, 304.0), 45.0, 0.0)
    cz = {'corps': {'inclinaison': 8.5, 'x': 3.0, 'y': 1.5, 'epaules': 0.5},
          'zones': {'tete_rotation': 9.0, 'tete_x': 3.0, 'tete_y': 1.0, 'oeil_pendant_regard': -25.0}}
    avec_bras('main_saisit', "La main ouverte arrive sur le morceau posé sur le bord du cercueil ; buste penché, bras presque tendu.",
              cz, SUR_LE_BORD, 58.0, 0.0)
    avec_bras('main_fermee', "Les doigts se referment sur le morceau (le morceau s'attache à la main).",
              cz, SUR_LE_BORD, 58.0, 1.0)
    cz = {'corps': {'inclinaison': 4.0, 'x': 1.5, 'epaules': -0.5}, 'zones': {'tete_rotation': 6.0, 'tete_x': 2.0, 'oeil_pendant_regard': -10.0}}
    avec_bras('bras_leve', "Le morceau remonte : le buste se redresse, le coude se plie, le poignet tourne.",
              cz, (288.0, 266.0), -15.0, 1.0)
    cz = {'corps': {'inclinaison': 1.5, 'x': 0.5}, 'zones': {'tete_rotation': 6.0, 'tete_x': 2.0, 'tete_y': 0.5, 'oeil_pendant_regard': 0.0}}
    p = fusion(REPOS, cz)
    b = point(p, *BOUCHE_AVANT)
    avec_bras('bras_presque_bouche', "Bras presque à la bouche : coude plié contre le corps, le morceau à hauteur du menton.",
              cz, (b[0] + 16.0, b[1] + 16.0), -95.0, 1.0)
    # pose « repas » de la planche : coude contre le corps, main devant la bouche, tête penchée vers la main
    cz = {'corps': {'inclinaison': 1.0}, 'zones': {'tete_rotation': 7.0, 'tete_x': 2.5, 'tete_y': 0.5, 'oeil_pendant_regard': 10.0}}
    p = fusion(REPOS, cz)
    b = point(p, *BOUCHE_AVANT)
    avec_bras('main_bouche', "Main à la bouche (d'après la pose « repas » de la planche) : le morceau juste devant la bouche.",
              cz, (b[0] + 12.0, b[1] + 2.0), -120.0, 1.0)
    cz = {'corps': {'inclinaison': 0.5, 'poitrine': 0.6}, 'zones': {'tete_rotation': 3.5, 'tete_x': 2.0, 'machoire': 1.0, 'oeil_pendant_regard': 10.0}}
    p = fusion(REPOS, cz)
    b = point(fusion(p, {'zones': {'machoire': 0.0}}), *BOUCHE_AVANT)
    avec_bras('bouche_ouverte', "La mâchoire s'ouvre grand, la tête se relève un peu (élan avant la morsure).",
              cz, (b[0] + 8.0, b[1] + 3.0), -120.0, 1.0)
    cz = {'corps': {'inclinaison': 1.5}, 'zones': {'tete_rotation': 8.0, 'tete_x': 3.0, 'tete_y': 0.8, 'machoire': -0.12, 'joues': 0.3, 'oeil_pendant_regard': 10.0}}
    p = fusion(REPOS, cz)
    b = point(fusion(p, {'zones': {'machoire': 0.0}}), *BOUCHE_AVANT)
    avec_bras('morsure', "Morsure : la main pousse le morceau dans la bouche et la mâchoire se referme d'un coup.",
              cz, (b[0] - 5.0, b[1] + 1.5), -120.0, 1.0)
    # mastication : poses partielles (visage seulement) ; le bras garde sa position
    ecrire('mastication_1', "Mâchoire mi-ouverte, joues gonflées, tête qui plonge un peu.",
           {'zones': {'machoire': 0.6, 'joues': 1.0, 'tete_rotation': 7.5, 'tete_y': 0.8}}, True)
    ecrire('mastication_2', "Mâchoire fermée, joues qui se vident, tête qui remonte.",
           {'zones': {'machoire': -0.1, 'joues': 0.3, 'tete_rotation': 5.5, 'tete_y': -0.2}}, True)
    ecrire('mastication_3', "Mâchoire mi-ouverte décalée, joues pleines, tête un peu en avant.",
           {'zones': {'machoire': 0.5, 'joues': 1.0, 'tete_rotation': 6.5, 'tete_x': 3.5, 'tete_y': 0.5}}, True)
    ecrire('avalement', "Il avale : bouche fermée, joues vides, menton qui descend, renflement qui descend dans le cou (0 → 1).",
           {'zones': {'machoire': -0.1, 'joues': 0.0, 'tete_rotation': 9.0, 'tete_y': 1.2, 'cou_deglutition': 1.0}}, True)
    cz = {'corps': {'inclinaison': 1.0}, 'zones': {'tete_rotation': 6.0, 'tete_x': 2.0, 'oeil_pendant_regard': 0.0}}
    p = fusion(REPOS, cz)
    b = point(p, *BOUCHE_AVANT)
    avec_bras('menton', "Main vide restée sous le menton pendant qu'il mâche.",
              cz, (b[0] + 12.0, b[1] + 24.0), -85.0, 0.8)
    cz = {'corps': {'inclinaison': -1.5, 'x': -1.0, 'epaules': -1.6, 'poitrine': 1.9},
          'zones': {'tete_rotation': -3.5, 'tete_y': -0.5, 'machoire': 0.15, 'paupieres': 0.45, 'oeil_pendant_regard': 0.0}}
    avec_bras('soulagement_inspire', "Satisfait, il inspire longuement : poitrine gonflée, épaules hautes, tête en arrière, yeux mi-clos ; le bras redescend.",
              cz, (290.0, 262.0), 15.0, 0.6)
    ecrire('soulagement', "Long soupir : la poitrine se vide, les épaules retombent, la tête s'affaisse, la main pend, détendue.",
           fusion(REPOS, {'squelette': {'epaule': 1.0, 'coude': 4.0, 'poignet': 12.0, 'main_fermeture': 0.45},
                          'corps': {'inclinaison': 0.8, 'x': 0.5, 'epaules': 2.6, 'poitrine': -1.3},
                          'zones': {'tete_rotation': 3.0, 'tete_y': 1.2, 'machoire': 0.25, 'paupieres': 0.5}}))


if __name__ == '__main__':
    main()

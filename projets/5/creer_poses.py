"""Écrit les poses (poses/*.json) et les séquences (sequences/*.json) de la demande 5 :
caresse, joie, dort, reveil. Les fichiers produits sont de simples JSON modifiables à la main.
Lancer : python3 creer_poses.py [caresse|joie|dort|reveil]"""
import json, sys
import outil_poses as op

def pose(nom, description, base='repos', **groupes):
    """Pose = repos (ou une autre pose) + valeurs modifiées, par groupe : sq, corps, zones, vie, att."""
    d = json.load(open('poses/%s.json' % base, encoding='utf-8')) if base != 'repos' or True else {}
    d = json.loads(json.dumps(d))
    d['nom'], d['description'] = nom, description
    noms = {'sq': 'squelette', 'corps': 'corps', 'zones': 'zones', 'vie': 'vie', 'phys': 'physique'}
    for k, v in groupes.items():
        d.setdefault(noms[k], {}).update(v)
    json.dump(d, open('poses/%s.json' % nom, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def sequence(nom, d):
    json.dump(d, open('sequences/%s.json' % nom, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

OEIL = 'oeil_pendant_regard'

def caresse():
    # base : sourire doux, paupières mi-closes, épaules détendues ; la tête s'incline vers le gant
    pose('caresse_arrivee', "Thomas lève les yeux vers le gant qui descend ; il se méfie encore un peu.",
         sq={'racine_x': -1.0, 'tronc': -1.0}, corps={'epaules': -0.6},
         zones={'tete_rotation': -6.0, 'tete_x': 1.0, 'tete_y': -1.0, 'machoire': 0.1, OEIL: 22.0})
    comm = dict(sq={'epaule': 2.0, 'coude': 5.0, 'poignet': 10.0, 'epaule2': 3.0, 'coude2': 2.0, 'main_fermeture': 0.4},
                vie={'frisson': 0.0})
    for nom, s, rot, dx in (('caresse_g', -1, -2.0, -3.0), ('caresse_d', 1, 2.5, 2.5)):
        pose(nom, "Le gant frotte la tête : elle s'incline, les yeux se plissent, léger sourire, épaules détendues.",
             sq={**comm['sq'], 'racine_x': 0.5, 'racine_y': 0.8, 'tronc': 1.2 + 0.5 * s},
             corps={'epaules': 2.2, 'poitrine': 0.0, 'inclinaison': 0.4 * s},
             zones={'tete_rotation': rot, 'tete_x': dx, 'tete_y': 3.2, 'machoire': 0.12, 'joues': 0.55, 'sourire': 0.55,
                    'paupieres': 0.5, OEIL: -4.0 * s}, vie={'frisson': 0.0})
    pose('caresse_frisson', "Un frisson de plaisir : épaules hautes un instant, sourire plus large, tremblement léger.",
         sq={**comm['sq'], 'racine_x': 0.2, 'racine_y': 0.5, 'tronc': 0.8},
         corps={'epaules': -1.2, 'poitrine': 0.8},
         zones={'tete_rotation': 0.5, 'tete_x': 0.0, 'tete_y': 3.0, 'machoire': 0.1, 'joues': 0.8, 'sourire': 0.9,
                'paupieres': 0.62, OEIL: 0.0}, vie={'frisson': 0.8})
    pose('caresse_detendu', "Détendu après la caresse : poitrine vidée, yeux mi-clos, sourire qui s'attarde.",
         sq={**comm['sq'], 'racine_x': 0.4, 'racine_y': 1.2, 'tronc': 1.0},
         corps={'epaules': 2.8, 'poitrine': -0.8},
         zones={'tete_rotation': 2.0, 'tete_x': 0.0, 'tete_y': 2.0, 'machoire': 0.15, 'joues': 0.4, 'sourire': 0.8,
                'paupieres': 0.45, OEIL: 0.0}, vie={'frisson': 0.0})
    T = []
    g = []
    def t(pose_, duree, courbe='doux', tenir=0.0, **v):
        e = {'pose': pose_, 'duree': duree, 'courbe': courbe}
        if tenir: e['tenir'] = tenir
        if v: e['valeurs'] = v
        T.append(e)
    T.append({'pose': 'repos', 'tenir': 0.4})
    t('caresse_arrivee', 0.5)
    # le gant descend du haut (0,4 → 1,9 s), touche la tête, frotte (6 × 0,75 s), puis remonte
    t('caresse_g', 1.0)
    t('caresse_d', 0.75)
    t('caresse_g', 0.75)
    t('caresse_frisson', 0.75)
    t('caresse_d', 0.75)
    t('caresse_g', 0.75)
    t('caresse_d', 0.75)
    t('caresse_detendu', 0.8)
    t('repos', 0.8)
    X0, XA, XB, Y0, Y1 = 246.0, 230.0, 262.0, 94.0, 98.0
    g.append({'valeurs': {'x': 330.0, 'y': -110.0, 'angle': 6.0, 'ouverture': 0.4, 'paume': 1.0}, 'tenir': 0.4})
    g.append({'valeurs': {'x': X0, 'y': Y0, 'angle': 0.0}, 'duree': 1.5, 'courbe': 'doux'})
    for x in (XA, XB, XA, XB, XA, XB):
        g.append({'valeurs': {'x': x, 'y': Y1}, 'duree': 0.75, 'courbe': 'doux'})
    g.append({'valeurs': {'x': 330.0, 'y': -110.0, 'angle': 6.0}, 'duree': 1.6, 'courbe': 'doux'})
    # durée 8,0 s : la respiration et les clignements de la recette « vie » reviennent à l'identique (période 8 s)
    sequence('caresse', {'nom': 'caresse', 'duree': 8.0, 'boucle': True,
        'description': "Le gant blanc frotte doucement la tête de Thomas : frisson, paupières mi-closes, léger sourire, œil pendant qui oscille, épaules détendues. 8 s, boucle continue.",
        'recettes': {'thomas': ['vie']}, 'pistes': {'thomas': T, 'gant': g}})


BRAS_HAUT = {'epaule': -100.0, 'coude': 46.0, 'poignet': -8.0, 'epaule2': 158.0, 'coude2': 3.0, 'main_fermeture': 0.0}

def joie():
    pose('joie_elan', "Il se ramasse avant de sauter : genoux fléchis, bras qui reculent, bouche qui s'ouvre déjà.",
         sq={'racine_y': 10.0, 'racine_x': -1.0, 'tronc': 3.0, 'epaule': -45.0, 'coude': 22.0, 'epaule2': 75.0, 'coude2': 10.0, 'main_fermeture': 0.2},
         corps={'epaules': 1.5}, zones={'sourire': 0.5, 'machoire': 0.3, 'joues': 0.3, 'tete_y': 2.0, 'tete_rotation': 3.0})
    pose('joie_saut', "Au sommet du saut : bras levés en V, grande bouche joyeuse, tête en arrière, pieds décollés.",
         sq={**BRAS_HAUT, 'racine_y': -14.0, 'racine_x': 0.5, 'tronc': -3.0, 'pied_g_y': -9.0, 'pied_d_y': -11.0, 'pied_g': -12.0, 'pied_d': -8.0},
         corps={'epaules': -1.2, 'poitrine': 1.2}, zones={'sourire': 1.0, 'machoire': 0.85, 'joues': 0.9, 'tete_y': -1.5, 'tete_rotation': -5.0, OEIL: 8.0})
    pose('joie_bras_hauts', "Les pieds au sol, bras toujours levés, bouche ouverte, poitrine gonflée.",
         sq={**BRAS_HAUT, 'racine_y': 1.0, 'tronc': -2.0, 'epaule': -96.0, 'epaule2': 150.0, 'coude': 44.0, 'coude2': 8.0},
         corps={'epaules': -1.0, 'poitrine': 1.4}, zones={'sourire': 1.0, 'machoire': 0.75, 'joues': 0.8, 'tete_y': -0.8, 'tete_rotation': -3.0})
    pose('joie_creux', "Petit fléchissement entre deux rebonds, bras levés, la bouche reste ouverte.",
         sq={**BRAS_HAUT, 'racine_y': 5.0, 'tronc': 1.0, 'epaule': -104.0, 'epaule2': 154.0, 'coude': 50.0, 'coude2': 6.0},
         corps={'epaules': 1.2, 'poitrine': 0.2}, zones={'sourire': 1.0, 'machoire': 0.7, 'joues': 0.9, 'tete_y': 1.0, 'tete_rotation': 1.0})
    pose('joie_petit_saut', "Petit rebond : pieds qui quittent à peine le sol, bras en V.",
         sq={**BRAS_HAUT, 'racine_y': -7.0, 'tronc': -2.0, 'pied_g_y': -4.0, 'pied_d_y': -5.0, 'epaule': -98.0, 'epaule2': 152.0, 'coude': 46.0, 'coude2': 6.0},
         corps={'epaules': -1.0, 'poitrine': 1.0}, zones={'sourire': 1.0, 'machoire': 0.8, 'joues': 0.9, 'tete_y': -1.0, 'tete_rotation': -4.0})
    pose('joie_bras_milieu', "Les bras redescendent à mi-hauteur, le sourire reste.",
         sq={'epaule': -55.0, 'coude': 25.0, 'epaule2': 75.0, 'coude2': 15.0, 'main_fermeture': 0.2, 'racine_y': 2.0, 'tronc': 0.0},
         corps={'epaules': 0.8, 'poitrine': 0.5}, zones={'sourire': 0.8, 'machoire': 0.4, 'joues': 0.6, 'tete_y': 0.0})
    pose('joie_calme', "Retour au calme : bras presque le long du corps, souffle, léger sourire.",
         sq={'epaule': 6.0, 'coude': 6.0, 'epaule2': 4.0, 'coude2': 2.0, 'main_fermeture': 0.45, 'racine_y': 1.5, 'tronc': 1.0},
         corps={'epaules': 2.0, 'poitrine': 0.8}, zones={'sourire': 0.5, 'machoire': 0.2, 'joues': 0.3, 'tete_y': 1.0, 'paupieres': 0.3})

    plan = [('repos', 0.0, None), ('joie_elan', 0.55, 'doux'), ('joie_saut', 0.50, 'spline'), ('joie_bras_hauts', 0.30, 'spline'),
            ('joie_creux', 0.30, 'spline'), ('joie_petit_saut', 0.30, 'spline'), ('joie_bras_hauts', 0.30, 'spline'),
            ('joie_creux', 0.30, 'spline'), ('joie_petit_saut', 0.30, 'spline'), ('joie_bras_hauts', 0.30, 'spline'),
            ('joie_creux', 0.35, 'spline'), ('joie_saut', 0.45, 'spline'), ('joie_bras_hauts', 0.30, 'spline'),
            ('joie_creux', 0.35, 'spline'), ('joie_petit_saut', 0.30, 'spline'), ('joie_bras_hauts', 0.40, 'doux'),
            ('joie_bras_milieu', 0.80, 'doux'), ('joie_calme', 0.80, 'doux'), ('repos', 0.80, 'doux')]
    T = [{'pose': 'repos', 'tenir': 0.3, 'valeurs': {'physique': {'tige_devant': 1.0}}}] + [{'pose': p, 'duree': d, 'courbe': c} for p, d, c in plan[1:]]
    sequence('joie', {'nom': 'joie', 'duree': 8.0, 'boucle': True,
        'description': "Bras levés en V, grand sourire bouche ouverte, un grand saut puis des petits rebonds, retour doux au repos. 8 s, boucle continue.",
        'recettes': {'thomas': ['vie']}, 'pistes': {'thomas': T}})


if __name__ == '__main__':
    for n in (sys.argv[1:] or ['caresse', 'joie', 'dort', 'reveil']):
        globals()[n]()

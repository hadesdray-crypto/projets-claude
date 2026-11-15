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

if __name__ == '__main__':
    for n in (sys.argv[1:] or ['caresse']):
        globals()[n]()

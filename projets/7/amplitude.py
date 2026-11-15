"""Test d'articulations : les deux bras parcourent toute leur amplitude (4 s, 30 i/s).
Épaule 0 -> 170°, coude 0 -> 140°, poignet ±40°, main ouverte -> fermée. Zéro = bras pendant, tendu."""
import math
import numpy as np
import moteur7

DUREE = 4.0


def lisse(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def valeurs(t):
    """Angles (degrés) à l'instant t : épaule 0->170 (0-1,2 s), coude 0->140 (1-2,2 s), poignet (1,9-3 s), retour (2,8-4 s)."""
    s = lisse(t / 1.2) * (1 - lisse((t - 2.8) / 1.2))
    e = lisse((t - 1.0) / 1.2) * (1 - lisse((t - 2.6) / 1.2))
    w = math.sin(2 * math.pi * (t - 1.9) / 1.1) * 40 * lisse((t - 1.9) / 0.3) * (1 - lisse((t - 3.0) / 0.3)) if 1.9 <= t <= 3.3 else 0.0
    f = 0.5 - 0.5 * math.cos(2 * math.pi * t / DUREE)
    return {'epaule': 170 * s, 'coude': 140 * e, 'poignet': w, 'fermeture': f}


class SceneAmp(moteur7.Scene7):
    def parametres(self, objet, t):
        p, z = super().parametres(objet, t)
        if objet == 'thomas':
            v = valeurs(t % DUREE)
            p.update({'squelette.epaule': -v['epaule'], 'squelette.coude': -v['coude'], 'squelette.poignet': v['poignet'],
                      'squelette.main_fermeture': v['fermeture'],
                      'squelette.epaule2': v['epaule'], 'squelette.coude2': v['coude'], 'squelette.poignet2': -v['poignet'],
                      'squelette.main_fermeture2': v['fermeture'],
                      'squelette.tronc': 0.0, 'squelette.cou': 0.0, 'squelette.racine': 0.0,
                      'squelette.racine_x': 0.0, 'squelette.racine_y': 0.0})
            z = []
        return p, z


class RenduAmp(moteur7.Rendu7):
    def __init__(self):
        self.fps = 30
        self.effets = []
        self.scene = SceneAmp('scene7.json', 's7_joie')
        self.sequence = self.scene.sequence
        self.gels = []
        self.pas = 1
        self.fond = np.round(self.scene.fond).astype(np.uint8)
        self.derniere = None
        self.marques = {}
        self.fenetre_anim = None

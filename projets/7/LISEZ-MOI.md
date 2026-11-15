# Demande 7 : bras, articulations et découpages de Thomas

Les bras de `projets/6` sont refaits sans modifier le moteur (`projets/5/moteur.py`) ni les effets (`projets/6/effets.py`).

## Ce qui est livré
| Fichier | Contenu |
|---|---|
| `amplitude-bras.gif` | 4 s, 30 i/s, gros plan : épaule 0 à 170°, coude 0 à 140°, poignet ±40°, main ouverte à fermée (6,2 Mo, pas de limite demandée) |
| `joie-avant-apres.gif` | joie, 3 s, avant (projets/6) à gauche, après à droite |
| `mange-avant-apres.gif` | mange, 3,6 s (du regard sur le morceau à la première morsure) |
| `mains.png` | les 4 formes de main, agrandies 8 fois |
| `controle.md`, `mesures.json` | contrôle regardé et mesures chiffrées |
| `apercu/` | images extraites des GIF pour le contrôle |

## Ce que j'ai changé
- **Squelette** (`scene7.json`, fait par `preparer7.py`) : vraies épaules sur le torse, deux os de 56 et 50 px par bras, bras pendants au repos (zéro = tendu), un os de main arrière en plus. Les anciens calques de bras ne sont plus utilisés.
- **Dessin des bras** (`moteur7.py`, réglages `bras.json`) : haut du bras, avant-bras, manche déchirée, pli du coude et main sont dessinés par le code en pixel art (pixels de 2 px, contour d'un pixel, couleurs de Thomas) à partir des articulations. Les longueurs d'os ne changent jamais, l'épaisseur est fixe (rayons 14, 12, 10 px).
- **Mains** : 4 formes (ouverte, relâchée, saisissante, fermée) mélangées selon `main_fermeture` ; une main arrière existe désormais (`main_fermeture2`, `poignet2`).
- **Poses** (`poses/n7_*.json`) : toutes les poses de projets/5 recalées pour que la main arrive au même endroit qu'avant ; **séquences** `sequences/s7_*.json` : joie, mange, saisie, caresse, etc.
- **Mesures** : `mesures7.py`. **Test d'amplitude** : `amplitude.py`. **GIF** : `fabriquer7.py` (`python3 fabriquer7.py amplitude|joie|mange`). **Extraction** : `extraire.py`. **Planche des mains** : `mains.py`.

## Limites
Fond derrière le bras non reconstitué ; manches un peu plates ; poings brouillons ; mesures d'épaisseur peu fiables quand le bras est replié. Détails dans `controle.md`.

# Demande 6 : six mini GIF « avant / après » (fluidité, style arcade)

Chaque GIF : 3 s, 90 images à 30 i/s (le GIF n'a que des pauses de 1/100 s : on alterne 30, 30, 40 ms), boucle, au plus 2,35 Mo.
À gauche « avant » (Thomas de projets/5), à droite « après » (principes ajoutés). Le moteur de projets/5 n'est **pas modifié** : `effets.py` le complète.

| GIF | Ce qu'on compare |
|---|---|
| `1-repos-vivant.gif` | repos régulier / micro-vie irrégulière |
| `2-joie.gif` | joie actuelle / anticipation, étirement, écrasement, dépassement des bras |
| `3-morsure.gif` | morsure actuelle / tenue, arrêt sur impact, éclair, secousse, miettes |
| `4-saisie.gif` | saisie actuelle / anticipation et dépassement de la main |
| `5-caresse.gif` | caresse actuelle / frisson à ressort avec retard |
| `6-lisse-contre-sur2.gif` | même mouvement lisse à 30 i/s / « sur 2 » (15 poses par seconde) |

## Ce que fait chaque effet (et où il est écrit)
Les effets sont des **fichiers JSON** dans `recettes/` ; ajouter une animation ne demande pas de toucher au moteur.

- **micro_vie** (`recettes/micro_vie.json`) : respiration à deux rythmes, clignements à des instants irréguliers (liste `instants`, en s), regard qui dérive. Le déplacement du poids est dans la séquence (poses tenues puis passage rapide) : `sequences/g1_apres.json`.
- **squash_stretch** (`recettes/squash_stretch.json`) : un seul paramètre de pose, `anim.ecrasement` (> 0 écrasement, < 0 étirement, 0 neutre). Il baisse le bassin, élargit la poitrine et la tête (ou l'inverse). Chaque couche a son `amplitude`. Le volume est conservé seulement à peu près (pas de déformation exacte).
- **overshoot** (`overshoot_bras.json`, `overshoot_main.json`, `frisson_ressort.json`) : courbe `ressort` (ajoutée par `effets.py`) : à chaque `instants`, oscillation amortie. Paramètres : `frequence` (Hz), `amortissement` (1/s), `amplitude` (degrés ou px, le signe donne le sens). Le retard s'obtient en décalant les instants de quelques centièmes de seconde.
- **anticipation** et **tenue** : ce sont des poses insérées dans les séquences (`sequences/g*_apres.json`, clés `pose`, `duree`, `tenir`) ; la tenue est le champ `tenir` (secondes).
- **hit_stop** (`effets_morsure.json`) : gèle le temps d'animation `images` images à l'instant `a`. L'image gelée est répétée.
- **flash** : éclair de couleur sur **toute l'image** (`images`, `opacite`, `couleur`). Effet global assumé.
- **secousse** : décale **toute l'image** (bord répété), amplitude qui s'éteint (`amplitude_x`, `amplitude_y`, `images`). Effet global assumé.
- **miettes** : petits carrés de chair (couleurs de la palette) projetés depuis (`x`, `y`) avec gravité, tirage fixe (`graine`).
- **pas_de_temps** (`effets_sur2.json`) : `images_par_pose` = 2 pour « sur 2 », 3 pour « sur 3 ». Les ressorts (œil, cheveux) avancent aussi à ce rythme.

## Fichiers
- Code ajouté : `effets.py` (effets globaux, courbe `ressort`, recherche des fichiers dans projets/6 puis projets/5), `fabriquer.py` (rendu côte à côte, GIF, mesures), `planche.py` (planches de contrôle).
- Réglages : `gifs.json` (un GIF = deux séquences + effets), `sequences/`, `recettes/`.
- Contrôle : `controle.md`, `mesures.json`, `apercu/` (images ouvertes).
- Refaire un GIF : `python3 fabriquer.py 3` (Pillow, numpy, scipy ; poses et calques lus dans projets/5).

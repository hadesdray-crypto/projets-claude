# Contrôle visuel (images réellement ouvertes et regardées)

Mesures automatiques : `mesures.json` (une entrée par séquence). Les constats ci-dessous sont ceux de mes yeux, image par image.
Remarque commune : les clignements de la recette « vie » ferment la paupière de l'œil de la tête ; le détecteur compte alors 1 œil (l'œil existe toujours, paupière dessinée), voir `mesures.json › yeux`.

## caresse (8 s, 240 images)
Images ouvertes (rendu final) : 0, 25, 57, 90, 119, 150, 205, 239, plus les 3 images clés (57, 111, 210).
- 0 : repos, gant absent, deux yeux (tête grand ouvert, pendant au bout de sa tige). Départ de la boucle.
- 25 : tête levée vers le haut, œil pendant décalé vers la droite, gant pas encore visible.
- 57 : gant posé sur le dessus du crâne, paupière mi-close, deux yeux, tête qui s'incline.
- 90 : gant déplacé vers la droite, tête suit un peu en retard, paupière mi-close, œil pendant balancé.
- 119 : clignement : paupière fermée sur l'œil de la tête (œil pendant visible), gant sur la tête.
- 150 : gant à gauche, tête inclinée, sourire léger, épaules basses.
- 205 : gant qui remonte et quitte la tête, yeux mi-clos, sourire.
- 239 : retour vers le repos, gant sorti, œil de la tête rouvert.
- Clés 1, 2, 3 : cohérentes avec leur légende (arrivée, frisson/yeux mi-clos, départ).
Constat : membres continus, pas de doublon, style du gant et de Thomas identiques à `projets/4`. Le sourire est discret (peu visible). Le frisson est un tremblement fin, difficile à voir sur image fixe.

## joie (8 s, 240 images)
Images ouvertes (rendu final) : 20, 34, 45, 60, 100, 130, 200, 225, plus les 3 images clés (26, 38, 198).
- 20 : élan, genoux fléchis, tronc penché, bras arrière qui part vers l'arrière-haut, deux yeux visibles.
- 34 : sommet du saut, bras arrière levé à gauche, bras avant levé près de la tête, grande bouche ouverte, deux yeux.
- 45 : bras en V, bouche ouverte, œil pendant devant le bras.
- 60, 100, 130 : rebonds, bras en V, bouche ouverte, deux yeux ; la tête reste en place.
- 200 : bras qui redescendent, sourire, œil pendant libre.
- 225 : retour au repos, bras le long du corps.
- Clés 1 à 3 : conformes à leur légende.
Constat : mouvement fluide, deux yeux sur toutes les images sauf pendant les clignements. Défaut visible (moyen) : sur le bras avant levé, la manche forme un petit bloc brun mal raccordé sous le menton ; le bras avant se lève très près du visage (l'épaule du dessin d'origine est sous la mâchoire). Pour garder l'œil pendant visible, il est dessiné devant le bras (paramètre `physique.tige_devant`, ajouté au moteur).

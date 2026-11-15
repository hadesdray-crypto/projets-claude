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

## dort (12 s, 360 images, sans boucle : il finit couché)
Images ouvertes (rendu final) : 0, 30, 60, 100, 150, 200, 250, 350, une image agrandie de la tête (350) et les 3 images clés (60, 138, 330).
- 0 : debout, repos, deux yeux.
- 30 : tête qui part en arrière, bouche qui s'entrouvre, paupière qui descend.
- 60 : bâillement, bouche grande ouverte, bras avant tendu, bras arrière écarté. Deux yeux (paupière mi-close).
- 100 : bouche refermée, bras qui retombent, tête lourde.
- 150 : accroupi, dos rond, genoux pliés vers l'avant, pieds restés au sol : le squelette (hanches, genoux, tronc, tête) fonctionne.
- 200 : assis puis penché en arrière, tronc et tête qui basculent ensemble, sans déchirure.
- 250 : couché sur le dos, tête à gauche, jambes à droite, œil pendant retombé sur la joue.
- 350 : endormi, œil de la tête fermé (fente verticale car la tête est couchée), petite bulle « Z » au-dessus de la tête.
- Agrandissement (350) : un liseré bleu clair entourait le corps sur le sol sombre ; je l'ai retiré (`nettoyer_calques.py`) ; il en reste un fil très fin sous le torse.
Constat : la descente (bâillement, accroupi, assis, couché) est continue, longueurs d'os constantes (mesuré 0), déplacement maximal 14 px par image. MOYEN : couché, la pose manque de naturel (le torse paraît court et l'œil pendant repose sur la bouche), la bulle Zzz est petite (la même que dans `projets/4`, un seul « Z » visible à certains instants). Dès que la paupière se ferme (images 278 à 359), le détecteur compte 1 œil : l'œil de la tête est fermé, pas absent.

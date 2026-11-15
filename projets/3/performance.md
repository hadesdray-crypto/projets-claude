# Performance

## Mesuré sur le runner
Conditions de la mesure :
- Machine : AMD EPYC 7763, 4 cœurs ; Python 3.14, numpy 2.5, scipy 1.18. Le moteur tourne sur un seul cœur.
- On mesure le temps de `Scene.image(t)` seul : rendu complet d'une image (Thomas, gant, morceau, mouches) plus un pas des ressorts. L'écriture des fichiers et l'encodage ne sont pas comptés.
- 312 images (13 s à 24 i/s). Détail dans `mesures.json`.

| | Temps par image |
|---|---|
| Moyenne | 46,4 ms |
| Médiane | 45,6 ms |
| Pire image | 59,6 ms |
| Meilleure image | 42,5 ms |
| Préchauffage des ressorts (une fois, une boucle simulée) | 0,31 s |

- Le budget à 24 i/s est de 41,7 ms par image. Sur ce runner, le calcul en direct est donc **un peu trop lent** : environ 21 i/s en moyenne.
- Répartition mesurée avec le profileur sur les 312 images (moyenne par image, le profileur ajoute un peu de temps) :
  - lectures sous-pixel : environ 32 ms, dont environ 20 ms pour l'inversion du champ du corps (4 passes) ;
  - rastérisation des triangles du bras : environ 3,4 ms ;
  - main : environ 1,7 ms ;
  - tige et œil pendant : environ 1,2 ms ;
  - le reste (champ de zones, ressorts, gant, morceau, mouches) : quelques ms.
- Seuls les rectangles animés sont recalculés : celui de Thomas (270x310, soit 27 % de l'image), plus ceux du gant, du morceau et des mouches. Hors de ces rectangles, aucun pixel du décor n'a changé (mesuré sur les 312 images).

## Console ARM faible (RK3326, 4 cœurs Cortex-A35, 640x480) : estimation, **non vérifiée**
Rien n'a été lancé sur cette console. Tout ce qui suit est une estimation **non vérifiée** :
- Un cœur Cortex-A35 est nettement plus lent qu'un cœur EPYC. Avec un rapport de 5 à 10 fois (**non mesuré**), on obtiendrait environ 230 à 470 ms par image sur un cœur. C'est très loin des 41,7 ms nécessaires à 24 i/s.
- Le futur jeu en Love2D/Lua n'aura pas numpy. Faire le même calcul pixel par pixel en Lua serait encore plus lent. Une piste existe : le champ de déplacement (somme « carte × mouvement ») et le bras en triangles conviennent bien à un shader et à un maillage du processeur graphique. Cette piste n'est **pas testée**.
- Conclusion honnête : le calcul en direct sur RK3326 est probablement impossible avec cette méthode telle quelle (**non vérifié**).

## Repli : images précalculées au chargement (chiffres mesurés sur le runner)
Le principe :
- Au chargement, on calcule une fois la séquence avec ce moteur.
- On ne garde que le rectangle de Thomas (270x310). Le morceau tenu en main y est inclus.
- En jeu, on affiche le décor fixe, puis le rectangle de l'image courante, puis le gant, le morceau quand il n'est pas en main, et les mouches. Ces derniers sont des sprites légers, dessinés en direct ou précalculés de la même façon.

| | Valeur |
|---|---|
| Nombre d'images | 312 (13 s à 24 i/s) |
| Taille d'une image | 270 x 310 pixels |
| Poids brut RGBA (4 octets par pixel) | 104,5 Mo |
| Poids brut avec palette de 256 couleurs (1 octet par pixel) | 26,1 Mo |
| Poids sur disque en PNG à 256 couleurs (mesuré) | 15,9 Mo |

Ce qui reste à vérifier :
- Pistes pour réduire la mémoire (**non mesurées**) : 12 i/s au lieu de 24 (divise par 2), ne garder que la boîte qui bouge vraiment à chaque image (les jambes sont fixes), réutiliser les images du repos au début et à la fin.
- Temps de précalcul sur la console : **non vérifié**. Avec le rapport estimé ci-dessus, environ 1 à 2,5 minutes pour les 312 images. C'est sans doute trop long au chargement : il vaudrait mieux préparer les images à l'avance sur ordinateur et les livrer avec le jeu (**non vérifié**).
- Mémoire disponible sur la console pour 26 Mo d'images : **non vérifié**.

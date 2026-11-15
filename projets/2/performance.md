# Performance

## Mesuré sur le runner
Machine : Intel Xeon Platinum 8370C à 2,8 GHz, 4 cœurs, Python 3.14, numpy 2.5.
Le moteur tourne sur un seul cœur.
Mesure : temps de `Scene.image(t)` seul, sans l'écriture du GIF, sur 100 images par animation (détail dans `mesures.json`).

| Animation | Moyenne par image | Pire image | Part de l'image recalculée |
|---|---|---|---|
| 01 repos vivant | 32,9 ms | 35,0 ms | 27,8 % (rectangle de Thomas 270x310 + mouches) |
| 02 frotter la tête | 32,6 ms | 35,3 ms | 27,9 % |
| 03 donner un os | 37,7 ms | 43,5 ms | 27,8 % |
| 04 transition sommeil | 34,4 ms | 37,3 ms | 28,0 % |

Le budget à 12,5 images/s est de 80 ms par image. Sur ce runner, il est donc tenu en direct, avec de la marge.
Hors des rectangles animés, le décor n'est jamais recalculé : 0 pixel différent du décor, mesuré dans les 4 GIF.

## Console ARM faible (RK3326, 4 cœurs Cortex-A35, 640x480) : estimation, non vérifiée
Rien n'a été lancé sur cette console. Tout ce qui suit est **non vérifié** :
- Un Cortex-A35 est un cœur économe, nettement plus lent qu'un cœur Xeon. L'écart réel sur ce calcul n'est **pas mesuré**. Avec un rapport de 5 à 10 fois, on obtiendrait environ 170 à 380 ms par image sur un cœur, au-dessus des 80 ms.
- Le futur jeu sera en Love2D/Lua, sans numpy. Le calcul pixel par pixel en Lua serait plus lent qu'en numpy, sauf à le confier à un shader du processeur graphique : le champ de déplacement est une simple somme « carte de zone × mouvement ». Cette piste n'est **pas testée**.

## Proposition de repli : images précalculées au chargement
- Au chargement, on calcule une fois chaque boucle avec ce même moteur. On ne garde que le rectangle animé (270x310), pas l'écran entier.
- Mémoire : 270 × 310 × 4 octets ≈ 0,33 Mo par image, soit environ 33 Mo pour une boucle de 100 images (calcul, non mesuré sur la console). On peut réduire avec une palette de 256 couleurs (1 octet par pixel, environ 8 Mo par boucle) ou avec des boucles plus courtes.
- En jeu, il ne reste qu'à afficher le décor fixe, le rectangle précalculé de l'image courante et les particules (quelques sprites).
- Les recettes et les actions restent des données. Seules les combinaisons utilisées en jeu sont précalculées, et les transitions entre poses peuvent l'être aussi, au même titre que les boucles.
- Temps de précalcul sur la console : **non vérifié**. Ordre de grandeur estimé : quelques dizaines de secondes par boucle de 100 images si le rapport de vitesse ci-dessus est juste.

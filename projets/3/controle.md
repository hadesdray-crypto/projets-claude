# Contrôle

Toutes les mesures viennent de `produire.py` (fichier `mesures.json`), calculées sur les 312 images du film final et sur l'image 312, qui est l'image 0 de la boucle suivante.
Les images regardées ont été extraites des fichiers livrés (`thomas-mange.mp4`, `thomas-mange.gif`, `cle-*.png`) avec ffmpeg, puis ouvertes et regardées : en entier et agrandies (×2 à ×3).

## 1. Images réellement ouvertes et regardées (version finale)
Numéro d'image : n (24 images par seconde, t = n / 24).

| Image | Fichier | Ce que j'ai constaté |
|---|---|---|
| n0 (0,00 s) | MP4 | Repos. Deux yeux (tête + œil au bout de la tige). Main vide, demi-fermée. Aucun os en main. |
| n12 (0,50 s) | cle-1.png | Repos, yeux ouverts. Deux yeux. Bras continu. Plus de ligne claire sur les jambes. |
| n50 (2,08 s) | MP4 | Repos, juste avant le gant. Deux yeux. |
| n64 (2,67 s) | MP4 | Le gant blanc descend du haut à droite et tient le morceau rouge et rose par la pince. Deux yeux. |
| n71 (2,96 s) | cle-2.png | La pince s'ouvre, le morceau vient d'être lâché sous le gant. Thomas regarde vers le haut. Deux yeux. |
| n78 (3,25 s) | MP4 | Le morceau est posé sur le bord du cercueil. Le gant repart, doigts ouverts. Thomas baisse la tête vers le morceau. |
| n90 (3,75 s) | MP4 | Le bras part, la main ouverte. Bras continu. |
| n104 (4,33 s) | MP4, agrandie | Buste penché, bras tendu vers le morceau. Épaule, coude et poignet bien visibles. Bras continu, sans déchirure ni morceau en double. |
| n114 (4,75 s) | cle-3.png, agrandie | Les doigts sont refermés sur le morceau, au bord du cercueil. Deux yeux. Ce n'est pas un os. |
| n126 (5,25 s) | MP4 | Le morceau monte vers la bouche. L'œil pendant passe derrière le morceau (il est poussé). |
| n139 (5,79 s) | MP4, agrandie | Le morceau touche le bord avant de la bouche. Coude plié, avant-bras remonté. Bras continu. Deux yeux. |
| n145 (6,04 s) | cle-5.png, agrandie | Mâchoire ouverte : le bas du visage a pivoté, l'intérieur de la bouche est plus grand. Le morceau est devant la bouche. |
| n148 (6,17 s) | cle-4.png, MP4 et GIF agrandis | Morsure : le morceau recouvre l'intérieur de la bouche (96 pixels mesurés). La bouchée commence à disparaître. Deux yeux (l'œil pendant est juste sous la main). |
| n160 (6,67 s) | MP4, agrandie | Mastication. Le morceau a visiblement rapetissé (encoche de la bouchée). Il est tenu sous le menton. Deux yeux. |
| n176 (7,33 s) | MP4 | Mastication (mâchoire, joues). Deux yeux. |
| n188 (7,83 s) | MP4 | Déglutition : tête baissée, morceau tenu sous le menton. |
| n206 (8,58 s) | MP4, agrandie | Deuxième morsure : le morceau est à nouveau dans la bouche. Deux yeux. |
| n222 (9,25 s) | MP4 | Main vide sous le menton, il mâche. Plus de morceau. Deux yeux. |
| n246 (10,25 s) | cle-6.png | Avalé : main vide, plus rien à manger, tête baissée. Deux yeux. |
| n262 (10,92 s) | MP4 | Inspiration : tête en arrière, yeux mi-clos, le bras redescend. |
| n280 (11,67 s) | MP4 | Soupir : épaules basses, yeux mi-clos. |
| n300 (12,50 s) | MP4 | Retour vers le repos. |
| n311 (12,96 s) | MP4 | Pose de repos, semblable à n0 (jonction de boucle). |
| n24 (1,00 s) | GIF du rendu précédent (avant la correction de la ligne sous les jambes, qui ne change que les lignes 312 à 338, à gauche de x = 246) | Clignement : la paupière couvre l'œil de la tête. Palette du GIF correcte. Les os posés au sol font partie du décor d'origine. |

Sur toutes ces images :
- **Yeux** : jamais trois. Quand les deux sont visibles, il y en a exactement deux : celui de la tête et celui qui pend.
- **Morceau** : ce n'est jamais un os. C'est un morceau rouge et rose, avec des marbrures claires et de petits filaments.
- **Bras** : continu, sans déchirure ni morceau en double.

## 2. Comptage automatique des yeux (312 images)
- Méthode : on cherche les taches « blanc d'œil », crème ou blanches, de 40 pixels ou plus, dans le rectangle de Thomas, hors du gant.
- Résultat : 2 taches sur 303 images, 1 tache sur 10 images, **jamais 3**.
- Les 10 images à 1 tache sont : n25, n26, n67, n68, n71, n128, n129, n130, n233, n234. Il y a trois cas :
  - un clignement (n25, n26, n233, n234) ;
  - l'œil pendant compté dans le rectangle exclu du gant (n67, n68, n71 ; vérifié à l'œil sur n71 = cle-2 : il y a bien deux yeux) ;
  - l'œil pendant caché derrière le morceau ou la main (n128 à n130 ; vu sur n126, voisine).

## 3. Décor inchangé hors des zones animées
- Pixels du décor modifiés hors des rectangles animés (Thomas, gant, morceau, mouches) : **0** sur les 312 images (maximum par image : 0).
- Pendant le contrôle, j'ai trouvé une fine ligne claire qui traversait les jambes. Elle venait de la reconstruction du mur sous la coupe des jambes. Je l'ai corrigée, puis j'ai tout reproduit et revu : sur l'image cle-1, l'écart avec le décor est de 0 sur ces lignes.

## 4. Contact du morceau avec la bouche
- Mesure : pixels où le morceau recouvre l'intérieur de la bouche. Ce masque de la bouche est déformé avec le visage.
- Première morsure (n146 à n151) : 21,6, 46,9, 96,3, 88,2, 76,7, 67,3 pixels.
- Deuxième morsure (n205 à n207) : 17,8, 33,7, 25,7 pixels.
- Le morceau touche donc vraiment la bouche aux images de morsure. Entre les morsures (mastication), il est tenu sous le menton : 0 pixel de contact.

## 5. Continuité du mouvement
- On mesure, pour chaque image, le déplacement maximal d'un point depuis l'image précédente. Points suivis :
  - les articulations (épaule, coude, poignet) et le bout des doigts ;
  - tous les sommets du maillage du bras ;
  - tous les pixels du corps et du visage (champ de déformation) ;
  - l'œil pendant, le morceau, le gant.
- Un « saut » serait une image où un point se déplace plus de 2,5 fois plus que la moyenne des deux images voisines (et plus de 3 px).
- **Sauts détectés : 0.** Pendant la mise au point, un saut avait été trouvé : l'œil pendant rebondissait sèchement sur la main (n207). Je l'ai corrigé avec un contact plus doux, puis j'ai remesuré.
- Jonction de boucle : la dernière image (n311) suivie de l'image 0 ne montre que 0,2 px de déplacement maximal. L'écart de couleur entre l'image 312 calculée et l'image 0 est de 0,0.

### Déplacement maximal d'une image à la suivante, pour chaque passage entre deux poses
Les passages sont ceux de la piste de Thomas. La colonne « objets » donne le gant et le morceau à part : le gant est un objet rapide qui traverse l'image, ses grands déplacements sont réguliers d'une image à l'autre et ne sont pas des sauts.

| Passage (pose → pose) | Images (nombre de passages) | Thomas : déplacement max (point) | Objets : déplacement max |
|---|---|---|---|
| repos → regard_gant | 59 (1 passage) | 4,8 px (pixel du corps / visage) | 24,9 px (gant) |
| regard_gant → regard_morceau | 18 (1 passage) | 13,2 px (pixel du corps / visage) | 31,0 px (gant) |
| regard_morceau → anticipation | 8 (1 passage) | 9,3 px (bout des doigts) | 39,4 px (gant) |
| anticipation → bras_part | 9 (1 passage) | 10,2 px (bout des doigts) | 1,4 px (gant) |
| bras_part → bras_mi_chemin | 8 (1 passage) | 4,0 px (sommet du maillage du bras) | — |
| bras_mi_chemin → main_saisit | 7 (1 passage) | 4,3 px (sommet du maillage du bras) | — |
| main_saisit → main_fermee | 5 (1 passage) | 1,3 px (œil pendant) | — |
| main_fermee → bras_leve | 10 (1 passage) | 8,8 px (bout des doigts) | 8,8 px (morceau) |
| bras_leve → bras_presque_bouche | 8 (1 passage) | 10,5 px (bout des doigts) | 10,5 px (morceau) |
| bras_presque_bouche → main_bouche | 7 (1 passage) | 5,7 px (sommet du maillage du bras) | 2,7 px (morceau) |
| main_bouche → bouche_ouverte | 11 (2 passages) | 5,7 px (pixel du corps / visage) | 2,8 px (morceau) |
| bouche_ouverte → morsure | 10 (2 passages) | 8,0 px (pixel du corps / visage) | 3,5 px (morceau) |
| morsure → bras_presque_bouche | 6 (1 passage) | 8,3 px (sommet du maillage du bras) | 7,1 px (morceau) |
| bras_presque_bouche → mastication_1 | 4 (1 passage) | 4,2 px (pixel du corps / visage) | 0,1 px (morceau) |
| mastication_1 → mastication_2 | 16 (4 passages) | 5,7 px (pixel du corps / visage) | 0,1 px (morceau) |
| mastication_2 → mastication_3 | 8 (2 passages) | 4,4 px (pixel du corps / visage) | 0,1 px (morceau) |
| mastication_3 → mastication_2 | 9 (2 passages) | 4,6 px (pixel du corps / visage) | 0,1 px (morceau) |
| mastication_2 → mastication_1 | 8 (2 passages) | 5,7 px (pixel du corps / visage) | 0,1 px (morceau) |
| mastication_2 → avalement | 23 (2 passages) | 2,0 px (pixel du corps / visage) | 0,0 px (morceau) |
| avalement → main_bouche | 7 (1 passage) | 7,9 px (sommet du maillage du bras) | 3,9 px (morceau) |
| morsure → menton | 8 (1 passage) | 9,5 px (sommet du maillage du bras) | — |
| menton → mastication_1 | 4 (1 passage) | 4,6 px (pixel du corps / visage) | — |
| avalement → soulagement_inspire | 16 (1 passage) | 7,9 px (bout des doigts) | — |
| soulagement_inspire → soulagement | 24 (1 passage) | 3,2 px (pixel du corps / visage) | — |
| soulagement → repos | 19 (1 passage) | 1,7 px (bout des doigts) | — |

- Les plus grandes valeurs pour Thomas (10 à 13 px par image) sont :
  - la tête qui suit la chute du morceau (regard_gant → regard_morceau) ;
  - le bras qui part, puis qui remonte vers la bouche.

  Ce sont des gestes rapides mais continus : les images voisines ont des valeurs proches.

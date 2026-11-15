# Démo d'animation par zones : Thomas le zombie

Animation « par le code » à partir d'une seule image (`projets/demo-zombie/entrees/03-zombie.png`),
sans images dessinées une à une et sans vidéo générée. Python, bibliothèques libres (numpy, Pillow, scipy).

## Lancer
```
pip install numpy pillow scipy
python3 preparer.py       # une fois : découpe, cartes de zones, décor
python3 produire_gifs.py  # les 4 GIF + mesures.json
```

## Architecture
1. **Décor fixe** (`decor/fond.png`) : cadrage 640x480 de l'image d'origine, à taille réelle (pas de redimensionnement, les pixels restent nets). Il est posé une fois. À chaque image, le moteur ne remet le décor que dans les rectangles dessinés à l'image précédente, puis recalcule seulement le rectangle de Thomas et les petites particules. Hors de ces rectangles, aucun pixel ne change (vérifié : 0 écart dans les 4 GIF).
2. **Composant « animable »** (`scene.json`) : on peut l'ajouter à n'importe quel objet. Il contient :
   - des **calques** découpés (`calques/corps.png`, `bras_droit.png`, `oeil_pendant.png`), avec un parent et un pivot (le bras et l'œil suivent le corps) ;
   - des **cartes de zones** en niveaux de gris (`zones/*.png`) : plus c'est clair, plus la zone bouge (tête, haut du corps, ventre, mâchoire, coins de la bouche, bave, main) ;
   - des zones « cercle » pour les paupières ;
   - le mur reconstruit derrière Thomas (`objets/thomas_derriere.png`), visible seulement là où un calque s'écarte de sa place.
   Le cercueil et la tombe sont déclarés avec `"animable": null`. Pour les animer, il suffit de remplacer `null` par `{"zones": {...}}` : sans calques, le rectangle entier devient un calque. Rien d'autre n'est à modifier.
3. **Recettes** (`recettes/*.json`) : listes de couches `{zone, effet, amplitude, duree, courbe, phase, debut, fin, attaque, relache}`.
   - Effets de forme : `deplacement_x`, `deplacement_y`, `rotation`, `echelle`.
   - Effets de couleur : `luminosite`, `lueur`, `teinte`, `paupiere`.
   - Particules : `mouches`, `zzz`, `curseur`.
   - Courbes : `constante`, `sinus`, `sinus_positif`, `bruit` (doux et périodique), `clignement`.
   Le moteur additionne les couches de toutes les recettes actives, sans rien inventer. Ce sont de simples tables, faciles à relire en Lua.
4. **Actions** (`actions.json`) : action → zone touchée → recettes lancées ensemble, avec une durée commune. Exemples : `frotter_la_tete`, `donner_un_os`, `chatouiller_le_ventre`. Comme les recettes agissent sur les mêmes zones et partagent la même enveloppe, les mouvements restent cohérents entre eux.
5. **Passage d'une pose à l'autre** : une pose est une recette de valeurs constantes (`pose_sommeil`, `pose_repas`, `pose_joie`). `attaque` et `relache` la font entrer et sortir progressivement, avec une courbe douce. Il n'y a jamais de coupure.

## Comment un pixel bouge (`moteur.py`)
- Chaque calque reçoit un champ de déplacement : la somme, pour chaque couche, de « poids de la zone × mouvement ».
- Pour chaque pixel de sortie, on cherche d'où il vient (inversion par point fixe, 3 passes), puis on lit la source en bilinéaire. Le déplacement se fait donc au sous-pixel, sans saut de pixel en pixel.
- Les effets de couleur (paupières, lueur) sont appliqués sur le calque avant la déformation : ils suivent le mouvement.
- Les calques enfants (bras, œil pendant) ont une rotation rigide autour de leur pivot, à laquelle s'ajoute le mouvement du parent au point d'attache.
- Le GIF utilise une palette unique : un pixel fixe garde le même indice dans toutes les images.

## Fichiers
| Fichier | Rôle |
|---|---|
| `preparer.py` | découpe de Thomas, reconstruction du mur, cartes de zones, sprite de mouche |
| `moteur.py` | courbes, effets, composant animable, particules, scène |
| `produire_gifs.py` | scénarios des 4 GIF, mesures, contrôle du décor |
| `scene.json`, `actions.json`, `recettes/` | données |
| `01-…04-*.gif` | résultats (640x480, 12,5 images/s, 8 s en boucle) |
| `performance.md`, `mesures.json` | temps de calcul mesurés |

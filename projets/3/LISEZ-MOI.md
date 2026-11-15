# Démo d'animation par zones, version 2 : Thomas le zombie mange

Film de 13 s en boucle, calculé par le code à partir d'une seule image (`projets/demo-zombie/entrees/03-zombie.png`).
Aucune image n'est dessinée à la main, aucune vidéo n'est générée par une IA. Python avec des bibliothèques libres (numpy, Pillow, scipy) et ffmpeg pour l'encodage.

## Résultats
| Fichier | Contenu |
|---|---|
| `thomas-mange.mp4` | H.264, 640x480, 24 i/s, 312 images, boucle continue |
| `thomas-mange.gif` | même film, palette de 256 couleurs, 6,4 Mo |
| `cle-1.png` … `cle-6.png` | repos, le gant dépose, la main saisit, le morceau à la bouche, la mâchoire ouverte, avalé |
| `controle.md` | images regardées et mesures de contrôle |
| `performance.md`, `mesures.json` | temps de calcul et mesures brutes |

## Lancer
```
pip install numpy pillow scipy        # et ffmpeg installé sur la machine
python3 preparer.py      # une fois : découpe, calques, cartes de zones, décor
python3 outil_poses.py   # une fois : écrit les poses clés (poses/*.json)
python3 produire.py      # film MP4, GIF, images clés, mesures.json
```

## Corrections par rapport à la version 1
- **Deux yeux, pas trois.** L'œil exorbité au bord du visage est retiré du calque du corps. La joue est reconstruite à sa place, avec une petite orbite d'où sort la tige. Il reste l'œil de la tête et l'œil au bout de la tige (pixels d'origine).
- **Plus d'os.** L'os tenu en main est retiré de l'image (pixels crème et leur contour). La main d'origine, qui serrait l'os, est remplacée par une main dessinée par le code.
- **Il mange de la chair crue.** Le morceau est dessiné par le code : tons rouges et rosés, marbrures claires, petits filaments qui pendent. Il perd une bouchée à chaque morsure.
- **Le bras bouge vraiment** : épaule, coude et poignet, avec une déformation continue des pixels.

## Architecture
1. **Décor fixe** (`decor/fond.png`). À chaque image, le moteur remet le décor seulement dans les rectangles dessinés à l'image précédente. Il recalcule ensuite le rectangle de Thomas, puis ceux du gant, du morceau et des mouches. Mesure : 0 pixel du décor modifié hors de ces rectangles, sur les 312 images.
2. **Composant « animable »** (`scene.json`), ajoutable à tout objet :
   - Thomas : calques `corps` et `bras`, cartes de zones (`zones/*.png` : tête, haut du corps, poitrine, mâchoire, joues, cou, cheveux), squelette du bras, main, tige et œil pendant ;
   - le gant et le morceau : objets dessinés par le code, avec leurs couleurs dans `scene.json` ;
   - les mouches : vols périodiques, agitation et attirance vers le morceau ;
   - le cercueil et la tombe sont déclarés avec `"animable": null`. Ils restent fixes.
3. **Poses clés** (`poses/*.json`) : 20 poses réutilisables (détail plus bas).
4. **Séquences** (`sequences/*.json`) : listes de poses, avec pour chaque passage une durée et une courbe.
5. **Recettes** (`recettes/*.json`) : mouvements périodiques ajoutés par-dessus les poses (respiration, balancement du poids, clignements). Les périodes divisent 13 s, donc la boucle reste continue.
6. **Actions** (`actions.json`) : action → zone touchée → séquence et recettes. Exemple : `donner_de_la_chair` (zone touchée : `main`).

## Comment les pixels bougent (`moteur.py`)
- **Corps et visage** : un champ de déplacement est calculé. C'est la somme, pour chaque zone, de « poids de la carte × mouvement » (déplacement, rotation autour d'un pivot, échelle, renflement). Le champ est inversé par point fixe, puis la source est lue en bilinéaire : le mouvement se fait au sous-pixel.
  - La mâchoire pivote autour de la charnière, près de l'oreille. L'intérieur de la bouche s'étire quand elle s'ouvre.
  - Les joues gonflent pendant la mastication.
  - Un renflement, avec un léger reflet, descend dans le cou quand Thomas avale.
- **Bras** : un maillage de triangles (pas de 3 px) recouvre la manche et l'avant-bras. Chaque sommet porte des poids sur trois influences : le tronc (haut de la manche), le haut du bras, l'avant-bras. Le moteur applique le mélange linéaire des transformations des os (skinning linéaire). Il rastérise ensuite les triangles déformés et lit la texture d'origine au sous-pixel. Le bras se plie au coude, il ne glisse pas d'un bloc. Derrière, le mur et le torse caché sous la manche sont reconstruits.
- **Longueurs d'os constantes** : une pose ne stocke que des angles (épaule, coude, poignet). Les positions sont recalculées par cinématique directe.
- **Main** : elle est dessinée par le code (champ de distance) et attachée au poignet. Paume, pouce et trois doigts à deux phalanges s'enroulent selon `main_fermeture`. Le grain de peau est repris de l'avant-bras.
- **Mouvement secondaire** (ressorts amortis, simulés d'une image à l'autre) :
  - l'œil pendant est un pendule au bout de sa tige, qui suit la tête avec retard ; la main et le morceau le poussent s'ils passent tout près ;
  - les cheveux suivent la rotation de la tête avec retard ;
  - le morceau tremble à l'impact et ses filaments se balancent.

  Avant de filmer, le moteur simule une boucle complète. Les ressorts sont ainsi déjà dans l'état de fin de boucle, et la jonction est continue (écart mesuré : 0).

## Format d'une pose (`poses/<nom>.json`)
```json
{
  "nom": "main_bouche",
  "description": "…",
  "squelette": {"epaule": -29.6, "coude": -42.1, "poignet": -55.6, "main_fermeture": 1.0},
  "corps": {"inclinaison": 1.0, "x": 0.0, "y": 0.0, "epaules": 0.0, "poitrine": 0.0},
  "zones": {"tete_rotation": 7.0, "tete_x": 2.5, "tete_y": 0.5, "machoire": 0.0, "joues": 0.0,
            "paupieres": 0.0, "cou_deglutition": 0.0, "oeil_pendant_regard": 10.0},
  "attaches": {"prise_main": [16.0, 2.0]}
}
```
- `squelette` : angles en degrés, ajoutés à la pose de repos (sens horaire à l'écran = positif) ; `main_fermeture` de 0 (ouverte) à 1 (fermée).
- `corps` : inclinaison du buste autour des hanches (degrés), décalage (px), `epaules` (px, positif = elles retombent), `poitrine` (gonflement).
- `zones` : état de chaque zone.
  - `machoire` : 0 = repos, 1 = grande ouverte, négatif = serrée.
  - `joues` : de 0 à 1.
  - `paupieres` : de 0 = ouvertes à 1 = fermées.
  - `cou_deglutition` : 0 → 1 fait descendre le renflement une fois, 1 → 2 une deuxième fois.
  - `oeil_pendant_regard` : rotation de l'œil pendant, en degrés.
- `attaches` : points d'attache des objets. `prise_main` est le point où un objet tenu se fixe, dans le repère de la main (x vers les doigts).
- Une pose peut être **partielle** : par exemple, les poses de mastication ne donnent que le visage. Les paramètres absents gardent leur valeur précédente.
- Le lien entre un paramètre et les zones qu'il fait bouger est dans `scene.json` (`"parametres"`). Exemple : `"zones.machoire": [["machoire", "rotation", 13.0], ["machoire", "deplacement_y", 1.2]]`.

Les 20 poses : repos, regard_gant, regard_morceau, anticipation, bras_part, bras_mi_chemin, main_saisit, main_fermee, bras_leve, bras_presque_bouche, main_bouche, bouche_ouverte, morsure, mastication_1, mastication_2, mastication_3, avalement, menton, soulagement_inspire, soulagement.
`outil_poses.py` les a écrites. Pour les poses où la main doit atteindre un point précis (le morceau posé sur le bord du cercueil, la bouche), cet outil calcule les angles par cinématique inverse à deux os. La pose « repas » de la planche `10-zombie-animation.png` a servi de modèle pour `main_bouche` : coude contre le corps, avant-bras remonté, tête penchée vers la main. Elle est recalée sur la taille de Thomas. Une fois écrites, les poses sont de simples fichiers JSON : on peut les modifier à la main.

## Format d'une séquence (`sequences/<nom>.json`)
```json
{
  "nom": "thomas_mange", "duree": 13.0, "boucle": true,
  "recettes": {"thomas": ["repos_vivant"]},
  "pistes": {
    "thomas": [
      {"pose": "repos", "tenir": 2.1},
      {"pose": "regard_gant", "duree": 0.35, "courbe": "doux", "tenir": 0.45},
      {"pose": "avalement", "duree": 0.48, "courbe": "doux", "valeurs": {"zones": {"cou_deglutition": 2.0}}}
    ],
    "gant":    [{"valeurs": {"x": 392, "y": -36, "angle": 10, "ouverture": 0}, "tenir": 2.0}],
    "morceau": [{"valeurs": {"attache": "gant", "bouchees": 0}}]
  }
}
```
- Une piste par objet. Chaque entrée donne une pose (`pose`, et/ou `valeurs` qui complètent ou remplacent), puis :
  - `duree` : durée du passage depuis la clé précédente ;
  - `courbe` : courbe de ce passage ;
  - `tenir` : arrêt sur la pose.
- **Le moteur calcule seul l'entre-deux** de tous les paramètres numériques : angles, zones, positions, couleurs des paupières, bouchées.
- Courbes disponibles :
  - `spline` : spline d'Hermite monotone, dont la vitesse ne s'annule pas sur les poses intermédiaires, d'où un mouvement continu à travers plusieurs poses ;
  - `doux` : accélération puis décélération ;
  - `entree`, `sortie` ;
  - `chute` : accélération constante, pour un objet lâché ;
  - `lineaire`, `rebond`.
- Les valeurs texte (par exemple `attache` : `gant`, `libre`, `main`) changent à l'arrivée de la clé. Le léger écart entre l'ancienne et la nouvelle attache est résorbé en 0,2 s.
- **Ajouter une pose ou une séquence = ajouter un fichier JSON**, sans toucher au moteur.

## La séquence « Thomas mange » (13 s)
- 0 à 2 s : repos vivant (respiration, balancement du poids, clignement, œil pendant, mouches).
- 2 à 3,6 s : le gant entre par le haut à droite, descend, lâche le morceau et repart. Le morceau tombe sur le bord du cercueil et s'écrase un peu. Thomas lève la tête vers le gant, puis la baisse vers le morceau. Les mouches s'agitent, puis viennent tourner autour du morceau.
- 3,2 à 6 s : anticipation (recul, inspiration, la main s'ouvre). Le bras part, Thomas se penche, saisit le morceau (les doigts se referment) et le ramène vers sa bouche.
- 6 à 10,5 s : deux bouchées. Pour chacune : la bouche s'ouvre, le morceau entre dans la bouche, la mâchoire se referme et une bouchée disparaît. Thomas mâche 3 fois (mâchoire, joues, tête), puis avale (le renflement descend dans le cou). La deuxième bouchée finit le morceau.
- 10,5 à 13 s : longue inspiration, soupir, épaules qui retombent, yeux mi-clos, puis retour doux au repos.

## Fichiers
| Fichier | Rôle |
|---|---|
| `preparer.py` | découpe, retrait de l'œil en trop et de l'os, reconstruction du mur et du torse, cartes de zones |
| `moteur.py` | courbes, poses, séquences, champ de zones, skinning du bras, main, gant, morceau, mouches, ressorts, scène |
| `outil_poses.py` | écriture des poses clés (cinématique inverse pour les poses à cible) |
| `produire.py` | rendu du film, encodage, images clés, mesures de contrôle |
| `scene.json`, `actions.json`, `poses/`, `sequences/`, `recettes/` | données |
| `calques/`, `zones/`, `objets/`, `decor/` | images préparées |

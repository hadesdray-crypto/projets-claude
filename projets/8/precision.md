# Précision de la maquette

Mesures produites par `scripts/precision.py` (résultats bruts : `precision_mesures.json`) sur la zone lon -1,8545 à -1,8420, lat 46,5960 à 46,6080.

## Sources réellement utilisées
| Élément | Source | Ce qui a marché |
|---|---|---|
| Bâtiments | IGN BD TOPO `batiment` (WFS) | 519 retenus (surface ≥ 2 m²) sur 523 reçus |
| Routes et chemins | BD TOPO `troncon_de_route` (299 tronçons dont 42 sentiers) + OpenStreetMap `highway` (186 voies) | réseau fusionné : 1 976 nœuds, 2 185 arêtes, d'un seul tenant |
| Végétation (zones) | BD TOPO `zone_de_vegetation` | 34 zones (haies exclues du tracé) |
| Arbres | **LiDAR HD IGN, modèle numérique de hauteur (MNH, 0,5 m)** via le service WMS de l'IGN | voir ci-dessous |
| Relief | LiDAR HD, modèle numérique de terrain (MNT) | utilisé seulement pour la mesure, pas dans la maquette |
| Camping, piscines, poubelles, toilettes | OpenStreetMap (Overpass) | 14 piscines, 3 toilettes, 12 poubelles (non placées), **0 arbre** |
| Obstacles | OpenStreetMap `barrier` (Overpass) | 20 lignes : 9 haies, 7 clôtures, 2 murets, 2 portails (BD TOPO `construction_lineaire` : seulement 3 ponts, inutilisés) |
| Photo | IGN orthophoto (WMS, Lambert-93, 0,5 m/pixel) | calque de vérification |

Non utilisé : le nuage de points LiDAR brut (dalles de 1 km, très lourdes) — j'ai pris à la place les modèles de hauteur dérivés du LiDAR, fournis par l'IGN. La couche « chemin » demandée n'existe pas dans la BD TOPO : les chemins sont les tronçons de nature « Sentier ».
`itineraire_autre` (3,6 Mo) téléchargé mais non utilisé (doublon des sentiers de randonnée). Aucune piscine ni équipement dans `construction_surfacique`, `erp`, `point_d_acces` (vides).

## Empreintes des blocs contre l'orthophoto
Méthode : pour 102 bâtiments à toit orange (tuiles), d'au moins 50 m², on compare l'empreinte BD TOPO à la tache orange du toit sur l'orthophoto.
- Décalage médian : **1,6 m** ; 90 % des cas sous **2,6 m**.
- Décalage moyen : 1,0 m vers l'ouest, 0,1 m vers le nord (systématique : probablement l'effet de bascule des toits sur l'orthophoto, la BD TOPO étant saisie au pied ou à l'égout).
- Recouvrement (intersection / union) médian : 0,59.
Limite : la mesure ne couvre que les toits orange ; les toits gris ou sombres ne sont pas mesurés (non vérifié). Le calque photo de l'application permet de contrôler à l'œil (voir `captures/5-photo-superposee.png`).

## Hauteurs
- 504 bâtiments sur 519 ont une hauteur réelle BD TOPO (médiane 3,6 m, de 1 à 14,2 m). **15 n'en ont pas** : valeur par défaut 3,0 m, indiquée « (valeur par défaut) » dans l'éditeur.
- Comparaison avec le LiDAR (90e centile de la hauteur dans l'empreinte) sur 266 bâtiments : écart médian +0,7 m (le LiDAR voit le faîtage, la BD TOPO l'égout), écart absolu médian 0,8 m, 90 % sous 3,4 m.
- Le mobil-home d'exemple (3,0 m) est une valeur par défaut, pas une mesure.

## Arbres
- 3 453 arbres = maxima locaux de la canopée LiDAR (hauteur > 2,5 m, lissage 1 m, hors bâtiments élargis de 1,5 m). Hauteur médiane 6,9 m, 90 % sous 15,6 m, maximum 22,0 m.
- Position : précision attendue ≈ 1 m. Le rayon de chaque forme est une estimation (0,22 × hauteur, entre 1 et 3,2 m), pas une mesure. Une forme tient sur le sol (de 0 à la hauteur mesurée), donc rien ne flotte.
- Défauts connus : les maxima peuvent regrouper ou séparer des houppiers ; les pins serrés en forêt (à l'est et au sud du camping) ne sont pas tous individualisés ; les haies hautes et les poteaux ou antennes de plus de 2,5 m peuvent être comptés comme arbres (non vérifié).

## Relief
Le sol de la maquette est **plat** (demande : sol bleu uni). Dans le camping le terrain varie de 4,6 à 6,6 m d'altitude (90 % entre 4,9 et 5,7 m) : l'approximation est correcte. Sur toute la zone (dunes) il varie de −6,7 à +17,0 m : les distances de trajet sont donc des **distances horizontales** (la pente n'est pas comptée).

## Chemins
- Les trajets utilisent le réseau BD TOPO + OSM. Les lieux ne sont pas toujours sur une route : le trajet les raccorde en ligne droite au point le plus proche du réseau (tracé jaune, distance indiquée « hors route »).
- Vérification indépendante : `scripts/verifier_chemins.py` (A* en Python) donne les mêmes longueurs que la page (Mobil-home → Piscine 110 + 28 m ; Piscine → Accueil 25 + 33 m ; Accueil → Plage 1 433 + 128 m = 1 562 m ; total 1 758 m).
- Les chemins de dune sont des traces de la BD TOPO : leur état réel et leur praticabilité ne sont pas vérifiés sur le terrain.
- « Voiture » est déduit de la nature de la voie (route, route empierrée, OSM service/residential/track…) ; les voies internes du camping sont souvent privées (non vérifié).

## Ce que la maquette ne sait pas faire (limites)
- **Les mobil-homes, tentes et emplacements ne sont pas dans la BD TOPO** : seuls 10 bâtiments BD TOPO sont dans le contour du camping. Le gérant doit les ajouter avec l'éditeur. Un seul mobil-home d'exemple a été ajouté à la main (position relevée sur l'orthophoto, confiance 0,3).
- Classement automatique (champ `confiance`) : 1 « accueil » (0,3, plus gros bâtiment du camping : à vérifier), 3 « local technique » (0,3, < 12 m²), 1 « mobil-home » BD TOPO (0,5, 12 à 45 m²), le reste « bâtiment ». Douches, bar, poubelles, sanitaires : non placés (aucune donnée fiable).
- La « piscine » est la grande halle bleue du camping, issue d'OSM (surface 256 m²) ; une seconde piscine de 157 m² est aussi présente dans le contour. L'orthophoto montre que la halle bleue n'est pas dans la BD TOPO.
- Le contour du camping vient d'OSM ; il n'a pas été comparé à un plan officiel (non vérifié).

## Version 2 : toits, couleurs, numéros, obstacles
- **Toits** : calculés, non mesurés. Chaque bâtiment reçoit le rectangle orienté de plus petite aire qui l'englobe ; le toit est posé sur ce rectangle. Règle automatique : toit **plat** si annexe, local technique, poubelles, emprise < 25 m² ou si l'empreinte remplit moins de 80 % du rectangle (formes en L, etc.) ; sinon **deux pans** si longueur/largeur > 1,4, **quatre pans** sinon. Hauteur du faîte = 0,3 × la largeur (pente ≈ 30°), au plus 4,5 m. Résultat : 283 toits plats, 120 à deux pans, 117 à quatre pans (520 blocs, dont l'exemple ajouté à la main). La hauteur BD TOPO est prise comme hauteur des murs (à l'égout) ; le faîte affiché est donc une estimation. Pente et forme réelles des toits : non vérifiées (pas comparées à l'orthophoto ni au LiDAR). Le type de toit est modifiable dans l'éditeur (« Changer le toit »).
- **Routes** : largeur **forfaitaire par catégorie** (la largeur réelle n'est pas dans les données conservées) : route à une chaussée 5,5 m, rond-point 6 m, primaire 7 m, résidentielle 5 m, service et route empierrée 3,5 m, piste 3 m, piste cyclable 2,5 m, sentier 1,2 m. Ces valeurs sont des hypothèses, non mesurées.
- **Obstacles** : hauteurs et épaisseurs forfaitaires (clôture 1,5 m, muret 1,0 m, haie 1,5 m, portail 1,5 m) ; seules 20 lignes existent dans OpenStreetMap sur la zone ; il y en a peut-être d'autres sur le terrain (non vérifié). Ils sont éloignés du camping, sauf quelques-uns à l'ouest.
- **Arbres** : tronc (30 % de la hauteur mesurée au LiDAR) et houppier translucides ; même position et même rayon estimé qu'avant.
- **Numéros** : 41 éléments numérotés : piscines du camping (1-2), accueil (3), locaux techniques (4-6), mobil-homes (7-8), bâtiments du camping, commerces et bâtiments de sport à moins de 300 m du camping, terrains de sport proches (38-40) et la plage (41). Les numéros ne suivent pas l'exemple « 3 sanitaires » : aucun sanitaire n'est dans les données (3 toilettes OSM existent mais ne sont pas placées, faute de dimensions fiables).
- **Mesures au toucher** : longueur et largeur = rectangle englobant orienté (pas les côtés exacts des formes irrégulières), hauteur des murs, faîte, emprise ; pour une piscine, la hauteur du bloc (1 m, représentation) n'est pas la profondeur.

## Correction n°1 : vue de départ, repères, photo nette
- **Positions posées à la main** (relevées sur l'orthophoto IGN, grille de 10 m, à confirmer sur place) : piscine couverte, entrée, aire de gravier, zone des mobil-homes. L'accueil est le bâtiment BD TOPO à toit orange déjà classé « accueil » (204 m² mesurés, pas 437 m² : ce chiffre n'est pas retrouvé dans les données).
- **Piscine couverte** : voûte vitrée (demi-ellipse) de 29 × 12 m et 5 m de haut, posée sur l'axe du bassin OSM couvert (25,2 × 10,9 m mesurés). Les 29 × 12 m et les 5 m sont les valeurs demandées, pas des mesures ; le faîte réel n'est pas vérifié. Elle remplace le bloc plat de 1 m pour ce bassin.
- **Entrée** : barrière jaune et noire visible sur l'orthophoto vers (263,5 ; 437,5) m ; la barrière 3D est une simple série de lattes.
- **Parking** : polygone de 1 000 m² environ au centre haut, plus un prolongement clair au sud de l'accueil ; limites approximatives. **Zone des mobil-homes** : carré de 190 à 275 m est, 340 à 446 m nord, découpé sur le contour du camping (environ 7 400 m²). Aucun mobil-home individuel n'est inventé.
- **Orthophoto** : WMS de l'IGN, 10 pixels par mètre demandés (2 700 × 2 300), réduits à 8 pixels par mètre. La résolution d'origine de la prise de vue est de l'ordre de 0,2 m : les 10 pixels par mètre sont un échantillonnage du service, pas un détail de plus. Le zoom 21 n'a pas été cherché. Sur la photo les toits décalent de 1 à 2 m des blocs (vue oblique).
- **Vue de départ** : distance de 210 m sur tablette (1024 × 768) et 577 m sur téléphone (390 × 800) : sur un écran étroit, le camping entier (environ 240 × 205 m) ne tient pas à 150-200 m ; la distance est calculée pour garder tout le contour visible.
- **Lisibilité** : arbres plus petits (rayon × 0,75) et plus transparents (28 % au lieu de 50 %), arêtes des blocs plus sombres, couleurs propres à l'accueil (rouge) et aux sanitaires (vert d'eau). Aucun sanitaire n'existe toujours dans les données.

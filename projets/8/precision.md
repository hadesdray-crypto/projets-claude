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

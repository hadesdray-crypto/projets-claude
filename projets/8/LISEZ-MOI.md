# Maquette 3D du Camping Amitié & Nature

Plan 3D très simple « en blocs translucides », à l'échelle réelle (mètres), pour le camping et le chemin vers la plage des Dunes.

## Ouvrir
Double-cliquez sur `index.html` (aucune connexion nécessaire : Three.js est inclus dans `app.js`). Copiez tout le dossier pour l'utiliser hors ligne, sur téléphone ou tablette.

## Utiliser
- **Doigt** : un doigt tourne la vue, deux doigts déplacent et zooment. Souris : clic gauche tourne, clic droit déplace, molette zoome.
- **Ensemble / Camping** : deux vues prêtes.
- **Trajet** : itinéraire à pied mobil-home → piscine → accueil → plage, avec distance, temps (1,3 m/s) et possibilité en voiture. Le pion le parcourt (bouton « ×10 » : vitesse du pion ×1, ×10, ×30).
- **Mesurer** : touchez deux points au sol, la distance s'affiche. La règle d'échelle est en bas à gauche.
- **Modifier** : touchez un bloc puis glissez-le (pas de 0,5 m). Boutons : tourner (15°), plus/moins large, long, haut (0,5 m), changer le type, ajouter, supprimer, annuler, rétablir. Enregistrement automatique sur l'appareil ; Exporter / Importer un fichier JSON.
- **Calques** : bâtiments, arbres, routes et chemins, zones, étiquettes, photo aérienne (éteinte ; sert uniquement à vérifier les positions).

## Relancer le calcul des données
```
bash scripts/recuperer.sh          # télécharge IGN + OpenStreetMap (curl)
python3 scripts/preparer.py        # écrit donnees/*.json et donnees/donnees.js (shapely, pyproj, numpy, scipy, tifffile, pillow)
python3 scripts/verifier_chemins.py
python3 scripts/precision.py       # écrit precision_mesures.json
bash scripts/construire.sh         # reconstruit app.js depuis src/app.js (Node)
node scripts/captures.js           # captures + contrôles (puppeteer-core, Chrome)
```
`donnees/liens.json` : liaisons manuelles entre chemins (`{"de":[x,y],"a":[x,y]}` en mètres, repère local). Vide pour l'instant. Pour les rajouter, relancez `preparer.py`.
Repère local : origine en Lambert-93 (EPSG:2154) E 329 100 m, N 6 622 700 m ; x vers l'est, y vers le nord.
`donnees/orthophoto.js` est l'orthophoto en base64 (pour fonctionner depuis un fichier local).

## Origine des données et licences
- IGN : BD TOPO (bâtiments, routes, végétation, sport), LiDAR HD (hauteur de canopée, terrain), orthophotographie. Licence ouverte Etalab 2.0 — source : « IGN ».
- OpenStreetMap : contour du camping, piscines, voies. © contributeurs OpenStreetMap, licence ODbL. Les téléphones et courriels présents dans OSM n'ont pas été conservés.
- Three.js : licence MIT.
Précision et limites : voir `precision.md` (notamment : mobil-homes absents des données, à placer avec l'éditeur).

## Contenu
`index.html`, `app.js` (généré) / `src/app.js` (source), `donnees/`, `scripts/`, `captures/`, `precision.md`, `controle.md`.

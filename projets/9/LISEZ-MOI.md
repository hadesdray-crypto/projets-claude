# Site du Camping Amitié & Nature — version 1

Site vitrine, mobile d'abord, en HTML, CSS et JavaScript simples (aucune dépendance externe, aucun service payant).

## Ouvrir
Publié par GitHub Pages dans `projets/9/`. En local : `python3 -m http.server` depuis le dossier `projets/`, puis `http://localhost:8000/9/`. Le bouton « Voir le plan en 3D » ouvre `../8/` : il faut donc que le dossier `8` soit à côté du dossier `9`.

## Ce qui est fait
- Pages-sections : présentation, piscine, emplacements (~80) et mobil-homes (11), services et activités, aux alentours, accès et plan, contact et réservation.
- Textes repris du site actuel (lecture seule), orthographe corrigée, simplifiés.
- `theme.css` : les 8 couleurs du thème partagé (variables `--bleu`, `--bleu-fonce`, `--orange`, `--gris`, `--rouge`, `--violet`, `--ardoise`, `--jaune`) et les polices.
- Polices **Changa One** et **Open Sans** (licence SIL OFL) en woff2 dans `polices/`, sous-ensemble latin (Google Fonts, fichiers copiés dans le dépôt : aucun appel externe à l'ouverture).
- Barre fixe en bas (Menu / Contact / Réserver) sur téléphone et tablette ; barre du haut sur ordinateur (à partir de 960 px).
- Bouton « Voir le plan en 3D » (haut de page, section Accès et plan, menu) vers `../8/`.
- Aucune photo ni logo du camping : illustrations SVG dessinées par le code (`images/*.svg`) avec la mention « photo à ajouter ». L'image de l'aperçu 3D est une capture de la maquette `projets/8/`.
- Pas de formulaire : le contact et la réservation renvoient vers le site actuel du camping (page contact, contrat de réservation PDF, grille de prix PDF).

## Remplacer une image par une photo
1. Copier la photo dans `images/` (ex. `piscine.jpg`).
2. Dans `images.json`, écrire son nom dans `"fichier"` (ex. `"fichier": "piscine.jpg"`) et décrire la photo dans `"alt"`.
3. La mention « photo à ajouter » disparaît toute seule. Laisser `"fichier"` vide pour garder l'illustration.
Emplacements : accueil, piscine, emplacements, mobilhomes, activites, alentours.

## À faire / limites
- Téléphone et courriel du camping volontairement **non recopiés** (dépôt public) : à ajouter si le propriétaire le décide (ex. un lien `tel:` dans la section Contact).
- Adresse recopiée : 15 rue du Gournail, Brétignolles-sur-Mer (adresse du camping, publique sur son site).
- Pas de lecture de `images.json` en ouvrant `index.html` par double-clic (le navigateur bloque `fetch` sur un fichier local) : les illustrations par défaut restent ; il faut un serveur ou GitHub Pages pour les photos.
- Pas de version anglaise, pas de tarifs en clair (lien vers la grille PDF), pas de photos réelles.

## Vérifications faites (Chromium sans écran, 390 et 1280 px)
Aucun débordement horizontal, aucun texte coupé, polices chargées, aucune erreur JavaScript ni requête en échec, ancres internes valides, menu qui s'ouvre et se ferme (touche Échap), liens du site actuel et `../8/` répondent 200. Contrastes calculés (texte ≥ 4,7:1).
Non vérifié : rendu sur vrais téléphones et autres navigateurs (Safari, Firefox) ; lecteur d'écran ; le lien OpenStreetMap (répond 429 aux requêtes automatiques, non testé dans un navigateur).

## Captures (`captures/`)
`390-haut.png`, `390-page-entiere.png`, `390-menu.png`, `1280-haut.png`, `1280-page-entiere.png`. Sur la capture pleine page à 390 px, la barre du bas apparaît au milieu : c'est un effet de la capture, elle est fixée en bas à l'écran.

# Application du Camping Amitié & Nature (version 1)

Application web installable (PWA) : côté **campeurs** sur téléphone, **mode gérant** sur tablette.
HTML, CSS et JavaScript simples. Pas de serveur, rien de payant, aucune dépendance externe.
**Toutes les données de la démo sont fictives.**

Adresse (GitHub Pages) : https://hadesdray-crypto.github.io/projets-claude/projets/10/

## Ce qui marche
- **Aujourd'hui** : date, horaires (pain, piscine, pizza), programme du jour, affiches des événements du jour et des prochains jours.
- **Plan** : ouvre la maquette 3D `../8/`.
- **Balades** : plage des Dunes (1,6 km, 20 min, calculé sur la maquette 3D ; chemin de dune non vérifié sur le terrain), commerces et tour du camping (**fictifs**, marqués comme tels).
- **Infos pratiques** : piscine couverte (1/4 au 30/9), pain, pizza, laverie, wifi payant, contact. Horaires marqués « fictif ».
- **Barre basse** : Menu / Contact / Réserver, comme sur le site.
- **Mode gérant** (bouton « Gérant » ou Menu → Mode gérant) : choisir son rôle, taper le code.
  - **Publier un événement** : prendre ou choisir une photo, écrire titre, genre, date, heure, texte. L'affiche se fabrique toute seule (photo, titre, date, heure, couleurs du thème). Elle apparaît tout de suite dans « Aujourd'hui ». Modifier et supprimer sont possibles.
  - **Caisse** : gros boutons. **Un appui = une vente.** Total du jour en haut. « Plus d'options » : annuler la dernière vente, ventes par catégorie, export des ventes du jour (fichier tableur CSV), ajouter et régler les boutons (nom, prix, catégorie, couleur, forme, police, taille, photo ou texte).
  - **Arrivées du jour** (fictives).
  - **Plan (modifier)** : ouvre la maquette 3D ; y toucher « Modifier » pour ajouter douches, poteaux, jeux, mobil-homes.
  - **Codes et sauvegarde** : changer les codes, exporter / importer toutes les données (fichier JSON).
- **Hors réseau** : une fois l'application ouverte une fois en ligne, elle se recharge sans réseau (service worker).
- **Installation** : depuis le navigateur du téléphone, « Ajouter à l'écran d'accueil » / « Installer ».

## Code gérant
- Par défaut, **1234 pour les quatre rôles** (démo). À changer tout de suite dans « Codes et sauvegarde » (rôle Gérant).
- Chaque rôle a son propre code à 4 chiffres.

| Rôle | Événements | Caisse (vendre) | Régler les boutons | Arrivées | Plan | Codes et sauvegarde |
|---|---|---|---|---|---|---|
| Gérant | oui | oui | oui | oui | oui | oui |
| Réception | oui | oui | non | oui | oui | non |
| Animateur | oui | non | non | non | non | non |
| Vendeur | non | oui | non | non | non | non |

Attention : le code protège l'écran, pas les données. Quelqu'un qui connaît les outils du navigateur peut lire le stockage de l'appareil. Ne pas y mettre de données sensibles.

## Ce qui reste (limites honnêtes)
- **Pas de synchronisation entre appareils** : chaque appareil a ses propres données. Un événement publié sur la tablette n'apparaît **pas** sur le téléphone des campeurs. Pour l'instant : Exporter sur un appareil, Importer sur l'autre. Pour que les campeurs voient les événements sur leur téléphone, il faudra une étape suivante (par exemple publier le fichier exporté sur ce dépôt).
- Le plan 3D (`../8/`) n'est **pas** disponible hors réseau depuis cette application.
- Horaires, balades « commerces » et « tour du camping », arrivées, prix : **fictifs**.
- Contact (téléphone, courriel) et lien « Réserver » : **à renseigner** dans `donnees-demo.js`.
- Mémoire de l'appareil limitée (environ 5 Mo) : les photos sont réduites (900 px), mais beaucoup d'événements avec photo finiront par la remplir (un message le signale).
- Après une mise à jour des fichiers, changer `VERSION` dans `sw.js`, sinon les appareils gardent l'ancienne version.

## Remplacer les images
Le dépôt est public : aucune photo ni logo du camping. Remplacer un fichier par un autre **du même nom** :
- `images/demo-soiree.jpg`, `images/demo-pizza.jpg` : images de démo générées par IA (pollinations.ai ; une petite mention « pollinations.ai » est dans le coin).
- `images/demo-spectacle.svg` : dessinée par le code (la génération par IA a échoué).
- `images/emplacement-plan.svg` : emplacement d'image de l'écran Plan.
- `icones/icone-192.png`, `icones/icone-512.png` : icône de l'application (dessinée par le code depuis `icones/icone.svg`, pas le logo du camping).
Les photos des événements et des boutons se changent dans l'application.

## Modifier les textes fixes
`donnees-demo.js` : horaires, infos pratiques, balades, contact, lien Réserver, contenu de départ.
Les données de départ ne servent qu'au premier lancement sur un appareil.

## Fichiers
`index.html`, `theme.css` (couleurs, polices, formes du site), `app.css`, `app.js`, `donnees-demo.js`, `manifest.webmanifest`, `sw.js`, `polices/` (Changa One et Open Sans en woff2, licence SIL OFL, fichiers de licence inclus), `images/`, `icones/`, `captures/`, `scripts/`, `controle.md`, `resultats-tests.json`.

## Refaire les tests
```
cd <racine du dépôt>
python3 -m http.server 8710 &
npm i puppeteer-core          # dans un dossier à part
NODE_PATH=<ce dossier>/node_modules node projets/10/scripts/tester.js
```
Résultats dans `resultats-tests.json`, captures dans `captures/`. Voir `controle.md`.

# Contrôle (Chrome sans écran, `scripts/tester.js`)

Serveur local `python3 -m http.server` (racine du dépôt), Chromium sans écran, langue fr-FR.
Téléphone : 390 × 844 (tactile). Tablette : 1024 × 768.
Résultat : **35 / 35 réussis.**

| Contrôle | État | Détail |
|---|---|---|
| Polices du thème chargées | réussi |  |
| Aujourd'hui : affiches du jour dessinées | réussi |  |
| Lien du plan vers ../8/ | réussi |  |
| La maquette ../8/ répond | réussi | code 200 |
| Code faux refusé | réussi |  |
| Bouton « Gaufre » créé | réussi | Glace, 2,00 € / Boisson, 1,50 € / Crêpe, 2,50 € / Pizza, 9,00 € / Gaufre, 3,00 € |
| Trois ventes : total du jour 8,00 € | réussi | avant 0,00 €, après 8,00 €, 3 ventes |
| Annuler la dernière vente : 5,00 € | réussi | 5,00 € |
| Régler un bouton existant (prix de la glace) | réussi | Glace, 2,50 € / 5,00 € / http://localhost:8710/projets/10/index.html#gerant/caisse |
| Ventes conservées après rechargement | réussi |  |
| Message « Publié » | réussi |  |
| Photo réduite et enregistrée | réussi | data:image/jpeg;base64, |
| Événement visible côté campeurs (programme d'aujourd'hui) | réussi | 15 h Concours de pétanque Animation16 h Spectacle de magie Spectacle21 h Soirée guinguette Soirée |
| Affiche ajoutée (3 affiches du jour) | réussi |  |
| Événement modifiable | réussi |  |
| Gérant : 5 accès | réussi | evenements,caisse,arrivees,plan,reglages |
| Gérant voit les arrivées | réussi |  |
| Animateur : événements seulement | réussi | evenements |
| Animateur : arrivées refusées | réussi |  |
| Animateur : caisse refusée | réussi |  |
| Vendeur : caisse seulement | réussi | caisse |
| Vendeur : pas de réglage des boutons | réussi |  |
| Vendeur : création de bouton refusée | réussi |  |
| Vendeur : arrivées refusées | réussi |  |
| Réception : événements, caisse, arrivées, plan | réussi | evenements,caisse,arrivees,plan |
| Réception : codes refusés | réussi |  |
| Ancien code vendeur refusé | réussi |  |
| Nouveau code vendeur accepté | réussi |  |
| Import JSON : ventes restaurées | réussi |  |
| Service worker actif et contrôlant la page | réussi |  |
| Chrome : aucune erreur d'installabilité | réussi | [] |
| Hors réseau : la page se recharge avec ses affiches | réussi |  |
| Hors réseau : polices disponibles | réussi |  |
| Hors réseau : nouvel onglet sur ./ | réussi |  |
| Aucune erreur JavaScript | réussi |  |

## Captures (regardées une par une)
| Capture | Constat |
|---|---|
| `tel-1-aujourdhui.png`, `tel-1b-…-page-entiere.png` | Horaires en cartes arrondies avec pastilles « fictif », programme, affiches (photo, genre, titre, date, heure, bandeau orange). |
| `tel-2-menu.png` | Menu en grands boutons au-dessus de la page. |
| `tel-3-balades.png` | Distances et temps en pastilles ; source indiquée pour la plage ; « Données fictives » pour les deux autres. |
| `tel-4-infos.png`, `tel-8-hors-reseau-infos.png` | Infos pratiques ; la seconde prise **hors réseau**. |
| `tel-5-plan.png` | Emplacement d'image et bouton vers la maquette 3D. |
| `tel-6-code.png` | Pavé à gros chiffres, message « Code faux ». |
| `tel-7-aujourdhui-apres-publication.png` | L'événement publié (« pétanque géant » après modification) est dans le programme. |
| `tab-1-accueil-gerant.png` | 5 tuiles pour le gérant, rappel « pas de synchronisation ». |
| `tab-2-nouveau-bouton.png` | Réglage d'un bouton : couleurs, forme, police, taille, photo ; aperçu rond vert « Gaufre ». |
| `tab-3-caisse-apres-ventes.png` | Total 8,00 €, 3 ventes, message « + Gaufre 3,00 € ». |
| `tab-4-caisse-plus-options.png` | « Plus d'options » ouvert : annuler, tableau par catégorie, export, ajouter un bouton. |
| `tab-5-publier-evenement.png` | Formulaire et aperçu de l'affiche fabriquée avec la photo choisie. |
| `tab-6-aujourdhui-avec-nouvel-evenement.png` | 3 affiches du jour dont la nouvelle (texte visible sous un titre sur deux lignes). |
| `tab-7` à `tab-10` | Arrivées (gérant), accueil animateur (1 tuile), « Accès refusé » pour l'animateur, caisse du vendeur sans réglage des boutons. |
| `tab-11-codes-sauvegarde.png` | Codes modifiés (vendeur 5678), export / import. |

Dans les captures « page entière », les barres fixes (haut et bas) sont placées à leur position dans la page pour ne pas cacher le contenu ; sur l'appareil, elles restent fixes.

## Non vérifié
- Vrai téléphone et vraie tablette (Android, iPhone) : gestes, appareil photo (« Prendre une photo » a été testé avec un fichier, pas avec la caméra), installation réelle sur l'écran d'accueil. Chrome indique seulement « aucune erreur d'installabilité ».
- Safari / iPhone et Firefox : non vérifiés.
- Téléchargement réel des fichiers exportés (JSON et CSV) : non vérifié (l'import a été vérifié).
- Lecture par un lecteur d'écran : non vérifiée. Contrastes choisis pour être lisibles (texte foncé sur orange, jaune et bleu clair ; texte blanc sur bleu foncé, violet, rouge), non mesurés par un outil.
- Utilisation par un enfant de 10 ans : non testée avec un enfant.
- Fonctionnement une fois publié sur GitHub Pages : non vérifié au moment de l'écriture.

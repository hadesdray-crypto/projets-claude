# Contrôle des captures (1280×720, Chrome du poste d'exécution, rendu logiciel)

Les captures sont dans `captures/`. Pour chacune : ce qui a été regardé réellement.

| Capture | Constat | État |
|---|---|---|
| `1-vue-ensemble.png` | Sol bleu uni, bâtiments en blocs bleus, arbres verts translucides, routes claires, étiquettes camping et plage lisibles. Les blocs sont petits à cette échelle. | réussi |
| `2-gros-plan-camping.png` | Blocs translucides avec arêtes, hauteurs plausibles (maisons de 1 à 2 étages), arbres posés au sol, contour orange du camping, étiquettes « piscine », « accueil ». Étiquettes un peu serrées. | réussi |
| `3a-trajet-gros-plan.png` | Tracé orange le long des voies du camping, pion orange et jaune posé juste au-dessus du sol (hauteur mesurée 0,3 à 0,4 m), panneau avec distances, temps, voiture. | réussi |
| `3b-trajet-plage.png` | Le trajet descend par la route puis le chemin de dune jusqu'à la plage ; le dernier raccord (jaune) traverse du sable en ligne droite (128 m). Que le chemin de dune soit réellement praticable : non vérifié. | moyen |
| `4-editeur-bloc-deplace.png` | Le mobil-home d'exemple a été glissé à la souris de (195 ; 423) à (181 ; 412,5), pas de 0,5 m, puis tourné de −15° ; annuler et rétablir contrôlés (valeurs lues dans la page) ; sauvegarde locale présente. Le panneau couvre une partie de la vue. Essai tactile réel : non vérifié (souris seulement). | réussi (souris) |
| `5-photo-superposee.png` | Photo aérienne sous les blocs : les blocs coïncident avec les toits des maisons, décalage de 1 à 2 m visible sur certains (bascule des toits) ; la halle bleue de la piscine coïncide avec son bloc. Voir `precision.md`. | réussi |
| `6-mesure.png` | Deux points placés à 50 m l'un de l'autre : la page affiche « 50,0 m ». | réussi |

| `7-toits-et-numeros.png` | Toits à deux et quatre pans visibles sur l'accueil (3) et les bâtiments voisins, annexes et petits blocs plats, couleurs par usage (jaune commerces, violet mobil-home, gris annexes, bleu piscine), numéros lisibles au-dessus des éléments. Pentes réelles non vérifiées. | réussi |
| `8-obstacles.png` | Clôture et muret bruns, ronds-points sans crans après ajout de disques aux jonctions de routes. | réussi |
| `9-legende.png` | Légende avec les 15 couleurs, les numéros renvoient à la liste. | réussi |
| `10-liste-numerotee.png` | Liste numérotée (pastille de couleur, numéro, nom) ; la ligne 1 amène sur la piscine. | réussi |
| `11-fiche-mesures.png` | Touche sur l'accueil : « n° 3 · 15,2 m × 14,0 m · murs 3,7 m · faîte 7,9 m (quatre pans) » ; touche par un clic de souris, pas au doigt. | réussi (souris) |

## Correction n°1 (captures 390×800 « telephone » et 1024×768 « tablette »)
| Capture | Constat | État |
|---|---|---|
| `21-depart-*.png` | Au démarrage, le camping est centré et entier dans l'écran ; les cinq repères sont lisibles ; sur téléphone les cartouches sont serrés (Parking et Entrée proches) et le camping reste petit (577 m de distance). | tablette réussi, téléphone moyen |
| `22-photo-*.png` | Bouton « Photo / Maquette » actif : photo IGN nette sous des blocs très transparents, routes et zones boisées coloriées masquées. | réussi |
| `23-piscine-photo-*.png` | Voûte bleu clair de 5 m posée sur la halle vitrée de l'orthophoto ; léger décalage visible avec la halle (vue oblique ; valeur non mesurée, position à confirmer). | moyen |
| `24-piscine-maquette-*.png` | Voûte bleu clair, parking sable et pastille « 1 » ; contour du bloc de 1 m disparu. | réussi |
| `25-fiche-repere-*.png` | Toucher le repère Accueil : fiche « position à confirmer sur place ». | réussi |
| `26-reperes-caches-*.png` | Bouton « Repères » : repères cachés (contrôlé dans la page). | réussi |

Contrôles refaits avec `scripts/captures.js` : mesure 50,0 m, déplacement, rotation, annuler, rétablir, sauvegarde locale, trajet : sans erreur de page. Souris seulement, rendu logiciel.

Non vérifié : fonctionnement sur un vrai téléphone (fluidité, gestes), rendu sur carte graphique réelle, import d'un fichier JSON, export (téléchargement), fonctionnement dans d'autres navigateurs.

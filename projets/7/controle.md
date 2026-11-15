# Contrôle visuel (images extraites des GIF finaux et regardées en gros plan)

Images regardées : 12 de `amplitude-bras.gif` (0, 11, 22, 32, 43, 54, 65, 76, 87, 97, 108, 119), 8 de `joie-avant-apres.gif` (0, 13, 25, 38, 51, 64, 76, 89), 8 de `mange-avant-apres.gif` (0, 15, 31, 46, 61, 76, 92, 107), 8 images de `saisie` et `caresse` (`apercu/saisie-caresse-planche.png`). Planches : `apercu/*-planche.png`.
Ce qui est écrit ici vient de mes yeux ; les chiffres sont dans `mesures.json`.

## Constat image par image
- **Épaules rattachées au tronc** : oui sur toutes les images regardées. Chaque bras part d'une épaule placée sur le côté du torse (environ 25 px sous le menton), avec une manche. Sur certaines images de joie (25, 38) la tête, penchée, passe très près de l'épaule droite : la manche reste proche de la mâchoire.
- **Coudes** : propres, arrondis, un trait de pli à l'intérieur quand le coude est plié (images 32 à 87 de l'amplitude). Quand le coude est plié à 140° (image 76), les deux avant-bras se croisent devant le torse et le visage : lisible mais encombré (c'est un test extrême, les deux bras plient en même temps).
- **Épaisseur** : régulière à l'œil, bras environ 24 px (haut) et 22 px (avant-bras), comme le torse en proportion ; plus de tube fin.
- **Manche** : suit le haut du bras, bord bas déchiré. Elle est plus claire et plus plate que le gilet de Thomas (taches discrètes) : on la voit comme une pièce collée. Moyen.
- **Mains** : 4 formes lisibles sur `mains.png` (ouverte, relâchée, saisissante, fermée). En situation (joie, amplitude), la main ouverte est lisible ; poing et main saisissante sont plus brouillons (doigts serrés, traits noirs entre eux). Moyen.
- **Contours** : bords nets en pixels de 2 px, contour d'un texel de la même teinte que Thomas. Plus de bords crénelés flous. Les teintes de peau des bras sont un peu plus claires que celles du corps.
- **Fond reconstitué** : NON traité. Je n'ai pas repeint le torse (`calques/corps7.png` est une copie de `corps.png`). Sur les images regardées je n'ai vu aucun trou, car les manches couvrent l'épaule, mais ce n'est pas une reconstitution.
- **Deux yeux** : voir les listes dans les mesures de `fabriquer7.py` : les images où le détecteur ne compte pas 2 yeux sont les mêmes qu'avant (clignements) pour la joie ; pour `mange`, avant et après ont des listes proches (gant devant l'œil, clignements). Regardées à l'œil : image 5 de `mange` et les images de la joie, deux yeux. Les autres images listées : non vérifiées une par une.

## Les six défauts de la demande
1. Épaule droite sortant du cou : **corrigé** (vraie épaule sur le côté du torse), avec la réserve ci-dessus (tête proche sur quelques images).
2. Bras gauche tube fin, sans coude, étiré, raccord coupé : **corrigé** pour l'épaisseur, le coude et la longueur (os de 106 px constants, écart 0 % mesuré sur le squelette) ; raccord à l'épaule : **amélioré** (manche arrondie qui recouvre).
3. Mains : **amélioré** (formes plus grandes et distinctes), pas parfait.
4. Contours bruités : **amélioré** (pixels isolés autour des bras : 13,4 par image avant, 5,4 après, voir mesures). Pas à zéro : le détecteur compte aussi le décor et l'œil.
5. Épaisseur non conservée : **corrigé par construction** (rayons fixes). Mesure par masque : voir limites.
6. Fond derrière le bras : **inchangé** (non traité).

## Limites honnêtes
- Les bras sont dessinés par le code (rigides), pas déformés : pas de bosse de muscle.
- La mesure d'épaisseur par masque n'est pas fiable quand le bras touche l'autre bras ou lui-même (coude très plié) : valeurs aberrantes (40 px) dans `mesures.json`. Sur les poses non repliées : écart de 2 à 10 % sur l'avant-bras, et 6 à 20 % sur le haut du bras (la manche déchirée y entre parfois).
- La mesure de longueur apparente par masque n'est valable que bras peu plié (< 50°). Elle varie à cause des mains qui se recouvrent et des parties cachées : ne pas la lire comme la longueur de l'os (celle-ci est exacte : 106 px).
- Les mesures de trous aux jointures valent 0 avant et après (peu informatif) ; les traits sombres sur l'épaule : 3130 px avant (coupure visible) contre 0 après.
- Poses de `mange` et `saisie` : recalées par cinématique inverse pour que la main arrive au même endroit ; vérifié à l'œil sur quelques images seulement.

// Données de démonstration — TOUT EST FICTIF sauf ce qui est marqué « source ».
// Pour modifier les textes fixes (horaires, infos, balades, contact), changez ce fichier.
// Les événements et la caisse se modifient dans l'application (mode gérant).
window.DEMO = {
  // Lien du bouton « Réserver » : à renseigner (laisser vide tant qu'il n'est pas connu).
  lienReserver: '',
  contact: {
    texte: "Accueil du camping, aux heures d'ouverture.",
    telephone: '',   // à renseigner
    courriel: '',    // à renseigner
  },
  // Horaires affichés dans « Aujourd'hui » (fictifs, à vérifier).
  horaires: [
    { nom: 'Pain', quand: '8 h – 10 h', ou: "à l'accueil", fictif: true },
    { nom: 'Piscine couverte', quand: '10 h – 19 h', ou: 'ouverte du 1er avril au 30 septembre', fictif: true },
    { nom: 'Pizza', quand: '18 h – 21 h', ou: 'food-truck, mardi et vendredi', fictif: true },
  ],
  infos: [
    { titre: 'Piscine couverte', texte: 'Ouverte du 1er avril au 30 septembre. Horaires : 10 h – 19 h (fictif).' },
    { titre: 'Pain le matin', texte: "Pain et viennoiseries à l'accueil, 8 h – 10 h (fictif). Commande la veille (fictif)." },
    { titre: 'Pizza', texte: 'Food-truck pizza le mardi et le vendredi, 18 h – 21 h (fictif).' },
    { titre: 'Laverie', texte: 'Lave-linge et sèche-linge près des sanitaires (fictif). Jetons à l\'accueil (fictif).' },
    { titre: 'Wi-Fi', texte: "Wi-Fi payant. Tarifs et code à l'accueil (tarifs à renseigner)." },
  ],
  // Balades à pied. « source » : calculé, sinon fictif.
  balades: [
    { nom: 'La plage des Dunes', depart: 'Accueil', metres: 1562, minutes: 20,
      source: "Distance calculée sur la maquette 3D (projet 8, données IGN et OpenStreetMap), à 1,3 m/s. Chemin de dune non vérifié sur le terrain.",
      etapes: ["Sortir par l'accueil", 'Suivre la route puis le chemin de dune', 'Arrivée sur la plage'] },
    { nom: 'Les commerces', depart: 'Accueil', metres: 1200, minutes: 16, fictif: true,
      etapes: ['Exemple : boulangerie, épicerie, pharmacie', 'Distance et temps fictifs'] },
    { nom: 'Le tour du camping', depart: 'Accueil', metres: 800, minutes: 11, fictif: true,
      etapes: ['Exemple : piscine, aires de jeux, sanitaires', 'Distance et temps fictifs'] },
  ],
  // Événements de départ (dates : jours après aujourd'hui).
  evenements: [
    { jour: 0, heure: '21:00', type: 'Soirée', titre: 'Soirée guinguette', texte: 'Musique et lampions sur la place.', photo: 'images/demo-soiree.jpg' },
    { jour: 0, heure: '16:00', type: 'Spectacle', titre: 'Spectacle de magie', texte: 'Pour les enfants, devant la piscine.', photo: 'images/demo-spectacle.svg' },
    { jour: 1, heure: '18:30', type: 'Animation', titre: 'Pizza party', texte: 'Le food-truck vient au camping.', photo: 'images/demo-pizza.jpg' },
  ],
  // Boutons de caisse de départ.
  boutons: [
    { nom: 'Glace', prix: 2, categorie: 'Glaces', couleur: '#E6DB55', forme: 'arrondi', police: 'titres', taille: 'grand', affichage: 'texte' },
    { nom: 'Boisson', prix: 1.5, categorie: 'Boissons', couleur: '#789CF2', forme: 'arrondi', police: 'titres', taille: 'grand', affichage: 'texte' },
    { nom: 'Crêpe', prix: 2.5, categorie: 'Snack', couleur: '#FE8D4F', forme: 'rond', police: 'titres', taille: 'grand', affichage: 'texte' },
    { nom: 'Pizza', prix: 9, categorie: 'Snack', couleur: '#C02B0A', forme: 'carre', police: 'titres', taille: 'grand', affichage: 'photo-texte', photo: 'images/demo-pizza.jpg' },
  ],
  // Arrivées du jour : personnes fictives.
  arrivees: [
    { emplacement: 'MH 12', nom: 'Famille A (fictif)', personnes: 4, heure: '15:00' },
    { emplacement: 'T 3', nom: 'M. B (fictif)', personnes: 2, heure: '16:30' },
    { emplacement: 'MH 7', nom: 'Famille C (fictif)', personnes: 5, heure: '17:00' },
  ],
};

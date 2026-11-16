// Fonctionnement sans réseau : tous les fichiers de l'application sont mis en cache à l'installation.
// Changer VERSION à chaque mise à jour des fichiers.
const VERSION = 'camping10-v1';
const FICHIERS = [
  './', './index.html', './theme.css', './app.css', './app.js', './donnees-demo.js', './manifest.webmanifest',
  './polices/changa-one.woff2', './polices/open-sans.woff2',
  './icones/icone-192.png', './icones/icone-512.png',
  './images/demo-soiree.jpg', './images/demo-pizza.jpg', './images/demo-spectacle.svg', './images/emplacement-plan.svg',
];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(VERSION).then((c) => c.addAll(FICHIERS)).then(() => self.skipWaiting())); });
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((cles) => Promise.all(cles.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then((r) => r || fetch(e.request).catch(() =>
    e.request.mode === 'navigate' ? caches.match('./index.html') : Response.error())));
});

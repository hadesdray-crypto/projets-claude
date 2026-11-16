// Captures de la correction n°1 : vue de départ, vue photo, piscine de près, en 390×800 (téléphone) et 1024×768 (tablette).
// Usage : npm i puppeteer-core ; node scripts/captures_correction.js /usr/bin/chromium   (depuis projets/8)
const puppeteer = require('puppeteer-core');
const path = require('path'), P = process.cwd();
const att = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await puppeteer.launch({ executablePath: process.argv[2] || '/usr/bin/chromium', headless: 'new', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  for (const [nom, w, h] of [['telephone', 390, 800], ['tablette', 1024, 768]]) {
    const p = await b.newPage(); await p.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
    const err = []; p.on('pageerror', e => err.push(e.message)); p.on('console', m => { if (m.type() === 'error') err.push(m.text()); });
    const shot = (n) => p.screenshot({ path: path.join(P, 'captures', `${n}-${nom}.png`) });
    const M = (f, ...a) => p.evaluate(`(${f})(...${JSON.stringify(a)})`);
    await p.goto('file://' + P + '/index.html'); await att(3000);
    console.log(nom, 'caméra au départ :', await M(() => { const m = window.__maquette; return JSON.stringify({ dist: Math.round(m.camera.position.distanceTo(m.controls.target)), cible: [m.controls.target.x, -m.controls.target.z].map(Math.round), reperes: m.REPS.map(r => r.nom) }); }));
    console.log(nom, 'contour dans l\'écran :', await M(() => { const m = window.__maquette, c = window.DONNEES.camping, W = innerWidth, H = innerHeight; let ok = 0; for (const q of c) { const e = m.versEcran(q[0], q[1]); if (e[0] >= 0 && e[0] <= W && e[1] >= 0 && e[1] <= H) ok++; } return ok + '/' + c.length + ' sommets'; }));
    await shot('21-depart');
    await p.click('#bPhoto'); await att(3500); await shot('22-photo');
    await M(() => window.__maquette.vueSur(121, 462, 55, 0.9)); await att(900); await shot('23-piscine-photo');
    await p.click('#bPhoto'); await att(900); await shot('24-piscine-maquette');
    await M(() => window.__maquette.vueCamping()); await att(600);
    // fiche d'un repère au toucher
    const e = await M(() => { const m = window.__maquette, r = m.REPS.find(r => r.nom === 'Accueil'); return m.versEcran(r.x, r.y, r.haut + 2); });
    await p.mouse.click(e[0], e[1]); await att(400);
    console.log(nom, 'fiche du repère Accueil :', await p.$eval('#ficheTxt', x => x.textContent));
    await shot('25-fiche-repere'); await p.click('#bFermerFiche');
    await p.click('#bReperes'); await att(400); console.log(nom, 'repères cachés :', await M(() => !window.__maquette.calques.reperes.visible)); await shot('26-reperes-caches');
    await p.click('#bReperes'); await p.click('#bEnsemble'); await att(500); await p.click('#bCamping'); await att(600);
    console.log(nom, 'erreurs :', err.length ? err.join(' | ') : 'aucune');
    await p.close();
  }
  await b.close();
})();

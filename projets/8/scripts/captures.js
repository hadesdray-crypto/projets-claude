// Captures 1280x720 + contrôles de l'éditeur et de la mesure avec un vrai Chrome (pilotage par souris).
// Usage : npm i puppeteer-core ; node scripts/captures.js /usr/bin/chromium   (depuis projets/8)
const puppeteer = require('puppeteer-core');
const path = require('path'), P = process.cwd();
const att = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await puppeteer.launch({ executablePath: process.argv[2] || '/usr/bin/chromium', headless: 'new', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const p = await b.newPage(); await p.setViewport({ width: 1280, height: 720 });
  p.on('pageerror', e => console.log('ERREUR PAGE:', e.message));
  const shot = (n) => p.screenshot({ path: path.join(P, 'captures', n) });
  const M = (f, ...a) => p.evaluate(`(${f})(...${JSON.stringify(a)})`);
  await p.goto('file://' + P + '/index.html'); await att(2500);
  await shot('1-vue-ensemble.png');
  await p.click('#bCamping'); await att(1200); await shot('2-gros-plan-camping.png');
  // toits, couleurs, numéros (gros plan sur l'accueil et la piscine)
  await M(() => window.__maquette.vueSur(120, 450, 90, 0.55)); await att(900); await shot('7-toits-et-numeros.png');
  console.log('toits :', await M(() => { const t = {}; window.__maquette.blocs.forEach(b => t[b.toit] = (t[b.toit] || 0) + 1); return JSON.stringify(t); }));
  // obstacles (clôtures, murets, portails) à l'ouest du camping
  await M(() => window.__maquette.vueSur(-64, 405, 60, 0.6)); await att(800); await shot('8-obstacles.png');
  // légende
  await M(() => window.__maquette.vueCamping()); await p.click('#bLegende'); await att(500); await shot('9-legende.png'); await p.click('#bLegende');
  // liste numérotée : on touche la ligne 1 (piscine) puis un bloc au toucher (fiche des mesures)
  await p.click('#bListe'); await att(300); await shot('10-liste-numerotee.png');
  await p.click('#listeCorps .cliquable'); await att(900); await p.click('#bListe');
  console.log('fiche après la liste :', await p.$eval('#ficheTxt', e => e.textContent));
  await M(() => window.__maquette.vueSur(118, 434, 80, 0.7)); await att(700);
  const acc = await M(() => { const b = window.__maquette.blocs.find(b => b.type === 'accueil'); return window.__maquette.versEcran(b.x, b.y, b.h * 0.5); });
  await p.mouse.click(acc[0], acc[1]); await att(400);
  console.log('fiche au toucher sur l\'accueil :', await p.$eval('#ficheTxt', e => e.textContent));
  await shot('11-fiche-mesures.png'); await p.click('#bFermerFiche');
  // trajet : gros plan puis vue large avec le pion
  await p.click('#bTrajet'); await att(1500);
  await M(() => window.__maquette.setTPion(60)); await att(600); await shot('3a-trajet-gros-plan.png');
  await M(() => { window.__maquette.vueSur(-80, -150, 1250, 1.0); window.__maquette.setTPion(1560); }); await att(800); await shot('3b-trajet-plage.png');
  console.log('hauteur du pion (m, doit être > 0 et petit) :', await M(() => window.__maquette.pion.position.y));
  await p.click('#bTrajet');
  // photo aérienne superposée
  await p.click('#bCalques'); await p.click('#cal_photo'); await att(2500);
  await M(() => window.__maquette.vueSur(150, 440, 190, 1.35)); await p.click('#bCalques'); await att(1200); await shot('5-photo-superposee.png');
  await p.click('#bCalques'); await p.click('#cal_photo'); await p.click('#bCalques');
  // mesure : deux points connus à 50,0 m
  await M(() => window.__maquette.vueSur(150, 440, 140, 1.2)); await att(600);
  await p.click('#bMesure');
  const a = await M(() => window.__maquette.versEcran(120, 420)), c = await M(() => window.__maquette.versEcran(170, 420));
  await p.mouse.click(a[0], a[1]); await p.mouse.click(c[0], c[1]); await att(400);
  console.log('mesure affichée (attendu 50,0 m) :', await p.$eval('#mesureTxt', e => e.textContent));
  await shot('6-mesure.png'); await p.click('#bMesure');
  // édition : on déplace le mobil-home d'exemple
  await M(() => window.__maquette.vueSur(170, 430, 110, 1.1)); await att(600);
  await p.click('#bModifier'); await att(300);
  const g = (x) => M(() => { const b = window.__maquette.blocs.find(b => b.id === 'exemple-mobil-home'); return [b.x, b.y, b.rot, b.sx]; });
  const pos = await M(() => { const b = window.__maquette.blocs.find(b => b.id === 'exemple-mobil-home'); return window.__maquette.versEcran(b.x, b.y, 1.5); });
  const avant = await g();
  await p.mouse.move(pos[0], pos[1]); await p.mouse.down(); await p.mouse.move(pos[0] - 50, pos[1] + 40, { steps: 10 }); await p.mouse.move(pos[0] - 110, pos[1] + 80, { steps: 10 }); await p.mouse.up(); await att(400);
  await p.click('#bRotD'); await att(300);
  console.log('mobil-home avant', avant, 'après déplacement+rotation', await g());
  await shot('4-editeur-bloc-deplace.png');
  await p.click('#bAnnuler'); await att(200); console.log('après annuler (rotation défaite)', await g());
  await p.click('#bRetablir'); await att(200); console.log('après rétablir', await g());
  console.log('sauvegarde locale présente :', await M(() => !!localStorage.getItem('maquette8_blocs')));
  await b.close();
})();

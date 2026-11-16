// Test des parcours dans un Chrome sans écran + captures 390 px et 1024 px.
// Usage (depuis la racine du dépôt) :
//   python3 -m http.server 8710 &      (sert le dépôt : ../8 doit être joignable)
//   NODE_PATH=<dossier avec puppeteer-core>/node_modules node projets/10/scripts/tester.js
const puppeteer = require('puppeteer-core'), path = require('path');
const BASE = 'http://localhost:8710/projets/10/', DOSSIER = path.join(__dirname, '..');
const att = (ms) => new Promise((r) => setTimeout(r, ms));
const resultats = []; const note = (nom, ok, detail = '') => { resultats.push({ nom, ok, detail }); console.log((ok ? 'RÉUSSI ' : 'ÉCHEC  ') + nom + (detail ? ' — ' + detail : '')); };

(async () => {
  const b = await puppeteer.launch({ executablePath: process.env.CHROME || '/usr/bin/chromium', headless: 'new', args: ['--no-sandbox', '--lang=fr-FR'], env: Object.assign({}, process.env, { LANG: 'fr_FR.UTF-8' }) });
  const p = await b.newPage();
  const erreurs = []; p.on('pageerror', (e) => erreurs.push(e.message)); p.on('console', (m) => { if (m.type() === 'error') erreurs.push(m.text()); });
  p.on('dialog', (d) => d.accept());
  const tel = { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true };
  const tab = { width: 1024, height: 768, deviceScaleFactor: 1, isMobile: false, hasTouch: true };
  // page entière : les barres fixes sont posées à leur place dans le document (sinon elles apparaissent au milieu)
  const shot = async (n, plein = false) => { if (plein) await p.addStyleTag({ content: '.entete,.barre-basse{position:static!important}' }); await att(500); await p.screenshot({ path: path.join(DOSSIER, 'captures', n), fullPage: plein }); if (plein) await p.evaluate(() => document.querySelectorAll('style').forEach((x) => x.textContent.includes('position:static!important') && x.remove())); };
  const aller = async (h) => { await p.evaluate((h) => { location.hash = h; }, h); await att(400); };
  // on centre l'élément avant d'appuyer (la barre basse fixe ne doit pas le cacher)
  const appuyer = async (s) => { await p.$eval(s, (e) => e.scrollIntoView({ block: 'center' })); await att(100); await p.click(s); };
  const remplir = async (s, v) => { await p.$eval(s, (e) => { e.value = ''; e.focus(); }); await p.type(s, v); };
  const texte = (s) => p.$eval(s, (e) => e.textContent.trim());
  const connexion = async (role, code = '1234') => {
    await aller('#gerant'); await p.evaluate(() => sessionStorage.removeItem('camping10_role')); await aller('#aujourdhui'); await aller('#gerant');
    await p.click(`.role[data-role="${role}"]`); await att(200);
    for (const c of code) await p.click(`.touche[data-t="${c}"]`);
    await att(400);
  };

  // ---- téléphone, côté campeurs ----
  await p.setViewport(tel);
  await p.goto(BASE + 'index.html', { waitUntil: 'networkidle0' }); await p.evaluate(() => localStorage.clear()); await p.reload({ waitUntil: 'networkidle0' });
  await att(800);
  note('Polices du thème chargées', await p.evaluate(() => document.fonts.check('20px "Changa One"') && document.fonts.check('16px "Open Sans"')));
  note("Aujourd'hui : affiches du jour dessinées", (await p.$$('#affiches-jour canvas')).length === 2);
  await shot('tel-1-aujourdhui.png'); await shot('tel-1b-aujourdhui-page-entiere.png', true);
  await p.click('#bouton-menu'); await shot('tel-2-menu.png'); await p.click('#fermer-menu');
  await aller('#balades'); await shot('tel-3-balades.png', true);
  await aller('#infos'); await shot('tel-4-infos.png', true);
  await aller('#plan'); await shot('tel-5-plan.png');
  note('Lien du plan vers ../8/', (await p.$eval('#ecran a.bouton', (a) => a.href)) === new URL('../8/index.html', BASE).href);
  const p8 = await b.newPage(); const r8 = await p8.goto(new URL('../8/index.html', BASE).href, { waitUntil: 'domcontentloaded' }); note('La maquette ../8/ répond', r8.status() === 200, 'code ' + r8.status()); await p8.close(); await p.bringToFront();

  // ---- code faux ----
  await aller('#gerant'); await p.click('.role[data-role="gerant"]'); for (const c of '9999') await p.click(`.touche[data-t="${c}"]`); await att(200);
  note('Code faux refusé', (await texte('#code-erreur')).includes('faux'));
  await shot('tel-6-code.png');

  // ---- tablette : caisse ----
  await p.setViewport(tab);
  await connexion('gerant');
  await shot('tab-1-accueil-gerant.png');
  await aller('#gerant/caisse');
  const totalAvant = await texte('#total');
  await appuyer('details.plus summary'); await att(200); await appuyer('#ajout-bouton'); await att(400);
  await remplir('#b-nom', 'Gaufre');
  await remplir('#b-prix', '3');
  await remplir('#b-cat', 'Snack');
  await p.click('.pastille-couleur[style*="#2f9e44"]'); await p.click('input[name="forme"][value="rond"] + span'); await p.click('input[name="taille"][value="tres-grand"] + span');
  await shot('tab-2-nouveau-bouton.png');
  await appuyer('#b-enregistrer'); await att(500);
  const boutons = await p.$$eval('.bouton-caisse', (l) => l.map((e) => e.getAttribute('aria-label')));
  note('Bouton « Gaufre » créé', boutons.some((x) => x.startsWith('Gaufre')), boutons.join(' | '));
  const cliquer = async (nom) => { const els = await p.$$('.bouton-caisse'); for (const e of els) if ((await e.evaluate((x) => x.getAttribute('aria-label'))).startsWith(nom)) { await e.click(); await att(150); return; } };
  await cliquer('Gaufre'); await cliquer('Glace'); await cliquer('Gaufre');
  const total = await texte('#total');
  note('Trois ventes : total du jour 8,00 €', total.replace(/\s/g, ' ') === '8,00 €', 'avant ' + totalAvant + ', après ' + total + ', ' + (await texte('#nb-ventes')));
  await shot('tab-3-caisse-apres-ventes.png');
  await appuyer('details.plus summary'); await att(200); await appuyer('#annuler-vente'); await att(300);
  note('Annuler la dernière vente : 5,00 €', (await texte('#total')).replace(/\s/g, ' ') === '5,00 €', await texte('#total'));
  await shot('tab-4-caisse-plus-options.png', true);
  // régler un bouton existant (Glace : 2 € -> 2,50 €)
  await p.$eval('#mode-reglage', (e) => { e.checked = true; e.dispatchEvent(new Event('change')); }); await att(200);
  await appuyer('.case-caisse .regler'); await att(400);
  await remplir('#b-prix', '2.5'); await appuyer('#b-enregistrer'); await att(400);
  { const lab = await p.$eval('.bouton-caisse', (e) => e.getAttribute('aria-label')), tt = await texte('#total'); note('Régler un bouton existant (prix de la glace)', lab.replace(/\s/g, ' ') === 'Glace, 2,50 €' && tt.replace(/\s/g, ' ') === '5,00 €', lab + ' / ' + tt + ' / ' + p.url()); }
  await p.reload({ waitUntil: 'networkidle0' }); await att(400);
  note('Ventes conservées après rechargement', (await texte('#total')).replace(/\s/g, ' ') === '5,00 €');

  // ---- publier un événement ----
  await aller('#gerant/evenements');
  const fichier = await p.$('#ev-photo'); await fichier.uploadFile(path.join(DOSSIER, 'images/demo-soiree.jpg')); await att(800);
  await remplir('#ev-titre', 'Concours de pétanque');
  await p.select('#ev-type', 'Animation');
  await p.$eval('#ev-heure', (e) => { e.value = '15:00'; e.dispatchEvent(new Event('input', { bubbles: true })); });
  await p.type('#ev-texte', 'Équipes de deux, inscription sur place.');
  await att(600); await shot('tab-5-publier-evenement.png');
  await appuyer('#publier'); await att(500);
  note('Message « Publié »', (await texte('#ev-message')).startsWith('Publié'));
  const photoGardee = await p.evaluate(() => JSON.parse(localStorage.getItem('camping10')).evenements.find((e) => e.titre === 'Concours de pétanque').photo.slice(0, 23));
  note('Photo réduite et enregistrée', photoGardee === 'data:image/jpeg;base64,', photoGardee);
  await aller('#aujourdhui'); await att(800);
  const prog = await texte('.programme');
  note("Événement visible côté campeurs (programme d'aujourd'hui)", prog.includes('Concours de pétanque'), prog.replace(/\s+/g, ' '));
  note('Affiche ajoutée (3 affiches du jour)', (await p.$$('#affiches-jour canvas')).length === 3);
  await shot('tab-6-aujourdhui-avec-nouvel-evenement.png', true);
  // modifier
  await aller('#gerant/evenements'); const ids = await p.$$eval('.modif', (l) => l.map((e) => e.dataset.id));
  const idPet = await p.evaluate(() => JSON.parse(localStorage.getItem('camping10')).evenements.find((e) => e.titre === 'Concours de pétanque').id);
  await p.click(`.modif[data-id="${idPet}"]`); await att(500);
  await remplir('#ev-titre', 'Concours de pétanque géant'); await appuyer('#publier'); await att(500);
  await aller('#aujourdhui'); note('Événement modifiable', (await texte('.programme')).includes('pétanque géant'));
  await p.setViewport(tel); await aller('#aujourdhui'); await att(800); await shot('tel-7-aujourdhui-apres-publication.png');
  await p.setViewport(tab);

  // ---- rôles ----
  const tuiles = async () => p.$$eval('.tuile', (l) => l.map((e) => e.dataset.droit));
  await connexion('gerant'); note('Gérant : 5 accès', (await tuiles()).join(',') === 'evenements,caisse,arrivees,plan,reglages', (await tuiles()).join(','));
  await aller('#gerant/arrivees'); note('Gérant voit les arrivées', !!(await p.$('#table-arrivees'))); await shot('tab-7-arrivees-gerant.png');
  await connexion('animateur'); note('Animateur : événements seulement', (await tuiles()).join(',') === 'evenements', (await tuiles()).join(','));
  await shot('tab-8-accueil-animateur.png');
  await aller('#gerant/arrivees'); note('Animateur : arrivées refusées', !(await p.$('#table-arrivees')) && (await texte('h1')) === 'Accès refusé');
  await shot('tab-9-animateur-arrivees-refusees.png');
  await aller('#gerant/caisse'); note('Animateur : caisse refusée', !(await p.$('#grille')));
  await connexion('vendeur'); note('Vendeur : caisse seulement', (await tuiles()).join(',') === 'caisse', (await tuiles()).join(','));
  await aller('#gerant/caisse'); await appuyer('details.plus summary'); await att(200);
  note('Vendeur : pas de réglage des boutons', !(await p.$('#ajout-bouton')) && !!(await p.$('#annuler-vente')));
  await shot('tab-10-caisse-vendeur.png');
  await aller('#gerant/bouton/nouveau'); note('Vendeur : création de bouton refusée', (await texte('h1')) === 'Accès refusé');
  await aller('#gerant/arrivees'); note('Vendeur : arrivées refusées', !(await p.$('#table-arrivees')));
  await connexion('reception'); note('Réception : événements, caisse, arrivées, plan', (await tuiles()).join(',') === 'evenements,caisse,arrivees,plan', (await tuiles()).join(','));
  await aller('#gerant/reglages'); note('Réception : codes refusés', (await texte('h1')) === 'Accès refusé');
  // changer un code
  await connexion('gerant'); await aller('#gerant/reglages');
  await remplir('#code-vendeur', '5678'); await appuyer('#form-codes button'); await att(300);
  await shot('tab-11-codes-sauvegarde.png', true);
  await connexion('vendeur', '1234'); note('Ancien code vendeur refusé', (await texte('#code-erreur')).includes('faux'));
  await connexion('vendeur', '5678'); note('Nouveau code vendeur accepté', (await tuiles()).join(',') === 'caisse');

  // ---- export / import (format) ----
  const exporte = await p.evaluate(() => localStorage.getItem('camping10'));
  await connexion('gerant'); await aller('#gerant/reglages');
  const fs = require('fs'), tmp = path.join(require('os').tmpdir(), 'camping-export.json'); fs.writeFileSync(tmp, exporte);
  await p.evaluate(() => { const e = JSON.parse(localStorage.getItem('camping10')); e.ventes = []; localStorage.setItem('camping10', JSON.stringify(e)); });
  await (await p.$('#importer')).uploadFile(tmp); await att(600);
  note('Import JSON : ventes restaurées', (await texte('#import-ok')) === 'Import terminé.' && (await p.evaluate(() => JSON.parse(localStorage.getItem('camping10')).ventes.length)) === 2);

  // ---- installation et hors réseau ----
  await p.goto(BASE + 'index.html', { waitUntil: 'networkidle0' });
  await p.evaluate(() => navigator.serviceWorker.ready); await p.reload({ waitUntil: 'networkidle0' }); await att(500);
  note('Service worker actif et contrôlant la page', await p.evaluate(() => !!navigator.serviceWorker.controller));
  const cdp = await p.createCDPSession();
  const inst = await cdp.send('Page.getInstallabilityErrors');
  note("Chrome : aucune erreur d'installabilité", inst.installabilityErrors.length === 0, JSON.stringify(inst.installabilityErrors));
  await p.setOfflineMode(true);
  await p.reload({ waitUntil: 'load' }); await att(1200);
  note('Hors réseau : la page se recharge avec ses affiches', (await p.$$('#affiches-jour canvas')).length === 3);
  note('Hors réseau : polices disponibles', await p.evaluate(() => document.fonts.check('20px "Changa One"')));
  const p2 = await b.newPage(); await p2.setOfflineMode(true);
  try { await p2.goto(BASE, { waitUntil: 'load' }); await att(800); note('Hors réseau : nouvel onglet sur ./', (await p2.$$('#ecran h1')).length === 1); } catch (e) { note('Hors réseau : nouvel onglet sur ./', false, e.message); }
  await p.setViewport(tel); await aller('#infos'); await shot('tel-8-hors-reseau-infos.png');
  await p.setOfflineMode(false);

  note('Aucune erreur JavaScript', erreurs.length === 0, erreurs.join(' | '));
  fs.writeFileSync(path.join(DOSSIER, 'resultats-tests.json'), JSON.stringify(resultats, null, 1));
  console.log(resultats.filter((r) => r.ok).length + ' / ' + resultats.length + ' réussis');
  await b.close();
})();

// Application du camping — campeurs (téléphone) et mode gérant (tablette).
// Tout est stocké sur l'appareil (localStorage). Pas de serveur, pas de synchronisation.
(function () {
  'use strict';
  const CLE = 'camping10';
  const ROLES = {
    gerant: 'Gérant', reception: 'Réception', animateur: 'Animateur', vendeur: 'Vendeur',
  };
  // Autorisations de chaque rôle
  const DROITS = {
    gerant:    { evenements: true,  caisse: true,  boutons: true,  arrivees: true,  plan: true,  reglages: true },
    reception: { evenements: true,  caisse: true,  boutons: false, arrivees: true,  plan: true,  reglages: false },
    animateur: { evenements: true,  caisse: false, boutons: false, arrivees: false, plan: false, reglages: false },
    vendeur:   { evenements: false, caisse: true,  boutons: false, arrivees: false, plan: false, reglages: false },
  };
  const TYPES = ['Soirée', 'Spectacle', 'Animation', 'Intervenant'];
  const COULEURS = ['#789CF2', '#1d3f9e', '#FE8D4F', '#E6E6E6', '#C02B0A', '#3D2F81', '#607382', '#E6DB55', '#2f9e44', '#ffffff'];
  const PLAN = '../8/index.html';

  // ---------- outils ----------
  const $ = (s, r = document) => r.querySelector(s);
  const echap = (t) => String(t ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const deux = (n) => String(n).padStart(2, '0');
  const dateLocale = (d) => d.getFullYear() + '-' + deux(d.getMonth() + 1) + '-' + deux(d.getDate());
  const aujourdhui = () => dateLocale(new Date());
  const euros = (n) => (Math.round(n * 100) / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  const id = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  const JOURS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
  const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  const dateLongue = (iso) => { const [a, m, j] = iso.split('-').map(Number); const d = new Date(a, m - 1, j); return JOURS[d.getDay()] + ' ' + j + ' ' + MOIS[m - 1]; };
  const heureTexte = (h) => h ? h.replace(':', ' h ').replace(/ h 00$/, ' h') : '';
  const couleurTexte = (hex) => {
    const n = parseInt(hex.slice(1), 16), c = [n >> 16, (n >> 8) & 255, n & 255].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    const L = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    return (L + 0.05) / 0.05 > 1.05 / (L + 0.05) ? '#1c1c28' : '#ffffff';
  };

  // ---------- données ----------
  function etatDeDepart() {
    const D = window.DEMO, auj = new Date();
    return {
      version: 1,
      codes: { gerant: '1234', reception: '1234', animateur: '1234', vendeur: '1234' },
      evenements: D.evenements.map((e) => {
        const d = new Date(auj); d.setDate(d.getDate() + e.jour);
        return { id: id(), titre: e.titre, texte: e.texte, type: e.type, date: dateLocale(d), heure: e.heure, photo: e.photo };
      }),
      boutons: D.boutons.map((b) => Object.assign({ id: id() }, b)),
      ventes: [],
      arrivees: D.arrivees.map((a) => Object.assign({ date: dateLocale(auj) }, a)),
    };
  }
  let etat;
  try { etat = JSON.parse(localStorage.getItem(CLE)); } catch (e) { etat = null; }
  if (!etat || etat.version !== 1) etat = etatDeDepart();
  function enregistrer() {
    try { localStorage.setItem(CLE, JSON.stringify(etat)); return true; }
    catch (e) { alert("Mémoire de l'appareil pleine : la dernière modification n'est pas enregistrée. Utilisez des photos plus petites ou supprimez d'anciens événements."); return false; }
  }
  enregistrer();

  const role = () => sessionStorage.getItem('camping10_role');
  const peut = (droit) => !!(role() && DROITS[role()][droit]);

  // ---------- images ----------
  function chargerImage(src) {
    return new Promise((ok) => { if (!src) return ok(null); const i = new Image(); i.onload = () => ok(i); i.onerror = () => ok(null); i.src = src; });
  }
  // Photo choisie -> JPEG réduit (900 px max) pour tenir dans la mémoire de l'appareil
  function reduirePhoto(fichier) {
    return new Promise((ok, ko) => {
      const lecteur = new FileReader();
      lecteur.onload = async () => {
        const img = await chargerImage(lecteur.result);
        if (!img) return ko(new Error('image illisible'));
        const k = Math.min(1, 900 / Math.max(img.width, img.height));
        const c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
        c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
        ok(c.toDataURL('image/jpeg', 0.8));
      };
      lecteur.onerror = ko; lecteur.readAsDataURL(fichier);
    });
  }

  // ---------- affiche automatique (canvas) ----------
  function lignes(ctx, texte, largeur) {
    const mots = String(texte || '').split(/\s+/).filter(Boolean), res = []; let l = '';
    for (const m of mots) { const t = l ? l + ' ' + m : m; if (ctx.measureText(t).width > largeur && l) { res.push(l); l = m; } else l = t; }
    if (l) res.push(l); return res;
  }
  function arrondi(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  async function dessinerAffiche(canvas, ev) {
    const W = 720, H = 1020; canvas.width = W; canvas.height = H;
    try { await Promise.all([document.fonts.load('60px "Changa One"'), document.fonts.load('28px "Open Sans"'), document.fonts.load('bold 28px "Open Sans"')]); } catch (e) { /* polices de secours */ }
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#3D2F81'; ctx.fillRect(0, 0, W, H);
    // photo (recadrée pour remplir le cadre)
    const img = await chargerImage(ev.photo);
    const px = 30, py = 30, pw = W - 60, ph = 480;
    ctx.save(); arrondi(ctx, px, py, pw, ph, 28); ctx.clip();
    if (img) {
      const k = Math.max(pw / img.width, ph / img.height), w = img.width * k, h = img.height * k;
      ctx.drawImage(img, px + (pw - w) / 2, py + (ph - h) / 2, w, h);
    } else {
      ctx.fillStyle = '#789CF2'; ctx.fillRect(px, py, pw, ph);
      ctx.fillStyle = '#1d3f9e'; ctx.font = '40px "Changa One", sans-serif'; ctx.textAlign = 'center'; ctx.fillText('Photo', W / 2, py + ph / 2); ctx.textAlign = 'left';
    }
    ctx.restore();
    // étiquette du type
    ctx.font = '34px "Changa One", sans-serif';
    const tt = (ev.type || 'Animation').toUpperCase(), tw = ctx.measureText(tt).width + 44;
    ctx.fillStyle = '#FE8D4F'; arrondi(ctx, 50, py + ph - 34, tw, 64, 32); ctx.fill();
    ctx.fillStyle = '#3D2F81'; ctx.fillText(tt, 72, py + ph + 10);
    // titre
    let y = py + ph + 100;
    ctx.fillStyle = '#ffffff'; let taille = 64; ctx.font = taille + 'px "Changa One", sans-serif';
    let tl = lignes(ctx, ev.titre || 'Titre', W - 100);
    if (tl.length > 2) { taille = 50; ctx.font = taille + 'px "Changa One", sans-serif'; tl = lignes(ctx, ev.titre, W - 100); }
    tl.slice(0, 3).forEach((l) => { ctx.fillText(l, 50, y); y += taille * 1.05; });
    // date et heure
    ctx.fillStyle = '#E6DB55'; ctx.font = '42px "Changa One", sans-serif';
    const dh = (ev.date ? dateLongue(ev.date) : '') + (ev.heure ? ' · ' + heureTexte(ev.heure) : '');
    ctx.fillText(dh.charAt(0).toUpperCase() + dh.slice(1), 50, y + 10); y += 66;
    // texte
    ctx.fillStyle = '#ffffff'; ctx.font = '30px "Open Sans", sans-serif';
    lignes(ctx, ev.texte, W - 100).slice(0, Math.max(0, Math.floor((H - 90 - y) / 40))).forEach((l) => { ctx.fillText(l, 50, y); y += 40; });
    // bandeau bas
    ctx.fillStyle = '#FE8D4F'; ctx.fillRect(0, H - 70, W, 70);
    ctx.fillStyle = '#3D2F81'; ctx.font = '32px "Changa One", sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('Camping Amitié & Nature', W / 2, H - 24); ctx.textAlign = 'left';
  }
  function canvasAffiche(ev) {
    const c = document.createElement('canvas'); c.className = 'affiche'; c.setAttribute('role', 'img');
    c.setAttribute('aria-label', (ev.type || '') + ' : ' + ev.titre + ', ' + dateLongue(ev.date) + ' ' + heureTexte(ev.heure) + '. ' + (ev.texte || ''));
    dessinerAffiche(c, ev); return c;
  }

  // ---------- écrans campeurs ----------
  const ecran = $('#ecran');
  function page(html) { ecran.innerHTML = html; ecran.focus({ preventScroll: true }); window.scrollTo(0, 0); }

  function ecranAujourdhui() {
    const auj = aujourdhui();
    const tri = (a, b) => (a.date + a.heure).localeCompare(b.date + b.heure);
    const duJour = etat.evenements.filter((e) => e.date === auj).sort(tri);
    const aVenir = etat.evenements.filter((e) => e.date > auj).sort(tri).slice(0, 6);
    const h = window.DEMO.horaires;
    page(`
      <h1>Aujourd'hui</h1>
      <p class="date-du-jour">${echap(dateLongue(auj))}</p>
      <div class="horaires">${h.map((x) => `<div class="carte horaire"><h3>${echap(x.nom)}</h3><p class="grand">${echap(x.quand)}</p><p>${echap(x.ou)}${x.fictif ? ' <span class="fictif">fictif</span>' : ''}</p></div>`).join('')}</div>
      <h2>Programme</h2>
      ${duJour.length ? `<ol class="programme carte">${duJour.map((e) => `<li><b>${echap(heureTexte(e.heure))}</b> ${echap(e.titre)} <span class="type">${echap(e.type)}</span></li>`).join('')}</ol>` : '<p class="carte">Rien de prévu aujourd\'hui.</p>'}
      <div class="affiches" id="affiches-jour"></div>
      ${aVenir.length ? '<h2>Les prochains jours</h2><div class="affiches petites" id="affiches-avenir"></div>' : ''}
    `);
    duJour.forEach((e) => $('#affiches-jour').appendChild(canvasAffiche(e)));
    aVenir.forEach((e) => $('#affiches-avenir').appendChild(canvasAffiche(e)));
  }

  function ecranPlan() {
    page(`<h1>Plan</h1>
      <div class="carte"><img class="emplacement-image" src="images/emplacement-plan.svg" alt="">
      <p>Le plan du camping en 3D : bâtiments, piscine, chemin de la plage.</p>
      <a class="bouton large" href="${PLAN}">Ouvrir le plan 3D</a>
      <p class="petit">Le plan 3D demande une connexion internet.</p></div>`);
  }

  function ecranBalades() {
    page(`<h1>Balades</h1><p>À pied, depuis le camping.</p>
      ${window.DEMO.balades.map((b) => `<div class="carte balade">
        <h2>${echap(b.nom)}</h2>
        <p class="chiffres"><span>${(b.metres / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} km</span><span>${b.minutes} min</span></p>
        <p>Départ : ${echap(b.depart)}</p>
        <ul>${b.etapes.map((t) => `<li>${echap(t)}</li>`).join('')}</ul>
        ${b.fictif ? '<p class="fictif">Données fictives (exemple), non vérifiées.</p>' : `<p class="petit">${echap(b.source)}</p>`}
        <a class="bouton clair" href="${PLAN}">Voir sur le plan</a>
      </div>`).join('')}`);
  }

  function blocContact() {
    const c = window.DEMO.contact;
    return `<p>${echap(c.texte)}</p>
      ${c.telephone ? `<a class="bouton large" href="tel:${echap(c.telephone)}">Appeler</a>` : '<p class="petit">Téléphone : à renseigner.</p>'}
      ${c.courriel ? `<a class="bouton large clair" href="mailto:${echap(c.courriel)}">Écrire</a>` : '<p class="petit">Courriel : à renseigner.</p>'}`;
  }
  function ecranInfos() {
    page(`<h1>Infos pratiques</h1>
      ${window.DEMO.infos.map((i) => `<div class="carte"><h2>${echap(i.titre)}</h2><p>${echap(i.texte).replace(/\(fictif\)/g, '<span class="fictif">fictif</span>')}</p></div>`).join('')}
      <div class="carte"><h2>Contact</h2>${blocContact()}</div>`);
  }
  function ecranContact() { page(`<h1>Contact</h1><div class="carte">${blocContact()}</div>`); }
  function ecranReserver() {
    const l = window.DEMO.lienReserver;
    page(`<h1>Réserver</h1><div class="carte">${l ? `<a class="bouton large orange" href="${echap(l)}">Réserver un séjour</a>` : "<p>Réservation à l'accueil du camping.</p><p class=\"petit\">Lien de réservation en ligne : à renseigner.</p>"}</div>`);
  }

  // ---------- mode gérant ----------
  function ecranConnexion() {
    page(`<h1>Mode gérant</h1><p>Qui êtes-vous ?</p>
      <div class="grille-roles">${Object.keys(ROLES).map((r) => `<button class="bouton violet role" data-role="${r}">${ROLES[r]}</button>`).join('')}</div>`);
    ecran.querySelectorAll('.role').forEach((b) => b.onclick = () => ecranCode(b.dataset.role));
  }
  function ecranCode(r) {
    let saisie = '';
    page(`<h1>${ROLES[r]}</h1><p>Tapez le code.</p>
      <div class="code-affiche" aria-live="polite" id="code-points">○ ○ ○ ○</div>
      <p class="erreur" id="code-erreur" role="alert"></p>
      <div class="pave">${[1, 2, 3, 4, 5, 6, 7, 8, 9, '', 0, '⌫'].map((t) => t === '' ? '<span></span>' : `<button class="bouton clair touche" data-t="${t}" aria-label="${t === '⌫' ? 'Effacer' : t}">${t}</button>`).join('')}</div>
      <button class="bouton clair large" id="retour-roles">Retour</button>`);
    const maj = () => { $('#code-points').textContent = [0, 1, 2, 3].map((i) => i < saisie.length ? '●' : '○').join(' '); };
    ecran.querySelectorAll('.touche').forEach((b) => b.onclick = () => {
      if (b.dataset.t === '⌫') saisie = saisie.slice(0, -1); else if (saisie.length < 4) saisie += b.dataset.t;
      maj();
      if (saisie.length === 4) {
        if (saisie === etat.codes[r]) { sessionStorage.setItem('camping10_role', r); location.hash = '#gerant'; afficher(); }
        else { $('#code-erreur').textContent = 'Code faux. Recommencez.'; saisie = ''; setTimeout(maj, 300); }
      }
    });
    $('#retour-roles').onclick = ecranConnexion;
  }

  function barreGerant(titre) {
    return `<div class="barre-gerant"><span class="pastille">${ROLES[role()]}</span><a class="bouton clair" href="#gerant">Accueil gérant</a><button class="bouton clair" id="quitter">Changer de rôle</button></div><h1>${titre}</h1>`;
  }
  function brancherQuitter() { const q = $('#quitter'); if (q) q.onclick = () => { sessionStorage.removeItem('camping10_role'); location.hash = '#gerant'; afficher(); }; }
  function refus() { page(barreGerant('Accès refusé') + `<p class="carte">Le rôle ${ROLES[role()]} n'a pas accès à cette page.</p>`); brancherQuitter(); }

  function ecranGerantAccueil() {
    const tuiles = [
      ['evenements', '#gerant/evenements', 'Publier un événement', 'orange'],
      ['caisse', '#gerant/caisse', 'Caisse', ''],
      ['arrivees', '#gerant/arrivees', 'Arrivées du jour', 'violet'],
      ['plan', '#gerant/plan', 'Plan (modifier)', ''],
      ['reglages', '#gerant/reglages', 'Codes et sauvegarde', 'clair'],
    ].filter((t) => peut(t[0]));
    page(barreGerant('Mode gérant') + `<div class="tuiles">${tuiles.map((t) => `<a class="bouton tuile ${t[3]}" href="${t[1]}" data-droit="${t[0]}">${t[2]}</a>`).join('')}</div>
      <p class="petit carte">Les données restent sur cet appareil. Pas de synchronisation entre appareils pour l'instant : utilisez Exporter / Importer.</p>`);
    brancherQuitter();
  }

  // --- événements ---
  function ecranEvenements(idModif) {
    if (!peut('evenements')) return refus();
    const ev = idModif ? Object.assign({}, etat.evenements.find((e) => e.id === idModif)) : { titre: '', texte: '', type: 'Soirée', date: aujourdhui(), heure: '21:00', photo: '' };
    const liste = etat.evenements.slice().sort((a, b) => (a.date + a.heure).localeCompare(b.date + b.heure));
    page(barreGerant(idModif ? "Modifier l'événement" : 'Publier un événement') + `
      <div class="deux-colonnes">
        <form class="carte" id="form-ev">
          <div class="rangee"><label class="bouton orange fichier">Prendre une photo<input type="file" accept="image/*" capture="environment" id="ev-photo-cam"></label>
          <label class="bouton clair fichier">Choisir une photo<input type="file" accept="image/*" id="ev-photo"></label></div>
          <label for="ev-titre">Titre</label><input id="ev-titre" required maxlength="60" value="${echap(ev.titre)}">
          <label for="ev-type">Genre</label><select id="ev-type">${TYPES.map((t) => `<option ${t === ev.type ? 'selected' : ''}>${t}</option>`).join('')}</select>
          <div class="rangee"><div><label for="ev-date">Date</label><input type="date" id="ev-date" required value="${ev.date}"></div>
          <div><label for="ev-heure">Heure</label><input type="time" id="ev-heure" value="${ev.heure}"></div></div>
          <label for="ev-texte">Texte</label><textarea id="ev-texte" maxlength="200">${echap(ev.texte)}</textarea>
          <button class="bouton large orange" id="publier" type="submit">${idModif ? 'Enregistrer' : 'Publier'}</button>
          ${idModif ? '<a class="bouton large clair" href="#gerant/evenements">Annuler</a>' : ''}
          <p class="ok" id="ev-message" role="status"></p>
        </form>
        <div><h2>Aperçu de l'affiche</h2><canvas class="affiche" id="apercu"></canvas></div>
      </div>
      <h2>Événements publiés</h2>
      <div class="liste-ev">${liste.map((e) => `<div class="carte ligne-ev"><div><b>${echap(e.titre)}</b><br>${echap(dateLongue(e.date))} · ${echap(heureTexte(e.heure))} · ${echap(e.type)}</div>
        <div class="rangee"><button class="bouton clair modif" data-id="${e.id}">Modifier</button><button class="bouton rouge suppr" data-id="${e.id}">Supprimer</button></div></div>`).join('') || '<p>Aucun.</p>'}</div>`);
    brancherQuitter();
    const lire = () => { ev.titre = $('#ev-titre').value.trim(); ev.type = $('#ev-type').value; ev.date = $('#ev-date').value; ev.heure = $('#ev-heure').value; ev.texte = $('#ev-texte').value.trim(); };
    const apercu = () => { lire(); dessinerAffiche($('#apercu'), ev); };
    ['#ev-titre', '#ev-type', '#ev-date', '#ev-heure', '#ev-texte'].forEach((s) => $(s).addEventListener('input', apercu));
    const surPhoto = async (inp) => { if (!inp.files[0]) return; try { ev.photo = await reduirePhoto(inp.files[0]); apercu(); } catch (e) { alert('Photo illisible.'); } };
    $('#ev-photo').onchange = (e) => surPhoto(e.target); $('#ev-photo-cam').onchange = (e) => surPhoto(e.target);
    apercu();
    $('#form-ev').onsubmit = (e) => {
      e.preventDefault(); lire();
      if (!ev.titre || !ev.date) return;
      if (idModif) { const i = etat.evenements.findIndex((x) => x.id === idModif); etat.evenements[i] = ev; }
      else { ev.id = id(); etat.evenements.push(ev); }
      if (enregistrer()) {
        if (idModif) { location.hash = '#gerant/evenements'; return; }
        ecranEvenements();
        $('#ev-message').innerHTML = `Publié ! <a href="#aujourdhui">Voir côté campeurs</a>`;
      }
    };
    ecran.querySelectorAll('.modif').forEach((b) => b.onclick = () => { location.hash = '#gerant/evenements/' + b.dataset.id; });
    ecran.querySelectorAll('.suppr').forEach((b) => b.onclick = () => {
      if (!confirm('Supprimer cet événement ?')) return;
      etat.evenements = etat.evenements.filter((e) => e.id !== b.dataset.id); enregistrer(); ecranEvenements();
    });
  }

  // --- caisse ---
  function elementBouton(b, balise = 'button') {
    const el = document.createElement(balise);
    el.className = 'bouton-caisse forme-' + (b.forme || 'arrondi') + ' police-' + (b.police || 'titres') + ' taille-' + (b.taille || 'grand');
    el.style.background = b.couleur || '#789CF2'; el.style.color = couleurTexte(b.couleur || '#789CF2');
    const avecPhoto = b.photo && b.affichage !== 'texte', avecTexte = !b.photo || b.affichage !== 'photo';
    el.innerHTML = (avecPhoto ? `<img src="${echap(b.photo)}" alt="">` : '') + (avecTexte ? `<span class="nom">${echap(b.nom)}</span>` : '') + `<span class="prix">${euros(b.prix || 0)}</span>`;
    el.setAttribute('aria-label', b.nom + ', ' + euros(b.prix || 0));
    return el;
  }
  const ventesDuJour = () => etat.ventes.filter((v) => v.date.slice(0, 10) === aujourdhui());
  function ecranCaisse() {
    if (!peut('caisse')) return refus();
    page(barreGerant('Caisse') + `
      <div class="total carte" aria-live="polite"><span>Total du jour</span><b id="total">${euros(ventesDuJour().reduce((s, v) => s + v.prix, 0))}</b><span id="nb-ventes">${ventesDuJour().length} ventes</span></div>
      <p class="flash" id="flash" role="status"></p>
      <div class="grille-caisse" id="grille"></div>
      <details class="carte plus"><summary>Plus d'options</summary>
        <button class="bouton large rouge" id="annuler-vente">Annuler la dernière vente</button>
        <div id="detail-jour"></div>
        <button class="bouton large clair" id="export-csv">Exporter les ventes du jour (tableur)</button>
        ${peut('boutons') ? '<button class="bouton large orange" id="ajout-bouton">Ajouter un bouton</button><p class="petit">Pour régler un bouton : « Régler » sous chaque bouton.</p><label class="interrupteur"><input type="checkbox" id="mode-reglage"> Afficher « Régler » sous les boutons</label>' : ''}
      </details>`);
    brancherQuitter();
    const grille = $('#grille');
    const maj = () => {
      const vj = ventesDuJour();
      $('#total').textContent = euros(vj.reduce((s, v) => s + v.prix, 0));
      $('#nb-ventes').textContent = vj.length + (vj.length > 1 ? ' ventes' : ' vente');
      const parCat = {}; vj.forEach((v) => { parCat[v.categorie] = parCat[v.categorie] || { n: 0, s: 0 }; parCat[v.categorie].n++; parCat[v.categorie].s += v.prix; });
      $('#detail-jour').innerHTML = Object.keys(parCat).length ? '<table class="tableau"><tr><th>Catégorie</th><th>Nombre</th><th>Total</th></tr>' + Object.entries(parCat).map(([c, x]) => `<tr><td>${echap(c)}</td><td>${x.n}</td><td>${euros(x.s)}</td></tr>`).join('') + '</table>' : '<p>Aucune vente aujourd\'hui.</p>';
    };
    const dessinerGrille = () => {
      grille.innerHTML = '';
      const reglage = $('#mode-reglage') && $('#mode-reglage').checked;
      etat.boutons.forEach((b) => {
        const case_ = document.createElement('div'); case_.className = 'case-caisse';
        const el = elementBouton(b);
        el.onclick = () => {
          const d = new Date();
          etat.ventes.push({ id: id(), boutonId: b.id, nom: b.nom, prix: Number(b.prix) || 0, categorie: b.categorie || '', date: dateLocale(d) + 'T' + deux(d.getHours()) + ':' + deux(d.getMinutes()) + ':' + deux(d.getSeconds()) });
          enregistrer(); maj();
          const f = $('#flash'); f.textContent = '+ ' + b.nom + ' ' + euros(b.prix); f.classList.remove('vu'); void f.offsetWidth; f.classList.add('vu');
          el.classList.remove('appui'); void el.offsetWidth; el.classList.add('appui');
          if (navigator.vibrate) navigator.vibrate(30);
        };
        case_.appendChild(el);
        if (reglage) { const r = document.createElement('button'); r.className = 'bouton clair regler'; r.textContent = 'Régler'; r.onclick = () => { location.hash = '#gerant/bouton/' + b.id; }; case_.appendChild(r); }
        grille.appendChild(case_);
      });
    };
    dessinerGrille(); maj();
    $('#annuler-vente').onclick = () => {
      const vj = ventesDuJour(); if (!vj.length) return;
      const der = vj[vj.length - 1];
      if (!confirm('Annuler : ' + der.nom + ' ' + euros(der.prix) + ' ?')) return;
      etat.ventes = etat.ventes.filter((v) => v.id !== der.id); enregistrer(); maj();
      $('#flash').textContent = 'Annulé : ' + der.nom;
    };
    $('#export-csv').onclick = () => {
      const l = [['date', 'heure', 'produit', 'catégorie', 'prix']].concat(ventesDuJour().map((v) => [v.date.slice(0, 10), v.date.slice(11, 16), v.nom, v.categorie, String(v.prix).replace('.', ',')]));
      telecharger('ventes-' + aujourdhui() + '.csv', '﻿' + l.map((r) => r.map((c) => '"' + String(c).replace(/"/g, '""') + '"').join(';')).join('\r\n'), 'text/csv');
    };
    if ($('#ajout-bouton')) { $('#ajout-bouton').onclick = () => { location.hash = '#gerant/bouton/nouveau'; }; $('#mode-reglage').onchange = dessinerGrille; }
  }

  function ecranReglerBouton(idB) {
    if (!peut('boutons')) return refus();
    const nouveau = idB === 'nouveau';
    const existant = etat.boutons.find((x) => x.id === idB);
    if (!nouveau && !existant) { location.hash = '#gerant/caisse'; return; }
    const b = nouveau ? { nom: 'Nouveau', prix: 1, categorie: 'Divers', couleur: '#789CF2', forme: 'arrondi', police: 'titres', taille: 'grand', affichage: 'texte', photo: '' } : Object.assign({}, existant);
    const choix = (nom, valeurs, actuel) => `<div class="choix" role="radiogroup">${valeurs.map(([v, t]) => `<label class="option"><input type="radio" name="${nom}" value="${v}" ${v === actuel ? 'checked' : ''}><span>${t}</span></label>`).join('')}</div>`;
    page(barreGerant(nouveau ? 'Nouveau bouton' : 'Régler le bouton') + `
      <div class="deux-colonnes">
        <form class="carte" id="form-b">
          <label for="b-nom">Nom</label><input id="b-nom" required maxlength="24" value="${echap(b.nom)}">
          <div class="rangee"><div><label for="b-prix">Prix (€)</label><input id="b-prix" type="number" inputmode="decimal" min="0" step="0.1" required value="${b.prix}"></div>
          <div><label for="b-cat">Catégorie</label><input id="b-cat" maxlength="24" value="${echap(b.categorie)}"></div></div>
          <label>Couleur</label><div class="choix">${COULEURS.map((c) => `<label class="pastille-couleur" style="background:${c}"><input type="radio" name="couleur" value="${c}" ${c.toLowerCase() === (b.couleur || '').toLowerCase() ? 'checked' : ''} aria-label="couleur ${c}"></label>`).join('')}</div>
          <label>Forme</label>${choix('forme', [['arrondi', 'Arrondi'], ['carre', 'Carré'], ['rond', 'Rond']], b.forme)}
          <label>Police</label>${choix('police', [['titres', 'Titres'], ['texte', 'Texte']], b.police)}
          <label>Taille du texte</label>${choix('taille', [['normal', 'Normal'], ['grand', 'Grand'], ['tres-grand', 'Très grand']], b.taille)}
          <label>Afficher</label>${choix('affichage', [['texte', 'Texte'], ['photo', 'Photo'], ['photo-texte', 'Photo + texte']], b.affichage)}
          <div class="rangee"><label class="bouton orange fichier">Prendre une photo<input type="file" accept="image/*" capture="environment" id="b-photo-cam"></label>
          <label class="bouton clair fichier">Choisir une photo<input type="file" accept="image/*" id="b-photo"></label></div>
          <button class="bouton large" type="submit" id="b-enregistrer">Enregistrer</button>
          ${nouveau ? '' : '<button class="bouton large rouge" type="button" id="b-suppr">Supprimer ce bouton</button>'}
          <a class="bouton large clair" href="#gerant/caisse">Retour à la caisse</a>
        </form>
        <div><h2>Aperçu</h2><div class="grille-caisse apercu-bouton" id="apercu-b"></div></div>
      </div>`);
    brancherQuitter();
    const f = $('#form-b');
    const lire = () => {
      b.nom = $('#b-nom').value.trim() || 'Sans nom'; b.prix = Math.max(0, parseFloat(String($('#b-prix').value).replace(',', '.')) || 0); b.categorie = $('#b-cat').value.trim() || 'Divers';
      ['couleur', 'forme', 'police', 'taille', 'affichage'].forEach((k) => { const r = f.querySelector(`input[name="${k}"]:checked`); if (r) b[k] = r.value; });
    };
    const apercu = () => { lire(); const a = $('#apercu-b'); a.innerHTML = ''; a.appendChild(elementBouton(b, 'div')); };
    f.addEventListener('input', apercu); f.addEventListener('change', apercu);
    const surPhoto = async (inp) => { if (!inp.files[0]) return; try { b.photo = await reduirePhoto(inp.files[0]); if (b.affichage === 'texte') { f.querySelector('input[name="affichage"][value="photo-texte"]').checked = true; } apercu(); } catch (e) { alert('Photo illisible.'); } };
    $('#b-photo').onchange = (e) => surPhoto(e.target); $('#b-photo-cam').onchange = (e) => surPhoto(e.target);
    apercu();
    f.onsubmit = (e) => {
      e.preventDefault(); lire();
      if (nouveau) { b.id = id(); etat.boutons.push(b); } else etat.boutons[etat.boutons.findIndex((x) => x.id === idB)] = b;
      if (enregistrer()) location.hash = '#gerant/caisse';
    };
    if ($('#b-suppr')) $('#b-suppr').onclick = () => { if (confirm('Supprimer le bouton « ' + b.nom + ' » ?')) { etat.boutons = etat.boutons.filter((x) => x.id !== idB); enregistrer(); location.hash = '#gerant/caisse'; } };
  }

  // --- arrivées ---
  function ecranArrivees() {
    if (!peut('arrivees')) return refus();
    const l = etat.arrivees.filter((a) => a.date === aujourdhui());
    page(barreGerant('Arrivées du jour') + `<p class="fictif">Données fictives de démonstration.</p>
      <div class="carte"><table class="tableau" id="table-arrivees"><tr><th>Heure</th><th>Emplacement</th><th>Nom</th><th>Pers.</th></tr>
      ${l.map((a) => `<tr><td>${echap(heureTexte(a.heure))}</td><td>${echap(a.emplacement)}</td><td>${echap(a.nom)}</td><td>${a.personnes}</td></tr>`).join('') || '<tr><td colspan="4">Aucune arrivée.</td></tr>'}</table></div>`);
    brancherQuitter();
  }

  // --- plan ---
  function ecranPlanGerant() {
    if (!peut('plan')) return refus();
    page(barreGerant('Plan') + `<div class="carte"><p>Dans la maquette 3D, touchez <b>Modifier</b> pour ajouter des douches, poteaux, jeux, mobil-homes (bouton « Ajouter », puis « Changer le type »).</p>
      <a class="bouton large orange" href="${PLAN}">Ouvrir l'éditeur du plan</a>
      <p class="petit">Les modifications du plan sont enregistrées sur cet appareil (Exporter / Importer dans la maquette).</p></div>`);
    brancherQuitter();
  }

  // --- codes et sauvegarde ---
  function telecharger(nom, contenu, type) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([contenu], { type })); a.download = nom;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  function ecranReglages() {
    if (!peut('reglages')) return refus();
    page(barreGerant('Codes et sauvegarde') + `
      <form class="carte" id="form-codes"><h2>Codes (4 chiffres)</h2>
        ${Object.keys(ROLES).map((r) => `<label for="code-${r}">${ROLES[r]}</label><input id="code-${r}" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" required value="${etat.codes[r]}">`).join('')}
        <button class="bouton large" type="submit">Enregistrer les codes</button><p class="ok" id="codes-ok" role="status"></p></form>
      <div class="carte"><h2>Sauvegarde</h2>
        <p>Les données restent sur cet appareil. <b>Pas de synchronisation entre appareils pour l'instant.</b> Pour passer à un autre appareil : Exporter ici, puis Importer là-bas.</p>
        <button class="bouton large" id="exporter">Exporter (fichier JSON)</button>
        <label class="bouton large clair fichier">Importer un fichier JSON<input type="file" accept="application/json,.json" id="importer"></label>
        <p class="ok" id="import-ok" role="status"></p></div>`);
    brancherQuitter();
    $('#form-codes').onsubmit = (e) => {
      e.preventDefault();
      const n = {}; for (const r of Object.keys(ROLES)) { const v = $('#code-' + r).value; if (!/^\d{4}$/.test(v)) { $('#codes-ok').textContent = 'Il faut 4 chiffres pour ' + ROLES[r] + '.'; return; } n[r] = v; }
      etat.codes = n; if (enregistrer()) $('#codes-ok').textContent = 'Codes enregistrés.';
    };
    $('#exporter').onclick = () => telecharger('camping-sauvegarde-' + aujourdhui() + '.json', JSON.stringify(etat, null, 1), 'application/json');
    $('#importer').onchange = (e) => {
      const fi = e.target.files[0]; if (!fi) return;
      const r = new FileReader();
      r.onload = () => {
        try {
          const d = JSON.parse(r.result);
          if (d.version !== 1 || !Array.isArray(d.evenements) || !Array.isArray(d.boutons) || !Array.isArray(d.ventes) || !d.codes) throw new Error('format');
          if (!confirm('Remplacer toutes les données de cet appareil par ce fichier ?')) return;
          etat = d; enregistrer(); $('#import-ok').textContent = 'Import terminé.';
        } catch (err) { $('#import-ok').textContent = "Ce fichier n'est pas une sauvegarde de l'application."; }
      };
      r.readAsText(fi);
    };
  }

  // ---------- navigation ----------
  function afficher() {
    $('#feuille-menu').hidden = true;
    const h = (location.hash || '#aujourdhui').slice(1).split('/');
    document.body.classList.toggle('gerant', h[0] === 'gerant');
    document.querySelectorAll('.menu-large a').forEach((a) => a.classList.toggle('actif', a.getAttribute('href') === '#' + h[0]));
    if (h[0] === 'gerant') {
      if (!role() || !DROITS[role()]) return ecranConnexion();
      if (h[1] === 'evenements') return ecranEvenements(h[2]);
      if (h[1] === 'caisse') return ecranCaisse();
      if (h[1] === 'bouton') return ecranReglerBouton(h[2]);
      if (h[1] === 'arrivees') return ecranArrivees();
      if (h[1] === 'plan') return ecranPlanGerant();
      if (h[1] === 'reglages') return ecranReglages();
      return ecranGerantAccueil();
    }
    ({ plan: ecranPlan, balades: ecranBalades, infos: ecranInfos, contact: ecranContact, reserver: ecranReserver }[h[0]] || ecranAujourdhui)();
  }
  window.addEventListener('hashchange', afficher);
  $('#bouton-menu').onclick = () => { $('#feuille-menu').hidden = false; $('#feuille-menu a').focus(); };
  $('#fermer-menu').onclick = () => { $('#feuille-menu').hidden = true; };
  $('#feuille-menu').onclick = (e) => { if (e.target.id === 'feuille-menu') e.currentTarget.hidden = true; };
  afficher();

  // Fonctionnement sans réseau (seulement servi en http/https)
  if ('serviceWorker' in navigator && location.protocol !== 'file:') navigator.serviceWorker.register('sw.js').catch(() => {});
})();

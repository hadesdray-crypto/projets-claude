import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const D = window.DONNEES;
const BLEU = 0x789CF2, ORANGE = 0xFE8D4F, JAUNE = 0xE6DB55, VERT = 0x4FB86A;
const TYPES = ['mobil-home', 'sanitaires', 'douches', 'accueil', 'bar', 'piscine', 'poubelles', 'local technique', 'emplacement', 'bâtiment'];
const VITESSE_MARCHE = 1.3;          // m/s
const $ = (s) => document.querySelector(s);
const fmt = (v) => v.toFixed(1).replace('.', ',');

// ---------- scène
const canvas = $('#cv');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xb9caf7);
const camera = new THREE.PerspectiveCamera(45, 1, 1, 6000);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.12; controls.maxPolarAngle = Math.PI * 0.49;
controls.screenSpacePanning = false; controls.minDistance = 8; controls.maxDistance = 2600;
controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
scene.add(new THREE.AmbientLight(0xffffff, 1.3));
const sun = new THREE.DirectionalLight(0xffffff, 1.2); sun.position.set(-300, 600, 200); scene.add(sun);

const O = D.ortho, cx = (O.x0 + O.x1) / 2, cy = (O.y0 + O.y1) / 2;
const W3 = (x, y, h = 0) => new THREE.Vector3(x, h, -y);     // repère local (x est, y nord) -> Three (Z = -nord)

// sol bleu uni
const sol = new THREE.Mesh(new THREE.PlaneGeometry(12000, 12000),
  new THREE.MeshBasicMaterial({ color: 0xb9caf7 }));
sol.rotation.x = -Math.PI / 2; sol.position.set(cx, 0, -cy); scene.add(sol);

// ---------- calques
const calques = { batiments: new THREE.Group(), arbres: new THREE.Group(), routes: new THREE.Group(), zones: new THREE.Group(), etiquettes: new THREE.Group(), photo: new THREE.Group() };
for (const g of Object.values(calques)) scene.add(g);
calques.photo.visible = false;
const NOMS = { batiments: 'Bâtiments', arbres: 'Arbres', routes: 'Routes et chemins', zones: 'Zones', etiquettes: 'Étiquettes', photo: 'Photo aérienne (vérification)' };

function ruban(paires, largeur, couleur, y, opacite = 1, ordre = 0) {
  // paires : [[x1,y1,x2,y2],...] -> bandes plates au sol
  const pos = [], idx = []; let n = 0;
  for (const [x1, y1, x2, y2] of paires) {
    const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy); if (L < 0.01) continue;
    const nx = -dy / L * largeur / 2, ny = dx / L * largeur / 2;
    for (const [px, py] of [[x1 + nx, y1 + ny], [x1 - nx, y1 - ny], [x2 - nx, y2 - ny], [x2 + nx, y2 + ny]]) pos.push(px, y, -py);
    idx.push(n, n + 1, n + 2, n, n + 2, n + 3); n += 4;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx);
  const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: couleur, transparent: opacite < 1, opacity: opacite, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -ordre, polygonOffsetUnits: -ordre }));
  m.renderOrder = ordre; return m;
}

// routes et chemins (traits clairs)
{
  const N = D.chemins.noeuds, parLarg = { large: [], moyen: [], fin: [] };
  for (const [a, b, d, nat] of D.chemins.aretes) {
    const s = [N[a][0], N[a][1], N[b][0], N[b][1]];
    (nat === 'Route à 1 chaussée' || nat === 'Rond-point' || nat === 'primary' ? parLarg.large : (nat === 'Sentier' || nat === 'footway' || nat === 'path' || nat === 'cycleway' ? parLarg.fin : parLarg.moyen)).push(s);
  }
  calques.routes.add(ruban(parLarg.large, 4, 0xf8faff, 0.05, 0.95, 1), ruban(parLarg.moyen, 2.5, 0xf8faff, 0.05, 0.95, 1), ruban(parLarg.fin, 1.2, 0xf8faff, 0.05, 0.95, 1));
  const lim = D.camping, boucle = [];
  lim.forEach((p, i) => { const q = lim[(i + 1) % lim.length]; boucle.push([p[0], p[1], q[0], q[1]]); });
  calques.zones.add(ruban(boucle, 1.4, ORANGE, 0.12, 1, 2));
}

// zones : piscines (blocs bleus translucides), sport, végétation
const matBloc = new THREE.MeshLambertMaterial({ color: BLEU, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.DoubleSide });
function formeExtrudee(pts, h) {
  const s = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
  const g = new THREE.ExtrudeGeometry(s, { depth: h, bevelEnabled: false }); g.rotateX(-Math.PI / 2); return g;
}
function aplat(pts, couleur, op, y) {
  const s = new THREE.Shape(pts.map(([x, yy]) => new THREE.Vector2(x, yy)));
  const g = new THREE.ShapeGeometry(s); g.rotateX(-Math.PI / 2); g.translate(0, y, 0);
  return new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: couleur, transparent: true, opacity: op, depthWrite: false, side: THREE.DoubleSide }));
}
function contour(pts, h, couleur) {
  const v = []; pts.forEach((p, i) => { const q = pts[(i + 1) % pts.length]; v.push(p[0], h, -p[1], q[0], h, -q[1]); });
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
  return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: couleur }));
}
for (const z of D.zones) {
  if (z.type === 'piscine') {
    const m = new THREE.Mesh(formeExtrudee(z.pts, z.h), new THREE.MeshLambertMaterial({ color: 0x4f7cf0, transparent: true, opacity: 0.6, depthWrite: false, side: THREE.DoubleSide }));
    calques.zones.add(m, contour(z.pts, z.h, 0x1d3f9e), contour(z.pts, 0.02, 0x1d3f9e));
  } else if (z.type === 'vegetation') {
    calques.zones.add(aplat(z.pts, VERT, 0.18, 0.03));
  } else if (z.type === 'sport') {
    calques.zones.add(aplat(z.pts, JAUNE, 0.45, 0.04));
  }
}

// ---------- arbres : formes vertes translucides posées au sol (maxima de canopée LiDAR HD)
{
  const g = new THREE.SphereGeometry(1, 7, 5);
  const m = new THREE.MeshLambertMaterial({ color: VERT, transparent: true, opacity: 0.5, depthWrite: false });
  const inst = new THREE.InstancedMesh(g, m, D.arbres.length);
  const mat = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();
  D.arbres.forEach(([x, y, h], i) => {
    const r = Math.min(Math.max(h * 0.22, 1), 3.2);
    p.set(x, h / 2, -y); s.set(r, h / 2, r);                    // de 0 à h : jamais en l'air
    inst.setMatrixAt(i, mat.compose(p, q, s));
  });
  calques.arbres.add(inst);
}

// ---------- blocs (bâtiments) : un seul maillage fusionné, reconstruit à chaque modification
let blocs = JSON.parse(JSON.stringify(D.blocs));
let triVersBloc = [];
const maillageBlocs = new THREE.Mesh(new THREE.BufferGeometry(), matBloc);
const aretesBlocs = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0x2d4fa8, transparent: true, opacity: 0.8 }));
const maillageSel = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshLambertMaterial({ color: ORANGE, transparent: true, opacity: 0.6, depthWrite: false, side: THREE.DoubleSide }));
const aretesSel = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xc25a12 }));
calques.batiments.add(maillageBlocs, aretesBlocs, maillageSel, aretesSel);
let selection = -1;

function anneau(b) {
  const c = Math.cos(b.rot * Math.PI / 180), s = Math.sin(b.rot * Math.PI / 180);
  return b.pts.map(([px, py]) => { const X = px * b.sx, Y = py * b.sy; return [b.x + X * c - Y * s, b.y + X * s + Y * c]; });
}
function geomBloc(b, pos, idx, lignes, tris, i) {
  const r = anneau(b), h = b.h, n = r.length, base = pos.length / 3;
  r.forEach(([x, y]) => pos.push(x, h, -y));
  r.forEach(([x, y]) => pos.push(x, 0, -y));
  const tri = THREE.ShapeUtils.triangulateShape(r.map(([x, y]) => new THREE.Vector2(x, y)), []);
  for (const [a, bb, c] of tri) { idx.push(base + a, base + c, base + bb); tris && tris.push(i); }
  for (let k = 0; k < n; k++) {
    const k2 = (k + 1) % n;
    idx.push(base + k, base + n + k, base + k2, base + k2, base + n + k, base + n + k2); tris && tris.push(i, i);
    lignes.push(r[k][0], h, -r[k][1], r[k2][0], h, -r[k2][1], r[k][0], 0, -r[k][1], r[k2][0], 0, -r[k2][1], r[k][0], 0, -r[k][1], r[k][0], h, -r[k][1]);
  }
}
function remplir(maille, aretes, liste, tris) {
  const pos = [], idx = [], lig = [];
  liste.forEach(([b, i]) => geomBloc(b, pos, idx, lig, tris, i));
  maille.geometry.dispose(); aretes.geometry.dispose();
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  maille.geometry = g;
  const l = new THREE.BufferGeometry(); l.setAttribute('position', new THREE.Float32BufferAttribute(lig, 3)); aretes.geometry = l;
}
let indexSansSel = [];
function reconstruireBlocs() {   // triVersBloc : triangle -> rang dans indexSansSel (le bloc sélectionné est dessiné à part)
  indexSansSel = blocs.map((b, i) => i).filter(i => i !== selection);
  triVersBloc = [];
  remplir(maillageBlocs, aretesBlocs, indexSansSel.map((i, k) => [blocs[i], k]), triVersBloc);
  remplir(maillageSel, aretesSel, selection >= 0 && blocs[selection] ? [[blocs[selection], selection]] : [], null);
  maillageBlocs.geometry.computeBoundingSphere();
  majEtiquettes(); majPanneauSelection();
}

// ---------- étiquettes (taille constante à l'écran)
function sprite(texte, couleur = '#1d3f9e') {
  const c = document.createElement('canvas'), x = c.getContext('2d'); x.font = 'bold 34px sans-serif';
  const w = Math.ceil(x.measureText(texte).width) + 24; c.width = w; c.height = 52;
  x.font = 'bold 34px sans-serif'; x.fillStyle = 'rgba(255,255,255,0.88)'; x.beginPath(); x.roundRect(0, 0, w, 52, 12); x.fill();
  x.strokeStyle = couleur; x.lineWidth = 3; x.stroke(); x.fillStyle = couleur; x.textBaseline = 'middle'; x.fillText(texte, 12, 27);
  const t = new THREE.CanvasTexture(c);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, sizeAttenuation: false }));
  sp.scale.set(w / 1100 * 0.42, 52 / 1100 * 0.42, 1); sp.renderOrder = 10; return sp;
}
const groupeEtiq = new THREE.Group(); calques.etiquettes.add(groupeEtiq);
const labelFixes = [];
{
  const c = D.camping, mx = c.reduce((a, p) => a + p[0], 0) / c.length, my = c.reduce((a, p) => a + p[1], 0) / c.length;
  const s = sprite('Camping Amitié & Nature', '#c25a12'); s.position.copy(W3(mx, my, 25)); labelFixes.push(s);
  const z = D.zones.filter(z => z.type === 'piscine' && z.dans_camping).sort((a, b) => b.pts.length - a.pts.length)[0];
  if (z) { const px = z.pts.reduce((a, p) => a + p[0], 0) / z.pts.length, py = z.pts.reduce((a, p) => a + p[1], 0) / z.pts.length; const s2 = sprite('Piscine'); s2.position.copy(W3(px, py, 6)); labelFixes.push(s2); }
  const s3 = sprite('Plage des Dunes', '#c25a12'); s3.position.copy(W3(...D.lieux['Plage des Dunes'], 4)); labelFixes.push(s3);
}
labelFixes.forEach(s => groupeEtiq.add(s));
let etiqBlocs = [];
function majEtiquettes() {
  etiqBlocs.forEach(s => { groupeEtiq.remove(s); s.material.map.dispose(); s.material.dispose(); }); etiqBlocs = [];
  blocs.forEach(b => {
    if (b.type === 'bâtiment') return;
    const s = sprite(b.type); s.position.copy(W3(b.x, b.y, b.h + 2)); groupeEtiq.add(s); etiqBlocs.push(s);
  });
}

// ---------- photo aérienne IGN (chargée à la demande ; incorporée en base64 pour fonctionner hors ligne)
let photoChargee = false;
function chargerPhoto() {
  if (photoChargee) return; photoChargee = true;
  const sc = document.createElement('script'); sc.src = 'donnees/orthophoto.js';
  sc.onload = () => {
    new THREE.TextureLoader().load(window.ORTHO, (t) => {
      t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
      const p = new THREE.Mesh(new THREE.PlaneGeometry(O.x1 - O.x0, O.y1 - O.y0), new THREE.MeshBasicMaterial({ map: t }));
      p.rotation.x = -Math.PI / 2; p.position.set(cx, 0.02, -cy); calques.photo.add(p); window.__photoPrete = true;
    });
  }; document.head.appendChild(sc);
}

// ---------- itinéraires à pied (A* sur le réseau ; lieux raccordés au point le plus proche d'une arête)
const NOEUDS = D.chemins.noeuds.map(p => [p[0], p[1]]), ARETES = D.chemins.aretes;
const adjBase = NOEUDS.map(() => []);
ARETES.forEach(([a, b, d, nat, src, v], i) => { adjBase[a].push([b, d, v, nat]); adjBase[b].push([a, d, v, nat]); });
function projSeg(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy;
  const t = L2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2));
  const q = [a[0] + t * dx, a[1] + t * dy]; return [q, t, Math.hypot(p[0] - q[0], p[1] - q[1])];
}
function itineraire(p, q) {
  const noeuds = NOEUDS.slice(), adj = adjBase.map(l => l.slice());
  const virt = (pt) => {
    let best = null;
    ARETES.forEach(([a, b], i) => { const r = projSeg(pt, NOEUDS[a], NOEUDS[b]); if (!best || r[2] < best[0][2]) best = [r, i]; });
    const [[qq, t, dist], i] = best, [a, b, d, nat, , v] = ARETES[i];
    const k = noeuds.length; noeuds.push(qq); adj[k] = [];
    adj[k].push([a, d * t, v, nat]); adj[a].push([k, d * t, v, nat]); adj[k].push([b, d * (1 - t), v, nat]); adj[b].push([k, d * (1 - t), v, nat]);
    return [k, dist];
  };
  const [s, ds] = virt(p), [t, dt] = virt(q);
  const g = new Map([[s, 0]]), prev = new Map(), ouvert = [[0, s]], clos = new Set();
  while (ouvert.length) {
    ouvert.sort((a, b) => a[0] - b[0]); const [, u] = ouvert.shift();
    if (clos.has(u)) continue; clos.add(u); if (u === t) break;
    for (const [w, d, v, nat] of adj[u]) {
      const ng = g.get(u) + d;
      if (ng < (g.get(w) ?? 1e18)) { g.set(w, ng); prev.set(w, [u, v, nat]); ouvert.push([ng + Math.hypot(noeuds[w][0] - noeuds[t][0], noeuds[w][1] - noeuds[t][1]), w]); }
    }
  }
  if (!g.has(t)) return null;
  const pts = [noeuds[t]]; let voiture = true; const natures = new Set(); let u = t;
  while (u !== s) { const [pu, v, nat] = prev.get(u); voiture = voiture && !!v; natures.add(nat); pts.push(noeuds[pu]); u = pu; }
  pts.reverse();
  return { pts: [p, ...pts, q], reseau: g.get(t), raccord: ds + dt, voiture: voiture && ds + dt < 3, natures: [...natures] };
}

// ---------- trajet + pion
const groupeTrajet = new THREE.Group(); scene.add(groupeTrajet);
const pion = new THREE.Group();
{
  const corps = new THREE.Mesh(new THREE.ConeGeometry(0.45, 1.3, 14), new THREE.MeshLambertMaterial({ color: ORANGE }));
  corps.position.y = 0.65;
  const tete = new THREE.Mesh(new THREE.SphereGeometry(0.3, 14, 10), new THREE.MeshLambertMaterial({ color: JAUNE })); tete.position.y = 1.5;
  pion.add(corps, tete); pion.visible = false; scene.add(pion);
}
let parcours = null;      // { pts: [[x,y]...], cum: [] , total }
let tPion = 0, vit = 10, trajetActif = false;
function lieuPos(nom) {
  if (nom === 'Mobil-home exemple') { const b = blocs.find(b => b.id === 'exemple-mobil-home'); if (b) return [b.x, b.y]; }
  if (nom === 'Accueil') { const b = blocs.find(b => b.type === 'accueil'); if (b) return [b.x, b.y]; }
  return D.lieux[nom];
}
const ORDRE = ['Mobil-home exemple', 'Piscine', 'Accueil', 'Plage des Dunes'];
const fmtDuree = (s) => { const m = Math.floor(s / 60); return m > 0 ? `${m} min ${String(Math.round(s % 60)).padStart(2, '0')} s` : `${Math.round(s)} s`; };
function calculerTrajet() {
  groupeTrajet.clear(); parcours = null;
  const etapes = []; let pts = [];
  for (let i = 0; i < ORDRE.length - 1; i++) {
    const r = itineraire(lieuPos(ORDRE[i]), lieuPos(ORDRE[i + 1]));
    if (!r) { etapes.push({ de: ORDRE[i], a: ORDRE[i + 1], erreur: true }); continue; }
    etapes.push({ de: ORDRE[i], a: ORDRE[i + 1], ...r });
    pts = pts.concat(i === 0 ? r.pts : r.pts.slice(1));
  }
  const paires = [], hors = [];
  for (const e of etapes) if (e.pts) e.pts.forEach((p, k) => {
    if (k === 0) return; const a = e.pts[k - 1], seg = [a[0], a[1], p[0], p[1]];
    ((k === 1 || k === e.pts.length - 1) ? hors : paires).push(seg);
  });
  groupeTrajet.add(ruban(paires, 3.2, ORANGE, 0.2, 1, 5), ruban(hors, 2.2, JAUNE, 0.21, 1, 6));
  // repères des lieux
  ORDRE.forEach(n => { const p = lieuPos(n), m = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 0.4, 20), new THREE.MeshBasicMaterial({ color: JAUNE })); m.position.copy(W3(p[0], p[1], 0.25)); groupeTrajet.add(m); const s = sprite(n, '#c25a12'); s.position.copy(W3(p[0], p[1], 8)); groupeTrajet.add(s); });
  const cum = [0]; for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  parcours = { pts, cum, total: cum[cum.length - 1] };
  let tot = 0, html = '<b>Trajet à pied</b><br>';
  for (const e of etapes) {
    if (e.erreur) { html += `${e.de} → ${e.a} : aucun chemin<br>`; continue; }
    const L = e.reseau + e.raccord; tot += L;
    const v = e.voiture ? `voiture possible (${e.natures.join(', ')})` : 'à pied seulement' + (e.raccord >= 3 ? ` (dont ${Math.round(e.raccord)} m hors route)` : '');
    html += `${e.de} → ${e.a} : <b>${Math.round(L)} m</b>, ${fmtDuree(L / VITESSE_MARCHE)} · ${v}<br>`;
  }
  html += `<b>Total : ${Math.round(tot)} m, ${fmtDuree(tot / VITESSE_MARCHE)}</b> (1,3 m/s)<br><small>Orange : sur route ou chemin · jaune : raccord hors réseau</small>`;
  $('#trajetInfo').innerHTML = html; tPion = 0;
}
function placerPion(t) {
  if (!parcours) return;
  const { pts, cum, total } = parcours; const d = Math.min(Math.max(t, 0), total);
  let i = 1; while (i < cum.length - 1 && cum[i] < d) i++;
  const a = pts[i - 1], b = pts[i], seg = cum[i] - cum[i - 1] || 1, f = (d - cum[i - 1]) / seg;
  const x = a[0] + (b[0] - a[0]) * f, y = a[1] + (b[1] - a[1]) * f;
  pion.position.set(x, 0.35 + 0.05 * Math.sin(performance.now() / 150), -y);   // légèrement au-dessus du sol
  pion.rotation.y = Math.atan2(b[0] - a[0], -(b[1] - a[1])) + Math.PI;
  const k = Math.min(Math.max(camera.position.distanceTo(pion.position) / 35, 1), 14); pion.scale.setScalar(k);
}
function basculerTrajet(on) {
  trajetActif = on; $('#trajetPanneau').hidden = !on; pion.visible = on; groupeTrajet.visible = on;
  if (on) { calculerTrajet(); const p = lieuPos(ORDRE[0]); vueSur(p[0], p[1], 260, 0.9); }
}

// ---------- mesure
const groupeMesure = new THREE.Group(); scene.add(groupeMesure);
let mesurePts = [], modeMesure = false;
const sol0 = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
function pointSol(ev) {
  const r = canvas.getBoundingClientRect(); ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera); const out = new THREE.Vector3(); return ray.ray.intersectPlane(sol0, out) ? out : null;
}
function ajouterMesure(p) {
  if (mesurePts.length >= 2) { mesurePts = []; groupeMesure.clear(); $('#mesureTxt').hidden = true; }
  mesurePts.push(p);
  const m = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8), new THREE.MeshBasicMaterial({ color: ORANGE, depthTest: false })); m.position.copy(p).setY(0.5); m.renderOrder = 20; m.userData.marque = true; groupeMesure.add(m);
  if (mesurePts.length === 2) {
    const g = new THREE.BufferGeometry().setFromPoints([mesurePts[0].clone().setY(0.6), mesurePts[1].clone().setY(0.6)]);
    const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color: ORANGE, depthTest: false })); l.renderOrder = 20; groupeMesure.add(l);
    const d = mesurePts[0].distanceTo(mesurePts[1]); const t = $('#mesureTxt'); t.hidden = false; t.textContent = `${fmt(d)} m · à pied ${fmtDuree(d / VITESSE_MARCHE)}`;
  }
}
function majMarquesMesure() {
  const k = Math.max(camera.position.distanceTo(controls.target) / 200, 0.5);
  groupeMesure.children.forEach(o => { if (o.userData.marque) o.scale.setScalar(k); });
  const t = $('#mesureTxt');
  if (mesurePts.length === 2 && !t.hidden) {
    const m = mesurePts[0].clone().add(mesurePts[1]).multiplyScalar(0.5).project(camera), r = canvas.getBoundingClientRect();
    t.style.left = ((m.x + 1) / 2 * r.width) + 'px'; t.style.top = ((1 - m.y) / 2 * r.height - 28) + 'px';
  }
}

// ---------- règle (échelle)
function majRegle() {
  const d = camera.position.distanceTo(controls.target), hauteurMonde = 2 * d * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)), mParPx = hauteurMonde / canvas.clientHeight;
  const cibles = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]; let L = cibles[0];
  for (const c of cibles) if (c / mParPx <= 160) L = c;
  $('#regleBarre').style.width = (L / mParPx) + 'px'; $('#regleTxt').textContent = L >= 1000 ? (L / 1000) + ' km' : L + ' m';
}

// ---------- vues
function vueSur(x, y, dist, incl = 1.0, az = 0) {
  controls.target.set(x, 0, -y);
  camera.position.set(x + Math.sin(az) * dist * Math.cos(incl) , Math.sin(incl) * dist, -y + Math.cos(az) * dist * Math.cos(incl));
  controls.update();
}
const ctrCamp = (() => { const c = D.camping; return [c.reduce((a, p) => a + p[0], 0) / c.length, c.reduce((a, p) => a + p[1], 0) / c.length]; })();
const vueEnsemble = () => vueSur(cx - 60, cy - 120, 1150, 0.95);
const vueCamping = () => vueSur(ctrCamp[0], ctrCamp[1], 330, 0.8);

// ---------- éditeur
let modeEdition = false, historique = [], futur = [], glisse = null;
const CLE = 'maquette8_blocs';
function instantane() { return JSON.stringify(blocs); }
function sauver() { try { localStorage.setItem(CLE, instantane()); } catch (e) { } }
function pousserHistorique() { historique.push(instantane()); if (historique.length > 60) historique.shift(); futur = []; majBoutonsHisto(); }
function restaurer(s) { blocs = JSON.parse(s); if (selection >= blocs.length) selection = -1; reconstruireBlocs(); sauver(); if (trajetActif) calculerTrajet(); }
function majBoutonsHisto() { $('#bAnnuler').disabled = !historique.length; $('#bRetablir').disabled = !futur.length; }
function annuler() { if (!historique.length) return; futur.push(instantane()); restaurer(historique.pop()); majBoutonsHisto(); }
function retablir() { if (!futur.length) return; historique.push(instantane()); restaurer(futur.pop()); majBoutonsHisto(); }
function modif(fn) { if (selection < 0) return; pousserHistorique(); fn(blocs[selection]); reconstruireBlocs(); sauver(); if (trajetActif) calculerTrajet(); }
const dimsPts = (b) => { const xs = b.pts.map(p => p[0]), ys = b.pts.map(p => p[1]); return [Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)]; };
function majPanneauSelection() {
  const b = blocs[selection]; $('#selInfo').hidden = !b; $('#selVide').hidden = !!b;
  if (!b) return;
  const [w, l] = dimsPts(b); $('#selTxt').textContent = `${b.type} · ${fmt(w * b.sx)} × ${fmt(l * b.sy)} m · haut. ${fmt(b.h)} m${b.h_defaut ? ' (valeur par défaut)' : ''}`;
  $('#selType').value = b.type;
}
function basculerEdition(on) {
  modeEdition = on; $('#editPanneau').hidden = !on; $('#bModifier').classList.toggle('actif', on);
  if (on) { modeMesure = false; $('#bMesure').classList.remove('actif'); } else { selection = -1; reconstruireBlocs(); }
}
function pickBloc(ev) {
  const r = canvas.getBoundingClientRect(); ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hits = ray.intersectObjects([maillageBlocs, maillageSel], false);
  if (!hits.length) return -1;
  const h = hits[0];
  if (h.object === maillageSel) return selection;
  return indexSansSel[triVersBloc[h.faceIndex]] ?? -1;
}
canvas.addEventListener('pointerdown', (ev) => {
  if (modeEdition) {
    const i = pickBloc(ev);
    if (i >= 0) {
      if (i !== selection) { selection = i; reconstruireBlocs(); }
      const p = pointSol(ev); if (p) { glisse = { dx: blocs[selection].x - p.x, dy: blocs[selection].y - (-p.z), avant: instantane(), bouge: false }; controls.enabled = false; }
    } else if (selection >= 0) { selection = -1; reconstruireBlocs(); }
  }
  pointeurDebut = { x: ev.clientX, y: ev.clientY };
});
let pointeurDebut = null, rafBloque = false;
canvas.addEventListener('pointermove', (ev) => {
  if (!glisse) return;
  const p = pointSol(ev); if (!p) return;
  const b = blocs[selection], nx = Math.round((p.x + glisse.dx) * 2) / 2, ny = Math.round((-p.z + glisse.dy) * 2) / 2;
  if (nx !== b.x || ny !== b.y) { b.x = nx; b.y = ny; glisse.bouge = true; if (!rafBloque) { rafBloque = true; requestAnimationFrame(() => { rafBloque = false; reconstruireBlocs(); }); } }
});
addEventListener('pointerup', (ev) => {
  if (glisse) {
    if (glisse.bouge) { historique.push(glisse.avant); futur = []; majBoutonsHisto(); sauver(); reconstruireBlocs(); if (trajetActif) calculerTrajet(); }
    glisse = null; controls.enabled = true;
  } else if (modeMesure && pointeurDebut && ev.target === canvas && Math.hypot(ev.clientX - pointeurDebut.x, ev.clientY - pointeurDebut.y) < 6) {
    const p = pointSol(ev); if (p) ajouterMesure(p);
  }
  pointeurDebut = null;
});

// ---------- interface
function creerCalques() {
  const z = $('#calques'); z.innerHTML = '';
  for (const [k, nom] of Object.entries(NOMS)) {
    const l = document.createElement('label'); const c = document.createElement('input'); c.type = 'checkbox'; c.checked = calques[k].visible; c.id = 'cal_' + k;
    c.onchange = () => { calques[k].visible = c.checked; if (k === 'photo') { if (c.checked) chargerPhoto(); sol.visible = !c.checked; } };
    l.append(c, ' ' + nom); z.append(l);
  }
}
creerCalques();
TYPES.forEach(t => { const o = document.createElement('option'); o.value = o.textContent = t; $('#selType').append(o); });
$('#bEnsemble').onclick = vueEnsemble; $('#bCamping').onclick = vueCamping;
$('#bCalques').onclick = () => { $('#calques').hidden = !$('#calques').hidden; };
$('#bTrajet').onclick = () => { basculerTrajet(!trajetActif); $('#bTrajet').classList.toggle('actif', trajetActif); };
$('#bVitesse').onclick = () => { vit = vit === 1 ? 10 : vit === 10 ? 30 : 1; $('#bVitesse').textContent = '×' + vit; };
$('#bMesure').onclick = () => { modeMesure = !modeMesure; $('#bMesure').classList.toggle('actif', modeMesure); if (modeMesure) basculerEdition(false); if (!modeMesure) { mesurePts = []; groupeMesure.clear(); $('#mesureTxt').hidden = true; } $('#aideMesure').hidden = !modeMesure; };
$('#bModifier').onclick = () => { basculerEdition(!modeEdition); if (modeMesure) $('#bMesure').click(); };
$('#bAnnuler').onclick = annuler; $('#bRetablir').onclick = retablir;
$('#bRotG').onclick = () => modif(b => b.rot = (b.rot + 15) % 360); $('#bRotD').onclick = () => modif(b => b.rot = (b.rot - 15 + 360) % 360);
const redim = (axe, dm) => modif(b => { const [w, l] = dimsPts(b); const base = axe === 'x' ? w : l, cur = base * (axe === 'x' ? b.sx : b.sy); const nv = Math.max(1, cur + dm) / base; if (axe === 'x') b.sx = nv; else b.sy = nv; });
$('#bLarg1').onclick = () => redim('x', 0.5); $('#bLarg0').onclick = () => redim('x', -0.5);
$('#bLong1').onclick = () => redim('y', 0.5); $('#bLong0').onclick = () => redim('y', -0.5);
$('#bHaut1').onclick = () => modif(b => { b.h = Math.round((b.h + 0.5) * 2) / 2; b.h_defaut = false; });
$('#bHaut0').onclick = () => modif(b => { b.h = Math.max(0.5, Math.round((b.h - 0.5) * 2) / 2); b.h_defaut = false; });
$('#selType').onchange = (e) => modif(b => { b.type = e.target.value; b.confiance = 1; });
$('#bSuppr').onclick = () => { if (selection < 0) return; pousserHistorique(); blocs.splice(selection, 1); selection = -1; reconstruireBlocs(); sauver(); if (trajetActif) calculerTrajet(); };
$('#bAjout').onclick = () => {
  pousserHistorique(); const t = controls.target;
  blocs.push({ id: 'ajout-' + Date.now(), type: $('#selType').value || 'mobil-home', x: Math.round(t.x * 2) / 2, y: Math.round(-t.z * 2) / 2, rot: 0, sx: 1, sy: 1, h: 3, h_defaut: false, pts: [[-2, -4], [2, -4], [2, 4], [-2, 4]], usage: 'ajouté', aire: 32, confiance: 1 });
  selection = blocs.length - 1; reconstruireBlocs(); sauver();
};
$('#bExport').onclick = () => {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify({ version: 1, origine_l93: D.origine_l93, blocs }, null, 1)], { type: 'application/json' }));
  a.download = 'maquette-camping.json'; a.click();
};
$('#fImport').onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return;
  try { const j = JSON.parse(await f.text()); if (!Array.isArray(j.blocs)) throw 0; pousserHistorique(); blocs = j.blocs; selection = -1; reconstruireBlocs(); sauver(); }
  catch (er) { alert('Fichier non valide.'); }
  e.target.value = '';
};

// ---------- démarrage
try { const s = localStorage.getItem(CLE); if (s) blocs = JSON.parse(s); } catch (e) { }
reconstruireBlocs(); majBoutonsHisto(); majBoutonsHisto();
basculerTrajet(false); groupeTrajet.visible = false;
vueEnsemble();
function redim_() { const w = canvas.clientWidth, h = canvas.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
addEventListener('resize', redim_); redim_();
let tPrec = performance.now();
renderer.setAnimationLoop((t) => {
  const dt = Math.min((t - tPrec) / 1000, 0.1); tPrec = t;
  if (trajetActif && parcours) { tPion += dt * VITESSE_MARCHE * vit; if (tPion > parcours.total + 30) tPion = 0; placerPion(tPion); }
  etiqBlocs.forEach(e => { e.visible = camera.position.distanceTo(controls.target) < 650; }); controls.update(); majRegle(); majMarquesMesure();
  renderer.render(scene, camera);
});

// accès pour les contrôles automatiques (captures)
window.__maquette = { versEcran: (x, y, h = 0) => { const v = W3(x, y, h).project(camera); return [(v.x + 1) / 2 * canvas.clientWidth, (1 - v.y) / 2 * canvas.clientHeight]; }, vueSur, vueEnsemble, vueCamping, basculerTrajet, calques, chargerPhoto, camera, controls, get blocs() { return blocs; }, setTPion: (t) => { tPion = t; }, get parcours() { return parcours; }, pion, blocsInfo: () => ({ n: blocs.length, sel: selection }) };

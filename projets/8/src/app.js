import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const D = window.DONNEES;
const BLEU = 0x789CF2, ORANGE = 0xFE8D4F, JAUNE = 0xE6DB55, VERT = 0x4FB86A;
const TYPES = ['mobil-home', 'sanitaires', 'douches', 'accueil', 'bar', 'piscine', 'poubelles', 'local technique', 'emplacement', 'bâtiment'];
const TOITS = ['deux pans', 'quatre pans', 'plat'];
// couleurs par usage (légende)
const CATS = {
  residentiel: { nom: 'Bâtiments résidentiels', c: 0x6f8fe8 },
  accueil: { nom: 'Accueil', c: 0xe8504a },
  commerce: { nom: 'Commerces et services (bar, autres)', c: 0xf2c230 },
  sanitaires: { nom: 'Sanitaires, douches', c: 0x22b8a5 },
  sport: { nom: 'Sport (terrains, salles)', c: 0xe86fb0 },
  eau: { nom: 'Piscines', c: 0x2f6fe0 },
  annexe: { nom: 'Annexes (garages, locaux techniques)', c: 0x8d8d9d },
  hebergement: { nom: 'Hébergements (mobil-homes)', c: 0xa879e6 },
  autre: { nom: 'Autres bâtiments (usage non précisé)', c: 0xc9b99a },
};
const COULEURS_AUTRES = [
  ['Piscine couverte (voûte vitrée)', 0x7fd3ff], ['Parking (aire de gravier)', 0xe3cf9a], ['Zone des mobil-homes', 0xff9a3c], ['Zones boisées', 0x2f9e55], ['Arbres', 0x4FB86A], ['Routes', 0xfff3c4], ['Chemins et sentiers', 0xf0dca0],
  ['Clôtures, murets, portails', 0x8a5a3c], ['Haies', 0x3b7d3b], ['Limite du camping', 0xFE8D4F], ['Élément sélectionné', 0xFE8D4F],
];
function categorie(b) {
  const t = b.type;
  if (t === 'mobil-home' || t === 'emplacement') return 'hebergement';
  if (t === 'accueil') return 'accueil';
  if (t === 'sanitaires' || t === 'douches') return 'sanitaires';
  if (t === 'bar') return 'commerce';
  if (t === 'piscine') return 'eau';
  if (t === 'local technique' || t === 'poubelles') return 'annexe';
  const u = b.usage;
  if (u === 'Résidentiel') return 'residentiel';
  if (u === 'Commercial et services') return 'commerce';
  if (u === 'Sportif') return 'sport';
  if (u === 'Annexe') return 'annexe';
  return 'autre';
}
const nomBloc = (b) => b.type !== 'bâtiment' ? b.type : (b.usage && b.usage !== 'Indifférencié' && b.usage !== 'ajouté' ? 'bâtiment (' + b.usage.toLowerCase() + ')' : 'bâtiment');
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
const calques = { batiments: new THREE.Group(), arbres: new THREE.Group(), routes: new THREE.Group(), obstacles: new THREE.Group(), zones: new THREE.Group(), vegetation: new THREE.Group(), reperes: new THREE.Group(), etiquettes: new THREE.Group(), photo: new THREE.Group() };
for (const g of Object.values(calques)) scene.add(g);
calques.photo.visible = false;
const NOMS = { batiments: 'Bâtiments', arbres: 'Arbres', routes: 'Routes et chemins', obstacles: 'Clôtures et murets', zones: 'Zones (eau, sport, parking, mobil-homes)', vegetation: 'Zones boisées', reperes: 'Repères (piscine, accueil, entrée…)', etiquettes: 'Numéros', photo: 'Photo aérienne (vérification)' };

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

// routes et chemins : largeur forfaitaire par catégorie (la largeur réelle n'est pas dans les données), couleur claire
const LARGEURS = { 'primary': 7, 'Route à 1 chaussée': 5.5, 'Rond-point': 6, 'residential': 5, 'unclassified': 4.5, 'service': 3.5, 'Route empierrée': 3.5, 'track': 3, 'cycleway': 2.5, 'Sentier': 1.2, 'footway': 1.2, 'path': 1.2 };
const SENTIERS = ['Sentier', 'footway', 'path', 'cycleway', 'track'];
{
  const N = D.chemins.noeuds, parLarg = new Map();
  for (const [a, b, d, nat] of D.chemins.aretes) {
    const l = LARGEURS[nat] || 3.5, k = (SENTIERS.includes(nat) ? 'c' : 'r') + l;
    if (!parLarg.has(k)) parLarg.set(k, []);
    parLarg.get(k).push([N[a][0], N[a][1], N[b][0], N[b][1]]);
  }
  for (const [k, seg] of parLarg) {
    const l = +k.slice(1), coul = k[0] === 'c' ? 0xf0dca0 : 0xfff3c4, ordre = k[0] === 'c' ? 1 : 2;
    calques.routes.add(ruban(seg, l, coul, 0.05, 0.97, ordre));
    // disques aux jonctions : évitent les crans entre tronçons (ronds-points, virages)
    const pts = []; for (const [x1, y1, x2, y2] of seg) pts.push([x1, y1], [x2, y2]);
    const g = new THREE.CircleGeometry(l / 2, 10); g.rotateX(-Math.PI / 2);
    const im = new THREE.InstancedMesh(g, new THREE.MeshBasicMaterial({ color: coul, transparent: true, opacity: 0.97, polygonOffset: true, polygonOffsetFactor: -ordre, polygonOffsetUnits: -ordre }), pts.length);
    const mat = new THREE.Matrix4(); pts.forEach(([x, y], i) => im.setMatrixAt(i, mat.makeTranslation(x, 0.05, -y))); im.renderOrder = ordre;
    calques.routes.add(im);
  }
  const lim = D.camping, boucle = [];
  lim.forEach((p, i) => { const q = lim[(i + 1) % lim.length]; boucle.push([p[0], p[1], q[0], q[1]]); });
  calques.zones.add(ruban(boucle, 1.4, ORANGE, 0.12, 1, 3));
}

// zones : piscines (blocs bleus translucides), sport, végétation
const matBloc = new THREE.MeshLambertMaterial({ color: 0xffffff, vertexColors: true, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.DoubleSide });
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
const R = window.REPERES;
const centreZ = (z) => z.pts.reduce((a, p) => [a[0] + p[0] / z.pts.length, a[1] + p[1] / z.pts.length], [0, 0]);
let zonePiscineCouverte = null;
const pickables = [];     // mailles touchables (piscines, terrains de sport)
const ELEMENTS = [];     // éléments numérotés qui ne sont pas des blocs : { num, nom, cat, pts, h, lieu }
for (const z of D.zones) {
  if (z.type === 'piscine' && R && Math.hypot(centreZ(z)[0] - R.piscine.zone_centre[0], centreZ(z)[1] - R.piscine.zone_centre[1]) < 8) {
    z.nom = 'Piscine couverte'; z.voute = true; z.maille = null; zonePiscineCouverte = z;
  } else if (z.type === 'piscine') {
    const m = new THREE.Mesh(formeExtrudee(z.pts, z.h), new THREE.MeshLambertMaterial({ color: CATS.eau.c, transparent: true, opacity: 0.6, depthWrite: false, side: THREE.DoubleSide }));
    calques.zones.add(m, contour(z.pts, z.h, 0x1d3f9e), contour(z.pts, 0.02, 0x1d3f9e));
    z.maille = m; pickables.push(m);
  } else if (z.type === 'vegetation') {
    calques.vegetation.add(aplat(z.pts, 0x2f9e55, 0.3, 0.03), contour(z.pts, 0.04, 0x2f9e55));
  } else if (z.type === 'sport') {
    const m = aplat(z.pts, CATS.sport.c, 0.5, 0.04); calques.zones.add(m, contour(z.pts, 0.05, 0xb43c80)); z.maille = m; pickables.push(m);
  }
}

let matCime, matTronc;
// ---------- arbres : tronc brun + houppier vert translucides (maxima de canopée LiDAR HD), posés au sol
{
  const mat = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();
  matCime = new THREE.MeshLambertMaterial({ color: 0x4FB86A, transparent: true, opacity: 0.28, depthWrite: false }); matTronc = new THREE.MeshLambertMaterial({ color: 0x8a5a3c, transparent: true, opacity: 0.35, depthWrite: false });
  const cime = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 7, 5), matCime, D.arbres.length);
  const tronc = new THREE.InstancedMesh(new THREE.CylinderGeometry(1, 1, 1, 6), matTronc, D.arbres.length);
  D.arbres.forEach(([x, y, h], i) => {
    const r = Math.min(Math.max(h * 0.22, 1), 3.2) * 0.75, ht = h * 0.3;
    p.set(x, ht / 2, -y); s.set(Math.min(0.3, r / 4), ht / 2, Math.min(0.3, r / 4)); tronc.setMatrixAt(i, mat.compose(p, q, s));
    p.set(x, ht + (h - ht) / 2, -y); s.set(r, (h - ht) / 2, r); cime.setMatrixAt(i, mat.compose(p, q, s));   // de 0,3 h à h : jamais en l'air
  });
  calques.arbres.add(tronc, cime);
}

// ---------- obstacles : clôtures, murets, portails (brun), haies (vert foncé) ; hauteurs forfaitaires
{
  const O = window.OBSTACLES || [], segs = [];
  for (const o of O) for (let i = 1; i < o.pts.length; i++) segs.push([o.pts[i - 1], o.pts[i], o]);
  const boite = (couleur, liste) => {
    if (!liste.length) return;
    const im = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshLambertMaterial({ color: couleur, transparent: true, opacity: 0.7, depthWrite: false }), liste.length);
    const mat = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), sc = new THREE.Vector3();
    liste.forEach(([a, b, o], i) => {
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]) + 0.01;
      q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.atan2(b[1] - a[1], b[0] - a[0]));
      p.set((a[0] + b[0]) / 2, o.h / 2, -(a[1] + b[1]) / 2); sc.set(L, o.h, o.e); im.setMatrixAt(i, mat.compose(p, q, sc));
    });
    calques.obstacles.add(im);
  };
  boite(0x8a5a3c, segs.filter(s => s[2].type !== 'hedge')); boite(0x3b7d3b, segs.filter(s => s[2].type === 'hedge'));
}

// ---------- blocs (bâtiments) : un seul maillage fusionné, reconstruit à chaque modification
let blocs = JSON.parse(JSON.stringify(D.blocs));
let triVersBloc = [];
const maillageBlocs = new THREE.Mesh(new THREE.BufferGeometry(), matBloc);
const aretesBlocs = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0x14246b }));
const maillageSel = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshLambertMaterial({ color: ORANGE, transparent: true, opacity: 0.6, depthWrite: false, side: THREE.DoubleSide }));
const aretesSel = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xc25a12 }));
calques.batiments.add(maillageBlocs, aretesBlocs, maillageSel, aretesSel);
let selection = -1;

function anneau(b) {
  const c = Math.cos(b.rot * Math.PI / 180), s = Math.sin(b.rot * Math.PI / 180);
  return b.pts.map(([px, py]) => { const X = px * b.sx, Y = py * b.sy; return [b.x + X * c - Y * s, b.y + X * s + Y * c]; });
}
// rectangle orienté englobant (plus petite aire) : centre, axe long (ux,uy), longueur L, largeur l, taux de remplissage
function rectOriente(r) {
  let aire = 0; r.forEach((p, i) => { const q = r[(i + 1) % r.length]; aire += p[0] * q[1] - q[0] * p[1]; }); aire = Math.abs(aire) / 2;
  let best = null;
  r.forEach((p, i) => {
    const q = r[(i + 1) % r.length], L0 = Math.hypot(q[0] - p[0], q[1] - p[1]); if (L0 < 0.05) return;
    const ux = (q[0] - p[0]) / L0, uy = (q[1] - p[1]) / L0; let a0 = 1e9, a1 = -1e9, b0 = 1e9, b1 = -1e9;
    for (const [x, y] of r) { const u = x * ux + y * uy, v = -x * uy + y * ux; a0 = Math.min(a0, u); a1 = Math.max(a1, u); b0 = Math.min(b0, v); b1 = Math.max(b1, v); }
    const A = (a1 - a0) * (b1 - b0); if (!best || A < best.A) best = { A, ux, uy, a0, a1, b0, b1 };
  });
  const { ux, uy, a0, a1, b0, b1 } = best, ca = (a0 + a1) / 2, cb = (b0 + b1) / 2;
  let L = a1 - a0, l = b1 - b0, px = ux, py = uy;
  if (l > L) { [L, l] = [l, L]; px = -uy; py = ux; }
  return { cx: ca * ux + cb * -uy, cy: ca * uy + cb * ux, ux: px, uy: py, vx: -py, vy: px, L, l, fill: aire / best.A };
}
function toitAuto(b, ob) {
  if (b.type === 'poubelles' || b.type === 'local technique' || b.usage === 'Annexe' || ob.L * ob.l < 25 || ob.fill < 0.8) return 'plat';
  return ob.L / ob.l > 1.4 ? 'deux pans' : 'quatre pans';
}
const hautToit = (b, ob) => (b.toit === 'plat' ? 0 : Math.min(0.3 * ob.l, 4.5));   // pente ≈ 30° (faîte = 0,3 × largeur, au plus 4,5 m)
function geomBloc(b, pos, idx, lignes, tris, i, col) {
  const r = anneau(b), h = b.h, n = r.length, base = pos.length / 3, ob = rectOriente(r);
  if (!b.toit) b.toit = toitAuto(b, ob);
  const rise = hautToit(b, ob), cc = new THREE.Color(CATS[categorie(b)].c), cr = cc.clone().multiplyScalar(0.8);
  const poser = (x, y, z, c) => { pos.push(x, y, z); col.push(c.r, c.g, c.b); };
  r.forEach(([x, y]) => poser(x, h, -y, cc));
  r.forEach(([x, y]) => poser(x, 0, -y, cc));
  if (rise === 0) {
    const tri = THREE.ShapeUtils.triangulateShape(r.map(([x, y]) => new THREE.Vector2(x, y)), []);
    for (const [a, bb, c] of tri) { idx.push(base + a, base + c, base + bb); tris && tris.push(i); }
  }
  for (let k = 0; k < n; k++) {
    const k2 = (k + 1) % n;
    idx.push(base + k, base + n + k, base + k2, base + k2, base + n + k, base + n + k2); tris && tris.push(i, i);
    lignes.push(r[k][0], h, -r[k][1], r[k2][0], h, -r[k2][1], r[k][0], 0, -r[k][1], r[k2][0], 0, -r[k2][1], r[k][0], 0, -r[k][1], r[k][0], h, -r[k][1]);
  }
  if (rise > 0) {                                       // toit : 4 coins de l'égout + 2 points de faîtage
    const hip = b.toit === 'quatre pans', rl = hip ? Math.max(ob.L - ob.l, 0.02) / 2 : ob.L / 2;
    const P = (a, v, y) => [ob.cx + a * ob.ux + v * ob.vx, y, -(ob.cy + a * ob.uy + v * ob.vy)];
    const pts = [P(-ob.L / 2, -ob.l / 2, h), P(ob.L / 2, -ob.l / 2, h), P(ob.L / 2, ob.l / 2, h), P(-ob.L / 2, ob.l / 2, h), P(-rl, 0, h + rise), P(rl, 0, h + rise)];
    const b0 = pos.length / 3; pts.forEach(p => poser(p[0], p[1], p[2], cr));
    const faces = [[0, 1, 5], [0, 5, 4], [2, 3, 4], [2, 4, 5], [1, 2, 5], [3, 0, 4]];   // 2 pans + 2 pignons ou croupes
    for (const f of faces) { idx.push(b0 + f[0], b0 + f[1], b0 + f[2]); tris && tris.push(i); }
    for (const [a, c] of [[4, 5], [0, 4], [3, 4], [1, 5], [2, 5]]) lignes.push(...pts[a], ...pts[c]);
  }
}
function remplir(maille, aretes, liste, tris) {
  const pos = [], idx = [], lig = [], col = [];
  liste.forEach(([b, i]) => geomBloc(b, pos, idx, lig, tris, i, col));
  maille.geometry.dispose(); aretes.geometry.dispose();
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.setIndex(idx); g.computeVertexNormals();
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
// ---------- numérotation : éléments importants = pièces du camping, piscines, commerces et sport proches, plage
const dansPoly = ([x, y], P) => { let d = false; for (let i = 0, j = P.length - 1; i < P.length; j = i++) if ((P[i][1] > y) !== (P[j][1] > y) && x < (P[j][0] - P[i][0]) * (y - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0]) d = !d; return d; };
const distCamping = (p) => { const P = D.camping; let m = 1e9; P.forEach((a, i) => { m = Math.min(m, projSeg(p, a, P[(i + 1) % P.length])[2]); }); return dansPoly(p, P) ? 0 : m; };
const NUM = {}, NUMEROTES = [];      // NUM : id de bloc -> numéro ; NUMEROTES : { num, nom, cat, x, y, haut, ref }
{
  const cand = [];
  for (const z of D.zones) {
    const c = z.pts.reduce((a, p) => [a[0] + p[0] / z.pts.length, a[1] + p[1] / z.pts.length], [0, 0]);
    if (z.type === 'piscine' && z.dans_camping) cand.push([0, c[0], z, 'zone', z.nom || 'piscine', 'eau', c]);
    if (z.type === 'sport' && distCamping(c) < 300) cand.push([7, c[0], z, 'zone', z.nom || 'terrain de sport', 'sport', c]);
  }
  for (const b of D.blocs) {
    const d = distCamping([b.x, b.y]), t = b.type;
    const pr = t === 'accueil' ? 1 : (t === 'sanitaires' || t === 'douches' || t === 'bar') ? 2 : (t === 'local technique' || t === 'poubelles') ? 3 : t === 'mobil-home' ? 4 : d === 0 ? 5 : (b.usage === 'Commercial et services' || b.usage === 'Sportif') && d < 300 ? 6 : 99;
    if (pr < 99) cand.push([pr, b.x, b, 'bloc']);
  }
  cand.push([8, 0, null, 'lieu', 'Plage des Dunes', null, D.lieux['Plage des Dunes']]);
  cand.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  cand.forEach((c, k) => {
    const num = k + 1;
    if (c[3] === 'bloc') { NUM[c[2].id] = num; }
    else { const e = { num, nom: c[4], cat: c[5], x: c[6][0], y: c[6][1], haut: c[3] === 'zone' ? 4 : 4, ref: c[2], genre: c[3] }; NUMEROTES.push(e); if (c[2]) c[2].num = num; }
  });
}
{
  const c = D.camping, mx = c.reduce((a, p) => a + p[0], 0) / c.length, my = c.reduce((a, p) => a + p[1], 0) / c.length;
  const s = sprite('Camping Amitié & Nature', '#c25a12'); s.position.copy(W3(mx, my, 25)); labelFixes.push(s);
  for (const e of NUMEROTES) { const s2 = sprite(String(e.num), e.genre === 'lieu' ? '#c25a12' : '#1d3f9e'); s2.scale.multiplyScalar(1.3); s2.position.copy(W3(e.x, e.y, e.haut)); labelFixes.push(s2); }
}
labelFixes.forEach(s => groupeEtiq.add(s));

// ---------- repères et éléments posés d'après l'orthophoto (positions à confirmer)
const REPS = [], zonesRep = [], K_ECRAN = 1 / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));   // un sprite sans atténuation de taille : hauteur en pixels = échelle × K/2 × hauteur d'écran
function icone(x, type, cx0, cy0, r) {
  x.save(); x.translate(cx0, cy0); x.fillStyle = '#fff'; x.strokeStyle = '#fff'; x.lineWidth = 5; x.lineCap = 'round'; x.lineJoin = 'round';
  if (type === 'piscine') { for (const dy of [-8, 8]) { x.beginPath(); for (let t = -r * 0.6; t <= r * 0.6; t += 2) { const yy = dy + Math.sin(t / 5) * 4; t === -r * 0.6 ? x.moveTo(t, yy) : x.lineTo(t, yy); } x.stroke(); } }
  else if (type === 'accueil') { x.beginPath(); x.moveTo(-r * 0.6, -2); x.lineTo(0, -r * 0.6); x.lineTo(r * 0.6, -2); x.closePath(); x.fill(); x.fillRect(-r * 0.4, -2, r * 0.8, r * 0.55); }
  else if (type === 'entree') { x.rotate(-0.4); x.fillRect(-r * 0.7, -6, r * 1.4, 12); x.fillStyle = '#222'; for (let i = -3; i < 3; i++) x.fillRect(-r * 0.7 + (i + 3) * r * 0.24 + 4, -6, r * 0.11, 12); }
  else if (type === 'parking') { x.font = 'bold 46px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('P', 0, 3); }
  else { x.beginPath(); x.moveTo(-r * 0.62, 4); x.lineTo(-r * 0.4, -r * 0.35); x.lineTo(r * 0.4, -r * 0.35); x.lineTo(r * 0.62, 4); x.closePath(); x.fill(); x.fillRect(-r * 0.62, 4, r * 1.24, r * 0.3); }
  x.restore();
}
function reperSprite(nom, sous, type, couleur, ancre) {
  const c = document.createElement('canvas'), x = c.getContext('2d'), H = 100, r = 36;
  x.font = 'bold 44px sans-serif'; const w1 = x.measureText(nom).width; x.font = '26px sans-serif'; const w2 = sous ? x.measureText(sous).width : 0;
  const w = Math.ceil(Math.max(w1, w2)) + 2 * r + 36; c.width = w; c.height = H;
  x.fillStyle = 'rgba(255,255,255,0.93)'; x.beginPath(); x.roundRect(2, 2, w - 4, H - 4, 22); x.fill(); x.strokeStyle = couleur; x.lineWidth = 5; x.stroke();
  x.fillStyle = couleur; x.beginPath(); x.arc(14 + r, H / 2, r, 0, 7); x.fill(); icone(x, type, 14 + r, H / 2, r);
  x.textAlign = 'left'; x.textBaseline = 'middle'; x.fillStyle = '#14246b'; x.font = 'bold 44px sans-serif'; x.fillText(nom, 2 * r + 26, sous ? 36 : 52);
  if (sous) { x.fillStyle = '#5a5a6a'; x.font = '26px sans-serif'; x.fillText(sous, 2 * r + 26, 76); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, sizeAttenuation: false }));
  sp.scale.set(w / H * 0.04, 0.04, 1); sp.center.set(...ancre); sp.renderOrder = 12; return sp;
}
function ajouterRepere(nom, sous, type, couleur, x, y, haut, fiche, ancre = [0.5, 0]) {
  const s = reperSprite(nom, sous, type, couleur, ancre); s.position.copy(W3(x, y, haut)); calques.reperes.add(s);
  const g = new THREE.BufferGeometry().setFromPoints([W3(x, y, 0.1), W3(x, y, haut)]);
  calques.reperes.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: new THREE.Color(couleur) })));
  const pt = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 0.3, 16), new THREE.MeshBasicMaterial({ color: new THREE.Color(couleur) })); pt.position.copy(W3(x, y, 0.3)); calques.reperes.add(pt);
  REPS.push({ nom, x, y, haut, fiche, ancre: [...ancre], ancre0: ancre, sprite: s, ratio: s.scale.x / s.scale.y });
}
const A_CONFIRMER = 'position à confirmer sur place (relevée sur l\'orthophoto IGN)';
function zonePlate(pts, couleur, op, opPhoto, y, bord, fiche) {
  const m = aplat(pts, couleur, op, y); m.userData.fiche = fiche; calques.zones.add(m, contour(pts, y + 0.01, bord)); pickables.push(m); zonesRep.push({ mat: m.material, op, opPhoto });
}
if (R) {
  // piscine couverte : voûte vitrée (demi-ellipse extrudée), bleu clair très distinct
  const P = R.piscine, ang = P.angle * Math.PI / 180, ca = Math.cos(ang), sa = Math.sin(ang), N = 14;
  const pos = [], idx = [], ar = [];
  const pt = (u, v, h) => [P.x + v * ca - u * sa, h, -(P.y + v * sa + u * ca)];           // u : travers, v : long
  for (const v of [-P.L / 2, P.L / 2]) for (let i = 0; i <= N; i++) { const f = Math.PI * i / N; pos.push(...pt(-P.l / 2 * Math.cos(f), v, P.h * Math.sin(f))); }
  const w = N + 1;
  for (let i = 0; i < N; i++) { idx.push(i, i + 1, w + i, i + 1, w + i + 1, w + i); }
  const cA = pos.length / 3; pos.push(...pt(0, -P.L / 2, 0), ...pt(0, P.L / 2, 0));    // centres des deux pignons
  for (let i = 0; i < N; i++) { idx.push(cA, i + 1, i, cA + 1, w + i, w + i + 1); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  const voute = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ color: 0x7fd3ff, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.DoubleSide }));
  voute.userData.fiche = () => zonePiscineCouverte ? texteElement(NUMEROTES.find(e => e.ref === zonePiscineCouverte)) : '';
  for (let k = 0; k <= 8; k++) { const v = -P.L / 2 + P.L * k / 8; for (let i = 0; i < N; i++) { const f1 = Math.PI * i / N, f2 = Math.PI * (i + 1) / N; ar.push(...pt(-P.l / 2 * Math.cos(f1), v, P.h * Math.sin(f1)), ...pt(-P.l / 2 * Math.cos(f2), v, P.h * Math.sin(f2))); } }
  for (const [u, h] of [[-P.l / 2, 0], [P.l / 2, 0], [0, P.h]]) ar.push(...pt(u, -P.L / 2, h), ...pt(u, P.L / 2, h));
  const ag = new THREE.BufferGeometry(); ag.setAttribute('position', new THREE.Float32BufferAttribute(ar, 3));
  calques.zones.add(voute, new THREE.LineSegments(ag, new THREE.LineBasicMaterial({ color: 0x1b5fa0 })));
  pickables.push(voute); if (zonePiscineCouverte) zonePiscineCouverte.maille = voute;
  ajouterRepere('Piscine couverte', 'à confirmer', 'piscine', '#1f78d1', P.x, P.y, P.h + 12, () => `Piscine couverte<br>voûte vitrée d'environ ${fmt(P.L)} × ${fmt(P.l)} m, ${fmt(P.h)} m de haut<br>${A_CONFIRMER}`, [1, 0]);
  const a = R.accueil;
  ajouterRepere('Accueil', 'à confirmer', 'accueil', '#d63a32', a.x, a.y, 4, () => `Accueil<br>bâtiment à toit orange sous la piscine, probable accueil et bar<br>${A_CONFIRMER}`, [1, 1]);
  const e = R.entree;
  ajouterRepere('Entrée', 'à confirmer', 'entree', '#b07d00', e.x, e.y, 46, () => `Entrée<br>barrière jaune et noire sur la route qui longe le côté est<br>${A_CONFIRMER}`, [1, 0]);
  { // barrière : lattes jaunes et noires en travers de la voie
    const dx = e.b[0] - e.a[0], dy = e.b[1] - e.a[1], L = Math.hypot(dx, dy), n = 6;
    for (let i = 0; i < n; i++) { const m = new THREE.Mesh(new THREE.BoxGeometry(L / n, 1.1, 0.5), new THREE.MeshLambertMaterial({ color: i % 2 ? 0x222222 : 0xf5c800 })); m.position.copy(W3(e.a[0] + dx * (i + .5) / n, e.a[1] + dy * (i + .5) / n, 1.2)); m.rotation.y = Math.atan2(dy, dx); calques.reperes.add(m); }
  }
  const pk = R.parking, cen = (pts) => pts.reduce((q, p) => [q[0] + p[0] / pts.length, q[1] + p[1] / pts.length], [0, 0]);
  const aire = (pts) => airePoly(pts);
  const fPk = () => `Parking (aire de gravier)<br>environ ${Math.round(aire(pk.pts) + aire(pk.pts2))} m² · ${A_CONFIRMER}`;
  zonePlate(pk.pts, 0xe3cf9a, 0.8, 0.22, 0.08, 0xb09a5c, fPk); zonePlate(pk.pts2, 0xe3cf9a, 0.8, 0.22, 0.08, 0xb09a5c, fPk);
  const cp = cen(pk.pts); ajouterRepere('Parking', 'à confirmer', 'parking', '#3b5bb5', cp[0], cp[1], 8, fPk, [0, 0]);
  const mh = R.mobilhomes;
  zonePlate(mh.pts, 0xff9a3c, 0.2, 0.08, 0.07, 0xe0802a, () => `Mobil-homes<br>zone boisée, environ ${Math.round(aire(mh.pts))} m² · mobil-homes à placer un par un par le gérant<br>${A_CONFIRMER}`);
  const cm = cen(mh.pts); ajouterRepere('Mobil-homes', 'à placer un par un par le gérant', 'mobil', '#d9731a', cm[0], cm[1], 16, () => `Mobil-homes<br>zone boisée : mobil-homes à placer un par un par le gérant<br>${A_CONFIRMER}`);
}
const numBloc = (b) => b.num ?? NUM[b.id];
let etiqBlocs = [];
function majEtiquettes() {
  etiqBlocs.forEach(s => { groupeEtiq.remove(s); s.material.map.dispose(); s.material.dispose(); }); etiqBlocs = [];
  blocs.forEach(b => {
    const n = numBloc(b); if (!n) return;
    const ob = rectOriente(anneau(b)); if (!b.toit) b.toit = toitAuto(b, ob);
    const s = sprite(String(n)); s.scale.multiplyScalar(1.3); s.position.copy(W3(b.x, b.y, b.h + hautToit(b, ob) + 2)); groupeEtiq.add(s); etiqBlocs.push(s);
  });
  majListe();
}

// ---------- photo aérienne IGN (chargée à la demande ; incorporée en base64 pour fonctionner hors ligne)
let photoChargee = false;
function chargerPhoto() {
  if (photoChargee) return; photoChargee = true;
  const sc2 = document.createElement('script'); sc2.src = 'donnees/orthophoto_camping.js';
  sc2.onload = () => {
    const C = window.ORTHO_CAMPING;
    new THREE.TextureLoader().load(C.img, (t) => {
      t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
      const p = new THREE.Mesh(new THREE.PlaneGeometry(C.x1 - C.x0, C.y1 - C.y0), new THREE.MeshBasicMaterial({ map: t }));
      p.rotation.x = -Math.PI / 2; p.position.set((C.x0 + C.x1) / 2, 0.04, -(C.y0 + C.y1) / 2); calques.photo.add(p); window.__photoCampPrete = true;
    });
  }; document.head.appendChild(sc2);
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
  controls.update(); camera.updateMatrixWorld();
}
const ctrCamp = (() => { const c = D.camping; return [c.reduce((a, p) => a + p[0], 0) / c.length, c.reduce((a, p) => a + p[1], 0) / c.length]; })();
const vueEnsemble = () => vueSur(cx - 60, cy - 120, 1150, 0.95);
// vue de départ : centrée sur le camping, inclinée à 45°, la plus proche possible (≥ 150 m) qui garde tout le contour dans la zone libre de l'écran (hors barre de boutons)
function vueCamping() {
  const W = canvas.clientWidth, H = canvas.clientHeight, incl = Math.PI / 4;
  const yHaut = 1 - 2 * 50 / H, yBas = -1 + 2 * ($('#barre').offsetHeight + 10) / H, xm = 1 - 2 * 10 / W, yc = (yHaut + yBas) / 2, yh = (yHaut - yBas) / 2;
  const xs = D.camping.map(p => p[0]), ys = D.camping.map(p => p[1]);
  let tx = (Math.min(...xs) + Math.max(...xs)) / 2, ty = (Math.min(...ys) + Math.max(...ys)) / 2, d = 150;
  const sol_ = (nx, ny) => { ray.setFromCamera(new THREE.Vector2(nx, ny), camera); const o = new THREE.Vector3(); return ray.ray.intersectPlane(sol0, o) ? o : null; };
  for (d = 150; d < 2600; d *= 1.02) {
    let b;
    for (let k = 0; k < 4; k++) {
      vueSur(tx, ty, d, incl);
      b = [1e9, -1e9, 1e9, -1e9]; for (const p of D.camping) { const v = W3(p[0], p[1], 0).project(camera); b = [Math.min(b[0], v.x), Math.max(b[1], v.x), Math.min(b[2], v.y), Math.max(b[3], v.y)]; }
      const p1 = sol_((b[0] + b[1]) / 2, (b[2] + b[3]) / 2), p2 = sol_(0, yc); if (!p1 || !p2) break;
      tx += p1.x - p2.x; ty += -(p1.z - p2.z);
    }
    vueSur(tx, ty, d, incl); b = [1e9, -1e9, 1e9, -1e9]; for (const p of D.camping) { const v = W3(p[0], p[1], 0).project(camera); b = [Math.min(b[0], v.x), Math.max(b[1], v.x), Math.min(b[2], v.y), Math.max(b[3], v.y)]; }
    if ((b[1] - b[0]) / 2 <= xm && (b[3] - b[2]) / 2 <= yh) break;
  }
}

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
const airePoly = (r) => { let a = 0; r.forEach((p, i) => { const q = r[(i + 1) % r.length]; a += p[0] * q[1] - q[0] * p[1]; }); return Math.abs(a) / 2; };
function texteBloc(b) {
  const r = anneau(b), ob = rectOriente(r), rise = hautToit(b, ob), n = numBloc(b);
  return `${n ? 'n° ' + n + ' · ' : ''}${nomBloc(b)}<br>longueur ${fmt(ob.L)} m × largeur ${fmt(ob.l)} m (rectangle englobant) · emprise ${Math.round(airePoly(r))} m²<br>hauteur des murs ${fmt(b.h)} m${b.h_defaut ? ' (valeur par défaut)' : ''} · ` +
    (rise ? `faîte ${fmt(b.h + rise)} m (toit à ${b.toit})` : 'toit plat');
}
function texteElement(e) {
  if (e.genre === 'lieu') return `n° ${e.num} · ${e.nom}<br>lieu repère (position seulement, pas de mesure)`;
  const ob = rectOriente(e.ref.pts);
  return `n° ${e.num} · ${e.nom}<br>longueur ${fmt(ob.L)} m × largeur ${fmt(ob.l)} m (rectangle englobant) · surface ${Math.round(airePoly(e.ref.pts))} m²` + (e.ref.voute ? `<br>voûte vitrée de ${fmt(R.piscine.h)} m de haut (représentation) · position à confirmer (calée sur l'orthophoto IGN)` : e.ref.type === 'piscine' ? `<br>bloc de ${fmt(e.ref.h)} m de haut (représentation ; profondeur inconnue)` : '');
}
function montrerFiche(html) { $('#ficheTxt').innerHTML = html; $('#fiche').hidden = false; }
function majPanneauSelection() {
  const b = blocs[selection]; $('#selInfo').hidden = !b; $('#selVide').hidden = !!b;
  if (!b) return;
  $('#selTxt').innerHTML = texteBloc(b);
  $('#selType').value = b.type;
}
function basculerEdition(on) {
  modeEdition = on; $('#editPanneau').hidden = !on; if (on) { fermerDroite(); $('#fiche').hidden = true; } $('#bModifier').classList.toggle('actif', on);
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
function toucher(ev) {
  const r = canvas.getBoundingClientRect(); ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  if (calques.reperes.visible) {
    const r2 = canvas.getBoundingClientRect(); let best = null;
    for (const q of REPS) {
      const v = W3(q.x, q.y, q.haut).project(camera); if (v.z > 1) continue;
      const hs = 0.04 * K_ECRAN * r2.height / 2, ws = hs * q.ratio, ex = (v.x + 1) / 2 * r2.width + r2.left + (0.5 - q.ancre[0]) * ws, ey = (1 - v.y) / 2 * r2.height + r2.top - (0.5 - q.ancre[1]) * hs;   // centre du cartouche
      const d = Math.hypot(ev.clientX - ex, ev.clientY - ey); if (Math.abs(ev.clientX - ex) < ws / 2 + 4 && Math.abs(ev.clientY - ey) < hs / 2 + 4 && (!best || d < best[0])) best = [d, q];
    }
    if (best) { montrerFiche(best[1].fiche()); return; }
  }
  const cibles = [maillageBlocs, ...pickables.filter(m => m.visible && m.parent && m.parent.visible)];
  const h = ray.intersectObjects(cibles, false)[0];
  if (!h) { $('#fiche').hidden = true; return; }
  if (h.object === maillageBlocs) { const b = blocs[indexSansSel[triVersBloc[h.faceIndex]]]; if (b) montrerFiche(texteBloc(b)); }
  else if (h.object.userData.fiche && !D.zones.find(z => z.maille === h.object)) montrerFiche(h.object.userData.fiche());
  else { const z = D.zones.find(z => z.maille === h.object), e = NUMEROTES.find(e => e.ref === z); if (e) montrerFiche(texteElement(e)); else montrerFiche(`${z.type}<br>surface ${Math.round(airePoly(z.pts))} m²`); }
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
  } else if (!modeMesure && !modeEdition && pointeurDebut && ev.target === canvas && Math.hypot(ev.clientX - pointeurDebut.x, ev.clientY - pointeurDebut.y) < 6) {
    toucher(ev);
  } else if (modeMesure && pointeurDebut && ev.target === canvas && Math.hypot(ev.clientX - pointeurDebut.x, ev.clientY - pointeurDebut.y) < 6) {
    const p = pointSol(ev); if (p) ajouterMesure(p);
  }
  pointeurDebut = null;
});

// ---------- interface
function fermerDroite() { ['#calques', '#legende', '#liste'].forEach(i => $(i).hidden = true); ['#bCalques', '#bLegende', '#bListe'].forEach(i => $(i).classList.remove('actif')); }
function ouvrirDroite(p, bt) { const etait = !$(p).hidden; fermerDroite(); if (modeEdition) basculerEdition(false); if (!etait) { $(p).hidden = false; $(bt).classList.add('actif'); if (p === '#liste') majListe(); } }
const hex = (c) => '#' + c.toString(16).padStart(6, '0');
{
  let h = '<b>Légende</b>';
  for (const k of Object.keys(CATS)) h += `<div class="lg"><i style="background:${hex(CATS[k].c)}"></i>${CATS[k].nom}</div>`;
  for (const [n, c] of COULEURS_AUTRES) h += `<div class="lg"><i style="background:${hex(c)}"></i>${n}</div>`;
  h += '<small>Piscine couverte, accueil, entrée, parking et zone des mobil-homes : positions relevées sur l\'orthophoto IGN, à confirmer sur place. Toits : deux ou quatre pans (pente ≈ 30°), plats pour les petites annexes. Les chiffres renvoient à la liste.</small>';
  $('#legende').innerHTML = h;
}
function majListe() {
  if ($('#liste').hidden) return;
  const l = [];
  for (const b of blocs) { const n = numBloc(b); if (n) l.push({ n, nom: nomBloc(b), c: CATS[categorie(b)].c, x: b.x, y: b.y, html: () => texteBloc(b) }); }
  for (const e of NUMEROTES) l.push({ n: e.num, nom: e.nom, c: e.cat ? CATS[e.cat].c : ORANGE, x: e.x, y: e.y, html: () => texteElement(e) });
  l.sort((a, b) => a.n - b.n);
  const z = $('#listeCorps'); z.innerHTML = '';
  for (const e of l) {
    const d = document.createElement('div'); d.className = 'lg cliquable'; d.innerHTML = `<i style="background:${hex(e.c)}"></i><b>${e.n}</b>&nbsp;${e.nom}`;
    d.onclick = () => { vueSur(e.x, e.y, 70, 0.9); montrerFiche(e.html()); };
    z.append(d);
  }
}
function setCalque(k, v) {
  calques[k].visible = v; const c = $('#cal_' + k); if (c) c.checked = v;
  if (k === 'photo') { if (v) chargerPhoto(); sol.visible = !v; }
}
// « Photo / Maquette » : la photo IGN nette sous des blocs très transparents, sans routes ni zones boisées coloriées ni arbres qui la cachent
let modePhoto = false;
function basculerPhoto(on) {
  modePhoto = on; $('#bPhoto').classList.toggle('actif', on);
  setCalque('photo', on); setCalque('routes', !on); setCalque('vegetation', !on);
  matBloc.opacity = on ? 0.2 : 0.5; matCime.opacity = on ? 0.1 : 0.28; matTronc.opacity = on ? 0.1 : 0.35;
  zonesRep.forEach(z => { z.mat.opacity = on ? z.opPhoto : z.op; });
}
function creerCalques() {
  const z = $('#calques'); z.innerHTML = '';
  for (const [k, nom] of Object.entries(NOMS)) {
    const l = document.createElement('label'); const c = document.createElement('input'); c.type = 'checkbox'; c.checked = calques[k].visible; c.id = 'cal_' + k;
    c.onchange = () => setCalque(k, c.checked);
    l.append(c, ' ' + nom); z.append(l);
  }
}
creerCalques();
TYPES.forEach(t => { const o = document.createElement('option'); o.value = o.textContent = t; $('#selType').append(o); });
$('#bPhoto').onclick = () => basculerPhoto(!modePhoto); $('#bReperes').onclick = () => { setCalque('reperes', !calques.reperes.visible); $('#bReperes').classList.toggle('actif', calques.reperes.visible); };
$('#bReperes').classList.add('actif');
$('#bEnsemble').onclick = vueEnsemble; $('#bCamping').onclick = vueCamping;
$('#bCalques').onclick = () => ouvrirDroite('#calques', '#bCalques'); $('#bLegende').onclick = () => ouvrirDroite('#legende', '#bLegende'); $('#bListe').onclick = () => ouvrirDroite('#liste', '#bListe'); $('#bFermerFiche').onclick = () => { $('#fiche').hidden = true; };
$('#bToit').onclick = () => modif(b => { b.toit = TOITS[(TOITS.indexOf(b.toit) + 1) % TOITS.length]; });
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
  blocs.push({ id: 'ajout-' + Date.now(), type: $('#selType').value || 'mobil-home', x: Math.round(t.x * 2) / 2, y: Math.round(-t.z * 2) / 2, rot: 0, sx: 1, sy: 1, h: 3, h_defaut: false, pts: [[-2, -4], [2, -4], [2, 4], [-2, 4]], usage: 'ajouté', aire: 32, confiance: 1, toit: 'plat', num: Math.max(0, ...NUMEROTES.map(e => e.num), ...blocs.map(numBloc).filter(Boolean)) + 1 });
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
function redim_() { const w = canvas.clientWidth, h = canvas.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
addEventListener('resize', redim_); redim_();
vueCamping();
let tPrec = performance.now();
renderer.setAnimationLoop((t) => {
  const dt = Math.min((t - tPrec) / 1000, 0.1); tPrec = t;
  if (trajetActif && parcours) { tPion += dt * VITESSE_MARCHE * vit; if (tPion > parcours.total + 30) tPion = 0; placerPion(tPion); }
  { // les cartouches des repères restent entièrement dans l'écran (ancre ajustée)
    const W = canvas.clientWidth, H = canvas.clientHeight;
    for (const q of REPS) {
      const sp = q.sprite, v = W3(q.x, q.y, q.haut).project(camera), wn = sp.scale.x * K_ECRAN * H / W; let ax = q.ancre0[0];
      if (v.x - ax * wn < -0.97) ax = (v.x + 0.97) / wn; if (v.x + (1 - ax) * wn > 0.97) ax = 1 - (0.97 - v.x) / wn;
      sp.center.x = q.ancre[0] = Math.min(Math.max(ax, 0), 1);
    }
  }
  etiqBlocs.forEach(e => { e.visible = camera.position.distanceTo(controls.target) < 650; }); controls.update(); majRegle(); majMarquesMesure();
  renderer.render(scene, camera);
});

// accès pour les contrôles automatiques (captures)
window.__maquette = { basculerPhoto, setCalque, REPS, versEcran: (x, y, h = 0) => { const v = W3(x, y, h).project(camera); return [(v.x + 1) / 2 * canvas.clientWidth, (1 - v.y) / 2 * canvas.clientHeight]; }, vueSur, vueEnsemble, vueCamping, basculerTrajet, calques, chargerPhoto, camera, controls, get blocs() { return blocs; }, setTPion: (t) => { tPion = t; }, get parcours() { return parcours; }, pion, NUMEROTES, texteBloc, categorie, rectOriente, anneau, blocsInfo: () => ({ n: blocs.length, sel: selection }) };

"""Prépare les données de la maquette à partir des fichiers bruts (BD TOPO, OSM, LiDAR HD dérivé).
Usage : python3 scripts/preparer.py   (depuis projets/8)"""
import json, math, collections
import numpy as np, tifffile
from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, LineString, Point, mapping
from shapely.ops import transform, unary_union
from scipy import ndimage
from scipy.spatial import cKDTree

T = Transformer.from_crs(4326, 2154, always_xy=True)
BBOX_L93 = (328599.0, 6622081.0, 329637.0, 6623354.0)   # emprise des rasters (MNH, MNT, ortho)
W, H = 2076, 2546
OX, OY = 329100.0, 6622700.0                             # origine du repère local (m, Lambert-93)
def loc(x, y): return (x - OX, y - OY)
def to_local(geom): return transform(lambda x, y, z=None: loc(*T.transform(x, y)), geom)
def charge(n): return json.load(open(f'donnees/brut_{n}.json'))
def r1(v): return round(v, 1)

# ---------- OSM : camping, piscines, voies
osm = charge('osm')['elements']
def osm_geom(e):
    if e['type'] == 'node': return Point(e['lon'], e['lat'])
    if e['type'] == 'way' and 'geometry' in e:
        pts = [(p['lon'], p['lat']) for p in e['geometry']]
        return Polygon(pts) if pts[0] == pts[-1] and len(pts) > 3 else LineString(pts)
    if e['type'] == 'relation':
        outer = [[(p['lon'], p['lat']) for p in m['geometry']] for m in e['members'] if m['role'] == 'outer' and 'geometry' in m]
        from shapely.ops import polygonize
        ps = list(polygonize([LineString(o) for o in outer if len(o) > 1]))
        return unary_union(ps) if ps else None
camp = None; piscines = []; poubelles = []; wc = []; resto = []
for e in osm:
    t = e.get('tags', {}); g = osm_geom(e)
    if g is None: continue
    if t.get('tourism') == 'camp_site' and 'mitié' in t.get('name', ''): camp = to_local(g)
    if t.get('leisure') == 'swimming_pool' and g.geom_type == 'Polygon':
        piscines.append({'poly': to_local(g), 'interieure': t.get('location') == 'indoor'})
    if t.get('amenity') in ('waste_basket', 'waste_disposal'): poubelles.append(to_local(g))
    if t.get('amenity') == 'toilets': wc.append(to_local(g))
    if t.get('amenity') == 'restaurant': resto.append(to_local(g))
print('camping OSM', camp.bounds, 'piscines', len(piscines), 'poubelles', len(poubelles), 'wc', len(wc), 'resto', len(resto))

# ---------- Bâtiments BD TOPO
bat = charge('batiment')['features']
HAUT_DEFAUT = 3.0
blocs = []; sans_h = 0
for f in bat:
    g = to_local(shape(f['geometry']))
    if g.geom_type == 'MultiPolygon': g = max(g.geoms, key=lambda p: p.area)
    if g.is_empty or g.area < 2: continue
    p = f['properties']; h = p.get('hauteur')
    defaut = h is None
    if defaut: sans_h += 1; h = HAUT_DEFAUT
    c = g.centroid
    ring = [(r1(x - c.x), r1(y - c.y)) for x, y in g.simplify(0.15).exterior.coords[:-1]]
    blocs.append({'id': f['properties']['cleabs'], 'type': 'bâtiment', 'x': r1(c.x), 'y': r1(c.y), 'rot': 0,
                  'sx': 1, 'sy': 1, 'h': round(h, 1), 'h_defaut': defaut, 'pts': ring,
                  'usage': p.get('usage_1'), 'aire': round(g.area, 1), 'confiance': 1.0, '_g': g})
print('bâtiments', len(blocs), 'sans hauteur', sans_h)

# ---------- Classement automatique dans le camping (champ confiance)
dans = [b for b in blocs if camp.contains(b['_g'].centroid)]
print('dans le camping', len(dans), sorted(b['aire'] for b in dans)[::max(1, len(dans)//15)])
indoor = [p for p in piscines if p['interieure']]
gros = sorted(dans, key=lambda b: -b['aire'])
for b in dans:
    if 12 <= b['aire'] <= 45: b['type'], b['confiance'] = 'mobil-home', 0.5
    elif b['aire'] < 12: b['type'], b['confiance'] = 'local technique', 0.3
    else: b['type'], b['confiance'] = 'bâtiment', 0.4
for b in dans:
    for pz in indoor:
        if b['_g'].buffer(1).contains(pz['poly'].centroid) and b['aire'] > 60:
            b['type'], b['confiance'] = 'piscine', 0.7          # piscine couverte (OSM location=indoor)
for b in dans:
    if b['_g'].distance(camp.exterior) < 15 and b['aire'] > 25 and b['type'] == 'mobil-home' and False: pass
for b in dans:
    for r in resto:
        if b['_g'].buffer(3).intersects(r if r.geom_type != 'Point' else r.buffer(1)):
            b['type'], b['confiance'] = 'bar', 0.4
for b in dans:
    for w in wc:
        if b['_g'].buffer(3).intersects(w.buffer(1)): b['type'], b['confiance'] = 'sanitaires', 0.5
acc = [b for b in gros if b['type'] == 'bâtiment' and b['aire'] > 60]
if acc: acc[0]['type'], acc[0]['confiance'] = 'accueil', 0.3

# ---------- Zones : piscines (blocs translucides de 1 m), contour du camping, terrains de sport, végétation
zones = []
def poly_pts(g): return [[r1(x), r1(y)] for x, y in g.exterior.coords[:-1]]
for pz in piscines:
    zones.append({'type': 'piscine', 'h': 1.0, 'dans_camping': bool(camp.buffer(30).contains(pz['poly'].centroid)),
                  'interieure': pz['interieure'], 'pts': poly_pts(pz['poly'])})
for f in charge('terrain_de_sport')['features']:
    g = to_local(shape(f['geometry']))
    g = max(g.geoms, key=lambda p: p.area) if g.geom_type == 'MultiPolygon' else g
    if f['properties'].get('nature') == 'Bassin de natation': continue  # déjà couvert par OSM
    zones.append({'type': 'sport', 'nom': f['properties'].get('nature'), 'h': 0.0, 'pts': poly_pts(g)})
for f in charge('zone_de_vegetation')['features']:
    g = to_local(shape(f['geometry']))
    for p in (g.geoms if g.geom_type == 'MultiPolygon' else [g]):
        if p.area > 100 and f['properties'].get('nature') != 'Haie': zones.append({'type': 'vegetation', 'nom': f['properties'].get('nature'), 'h': 0.0, 'pts': poly_pts(p)})
limite = poly_pts(camp)

# ---------- Arbres : maxima locaux du MNH (LiDAR HD) hors bâtiments
mnh = tifffile.imread('brut_raster/MNH.tif'); mnt = tifffile.imread('brut_raster/MNT.tif')
res = (BBOX_L93[2] - BBOX_L93[0]) / W                      # ≈ 0,5 m / pixel
def px2loc(c, r): return (BBOX_L93[0] + (c + .5) * res - OX, BBOX_L93[3] - (r + .5) * res - OY)
from PIL import Image, ImageDraw
mask = Image.new('L', (W, H), 0); d = ImageDraw.Draw(mask)
for b in blocs:
    gg = b['_g'].buffer(1.5)
    for p in (gg.geoms if gg.geom_type == 'MultiPolygon' else [gg]):
        d.polygon([((x + OX - BBOX_L93[0]) / res, (BBOX_L93[3] - (y + OY)) / res) for x, y in p.exterior.coords], fill=1)
mask = np.array(mask).astype(bool)
sm = ndimage.gaussian_filter(np.clip(mnh, 0, 40), 2.0)
loc_max = (sm == ndimage.maximum_filter(sm, size=11)) & (sm > 2.5) & ~mask
rr, cc = np.nonzero(loc_max)
arbres = []
for r, c in zip(rr, cc):
    x, y = px2loc(c, r)
    h = float(mnh[r, c:c+1].max()) if False else float(np.max(mnh[max(r-2,0):r+3, max(c-2,0):c+3]))
    arbres.append([r1(x), r1(y), round(h, 1)])
print('arbres', len(arbres), 'hauteur médiane', np.median([a[2] for a in arbres]))
for b in blocs: b.pop('_g')

# ---------- Réseau de chemins (BD TOPO troncon_de_route + OSM highway)
lignes = []   # (LineString local, source, nature, voiture)
for f in charge('troncon_de_route')['features']:
    p = f['properties']
    if p['nature'] == 'Bac ou liaison maritime': continue
    g = to_local(shape(f['geometry']))
    for l in (g.geoms if g.geom_type == 'MultiLineString' else [g]):
        voiture = p['nature'] != 'Sentier' and p.get('acces_vehicule_leger') != 'Physiquement impossible'
        lignes.append((LineString([(x, y) for x, y, *_ in l.coords]), 'BDTOPO', p['nature'], voiture))
for e in charge('osm_voies')['elements']:
    t = e['tags']; h = t.get('highway')
    if h in ('steps',) : pass
    g = to_local(LineString([(p['lon'], p['lat']) for p in e['geometry']]))
    lignes.append((g, 'OSM', h, h in ('service', 'residential', 'unclassified', 'track', 'primary') and t.get('motor_vehicle') != 'no'))
print('lignes', len(lignes), collections.Counter((l[1], l[2]) for l in lignes))
# nœuds : on découpe aux sommets, puis on fusionne les sommets à moins de 1,5 m
liens = json.load(open('donnees/liens.json'))
for l in liens['liens']:
    lignes.append((LineString([tuple(l['de']), tuple(l['a'])]), 'LIEN', 'lien manuel', l.get('voiture', False)))
noeuds = []; aretes = []
def nid(pt): noeuds.append(pt); return len(noeuds) - 1
seg = []
for g, src, nat, v in lignes:
    cs = list(g.coords)
    for a, b in zip(cs[:-1], cs[1:]):
        if math.dist(a, b) > 0.05: seg.append((a, b, src, nat, v))
# intersections : on ajoute un sommet là où une extrémité de ligne est proche (<2 m) d'un segment d'une autre ligne
pts = [s[0] for s in seg] + [s[1] for s in seg]
tree = cKDTree(pts)
par = list(range(len(pts)))
def find(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for i, j in tree.query_pairs(1.5): par[find(i)] = find(j)
cluster = {}; 
for i, p in enumerate(pts):
    cluster.setdefault(find(i), []).append(p)
rep = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in cluster.items()}
ids = {}; N = []
def get(i):
    k = find(i)
    if k not in ids: ids[k] = len(N); N.append(rep[k])
    return ids[k]
n = len(seg); E = {}
for s_i, (a, b, src, nat, v) in enumerate(seg):
    u, w = get(s_i), get(s_i + n)
    if u == w: continue
    key = (min(u, w), max(u, w))
    d = math.dist(N[u], N[w])
    if key in E: E[key]['voiture'] = E[key]['voiture'] or v
    else: E[key] = {'a': key[0], 'b': key[1], 'd': round(d, 1), 'nat': nat, 'src': src, 'voiture': bool(v)}
# jonctions en T : un nœud à moins de 2 m de l'intérieur d'une arête coupe cette arête en deux
elist = list(E.values())
segs = [LineString([N[e['a']], N[e['b']]]) for e in elist]
st = STRtree(segs) if False else None
from shapely.strtree import STRtree
st = STRtree(segs)
coupes = collections.defaultdict(list)
for ni, p in enumerate(N):
    P = Point(p)
    best = None
    for si in st.query(P.buffer(2.0)):
        e = elist[si]
        if ni in (e['a'], e['b']): continue
        dd = segs[si].distance(P)
        t = segs[si].project(P)
        if dd < 2.0 and 1.0 < t < segs[si].length - 1.0 and (best is None or dd < best[0]): best = (dd, si, t)
    if best: coupes[best[1]].append((best[2], ni))
E = {}
def ajoute(u, w, e):
    key = (min(u, w), max(u, w))
    if u != w and key not in E: E[key] = {'a': key[0], 'b': key[1], 'd': round(math.dist(N[u], N[w]), 1), 'nat': e['nat'], 'src': e['src'], 'voiture': e['voiture']}
for si, e in enumerate(elist):
    chaine = [e['a']] + [ni for _, ni in sorted(coupes.get(si, []))] + [e['b']]
    for u, w in zip(chaine[:-1], chaine[1:]): ajoute(u, w, e)
aretes = list(E.values())
# composantes connexes
adj = collections.defaultdict(list)
for e in aretes: adj[e['a']].append(e['b']); adj[e['b']].append(e['a'])
seen = {}; comp = 0; tailles = []
for s in range(len(N)):
    if s in seen: continue
    st_ = [s]; seen[s] = comp; cnt = 0
    while st_:
        u = st_.pop(); cnt += 1
        for w in adj[u]:
            if w not in seen: seen[w] = comp; st_.append(w)
    tailles.append(cnt); comp += 1
print('nœuds', len(N), 'arêtes', len(aretes), 'composantes', sorted(tailles)[::-1][:8])
chemins = {'noeuds': [[r1(x), r1(y)] for x, y in N], 'aretes': [[e['a'], e['b'], e['d'], e['nat'], e['src'], int(e['voiture'])] for e in aretes]}

# ---------- Lieux (position approx., à corriger) : plage, piscine couverte, accueil, mobil-home
def pos(b): return [b['x'], b['y']]
lieux = {}
for nom, typ in (('Accueil', 'accueil'),):
    c = [b for b in blocs if b['type'] == typ]
    if c: lieux[nom] = pos(c[0])
pc = [z for z in zones if z['type'] == 'piscine' and z['dans_camping']]
if pc:
    g = Polygon(max(pc, key=lambda z: Polygon(z['pts']).area)['pts']).centroid
    lieux['Piscine'] = [r1(g.x), r1(g.y)]
# Aucun mobil-home n'existe dans la BD TOPO : un exemple est ajouté à la main (position relevée sur l'orthophoto)
blocs.append({'id': 'exemple-mobil-home', 'type': 'mobil-home', 'x': 195.0, 'y': 423.0, 'rot': 0, 'sx': 1, 'sy': 1, 'h': 3.0,
              'h_defaut': True, 'pts': [(-1.6, -3.3), (1.6, -3.3), (1.6, 3.3), (-1.6, 3.3)], 'usage': 'ajouté à la main', 'aire': 21.1, 'confiance': 0.3})
lieux['Mobil-home exemple'] = [195.0, 423.0]
px, py = loc(*T.transform(-1.8526, 46.5975)); lieux['Plage des Dunes'] = [r1(px), r1(py)]

# ---------- Sortie
sortie = {'origine_l93': [OX, OY], 'bbox_l93': list(BBOX_L93), 'camping': limite, 'blocs': blocs, 'arbres': arbres,
          'zones': zones, 'chemins': chemins, 'lieux': lieux,
          'ortho': {'fichier': 'donnees/orthophoto.jpg', 'x0': BBOX_L93[0] - OX, 'y0': BBOX_L93[1] - OY, 'x1': BBOX_L93[2] - OX, 'y1': BBOX_L93[3] - OY}}
for nom in ('blocs', 'arbres', 'zones', 'chemins', 'lieux'):
    json.dump(sortie[nom], open(f'donnees/{nom}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(sortie['camping'], open('donnees/camping.json', 'w'))
open('donnees/donnees.js', 'w').write('window.DONNEES=' + json.dumps(sortie, ensure_ascii=False, separators=(',', ':')) + ';window.LIENS=' + json.dumps(liens, ensure_ascii=False) + ';')
print(collections.Counter(b['type'] for b in blocs))
print(lieux)

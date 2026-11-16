"""Repères posés à la main d'après l'orthophoto IGN (positions à confirmer sur place) + orthophoto haute résolution du camping.
Écrit donnees/reperes.js et donnees/orthophoto_camping.js. Usage : python3 scripts/reperes.py (depuis projets/8 ; brut_raster/ortho_camping.jpg requis)"""
import json, math, base64, io
from shapely.geometry import Polygon, box
from PIL import Image
r1 = lambda v: round(v, 1)
camp = Polygon(json.load(open('donnees/camping.json')))
zones = json.load(open('donnees/zones.json'))
blocs = json.load(open('donnees/blocs.json'))

# --- piscine couverte : voûte vitrée posée sur le bassin OSM couvert, même axe, 12 × 29 m, 5 m de haut
pz = [z for z in zones if z['type'] == 'piscine' and z.get('dans_camping')]
pz = max(pz, key=lambda z: Polygon(z['pts']).area)
rect = list(Polygon(pz['pts']).minimum_rotated_rectangle.exterior.coords)[:4]
cote = [(math.dist(rect[i], rect[(i + 1) % 4]), i) for i in range(4)]
Lc, i = max(cote)
a, b = rect[i], rect[(i + 1) % 4]
ux, uy = (b[0] - a[0]) / Lc, (b[1] - a[1]) / Lc
c = Polygon(rect).centroid
piscine = {'nom': 'Piscine couverte', 'x': r1(c.x), 'y': r1(c.y), 'angle': round(math.degrees(math.atan2(uy, ux)), 1), 'L': 29.0, 'l': 12.0, 'h': 5.0,
           'zone_centre': [r1(Polygon(pz['pts']).centroid.x), r1(Polygon(pz['pts']).centroid.y)]}

# --- accueil : bâtiment BD TOPO à toit orange sous la piscine (déjà typé « accueil »)
acc = [b for b in blocs if b['type'] == 'accueil'][0]
accueil = {'nom': 'Accueil', 'x': acc['x'], 'y': acc['y']}

# --- entrée : barrière jaune et noire sur la route est (relevée sur l'orthophoto)
entree = {'nom': 'Entrée', 'x': 263.5, 'y': 437.5, 'a': [262.0, 434.5], 'b': [265.0, 440.5]}

# --- aire de gravier : polygone au sol relevé sur l'orthophoto
gravier = [[128, 462], [150, 458], [170, 454], [186, 451], [189, 445], [175, 441], [150, 438], [131, 437], [128, 444]]
sud = [[108, 424], [128, 424], [128, 403], [112, 402], [108, 410]]   # prolongement clair au sud de l'accueil
parking = {'nom': 'Parking', 'pts': gravier, 'pts2': sud}
pk = Polygon(gravier)

# --- zone des mobil-homes : grand carré boisé à l'est du parking, découpé sur le contour du camping
zm = box(190, 340, 275, 446).intersection(camp)
zm = max(zm.geoms, key=lambda p: p.area) if zm.geom_type == 'MultiPolygon' else zm
zone_mh = {'nom': 'Mobil-homes', 'pts': [[r1(x), r1(y)] for x, y in zm.exterior.coords[:-1]]}

# --- orthophoto haute résolution : x 20..290, y 290..520 (10 px/m) réduite à 8 px/m
im = Image.open('brut_raster/ortho_camping.jpg').convert('RGB')
im = im.resize((2160, 1840), Image.LANCZOS)
buf = io.BytesIO(); im.save(buf, 'JPEG', quality=80)
open('donnees/orthophoto_camping.js', 'w').write('window.ORTHO_CAMPING={"x0":20,"y0":290,"x1":290,"y1":520,"img":"data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode() + '"};')
R = {'piscine': piscine, 'accueil': accueil, 'entree': entree, 'parking': parking, 'mobilhomes': zone_mh,
     'commentaire': 'Positions relevées sur l\'orthophoto IGN, à confirmer sur place.'}
open('donnees/reperes.js', 'w').write('window.REPERES=' + json.dumps(R, ensure_ascii=False, separators=(',', ':')) + ';')
print(piscine, 'zone mh', round(zm.area), 'm²', 'gravier', round(pk.area), 'm²')

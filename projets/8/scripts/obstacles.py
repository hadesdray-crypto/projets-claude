# Obstacles (clôtures, murets, haies, portails) d'OpenStreetMap -> donnees/obstacles.js (repère local, mètres).
# Usage : python3 scripts/obstacles.py   (depuis projets/8, après recuperer.sh)
import json
from pyproj import Transformer
T = Transformer.from_crs(4326, 2154, always_xy=True)
OX, OY = 329100.0, 6622700.0
HAUT = {'fence': 1.5, 'wall': 1.0, 'retaining_wall': 1.0, 'hedge': 1.5, 'gate': 1.5}   # hauteurs forfaitaires (non mesurées)
EPAIS = {'fence': 0.15, 'wall': 0.3, 'retaining_wall': 0.4, 'hedge': 1.0, 'gate': 0.2}
res = []
for e in json.load(open('donnees/brut_osm_barrieres.json'))['elements']:
    b = e['tags']['barrier']
    pts = [[round(x - OX, 1), round(y - OY, 1)] for x, y in (T.transform(p['lon'], p['lat']) for p in e['geometry'])]
    res.append({'type': b, 'h': HAUT[b], 'e': EPAIS[b], 'pts': pts})
open('donnees/obstacles.js', 'w').write('window.OBSTACLES=' + json.dumps(res, separators=(',', ':')) + ';')
print(len(res), 'obstacles', sum(len(r['pts']) for r in res), 'points')

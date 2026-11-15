"""Mesure la précision des blocs : empreintes BD TOPO contre (1) toits orange de l'orthophoto, (2) hauteurs LiDAR HD (MNH).
Écrit les résultats chiffrés dans precision_mesures.json (repris dans precision.md)."""
import json, numpy as np, tifffile
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import Polygon
BB = (328599.0, 6622081.0, 329637.0, 6623354.0); W, H = 2076, 2546; OX, OY = 329100.0, 6622700.0; res = (BB[2]-BB[0])/W
blocs = [b for b in json.load(open('donnees/blocs.json')) if b['id'] != 'exemple-mobil-home']
mnh = tifffile.imread('brut_raster/MNH.tif'); mnt = tifffile.imread('brut_raster/MNT.tif')
ortho = np.array(Image.open('donnees/orthophoto.jpg').convert('RGB')).astype(int)
def px(x, y): return ((x + OX - BB[0]) / res, (BB[3] - (y + OY)) / res)
def poly(b): return Polygon([(b['x'] + p[0], b['y'] + p[1]) for p in b['pts']])
def masque(g):
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([px(*p) for p in g.exterior.coords], fill=1); return np.array(m).astype(bool)
R, G, B = ortho[..., 0], ortho[..., 1], ortho[..., 2]
orange = (R > 120) & (R - G > 28) & (R - B > 45)
res_or, res_mnh, dh = [], [], []
for b in blocs:
    g = poly(b)
    if g.area < 50: continue
    x0, y0, x1, y1 = [int(v) for v in (min(px(*p)[0] for p in g.exterior.coords) - 12, min(px(*p)[1] for p in g.exterior.coords) - 12, max(px(*p)[0] for p in g.exterior.coords) + 12, max(px(*p)[1] for p in g.exterior.coords) + 12)]
    if x0 < 0 or y0 < 0 or x1 >= W or y1 >= H: continue
    fp = masque(g)[y0:y1, x0:x1]; gb = masque(g.buffer(3))[y0:y1, x0:x1]
    # (1) toits orange
    o = orange[y0:y1, x0:x1]; inside = (o & fp).sum() / fp.sum()
    if inside > 0.45:
        lab, n = ndimage.label(o & gb); 
        if n:
            k = np.argmax(ndimage.sum(o & fp, lab, range(1, n + 1))) + 1; roof = lab == k
            if roof.sum() > 0.5 * fp.sum():
                cy, cx = ndimage.center_of_mass(roof); fy, fx = ndimage.center_of_mass(fp)
                inter = (roof & fp).sum(); iou = inter / (roof | fp).sum()
                res_or.append(((cx - fx) * res, -(cy - fy) * res, iou))
    # (2) MNH : hauteur max dans l'empreinte vs hauteur BD TOPO
    m = mnh[y0:y1, x0:x1]; h = np.percentile(m[fp], 90)
    if not b['h_defaut']: dh.append(h - b['h'])
a = np.array(res_or)
sortie = {'toits_orange': {'n': len(a), 'decalage_est_moy_m': float(a[:, 0].mean()), 'decalage_nord_moy_m': float(a[:, 1].mean()),
          'decalage_median_m': float(np.median(np.hypot(a[:, 0], a[:, 1]))), 'decalage_p90_m': float(np.percentile(np.hypot(a[:, 0], a[:, 1]), 90)), 'iou_median': float(np.median(a[:, 2]))},
          'hauteur_lidar_moins_bdtopo': {'n': len(dh), 'mediane_m': float(np.median(dh)), 'ecart_abs_median_m': float(np.median(np.abs(dh))), 'ecart_abs_p90_m': float(np.percentile(np.abs(dh), 90))}}
D = json.load(open('donnees/blocs.json'))
hs = [b['h'] for b in D if not b['h_defaut']]
sortie['hauteurs'] = {'batiments': len(D) - 1, 'avec_hauteur': len(hs), 'valeur_par_defaut_3m': sum(b['h_defaut'] for b in D if b['id'] != 'exemple-mobil-home'),
                      'min': min(hs), 'mediane': float(np.median(hs)), 'max': max(hs)}
ar = json.load(open('donnees/arbres.json'))
sortie['arbres'] = {'n': len(ar), 'h_mediane': float(np.median([a[2] for a in ar])), 'h_max': max(a[2] for a in ar), 'h_p90': float(np.percentile([a[2] for a in ar], 90))}
cp = json.load(open('donnees/camping.json')); g = Polygon([px(*[p[0], p[1]]) for p in cp]); mk = Image.new('L', (W, H), 0); ImageDraw.Draw(mk).polygon(list(g.exterior.coords), fill=1); mk = np.array(mk).astype(bool)
sortie['relief_camping_MNT_m'] = {'min': float(mnt[mk].min()), 'max': float(mnt[mk].max()), 'p5': float(np.percentile(mnt[mk], 5)), 'p95': float(np.percentile(mnt[mk], 95))}
sortie['relief_zone_MNT_m'] = {'min': float(mnt.min()), 'max': float(mnt.max())}
json.dump(sortie, open('precision_mesures.json', 'w'), indent=1, ensure_ascii=False); print(json.dumps(sortie, indent=1, ensure_ascii=False))

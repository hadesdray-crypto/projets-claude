#!/bin/bash
# Télécharge les données ouvertes (IGN, OpenStreetMap) dans donnees/brut_* et brut_raster/ (non versionnés).
# Usage : bash scripts/recuperer.sh   (depuis projets/8)
set -e
mkdir -p donnees brut_raster
B="-1.8545,46.5960,-1.8420,46.6080"
for t in batiment troncon_de_route zone_de_vegetation surface_hydrographique terrain_de_sport zone_d_activite_ou_d_interet haie construction_ponctuelle; do
  curl -sf -o donnees/brut_$t.json "https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=BDTOPO_V3:$t&OUTPUTFORMAT=application/json&BBOX=$B,EPSG:4326&COUNT=5000"
done
R="BBOX=328599,6622081,329637,6623354&WIDTH=2076&HEIGHT=2546&CRS=EPSG:2154&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES="
for L in MNH MNT; do
  curl -sf -o brut_raster/$L.tif "https://data.geopf.fr/wms-r?$R&LAYERS=IGNF_LIDAR-HD_${L}_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93&FORMAT=image/geotiff"
done
curl -sf -o donnees/orthophoto.jpg "https://data.geopf.fr/wms-r?$R&LAYERS=ORTHOIMAGERY.ORTHOPHOTOS&FORMAT=image/jpeg"
BX="(46.596,-1.8545,46.608,-1.842)"
ov() { curl -sf -m 80 -H "User-Agent: maquette-camping/1.0" -H "Accept: */*" --data-urlencode "data=$1" https://overpass-api.de/api/interpreter -o "$2"; }
ov "[out:json][timeout:40];(nwr[\"tourism\"~\"camp_site|camp_pitch\"]$BX;nwr[\"natural\"=\"tree\"]$BX;nwr[\"leisure\"=\"swimming_pool\"]$BX;nwr[\"amenity\"~\"toilets|waste_basket|waste_disposal|bar|restaurant\"]$BX;);out geom;" donnees/brut_osm.json
ov "[out:json][timeout:40];way[\"highway\"]$BX;out geom;" donnees/brut_osm_voies.json

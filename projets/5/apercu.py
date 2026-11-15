"""Aperçu d'une pose : python3 apercu.py <pose> [sortie.png]  (outil de mise au point)."""
import json, sys, os
import numpy as np
from PIL import Image
import moteur

def main():
    pose = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else '/tmp/apercu_%s.png' % pose
    poses = pose.split(',')
    imgs = []
    for p in poses:
        seq = {"nom": "_apercu", "duree": 1.0, "recettes": {}, "pistes": {"thomas": [{"pose": p, "tenir": 1.0}]}}
        json.dump(seq, open('sequences/_apercu.json', 'w'))
        s = moteur.Scene(sequence='_apercu')
        for i in range(40):
            im = s.image(i / 30.0)
        imgs.append(np.clip(np.round(im), 0, 255).astype(np.uint8))
    os.remove('sequences/_apercu.json')
    Image.fromarray(np.concatenate(imgs, 1)).save(out)
main()

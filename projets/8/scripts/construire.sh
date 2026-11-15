#!/bin/bash
# Reconstruit app.js (Three.js + src/app.js empaquetés, aucune dépendance réseau à l'exécution).
# Usage : bash scripts/construire.sh   (depuis projets/8 ; nécessite Node et npm)
set -e
D=$(mktemp -d); cp -r src "$D/src"; cd "$D"; npm init -y >/dev/null; npm i three esbuild >/dev/null 2>&1
./node_modules/.bin/esbuild src/app.js --bundle --minify --format=iife --outfile="$OLDPWD/app.js"

// Fabrique icones/icone-192.png et icone-512.png depuis icones/icone.svg (Chrome sans écran).
// Usage (depuis projets/10) : NODE_PATH=<dossier avec puppeteer-core>/node_modules node scripts/icones.js
const puppeteer = require('puppeteer-core'), path = require('path'), P = process.cwd();
(async () => {
  const b = await puppeteer.launch({ executablePath: process.env.CHROME || '/usr/bin/chromium', headless: 'new', args: ['--no-sandbox'] });
  const p = await b.newPage();
  for (const t of [192, 512]) {
    await p.setViewport({ width: 512, height: 512, deviceScaleFactor: t / 512 });
    await p.goto('file://' + path.join(P, 'icones/icone.svg'));
    await p.screenshot({ path: path.join(P, `icones/icone-${t}.png`) });
  }
  await b.close();
})();

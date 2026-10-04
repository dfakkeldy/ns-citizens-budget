// Paginate a flow HTML file in headless Chrome and print it to PDF.
// usage: node render.js <flow.html> <paged.html> <out.pdf> <pagemap.json> <pageW px> <pageH px>
// Chrome: $CHROME, else the usual macOS and Linux locations.
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');

const CANDIDATES = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
].filter(Boolean);
const CHROME = CANDIDATES.find(p => fs.existsSync(p));

(async () => {
  const [flow, paged, pdf, mapOut, w, h] = process.argv.slice(2);
  const W = parseInt(w || '816', 10), H = parseInt(h || '1056', 10);
  if (!CHROME) throw new Error('Chrome not found; set CHROME=/path/to/chrome');
  const browser = await puppeteer.launch({executablePath: CHROME, headless: true,
    args: ['--allow-file-access-from-files', '--font-render-hinting=none']});
  const page = await browser.newPage();
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warn') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  page.on('requestfailed', r => console.error('[missing]', r.url()));
  await page.setViewport({width: W, height: H, deviceScaleFactor: 1});
  await page.emulateMediaType('print');
  await page.goto('file://' + path.resolve(flow), {waitUntil: 'load', timeout: 120000});
  await page.evaluate(async () => { await document.fonts.ready; });
  const t0 = Date.now();
  await page.evaluate(() => window.__paginate());
  await page.waitForFunction(() => document.body.dataset.done === '1', {timeout: 600000});
  console.error(`paginated in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  const map = await page.evaluate(() => document.getElementById('pagemap').textContent);
  fs.writeFileSync(mapOut, map);
  // Save the paginated DOM without the paginator script, for checks and specimens.
  const html = await page.evaluate(() => {
    const clone = document.documentElement.cloneNode(true);
    clone.querySelectorAll('script[data-paginator]').forEach(s => s.remove());
    return '<!doctype html>\n' + clone.outerHTML;
  });
  fs.writeFileSync(paged, html);
  await page.pdf({path: pdf, width: `${W / 96}in`, height: `${H / 96}in`, printBackground: true,
    margin: {top: 0, right: 0, bottom: 0, left: 0}, outline: true, tagged: true, preferCSSPageSize: false});
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });

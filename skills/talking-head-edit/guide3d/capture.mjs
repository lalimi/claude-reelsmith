import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

async function resolveChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  try { const pp = await import('puppeteer'); const p = (pp.default || pp).executablePath(); if (p) return p; } catch {}
  return undefined;
}

const root = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(root, 'frames');
const fps = Number(process.env.FPS || 30);
const only = process.env.AT ? process.env.AT.split(',').map(Number) : null;
fs.mkdirSync(outDir, { recursive: true });

const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(root) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({
  executablePath: await resolveChrome(),
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on('console', m => console.log('page:', m.text()));
page.on('pageerror', e => console.log('pageerror:', e.message));
await page.goto(`http://127.0.0.1:${port}/index.html`);
await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });

const dur = await page.evaluate(() => window.DURATION);
const times = only || Array.from({ length: Math.round(dur * fps) }, (_, i) => i / fps);
const t0 = Date.now();
for (let i = 0; i < times.length; i++) {
  await page.evaluate(t => window.renderAt(t), times[i]);
  const name = only ? `still_${times[i].toFixed(2)}.png` : `f_${String(i).padStart(4, '0')}.png`;
  await page.screenshot({ path: path.join(outDir, name) });
  if (i % 30 === 0) console.log(`frame ${i}/${times.length} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
await browser.close();
server.close();

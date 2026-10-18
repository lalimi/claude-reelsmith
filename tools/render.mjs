import { chromium } from 'playwright';
import { spawn } from 'child_process';
const [dir, mode, out, fpsArg] = process.argv.slice(2);
const fps = +(fpsArg || 30);
const browser = await chromium.launch({ ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}), args: ['--force-color-profile=srgb'] });
const page = await browser.newPage({ viewport: { width: +(process.env.W||1920), height: +(process.env.H||1080) }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('PAGEERR', e.message));
page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
await page.goto('file://' + dir + '/' + (process.env.PAGE||'index.html'));
await page.evaluate(() => window.ready);
await page.waitForTimeout(300);
if (mode === 'stills') {
  const times = out.split(',').map(Number);
  for (const t of times) {
    await page.evaluate(t => window.render(t), t);
    await page.screenshot({ path: `${dir}/stills/t_${t.toFixed(2)}.jpg`, type: 'jpeg', quality: 80 });
  }
} else {
  const dur = await page.evaluate(() => window.DUR);
  const n = Math.round(dur * fps);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.render(t), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log('frame', i, '/', n);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
}
await browser.close();

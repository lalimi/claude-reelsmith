// Render the reel: scene.html -> PNG frames (Playwright, time set per frame) -> reel.mp4 (ffmpeg).
//
//   node source/render.mjs                    # mode B: typographic reel on brand backgrounds, silent AAC
//   node source/render.mjs --video my.mp4     # mode A: the creator's video underneath, its own sound
//   node source/render.mjs --audio vo.m4a     # mode B with a recorded voice-over instead of silence
//   node source/render.mjs --stills 1,5,12,20 # only check frames into source/stills/
//   --out other.mp4 writes the video elsewhere, --workers N sets parallel browser pages (3)
//
// Mode A also starts by itself when input/lalita.mp4 exists, the voice-over when input/voiceover.m4a
// (.mp3, .wav) exists; input/ is looked up in the reel folder, then in the current directory.
// Writes reel.mp4 and cover-slide-01.png into the reel folder.
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const SRC = path.dirname(fileURLToPath(import.meta.url));
const REEL = path.resolve(SRC, '..');
const FPS = 30;

const args = process.argv.slice(2);
const opt = name => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const stills = opt('--stills');
const workers = +(opt('--workers') || 3);
let video = opt('--video');
if (!video) video = [path.join(REEL, 'input/lalita.mp4'), path.resolve('input/lalita.mp4')].find(f => fs.existsSync(f)) || null;
const mode = video ? 'video' : 'brand';
const inputs = names => names.flatMap(n => [path.join(REEL, 'input', n), path.resolve('input', n)]).find(f => fs.existsSync(f)) || null;
const audio = opt('--audio') || (video ? null : inputs(['voiceover.m4a', 'voiceover.mp3', 'voiceover.wav']));

const sh = (cmd, a) => execFileSync(cmd, a, { stdio: ['ignore', 'pipe', 'inherit'] }).toString();

async function openPage(browser, m) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  await page.goto(pathToFileURL(path.join(SRC, 'scene.html')).href + `?mode=${m}`);
  const dur = await page.evaluate(() => window.__ready);
  return { page, dur };
}

async function shot(page, t, file, alpha) {
  await page.evaluate(t => window.__seek(t), t);
  await page.screenshot({ path: file, type: 'png', omitBackground: alpha });
}

async function main(browser) {
  const brand = await openPage(browser, 'brand');
  const DUR = brand.dur;
  const N = Math.round(DUR * FPS);

  if (stills) {
    console.log(await brand.page.evaluate(() => [...document.querySelectorAll('.head,.numline')].map(e => `${e.id} ${e.style.fontSize} y ${e.offsetTop}-${e.offsetTop + e.offsetHeight}`).join('\n')));
    const dir = path.join(SRC, 'stills');
    fs.mkdirSync(dir, { recursive: true });
    const pg = mode === 'video' ? (await openPage(browser, 'video')).page : brand.page;
    for (const s of stills.split(',').map(Number)) {
      const f = path.join(dir, `t${s.toFixed(2).padStart(5, '0')}.png`);
      await shot(pg, s, f, mode === 'video');
      console.log(f);
    }
    return;
  }

  // cover = the composition at t = 0, the same state as the first video frame
  await shot(brand.page, 0, path.join(REEL, 'cover-slide-01.png'), false);
  console.log('cover-slide-01.png');

  const frames = path.join(SRC, 'frames');
  fs.rmSync(frames, { recursive: true, force: true });
  fs.mkdirSync(frames, { recursive: true });
  const pages = [mode === 'video' ? (await openPage(browser, 'video')).page : brand.page];
  while (pages.length < workers) pages.push((await openPage(browser, mode)).page);
  const started = Date.now();
  await Promise.all(pages.map(async (pg, w) => {
    for (let i = w; i < N; i += pages.length) {
      await shot(pg, i / FPS, path.join(frames, `f${String(i).padStart(4, '0')}.png`), mode === 'video');
      if (w === 0 && i % 90 === 0) console.log(`frame ${i}/${N}`);
    }
  }));
  console.log(`${N} frames in ${((Date.now() - started) / 1000).toFixed(0)} s, mode ${mode}`);
  await browser.close();

  const out = path.resolve(opt('--out') || path.join(REEL, 'reel.mp4'));
  const enc = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
    '-level:v', '4.1', '-r', String(FPS), '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-movflags', '+faststart'];
  const framesIn = ['-framerate', String(FPS), '-i', path.join(frames, 'f%04d.png')];

  if (mode === 'brand') {
    // silent track by default; a recorded voice-over is levelled to -14 LUFS and padded or cut to the reel length
    const aIn = audio ? ['-i', audio] : ['-f', 'lavfi', '-t', String(DUR), '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000'];
    const aFx = audio ? ['-af', `loudnorm=I=-14:TP=-1.5:LRA=11,apad,atrim=0:${DUR}`] : [];
    console.log(audio ? `voice-over: ${audio}` : 'no voice-over: silent AAC track');
    sh('ffmpeg', ['-y', '-v', 'error', ...framesIn, ...aIn, '-map', '0:v', '-map', '1:a', ...aFx, '-tune', 'animation', ...enc, '-t', String(DUR), out]);
  } else {
    // creator's video: cover-crop to 1080x1920, speed 0.9-1.1 to fit, ink .35 for legibility, text on top
    const probe = JSON.parse(sh('ffprobe', ['-v', 'error', '-show_entries', 'format=duration:stream=codec_type', '-of', 'json', video]));
    const dur = +probe.format.duration;
    const hasAudio = probe.streams.some(s => s.codec_type === 'audio');
    const speed = Math.min(1.1, Math.max(0.9, dur / DUR));
    console.log(`video ${dur.toFixed(2)} s -> speed x${speed.toFixed(3)}${hasAudio ? '' : ', no audio track: silent'}`);
    const fv = `[0:v]setpts=PTS/${speed},fps=${FPS},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,` +
      `tpad=stop_mode=clone:stop_duration=${DUR},trim=0:${DUR},setpts=PTS-STARTPTS,drawbox=x=0:y=0:w=iw:h=ih:color=0x0c0f0e@0.35:t=fill[bg];` +
      `[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v];`;
    const fa = hasAudio ? `[0:a]atempo=${speed},apad,atrim=0:${DUR},asetpts=PTS-STARTPTS[a]` : `anullsrc=channel_layout=stereo:sample_rate=48000,atrim=0:${DUR}[a]`;
    sh('ffmpeg', ['-y', '-v', 'error', '-i', video, ...framesIn, '-filter_complex', fv + fa, '-map', '[v]', '-map', '[a]', ...enc, '-t', String(DUR), out]);
  }
  console.log(sh('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_name,width,height,r_frame_rate,pix_fmt:format=duration,size', '-of', 'compact', out]));
}

const browser = await chromium.launch();
try {
  await main(browser);
} finally {
  await browser.close().catch(() => {});
}

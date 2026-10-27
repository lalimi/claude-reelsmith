// Render the reel: scene.html -> PNG frames (Playwright, time set per frame) -> reel.mp4 (ffmpeg).
//
//   node source/render.mjs                    # brand backgrounds + the ElevenLabs voice-over (assets/voice)
//   node source/render.mjs --silent           # same, without voice: 22 s, silent AAC track
//   node source/render.mjs --audio vo.m4a     # your own recording instead of the ElevenLabs voice
//   node source/render.mjs --video my.mp4     # mode A: the creator's video underneath, its own sound
//   node source/render.mjs --stills 1,5,12,20 # only check frames into source/stills/
//   --out other.mp4 writes the video elsewhere (subtitles are then not rewritten),
//   --voice-file x.mp3 uses another file with the same word timings, --workers N parallel pages (3)
//
// input/lalita.mp4 starts mode A, input/voiceover.m4a (.mp3, .wav) counts as --audio; input/ is looked
// up in the reel folder, then in the current directory. Writes reel.mp4, cover-slide-01.png and, with
// the ElevenLabs voice, reel-subtitles.srt into the reel folder.
//
// ElevenLabs voice: assets/voice/voiceover.json holds the take (url, settings) and its word timings.
// The mp3 is downloaded once to assets/voice/voiceover.mp3, every pause longer than 0.3 s is shortened
// to 0.3 s, and the screens, accent pops, typing and subtitles are placed on the spoken words.
import { createRequire } from 'node:module';
import { execFileSync, spawnSync } from 'node:child_process';
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
const flag = name => args.includes(name);
const stills = opt('--stills');
const workers = +(opt('--workers') || 3);
const outArg = opt('--out');
const inputs = names => names.flatMap(n => [path.join(REEL, 'input', n), path.resolve('input', n)]).find(f => fs.existsSync(f)) || null;
const video = opt('--video') || inputs(['lalita.mp4']);
const mode = video ? 'video' : 'brand';
const audio = video || flag('--silent') ? null : opt('--audio') || inputs(['voiceover.m4a', 'voiceover.mp3', 'voiceover.wav']);

const VOICE_JSON = path.join(REEL, 'assets/voice/voiceover.json');
const VOICE_MP3 = path.join(REEL, 'assets/voice/voiceover.mp3');
const useVoice = mode === 'brand' && !audio && !flag('--silent') && fs.existsSync(VOICE_JSON);

const OFF = 0.08;       // voice starts 0.08 s into the reel (the file has its own 0.12 s lead-in)
const MAX_PAUSE = 0.30; // no pause in the voice longer than this
const TAIL = 2.3;       // the call to action stays this long after the last word

const sh = (cmd, a) => execFileSync(cmd, a, { stdio: ['ignore', 'pipe', 'inherit'] }).toString();
const clamp = (lo, hi, v) => Math.min(hi, Math.max(lo, v));
const r3 = v => Math.round(v * 1000) / 1000;

// ---------- voice plan: cuts in the pauses, the time map, screen beats and subtitle cues ----------
// pauses in the file: below -35 dB (soft breaths sit around -38 dB), pieces closer than 40 ms joined
function silences(file) {
  const log = spawnSync('ffmpeg', ['-hide_banner', '-i', file, '-af', 'silencedetect=noise=-35dB:d=0.05', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
  const out = [];
  let s = null;
  for (const line of log.split('\n')) {
    const a = line.match(/silence_start: ([\d.]+)/), b = line.match(/silence_end: ([\d.]+)/);
    if (a) s = +a[1];
    if (b && s != null) {
      const prev = out[out.length - 1];
      if (prev && s - prev[1] < 0.04) prev[1] = +b[1]; else out.push([s, +b[1]]);
      s = null;
    }
  }
  return out;
}

function voicePlan(vo, file) {
  const w = vo.words.map(([text, s, e]) => ({ text, s, e }));
  const quiet = silences(file);
  const cuts = [];
  const overlap = ([a, b], [c, d]) => Math.min(b, d) - Math.max(a, c);
  for (let i = 1; i < w.length; i++) {
    if (w[i].s - w[i - 1].e <= MAX_PAUSE) continue;
    // the real pause is the silence between the two words; cut its middle so MAX_PAUSE - 0.04 of it stays
    const span = [w[i - 1].e - 0.1, w[i].s + 0.1];
    const q = quiet.filter(x => overlap(x, span) > 0).sort((x, y) => overlap(y, span) - overlap(x, span))[0];
    if (!q) { console.warn(`  pause ${w[i - 1].text} / ${w[i].text}: no silence found, kept as is`); continue; }
    const len = q[1] - q[0];
    if (len <= MAX_PAUSE) continue;
    const mid = (q[0] + q[1]) / 2, r = len - (MAX_PAUSE - 0.04);
    cuts.push([r3(mid - r / 2), r3(mid + r / 2)]);
  }
  const map = t => OFF + t - cuts.reduce((acc, [a, b]) => acc + clamp(0, b - a, t - a), 0);
  const find = (prefix, from = 0) => {
    const i = w.findIndex((x, k) => k >= from && x.text.toLowerCase().startsWith(prefix));
    if (i < 0) throw new Error(`word "${prefix}" not in voiceover.json`);
    return i;
  };
  const S = p => map(w[find(p)].s);
  const last = w.length - 1, voiceEnd = map(w[last].e);

  const b = {};
  b.s2aIn = S('автор') - 0.06;    b.wipe12 = b.s2aIn - 0.20;   b.acc2a = Math.max(b.s2aIn + 0.5, S('польськ'));
  b.s2bIn = S('уроки') - 0.06;    b.s2aOut = b.s2bIn - 0.24;   b.countIn = S('1500') - 0.04;
  b.s3aIn = S('те,') - 0.06;      b.wipe23 = b.s3aIn - 0.20;   b.acc3a = Math.max(b.s3aIn + 0.5, S('пояснюв'));
  b.s3bIn = S('цифров') - 0.10;   b.s3aOut = b.s3bIn - 0.26;   b.acc3b = Math.max(b.s3bIn + 0.45, S('без'));
  b.s4In = S('скільки') - 0.06;   b.wipe34 = b.s4In - 0.20;    b.acc4 = Math.max(b.s4In + 0.45, S('урок?'));
  b.typeIn = Math.max(S('напиши'), b.s4In + 0.9);
  b.typeStep = clamp(0.04, 0.07, (voiceEnd - b.typeIn) / 25);
  b.end = Math.round(clamp(20, 24, voiceEnd + TAIL) * FPS) / FPS;
  for (const k in b) b[k] = r3(b[k]);

  const cues = vo.phrases.map(p => ({ a: Math.max(0, map(w[p.from].s) - 0.05), text: p.text }));
  cues.forEach((c, i) => { c.b = i < cues.length - 1 ? cues[i + 1].a : b.end; });
  return { cuts, map, beats: b, cues, voiceEnd };
}

const stamp = t => {
  const ms = Math.round(t * 1000), h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, s = Math.floor(ms / 1000) % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`;
};
const srt = cues => cues.map((c, i) => `${i + 1}\n${stamp(c.a)} --> ${stamp(c.b)}\n${c.text}\n`).join('\n');

// ---------- frames ----------
async function openPage(browser, m, beats) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  if (beats) await page.addInitScript(b => { window.__BEATS = b; }, beats);
  await page.goto(pathToFileURL(path.join(SRC, 'scene.html')).href + `?mode=${m}`);
  const dur = await page.evaluate(() => window.__ready);
  return { page, dur };
}

async function shot(page, t, file, alpha) {
  await page.evaluate(t => window.__seek(t), t);
  await page.screenshot({ path: file, type: 'png', omitBackground: alpha });
}

async function main(browser) {
  let plan = null, voiceFile = null;
  if (useVoice) {
    const vo = JSON.parse(fs.readFileSync(VOICE_JSON, 'utf8'));
    voiceFile = opt('--voice-file') || VOICE_MP3;
    if (!fs.existsSync(voiceFile)) {
      console.log(`downloading the ElevenLabs voice-over: ${vo.tts.url}`);
      const r = spawnSync('curl', ['-fsSL', '--retry', '2', '-o', voiceFile, vo.tts.url], { stdio: 'inherit' });
      if (r.status !== 0) {
        fs.rmSync(voiceFile, { force: true });
        console.error(`\nCould not download the voice-over. Save ${vo.tts.url}\nas ${VOICE_MP3} and run again, or build without voice: --silent`);
        process.exitCode = 1;
        return;
      }
    }
    plan = voicePlan(vo, voiceFile);
    console.log(`voice-over ${voiceFile}: ${plan.cuts.length} pauses shortened by ${r3(plan.cuts.reduce((s, [a, b]) => s + b - a, 0))} s, ` +
      `last word ends ${r3(plan.voiceEnd)} s, reel ${plan.beats.end} s`);
    console.log('beats', JSON.stringify(plan.beats));
  }
  const beats = plan && plan.beats;

  const brand = await openPage(browser, 'brand', beats);
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
  while (pages.length < workers) pages.push((await openPage(browser, mode, beats)).page);
  const started = Date.now();
  await Promise.all(pages.map(async (pg, w) => {
    for (let i = w; i < N; i += pages.length) {
      await shot(pg, i / FPS, path.join(frames, `f${String(i).padStart(4, '0')}.png`), mode === 'video');
      if (w === 0 && i % 90 === 0) console.log(`frame ${i}/${N}`);
    }
  }));
  console.log(`${N} frames in ${((Date.now() - started) / 1000).toFixed(0)} s, mode ${mode}`);
  await browser.close();

  const out = path.resolve(outArg || path.join(REEL, 'reel.mp4'));
  const enc = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
    '-level:v', '4.1', '-r', String(FPS), '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart'];
  const framesIn = ['-framerate', String(FPS), '-i', path.join(frames, 'f%04d.png')];

  if (plan) {
    // keep the voice between the cuts, start it at OFF, level to -14 LUFS, pad to the reel length
    const keeps = [];
    let t0 = 0;
    for (const [a, b] of plan.cuts) { keeps.push([t0, a]); t0 = b; }
    keeps.push([t0, null]);
    const fx = keeps.map(([a, b], i) => `[1:a]atrim=start=${a}${b == null ? '' : `:end=${b}`},asetpts=PTS-STARTPTS` +
      (b == null ? '' : `,afade=t=out:st=${r3(b - a - 0.006)}:d=0.006`) + (i ? ',afade=t=in:d=0.006' : '') + `[k${i}]`).join(';') +
      `;${keeps.map((_, i) => `[k${i}]`).join('')}concat=n=${keeps.length}:v=0:a=1,adelay=${Math.round(OFF * 1000)}:all=1,` +
      `loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,apad,atrim=0:${DUR}[a]`;
    sh('ffmpeg', ['-y', '-v', 'error', ...framesIn, '-i', voiceFile, '-filter_complex', fx, '-map', '0:v', '-map', '[a]',
      '-tune', 'animation', ...enc, '-t', String(DUR), out]);
    if (!outArg) { fs.writeFileSync(path.join(REEL, 'reel-subtitles.srt'), srt(plan.cues)); console.log('reel-subtitles.srt'); }
  } else if (mode === 'brand') {
    // silent track by default; your own recording is levelled to -14 LUFS and padded or cut to the reel length
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

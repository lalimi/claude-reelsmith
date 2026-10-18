---
name: talking-head-edit
description: Edit a talking-head video (one person speaking to camera) into a short in the "word-by-word captions + layout changes + UI cards + motion graphics" style - kinetic captions on every word with accent-box emphasis, the speaker moving between full frame, picture-in-picture beside a UI card, a square on a light motion-graphics board and a phone mock, punch-ins on emphasis, a HUD with a frame counter. Use when the user sends their own A-roll (selfie, webcam, podcast clip) and asks to edit it, "edit my talking-head video like this reference", "add word-by-word captions", make it look like a reference reel, or «змонтуй як у референсі». First cleans the voice (denoise, -14 LUFS) and proposes a rough cut (fillers, false starts, long pauses) for the person to approve. Renders an MP4 with the cleaned audio from a JSON edit list (EDL) through headless Chromium + ffmpeg, then QA-checks it.
---

# Talking-head edit

A system taken apart from a reference reel (36 s, edited "by voice" with an AI agent) and rebuilt as a
renderer. The person talks the whole time; the edit never cuts the voice. Everything around the voice changes
every ~2 s, and every change *illustrates the exact words being said*.

## The system, piece by piece

**1. A-roll is sacred.** One continuous take, original audio, no jump cuts in the reference. The picture of the
speaker moves between containers; the sound never stops. The only trimming happens once, before the edit, in
**prep** (fillers, false starts, long pauses, approved by the person); every prep join then gets a layout change or
a punch-in so the jump is never seen. Colour grade cool (blue room), accents warm — the accent colour is the only
saturated colour on screen apart from the footage.

**2. Captions on every word** (the backbone):
- A phrase is 1–5 words; it breaks on punctuation, on a pause > 0.45 s, or at the word limit. A new phrase
  *replaces* the old one (no scrolling).
- Each word appears exactly at its start time: ~0.15 s fade + 14 px rise + blur 8→0.
- Three weights, set per word: `n` normal = italic semibold (connective words); `c` caps = heavy upright
  uppercase (nouns, verbs that matter); `b` box = caps on an accent box that wipes in from the left with a
  slight overshoot — **one per phrase at most**, on the word the sentence is about.
- Caption sits in the lower third, centred, white with a soft shadow; on a light board it turns ink.

**3. Layout changes on sentence boundaries**, every 1.5–3 s. Transition = the video box tweens to its new rect
in ~0.32 s (ease-in-out) with a blur bump (0→14 px→0) — the reference uses this blur as its universal cut.
Layouts:
- `full` — face full frame, slow 0.6 %/s push.
- `top`/`left`/`right` — speaker in a rounded card + a UI card beside or under it on a dark board
  (grid lines, two or three warm bokeh blobs drifting).
- `square` on a `light` board — beige paper with grid; doodles animate in: progress ring counting 0→100 %,
  bar chart growing, line chart drawing, rotating triangle, outlined square, squiggle, floating dots.
- `phone` — speaker inside a phone frame (for "swipe", "in Reels").
- `player` — speaker inside a video-player frame + badge ("final cut · ready").

**4. UI cards that show what is being said** (literal visualisation — the strongest device):
- `terminal`: traffic-light dots + title, the spoken request typed out in quotes, a code line, a green
  "done · …" check.
- `list`: quoted chips appearing one by one (a recap of commands, features, steps).
- `toggles`: settings rows whose switches flip on in sequence (a "system" being configured).
- Cards rise 40 px with a small overshoot 0.1 s after the layout lands, and leave 0.18 s before the next beat.

**5. Emphasis devices**, used sparingly:
- **Punch-in**: hard zoom 1→1.18–1.25 in 0.12 s, a 1–2° tilt, held to the end of the phrase ("NO WAY?!").
- **Flash**: a 0.12 s white screen-blend glow on a big beat.
- **Title**: one giant accent word for the sign-off ("LET'S GO!"), captions hidden while it shows.
- A crossed-out element (red slash) for "not anymore" moments — draw it as a card or overlay when needed.

**6. HUD frame** (constant, makes it feel like a product): handle top-left, a status pill top-centre with a
blinking rec dot ("CLAUDE CODE · LISTENING ●"), a live frame counter top-right ("BUILT WITH CODE · FRAME 0136 / 1089"),
crop-mark corners. Small, uppercase, letter-spaced.

**Rhythm numbers**: new visual idea every 1.5–3 s; word pop 0.15 s; layout move 0.32 s; card in 0.35 s;
punch 0.12 s; box wipe 0.2 s; title hold ≥ 1 s at the end.

## Paths

Everything runs through the repo CLI (`reelsmith` on PATH, set up by the repo's `install.sh`):

```bash
PY="$(reelsmith py)"; SK="$(reelsmith root)/skills/talking-head-edit"; PR="$SK/prep"
```

`reelsmith py` is the repo's Python venv (faster-whisper, numpy); never use system Python for the `.py` scripts.
Shell variables do not persist between tool calls: prefix each command with the line above, or spell the paths
out, e.g. `"$(reelsmith py)" -I "$(reelsmith root)/skills/talking-head-edit/prep/lines.py" <job>`.
Shortcut for the same scripts: `reelsmith th lines|tighten|cut|qa|clean|transcribe|render <args>`.
If `reelsmith` is missing or `reelsmith doctor` complains, run `reelsmith setup` (see `INSTALL.md`).

## Workflow

0. **Prep: clean voice + rough cut** (`prep/`, default for a raw phone take; skip only if the clip is already
   edited). Job dir outside the skill folder; copy the clip in as `raw.<ext>` (never touch the original).
   1. `bash "$PR/clean_audio.sh" raw.mov voice.wav` — denoise, de-ess, EQ, −14 LUFS; prints the noise between
      words (want ≤ −45 dB). `--no-denoise` for a clean studio take. Uses DeepFilterNet (`deepFilter`) if it is on
      PATH, otherwise ffmpeg's built-in `afftdn`.
   2. `"$PY" -I "$PR/lines.py" <job>` — numbered spoken lines with times: `[…]` hesitation sound (um, uh, е —
      cut automatically later), `(…)` possible filler word, `«…»` stutter (word repeated). Also `head.jpg`/`tail.jpg`
      (a frame every 0.5 s, first/last 4 s): look at them and cut camera setup (reaching for the phone, pointing at
      the floor) even if words are spoken over it.
   3. **Their call, in chat**: propose lines to cut (warm-ups, false starts, a line that repeats an earlier one),
      soft fillers to drop, CTA moved to the end, the projected length. **Wait for their yes. Never cut a word you
      can't cut cleanly; leave it and say so.**
   4. Write `edl.json` from the approved lines (play order; reordering is fine):
      `{"source": "raw.mov", "audio": "voice.wav", "pacing": "natural", "keep": [[1.7, 9.4], [13.0, 38.2], [9.4, 13.0]], "cut": [[10.5, 11.2]]}`
      `cut` = approved bits inside kept lines (a stutter, "so, basically"). `pacing`: `natural` (pauses > 0.6 s, 1.0×),
      `tight` (> 0.3 s, 1.1×), `fast` (> 0.22 s, 1.15×); `"speed"` overrides.
   5. `"$PY" -I "$PR/tighten.py" <job>` — snaps edges into the quiet between words, removes hesitation fillers
      and shortens pauses. Safe to re-run (starts from `edl_rough.json`).
   6. `"$PY" -I "$PR/cut.py" <job>` — one pass: rotate, HDR→SDR if needed, crop to 1080×1920 (`[WxH]` as 2nd arg),
      cleaned voice, sync-safe joins → `aroll.mp4` (picture + clean voice), `aroll.webm` (for the engine),
      `joins.json`. **Put a beat (layout change) or a punch on every join time.** Then go to step 2 with `aroll.mp4`.

   `prep/` is adapted from [nicolapocock/claude-reel-editor](https://github.com/nicolapocock/claude-reel-editor)
   (MIT, see `prep/LICENSE-claude-reel-editor`).
1. **Get the A-roll** (the user's own footage). After prep it's ready: `"source": "aroll.webm", "audio": "aroll.mp4"`.
   Without prep, convert for the browser (the engine's Chromium has no H.264):
   `ffmpeg -i in.mp4 -c:v libvpx-vp9 -b:v 6M -g 15 -deadline realtime -cpu-used 8 -an aroll.webm`
   Keep the original file for audio.
2. **Words with timings** → `words.json`. `engine/transcribe.py` (faster-whisper, `word_timestamps=True`) does it
   where Hugging Face is reachable:
   `ffmpeg -i aroll.mp4 -ac 1 -ar 16000 a.wav` then `"$PY" -I "$SK/engine/transcribe.py" a.wav words.json small`
   (writes `{"lang", "words": [{"w", "s", "e"}]}` and prints the words with start times). In a sandbox where Hugging
   Face is blocked, ask the user for an SRT/transcript with timings (CapCut, Premiere, TurboScribe export) or time
   the words by hand from the audio waveform. Never invent timings for real speech.
3. **Write the edit** (`edit.json`, schema below): copy the words in, mark `k` on words (one `b` per phrase), cut
   the talk into beats on sentence boundaries, pick a layout + card that shows what the sentence says, add 1–2
   punches, a flash or two, a final title.
4. **Check stills first**: `AT=0.5,3,6 node "$SK/engine/render.mjs" edit.json out.mp4` → PNGs in `frames/` next to
   `edit.json`. Look at them; fix overlaps (title over a card, caption over a card, words off-frame).
5. **Render**: `node "$SK/engine/render.mjs" edit.json out.mp4` (≈0.1–0.2 s per frame at 1080×1920, depending on
   the machine) → MP4 with the original audio.
6. **QA**: `"$PY" -I "$PR/qa.py" <job>` (default `out.mp4`, or pass a file name as 2nd arg) — size, length
   (warn > 60 s, fail > 90 s), −15…−12.5 LUFS, peak ≤ −1 dBTP, noise between words (≤ −45 dB), joins that land
   inside a word, and words lost vs the raw transcript of what `edl.json` keeps (or `expected.txt`; fail under 90 %
   match). Exit 1 = FAIL: fix the edit, never lower the bar. Then tell them what to check by ear (joins, names,
   brand names).

Engine deps: playwright-core 1.56.1 (from `reelsmith setup`, or `npm i` in `engine/`), ffmpeg. Browser:
`CHROME_PATH=/path/to/chrome`; without it the engine tries Puppeteer's Chrome (if `puppeteer` is installed), then
Playwright's own (`npx playwright@1.56.1 install chromium`). See `INSTALL.md` next to this file.

## `edit.json`

```json
{
  "width": 1080, "height": 1920, "fps": 30, "duration": 36.6,
  "source": "aroll.webm", "audio": "aroll.mp4", "sourceOffset": 0,
  "theme": { "accent": "#FF5A1F", "accent-ink": "#0A0A0A", "light": "#F4EFE6", "ok": "#3DDC84" },
  "hud": { "handle": "@yourhandle", "pill": "Acme · rec", "counter": true, "counterLabel": "frame" },
  "captionSize": 76, "captionY": 1330, "maxWords": 4,
  "words": [ { "w": "Selling", "s": 0.15, "e": 0.42, "k": "n" }, { "w": "templates?", "s": 0.95, "e": 1.5, "k": "b" } ],
  "beats": [
    { "t": 0, "layout": "full" },
    { "t": 2.9, "layout": "top", "card": { "type": "terminal", "title": "Acme", "prompt": "“make a product page”", "code": "<Product price=\"$19\" />", "done": "Done · page is live" } },
    { "t": 4.6, "layout": "top", "card": { "type": "toggles", "title": "What Acme handles", "items": ["Taxes", "Receipts"] } },
    { "t": 6.8, "layout": "phone" },
    { "t": 8.6, "layout": "square", "bg": "light" },
    { "t": 20, "layout": "player", "badge": "final cut · ready" }
  ],
  "punches": [ { "t": 0.95, "until": 1.9, "z": 1.18, "rot": -1.5 } ],
  "titles": [ { "t": 34.9, "until": 36.6, "text": "Let's go!" } ],
  "flashes": [ 2.9 ]
}
```

- Paths (`source`, `audio`) are relative to `edit.json`; `sourceOffset` (s) skips into both. `frames/` is written
  next to `edit.json`.
- Layouts: `full`, `top` (vertical) / `left`, `right` (horizontal), `side`, `square`, `phone`, `player`.
  `bg: "light"` switches to the paper board with doodles (best with `square`).
- Cards: `terminal` {title, prompt, code?, done?}, `list` {title, items[]}, `toggles` {title, items[]},
  `text` {text}; `"theme": "light"` on a card for a white card. Cards render only for layouts that leave room
  (`top`/`side`/`player` vertical, `left`/`right` horizontal).
- Word `k`: `n` (default), `c`, `b`; `"br": true` forces a phrase break after the word.
- `theme` keys become CSS variables: `accent`, `accent-ink` (text on the accent badge), `dark`, `light`, `ink`,
  `ok`, `font`. `hud`: `handle`, `pill`, `counter` (false hides it), `counterLabel`. Titles take optional
  `size`/`y`; punches `z`/`rot`; `flashes` are times in seconds.
- Horizontal (1920×1080) works too: set width/height and use `left`/`right`.

## Rules that keep it good

- Every beat must answer "what is being said right now?" — a card or layout that does not illustrate the words
  is noise. When nothing fits, stay on `full` and let the captions work.
- Keep the face visible and large in at least half the runtime; viewers watch a person, not a deck.
- One `b` word per phrase; caps for at most two other words; everything else normal italic.
- Reels/TikTok safe zone (vertical): keep captions and cards between y≈250 and y≈1500, right edge clear of
  ~120 px.
- Brand: set `theme` colours and the `hud` handle/pill from the creator's own brand (the example uses a neutral
  "Acme" / `@yourhandle`). Captions and UI text can be in any language — Ukrainian and other Cyrillic text work
  with Inter. Whisper may mishear brand names and jargon: fix the text in `edit.json`, keep the timings.
- Use only the user's own footage. A reference reel is for learning the system, never re-edited and published.

## Notes

- **Language.** The renderer takes any text. Whisper language comes from `REELSMITH_LANG` (`uk`, `en`, `pl`, …; unset =
  auto-detect). Filler words are known for English and Ukrainian (`prep/common.py`: `HARD` hesitations are cut
  automatically, `SOFT` words only flagged); add your language's fillers and a hesitation prompt in `FILLER_PROMPT`.
  Some prep reports still print in Ukrainian.
- Keep each job's work dir (raw clip, voice.wav, edl.json, aroll.webm, aroll.mp4, words.json, edit.json, frames/)
  outside the skill folder.
- 3D guide generator: `guide3d/` next to this file — a three.js product promo (a guide falls in, price sticker,
  "Buy now" button, end card) rendered to PNG frames. `cd "$SK/guide3d" && AT=0,2.8 node capture.mjs` for stills
  (`frames/still_*.png`), plain `node capture.mjs` for all frames; texts and colours live in `index.html`. See
  `INSTALL.md`.

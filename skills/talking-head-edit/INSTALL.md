# talking-head-edit · install

Only what this skill needs on top of the repo setup. Three parts, all rendering frames in headless Chromium and
assembling video with ffmpeg:

- `engine/` — the talking-head renderer (word-by-word captions, layouts, cards, HUD) → MP4 with the original audio.
- `prep/` — voice cleanup, rough-cut table, tightening, cutting and QA (Python + ffmpeg).
- `guide3d/` — optional three.js product promo (a guide falls in, price sticker, "Buy now" button, end card) → PNG
  frames → MP4.

## 1. Repo setup first

```bash
reelsmith setup     # = install.sh at the repo root
reelsmith doctor    # report only
```

`install.sh` checks ffmpeg/ffprobe/node/npm/python3, creates the Python venv (numpy, faster-whisper) at
`$REELSMITH_DATA/venv` (default `~/.local/share/reelsmith/venv`), installs the repo's root Node deps and
Playwright Chromium, and links `reelsmith` into `~/.local/bin`. `reelsmith py` prints that venv's Python and
`reelsmith root` the repo root; the skill uses nothing else.

## 2. Requirements specific to this skill

| What | Version | Why |
|---|---|---|
| Node.js | ≥ 20 | `engine/render.mjs`, `guide3d/capture.mjs` |
| ffmpeg + ffprobe | recent, with `libx264`, `libvpx-vp9`, `aac`, `loudnorm`, `ebur128` | A-roll → VP9, MP4 assembly, voice cleanup, QA |
| Chromium / Chrome | Chrome 13x+ or Playwright Chromium (build 1194 for playwright 1.56.1) | frame rendering (VP9 video, WebGL for guide3d) |
| faster-whisper | tested 1.2.1 (in the repo venv) | word timings for captions, rough-cut table, QA |
| Inter font | any, with Cyrillic if you caption in Cyrillic | all text in the templates (`font-family: "Inter"`) — https://fonts.google.com/specimen/Inter · `brew install --cask font-inter` · `sudo apt install fonts-inter` |
| DejaVu Sans Mono | — | code line in the `terminal` card (another monospace is used otherwise) — https://dejavu-fonts.github.io |
| `deepFilter` (DeepFilterNet) | optional | stronger denoise in `prep/clean_audio.sh`; without it ffmpeg's `afftdn` is used |
| `python3` | system, stdlib only | `prep/clean_audio.sh` uses it for small JSON/level calculations |

No fonts, LUTs or other assets are bundled: fonts come from the system, colours from CSS variables set in
`edit.json` (`theme`).

## 3. Node dependencies

Versions are pinned in each folder's `package.json`.

```bash
cd "$(reelsmith root)/skills/talking-head-edit/engine"  && npm i   # playwright-core@1.56.1
cd "$(reelsmith root)/skills/talking-head-edit/guide3d" && npm i   # playwright-core@1.56.1, three@0.169.0
```

- `engine/`: after `reelsmith setup` the import of `playwright-core` already resolves from the repo's root
  `node_modules`; `npm i` here pins it next to the engine.
- `guide3d/`: required. `index.html` loads three.js from `guide3d/node_modules/three/...` through the local server
  in `capture.mjs`, which only serves files inside `guide3d/`.

## 4. Browser

Both scripts look for a browser in this order:

1. **`CHROME_PATH`** — any Chrome/Chromium:
   ```bash
   # macOS
   export CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   # Linux
   export CHROME_PATH=/usr/bin/chromium
   ```
2. **Puppeteer**, if installed next to the script: `npm i puppeteer@24.22.3` (downloads its own Chrome).
3. **Playwright's browser**: installed by `reelsmith setup`, or `npx playwright@1.56.1 install chromium`.

Chromium builds (Playwright, Puppeteer, distro `chromium`) do not play H.264, so the A-roll is re-encoded to VP9
before editing (`prep/cut.py` does it, or the `ffmpeg … libvpx-vp9` command in `SKILL.md`). Any Chrome plays VP9.

## 5. API keys

None. Nothing calls a paid API.

- faster-whisper models download from **huggingface.co** on first run (no key). If the network blocks it, supply
  an SRT / word timings by hand (CapCut, Premiere, TurboScribe). `HF_TOKEN` is optional (download rate limits only).

## 6. Smoke test

```bash
SK="$(reelsmith root)/skills/talking-head-edit"
mkdir -p ~/reels/th-test && cd ~/reels/th-test         # any folder outside the skill
ffmpeg -i my.mp4 -c:v libvpx-vp9 -b:v 6M -g 15 -deadline realtime -cpu-used 8 -an aroll.webm
cp my.mp4 aroll.mp4
ffmpeg -i my.mp4 -ac 1 -ar 16000 a.wav
"$(reelsmith py)" -I "$SK/engine/transcribe.py" a.wav words.json small
# write edit.json (schema in SKILL.md), then:
AT=0.5,3,6 node "$SK/engine/render.mjs" edit.json out.mp4   # PNG stills in ./frames/
node "$SK/engine/render.mjs" edit.json out.mp4              # full render
```

### guide3d

```bash
cd "$(reelsmith root)/skills/talking-head-edit/guide3d"
AT=0,2.8,6.2,9.5 node capture.mjs        # test stills in frames/still_*.png
node capture.mjs                         # 300 frames (10 s × 30 fps) in frames/
ffmpeg -framerate 30 -i frames/f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart guide-3d.mp4
```

The guide title, price and texts live in `index.html` (`cover`, `sticker`, the button labels and the `.end`
block); brand colours in `:root` and the `C` object. Sound effects are not included; the video is silent unless you
add a track (e.g. synthesised with ffmpeg `aevalsrc`).

## 7. Optional extras (third-party, not bundled)

Other people's Claude Code skills that pair well with this one for motion work. They are **not part of this repo**,
are not required, and come under their own licences; check each repository before installing. "Tested commit" is
the commit this skill was used with.

| Skill | Repository | Install | Tested commit |
|---|---|---|---|
| three.js (10 skills) | https://github.com/cloudai-x/threejs-skills | `git clone --depth 1 https://github.com/cloudai-x/threejs-skills /tmp/threejs-skills && cp -r /tmp/threejs-skills/skills/* ~/.claude/skills/` | `b1c6230` |
| GSAP (8 skills) | https://github.com/greensock/gsap-skills | `npx skills add https://github.com/greensock/gsap-skills` · in Claude Code: `/plugin marketplace add greensock/gsap-skills` | `aed9cfd` |
| genjutsu (cast, paint, bunshin) | https://github.com/AThevon/genjutsu · https://genjutsu.athevon.dev/docs/install | `npx skills add https://genjutsu.athevon.dev -g` · in Claude Code: `/plugin marketplace add AThevon/genjutsu`, then `/plugin install genjutsu` | `1f518a7` |
| design-dna | https://github.com/zanwei/design-dna | `npx skills add zanwei/design-dna -a claude-code -g -y` (colour-measurement scripts: `cd ~/.claude/skills/design-dna/scripts && npm i`, installs `sharp`) | `593e39b` |
| motion-design (LottieFiles) | https://github.com/lottiefiles/motion-design-skill | `npx skills add LottieFiles/motion-design-skill` | `f9a8a04` |

Manual route for any of them: `git clone` the repository and copy the folders that contain a `SKILL.md` into
`~/.claude/skills/`. For genjutsu, keep the `_jutsu` folder next to `cast`/`paint`/`bunshin` — without it the
skills cannot find their references. `npx skills` is the CLI from https://github.com/vercel-labs/skills.

# Third-party notices

claude-reelsmith is MIT-licensed (see `LICENSE`). It includes or builds on:

| Part | Where | Origin | License |
|---|---|---|---|
| Talking-head prep scripts (`clean_audio.sh`, `common.py`, `lines.py`, `tighten.py`, `cut.py`, `qa.py`), adapted | `skills/talking-head-edit/prep/` | [nicolapocock/claude-reel-editor](https://github.com/nicolapocock/claude-reel-editor) © 2026 Nicola Pocock (getgitgirl) | MIT — `skills/talking-head-edit/prep/LICENSE-claude-reel-editor` |
| Table of tested CapCut library sound ids | `engine/capcut.py` | same repository | MIT |
| Playfair Display, Manrope, JetBrains Mono (woff2 subsets) | `engine/fonts/` | Google Fonts / their authors | SIL Open Font License 1.1 — `engine/fonts/OFL.txt` |
| Playwright (installed by `reelsmith setup`) | `node_modules/` | Microsoft | Apache-2.0 |
| three.js (installed by `reelsmith setup`) | `node_modules/` | three.js authors | MIT |
| faster-whisper, NumPy, OpenCV (installed into the venv) | data folder | their authors | MIT / BSD / Apache-2.0 |

Not included, downloaded by the user if they want it: FFmpeg, CapCut's plugin bundle (uploader + draft builder, CapCut's own terms), ElevenLabs (their terms; the free plan requires attribution and is non-commercial).

The demo reel and the images in `docs/img/` are © lalimi; the footage is the author's own. Voice in the demo: ElevenLabs.

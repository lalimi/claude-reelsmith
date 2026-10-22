---
name: reel-builder
description: Build a finished voice-over reel (Instagram Reels / TikTok / Shorts, 1080×1920, 25–70 s) from one reel.json — the creator's own clips and photos + a voice-over + subtitles with accent words + hook/end cards, stamps, punch-ins, transitions and motion effects (cover story, orbit text, doodle boil, glass type, checklist, headline wall, black-and-white → colour burst, photo montage), music bed, −14 LUFS mix, safe-zone QA sheet, cover and caption. Use after a script is approved (reel-script skill) when the reel is a voice-over over footage (for someone talking to camera use talking-head-edit), or when asked to "make / build / rebuild / re-cut a reel", "змонтуй рілс", "перезбери".
---

# Reel builder

Engine: `$(reelsmith root)/engine/` (`build.py`, `template.html`, `music.py`, `pull_vo.py`, `capcut.py`, `fonts/`). One folder per reel: `<reel-dir>/reel.json` → `<reel-dir>/out/reel.mp4`. If `reelsmith` says it is not set up, run `reelsmith setup` once.

```bash
reelsmith new reels/my-reel            # folder with src/, vo/ and a template reel.json
reelsmith sheet reels/my-reel/src/*    # contact sheets → pick `ss` for every segment
reelsmith build reels/my-reel --stills # ~1 min: frames, word timings, subtitles, out/qa_sheet.jpg
reelsmith stills reels/my-reel 0.5,7.8,21.3   # extra check frames
reelsmith build reels/my-reel          # full render (~4–5 min for 60 s)
```

Always run `--stills` first. It prints **RETENTION CHECKS** (evidence in `docs/retention.md`): voice from the first frames, hook text at 0 s, no code word in the hook, pace ≈ 0.33 cuts/s (flags > 0.5/s for 6 s and > 4 s with no visual change), voice pace, end card ≤ 3 s, tail after the last word, > 60 s (Shorts), subtitles > 17 chars/s; the full build adds first-frame brightness, motion in the first 10 frames, silent start and loop similarity. Fix every bullet or say why it stays. `--lint` runs only these checks. Then read the printed subtitle list and look at `out/qa_sheet.jpg` (red = Reels/TikTok UI zones; nothing important may sit in red). Fix reel.json, then build. Check the loudness lines printed at the end (−14 LUFS ±1, peak ≤ −1 dB). Then look at frames of the final MP4 around every effect and transition before you hand it over.

## Workflow (creator's time ≈ 10 min per reel)

1. **Script**: `reel-script` skill → creator approves. Mark accent words with `<em>…</em>`; keep numbers as digits for display.
2. **Voice**: either the creator's own recording (`vo/vo.mp3`) or ElevenLabs (see `docs/voice.md`): TTS text = script without tags, numbers spelled out in words, brand names written phonetically. On the free plan generate in the ElevenLabs web UI (Claude in Chrome can drive it), then `reelsmith voice <reel-dir>` pulls the 2 newest takes into `vo/` with durations. Transcribe both, keep the cleaner one as `vo/vo.mp3`. Slow voices: `"speed": 1.07` in `vo`.
3. **Footage**: `footage-scout` skill — fresh clips only (check `used_footage.md`), contact sheets, privacy check. Segment durations must add up to the voice end + ~2 s.
4. **Edit plan**: `reel-director` skill picks the 3–5 effects for this story and where the transitions go.
5. Write reel.json → `--stills` → fix → build → deliver `out/reel.mp4` + `out/cover.jpg` + `out/caption.txt`.
6. Optional sound pass in CapCut: `reel-capcut` skill (library sound effects + music chosen by ear).

## reel.json

```json
{
  "vo": {"file": "vo/vo.mp3", "offset": 0.25, "speed": 1.07, "gaps": [[5.73, 0.8]]},
  "script": "I've been rewriting my guide for three months and yesterday I changed the cover font <em>for the fourth time</em>. …",
  "hook": {"tag": "the eternal-draft scenario", "lines": ["the guide is almost ready.", "<em>for three months now</em>"], "out": 5.55},
  "end": {"from": 55.6, "lines": ["how long has", "<em>yours been waiting?</em>"], "lines_at": [55.75, 56.6],
          "sub": "tell me in the comments", "sub_at": "@comments", "handle": "@yourhandle", "handle_at": 58.6},
  "cover": {"from": 0, "to": 4.35, "title": "DRAFT", "left": "No.4 · October", "right": "@yourhandle", "top": 330},
  "cover_t": 2.0,
  "stamps": [{"seg": ["I", "J"], "text": "tanya · 2 years in drafts"}],
  "punch": [[3.02, 4.4], ["@thousand", 9.0]],
  "segments": [
    {"id": "A", "clip": "src/night_desk.mp4", "ss": 9.5, "dur": 2.5, "crop": [0, 0.196, 0.75], "cut": true},
    {"id": "B", "clip": "src/keys.mp4", "ss": 1.3, "dur": 1.9, "move": "none"},
    {"id": "E", "clip": "src/phone_walk.mov", "ss": 0.8, "dur": 4.5, "cut": true, "in": "zoom"},
    {"id": "I", "clip": "src/cafe.mp4", "ss": 0.3, "dur": 3.2, "look": "bw"},
    {"id": "K", "clip": "src/walk.mov", "ss": 14.0, "dur": 4.95, "look": "burst"},
    {"id": "N", "clip": "src/breakfast.mov", "ss": 0.0, "dur": 3.45, "rate": 0.4},
    {"id": "Q", "clip": "src/meadow.mov", "ss": 13.2, "dur": 9.1, "move": "pull-out", "in": "zoom"}
  ],
  "caption": "…",
  "music": "synth"
}
```

A complete real example (Ukrainian, 61 s, 17 segments, every effect below) is in `$(reelsmith root)/examples/chernetka/reel.json`; a minimal one in `examples/template/reel.json`.

### Voice and subtitles
- **lang**: Whisper language of the voice-over (`"uk"`, `"en"`, …); omitted = auto-detect (or `REELSMITH_LANG`).
- **vo.gaps** `[vo_time, extra_s]`: a breathing pause inserted at the quietest point near that time of the (sped-up) voice — room for a photo montage. **vo.speed**: atempo factor.
- **"@word" anchors**: any time in hook / end / doodles / glass / checklist / cover / orbit / wall / punch / subs_skip can be `"@thousand"` (start of that script word; exact match first, else prefix), `"@again#2"` (2nd occurrence), `"@twice+0.3"`. Words Whisper mishears get interpolated times — use seconds there. `out/words.json` has the real timings after `--stills`.
- **subs / punch**: omitted = automatic from `script` + word timings (up to `subs_words` words, default 5, 1–2 lines, accent words in italic accent colour, no trailing dot, a line never ends on "and/in/of…"; punch-ins on up to 4 accent phrases ≥ 3 s apart). Override with `"subs": [[a, b, "html"]]`, `"punch": [[a, b]]`. Subtitles hide while the hook card is up, under glass titles and checklists, and once the end card starts (`subs_from` / `subs_until` / `subs_skip [[a, b]]` to adjust).

### Cards and text
- **hook**: paper card visible from frame 0 (`at: [t…]` reveals lines one by one, `size`, `top`). **end**: card from `from`, lines at `lines_at`, `sub`, `handle`.
- **stamps**: mono pill top-left over the listed segments (place, date, character name).
- **cover** (cover story + frame break): magazine masthead fitted to the width, letters drop in; on segments with `"cut": true` the person stands in front of the title. Choose/crop a shot where the head top sits 40–80 px below the masthead top — never across the eyes. `color` for the masthead, `top` to move it. `cover_t` ≈ 2 so `out/cover.jpg` shows the finished cover.
- **glass** (glass type): `{"from", "to", "lines", "at", "top"}` frosted-glass title.
- **checklist**: `{"from", "to", "title", "items": [{"text", "sub", "at", "sub_at"}]}` card that grows item by item, ticks drawn at `at`.
- **wall** (headline wall): `{"from", "to", "items": [...], "every": 0.06}` file-name / headline tiles piling up; put a glass title on top.
- **orbit**: `{"from", "to", "seg", "text": "1000 FOLLOWERS · ", "speed", "scale", "tilt", "lift"}` text ring around the head on a `cut` segment; the back half passes behind the person. Best on a close selfie.
- **doodles** (doodle boil): `{"kind": "text"|"circle"|"underline"|"strike"|"arrow", "at", "to", "x", "y", …}` — text: `text, size, rot, write`; circle/strike: `w, h` (strike `n` zig-zags; 3 keeps the word readable); underline: `w`; arrow: `x2, y2, bend`; `color`, `width`. Accent ink with a cream halo, written on left → right, wobbling every 3 frames. Keep them above y ≈ 1000 while the hook card is up and off faces.

### Segments
- **paths**: relative to the reel folder, then the current directory, then the repo. HEIC/JPG photos via `img` are fine.
- `ss` start in the clip, `dur` seconds; `pos` 0–1 horizontal framing for wide sources; `crop [x, y, size]` = punch-in crop of the upright frame (stays sharp from 4K); `rate` < 1 = slow motion when only a short part is usable.
- **cut**: `true` = macOS Vision person masks for this segment (`reelsmith masks`, ~0.2 s/frame, cached). Needed by cover and orbit.
- **in**: `"zoom"` (outgoing shot rushes in with blur, new one lands from a zoom) or `"whip"` (fast blurred slide, no black edges). Use on 4–6 key cuts, not every cut.
- **look**: `""` warm film · `"memory"` faded zoom-through fly-in for photo montages (`date` adds an orange camera date stamp) · `"bw"` black and white (music muffles) · `"burst"` grey → colour bloom (music opens up).
- **move**: `push` (default slow push-in) · `tilt-up` · `pull-out` · `none`.

### Sound and colour
- **music**: `"synth"` (a generated lo-fi bed shaped by the looks — fine as a placeholder, creators usually prefer a real track), a path to an audio file you have the rights to, or `null`. Original clip sound is never used.
- **music_gain**: default 0.16 under the voice (sidechain-ducked).
- **colors**: `{"accent": "#D4573A", "cream": "#F4EFE6", "ink": "#1F1A17"}` (defaults: beige / terracotta).

## Rules that came from real feedback
- Effects must read at phone size on the first watch: big, accent-coloured, animated. Small cream doodles and a faint glass panel were "where are the effects?".
- No repeated white flashes on cuts. Mute original clip sound. 3–5 techniques per reel, not all of them.
- Never put text, cards or doodles across the eyes; move the card or reframe the shot.
- Check the screens and backgrounds of clips at full resolution: other people's messages, car plates, street names, private dashboards → skip those seconds.
- Fresh footage every reel (`used_footage.md`). Ask before using shots with other people's faces.

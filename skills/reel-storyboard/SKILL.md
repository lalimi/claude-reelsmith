---
name: reel-storyboard
description: Before the first full render of a reel, show the creator a one-page HTML storyboard (scene cards with timecode, a real frame from their clip, on-screen text, the voice line, effects and sound, risk notes) and wait for "yes". Use after the script is approved and clips are picked, or when asked for a "storyboard", "розкадровка", "show me the plan before you render".
---

# Reel storyboard

A full render costs minutes and tokens; a storyboard costs seconds. The creator sees the whole edit on one page, fixes it in words, and the render comes out right the first time. **No full render without a "yes" on the storyboard.** (`reelsmith build --stills` is QA after the storyboard, not a replacement for it.)

## When
After `reel-script` (approved text) and `footage-scout` (clips picked), before `reel-builder` writes or renders anything heavy. Also when re-cutting: storyboard only the scenes that change.

## Gather
1. The approved script split into beats of 2–6 s (the director's beat map).
2. For every beat: the clip and in-point (`src`, `ss`) you plan to use, or the engine card (hook, glass, checklist, typewriter, timeline, end).
3. One frame per beat from the real clip, middle of the planned segment, small:
   `ffmpeg -v error -ss <t> -i <clip> -frames:v 1 -vf scale=216:-1 -q:v 6 sb/<nn>.jpg`
   Never render a scene to make a storyboard frame. For engine cards draw a simple CSS mock.
4. Timing: before TTS exists, estimate from word count (≈2.5 words/s for Ukrainian and English at `vo.speed` 1.15; slower languages ≈2.2). After `--stills`, use `out/words.json`.

## The page (one self-contained HTML file, frames as data: URIs)
Top: title, account, total words and seconds, structure, voice, music, cover.
One card per beat:
- number and timecode `05 · 0:45–0:51`, shot type (camera / screen / b-roll / b&w / card)
- source: clip id or file and in-point
- 9:16 thumbnail with the on-screen text laid over it the way it will sit (inside the safe zone)
- the voice line verbatim + `N words · X s`; flag ⚠️ when the line is faster than ~2.8 words/s ("won't fit") or slower than ~2.0 ("dead air, shorten the shot")
- effect / transition / sound for that beat (doodle, glass, burst, whip, pop, UI-beep…)
- a red risk note **only** when there is a real risk: private details on a screen (other people's messages, products, names, plates), text on packaging, the person talking on camera while the voice says something else, a claim that needs confirming
Bottom: a short checklist of what the creator must confirm (claims and numbers outside `facts.md`, the CTA / code word, risky frames) and one line: "What should I change? Or say yes and I'll render."

Save it next to the reel as `<reel-dir>/storyboard.html` and show it to the creator.

## After feedback
- Apply edits to the storyboard and reel.json, not to a video. Re-show the page only if the structure changed; confirm small text edits in one line.
- After "yes": `reelsmith build <dir> --stills` → fix → full build, as in `reel-builder`.
- If a scene changes after the render, rebuild that scene's segment rather than redesigning the whole reel, and note the change on the storyboard.

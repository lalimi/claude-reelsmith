---
name: reel-script
description: Write, analyse and plan short-video scripts (Instagram Reels, TikTok, YouTube Shorts, 30–60 s) in four proven viral structures — contrarian insight with a named archetype, series episode with a cliffhanger, humor hook + list of N factors, and "the scenario of …" confession. Use when the user asks to "write a reel script", "give me reel ideas", "analyse this viral reel", "break this reel down", "turn this transcript into a structure", "make one like this reel", pastes a reel transcript, or wants to edit a reel that has no script yet. Triggers in any language (e.g. "напиши сценарій для рілса"). Writes flowing spoken text in the creator's own language (English, Ukrainian, …), checks it against a checklist, and hands a montage plan to reel-builder, talking-head-edit or reel-director.
---

# Reel script

A script that stops the scroll, narrows a broad human topic down to the creator's niche, and ends with exactly one action. The structures come from real viral reels; reference transcripts teach the shape only and are never reused.

First read `references/facts.md`. If it is still the blank template, ask for the product in one line, the accounts, and the script language, then fill it in.

## Modes

### 1. Analyse a reel
Input: a transcript, a pasted script, or a link plus description.
1. Split it into numbered beats, with timings if known.
2. Name the device in each beat (device list in `references/structures.md`).
3. Say in one line why it works.
4. Match it to structure A–G. No match: write it up as a new structure in the same format, append it to `references/structures.md`, add an abstract beat map to `references/examples.md`, and tell the user it was added.

Store beats abstractly: paraphrase, at most a ~5-word illustration per beat. Never paste the source transcript into the reference files.

### 2. Write a script
1. **Account + language**: from `facts.md`. If there are several accounts and the request doesn't say which, ask once. Write in the creator's language.
2. **Structure and hook**: pick from the table in `references/structures.md` (A–G) and a hook type from `references/hooks.md`. For "give me ideas": one idea per structure, one line each; write the full script only for the one chosen.
3. **Script**: one flowing spoken text. Under it, the beat map (beat → time → sentence). Mark 4–8 accent words with `<em>…</em>`, numbers in digits.
4. **Checklist**: run `references/checklist.md` and fix before showing. Never show a draft that fails it.
5. **Facts**: product claims only from `facts.md`. Anything else goes in a "Confirm:" list at the end.
6. **Montage plan**: 3–5 techniques from the menu below, each mapped to a beat. Add subtitle chunks of 5–7 words only if the editor needs them (reel-builder chunks automatically).
7. **Caption**: one CTA, 3 hashtags, does not repeat the hook, follows the caption style in `facts.md`.

Full worked example: `references/examples.md` → "The eternal-draft scenario".

### 3. Series (structure B)
Keep `episodes.md` in the reel's project folder: episode number, topic, what the cliffhanger promised. The next episode must pay off that promise.

## Voice rules

- The creator's language, conversational, as if telling a friend. Full sentences that flow into each other.
- No choppy one-word rhythm ("And you answer. For free. For years." gets rejected). A short line is allowed only as a punchline right after a longer setup.
- Concrete over abstract: numbers, places, objects, times of day, named people ("Tanya from accounting"). Never "people", "many", "some".
- One reel = one idea. Humor and self-irony welcome; at most one sharp or edgy phrase.
- Length: 40–50 s ideal, 60 s hard cap. Time a read-aloud or the first voice take; slow TTS voices need ~15% fewer words.
- Natural target language: no calques or translated-sounding phrases. When adapting from another language, localise names, prices and idioms.
- On-screen text: no em-dashes.

## Montage menu

Effects the `reel-builder` engine renders (key in `reel.json`). Use 3–5 per reel, big enough to read on a phone at first watch; real transitions on key cuts only, not every cut.

| Technique | Best on | Key |
|---|---|---|
| Doodle boil (hand-drawn text, circles, strikes, arrows) | confessions, ironic asides | `doodles` |
| Glass type (frosted title card) | the coined name, the series title | `glass` |
| Checklist (items tick in as spoken) | steps, rules, list items | `checklist` |
| Orbit (text ring around the speaker's head) | one big number or goal | `orbit` |
| Cover story + frame break (masthead behind the head) | hook | `cover` |
| Headline wall (tiles piling up) | a pile of examples: files, messages | `wall` |
| Zoom-through / whip cut | 4–6 beat changes | segment `in` |
| Black-and-white → colour burst | sad "before", then the turn | segment `look` |
| Punch-in | accent words | automatic, or `punch` |
| Pull-back | the closing line | segment `move: "pull-out"` |

## Hand-off

- **Voice-over over footage** → `reel-builder` skill (`reelsmith build`). Pass the script with `<em>` accents, the beat map and the montage plan.
- **Talking to camera** → `talking-head-edit` skill. The script is what the creator says; the beat map tells the editor where layouts and cards change.
- **Creative review** → `reel-director` skill, on the script before recording or on the first cut.
- Keep every on-screen element inside the Reels/TikTok safe zone.

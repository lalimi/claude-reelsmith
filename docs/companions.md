# Companion tools: HyperFrames and OpenMontage

Two open-source video projects that work next to reelsmith. Neither is bundled: you install them yourself, under their own licenses.

| | reelsmith | HyperFrames | OpenMontage |
|---|---|---|---|
| Best for | Reels from **your own footage** and voice | Motion graphics with no footage: explainers, promos, kinetic type, slideshows | Whole productions from a prompt: AI-generated clips, stock-footage documentaries, dubbing |
| Form | Claude Code plugin | Claude Code plugin | A separate project folder you open Claude Code in |
| License | MIT | Apache-2.0 | AGPL-3.0 |

## HyperFrames

[heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) by HeyGen: a video is an HTML page with seekable animations, rendered frame by frame in headless Chrome and encoded with FFmpeg. That is the same idea as reelsmith's engine, packaged as a general framework with its own skills (`/hyperframes`, the CLI, a block registry, captions, media, Figma, slideshows, Remotion ports).

**In this repository** it is already listed in [`.claude/settings.json`](../.claude/settings.json): Claude Code offers to install it when you trust the folder.

**Anywhere else:**
```
/plugin marketplace add heygen-com/hyperframes
/plugin install hyperframes@hyperframes
```

Needs Node.js 22+ (reelsmith alone needs 20+) and FFmpeg. Check with `npx hyperframes doctor`.

Use it for a reel with no camera footage, or to prototype a card or a title animation before porting it into `engine/template.html`.

## OpenMontage

[calesthio/OpenMontage](https://github.com/calesthio/OpenMontage): an agentic production studio. It has 12 pipelines (animated explainer, talking head, screen demo, cinematic, documentary montage, clip factory, podcast repurpose, localization dub and more), Python tools for image, video, voice and music providers, and Remotion and HyperFrames composers. Provider API keys go in its `.env`. Every key is optional, and each one you add unlocks more tools.

It is not a plugin. Its agent rules expect Claude Code to run in its own folder, and its AGPL-3.0 license is why it is kept out of this MIT repository. Clone it next to your reels:

```bash
git clone https://github.com/calesthio/OpenMontage.git
cd OpenMontage
make setup        # Python venv, Remotion composer, HyperFrames runtime
```

Then open Claude Code in `OpenMontage/` and describe the video. Needs Python 3.10+, Node.js 18+ and FFmpeg.

Get it only from `github.com/calesthio/OpenMontage`.

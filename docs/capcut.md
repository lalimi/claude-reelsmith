# CapCut route (optional)

The engine always renders a finished MP4. The CapCut route adds an **editable CapCut Web draft** on top: the same picture (all graphics baked in) + voice and music as separate tracks + CapCut library sound effects on every effect and transition, so the creator can change music and sounds by ear.

## One-time setup
1. **MCP connector** — bundled in this plugin as `capcut` (`.mcp.json` → `https://www.capcut.com/api/external_mcp`). In Claude Code run `/mcp`, pick `capcut`, sign in with your CapCut account. Without the plugin: `claude mcp add --transport http capcut https://www.capcut.com/api/external_mcp`.
2. **CapCut's plugin bundle** (their uploader + draft builder scripts; not redistributed here). Download it yourself:
   ```bash
   mkdir -p ~/capcut-plugin && cd ~/capcut-plugin && \
   curl -L -o plugins.zip https://sf16-sg.tiktokcdn.com/obj/eden-sg/962370eh7nupenuhbo/capcut_codex_plugin/plugins_v21.zip && \
   unzip -q plugins.zip -d x
   ```
   If it lives elsewhere, set `CAPCUT_PLUGIN_DIR`. Read the scripts before running them (they only talk to CapCut / Volcengine / TikTok hosts).

## Use
Ask Claude: *"send this reel to CapCut with sound effects"* — the `reel-capcut` skill runs `reelsmith capcut stems`, the upload, `reelsmith capcut draft` and the push, and returns the editor link.

## Known issues
- Library sound effects (sid://…) have been reported to sit on the timeline but play/export silent. Listen before exporting; swap them in Audio → Sound effects if needed.
- The connector's sound search is a weak title search without previews. The full sound library is only in the CapCut app — this is why the creator does the final sound choice by ear.
- Export saves to the CapCut cloud first; a full cloud space makes it fail with "Couldn't save".
- A music track longer than the video adds a black tail — trim it to the video end.

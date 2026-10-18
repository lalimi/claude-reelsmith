#!/usr/bin/env bash
# claude-reelsmith setup: python venv (numpy, faster-whisper, opencv), Playwright Chromium, the macOS mask tool,
# and the `reelsmith` command on your PATH.  Re-run any time; `--check` only reports.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${REELSMITH_DATA:-$HOME/.local/share/reelsmith}"   # venv + compiled tools (survive plugin updates)
CHECK=0; LINK_SKILLS=0
for a in "$@"; do case "$a" in --check) CHECK=1 ;; --link-skills) LINK_SKILLS=1 ;; esac; done

ok() { printf "  \033[32m✓\033[0m %s\n" "$1"; }
bad() { printf "  \033[31m✗\033[0m %s\n" "$1"; MISSING=1; }
MISSING=0

echo "claude-reelsmith · $ROOT"
echo "System tools:"
for t in ffmpeg ffprobe node npm python3; do command -v "$t" >/dev/null && ok "$t" || bad "$t (macOS: brew install ffmpeg node python)"; done
if [ "$(uname)" = Darwin ]; then command -v swiftc >/dev/null && ok "swiftc (person masks)" || bad "swiftc (xcode-select --install)"; fi
if command -v node >/dev/null; then
  v=$(node -p 'process.versions.node.split(".")[0]'); [ "$v" -ge 20 ] && ok "node $v" || bad "node >= 20 needed (have $v)"
fi

if [ "$CHECK" = 1 ]; then
  echo "Project:"
  [ -x "$DATA/venv/bin/python" ] && ok "python venv ($DATA/venv)" || bad "python venv (run: reelsmith setup)"
  [ -d "$ROOT/node_modules/playwright" ] && ok "playwright" || bad "playwright (run: reelsmith setup)"
  [ -x "$DATA/bin/masks" ] && ok "mask tool" || echo "  · mask tool: built on first use (macOS)"
  command -v reelsmith >/dev/null && ok "reelsmith on PATH" || bad "reelsmith not on PATH (add ~/.local/bin to PATH)"
  [ -n "${ELEVENLABS_API_KEY:-}" ] || [ -f "$HOME/.config/reelsmith/.env" ] && ok "ElevenLabs key" || echo "  · ElevenLabs key: optional, see docs/voice.md"
  [ -d "${CAPCUT_PLUGIN_DIR:-$HOME/capcut-plugin}" ] && ok "CapCut plugin bundle" || echo "  · CapCut plugin bundle: optional, see docs/capcut.md"
  exit $MISSING
fi
[ "$MISSING" = 0 ] || { echo "Install the missing tools above, then run this again."; exit 1; }

echo "Python venv:"
mkdir -p "$DATA"
[ -x "$DATA/venv/bin/python" ] || python3 -m venv "$DATA/venv"
"$DATA/venv/bin/pip" install -q --upgrade pip
"$DATA/venv/bin/pip" install -q -r "$ROOT/requirements.txt" && ok "numpy, faster-whisper, opencv → $DATA/venv"

echo "Node + Chromium:"
[ -d "$ROOT/node_modules/playwright" ] || (cd "$ROOT" && npm install --silent); ok "playwright, three"
(cd "$ROOT" && npx --yes playwright install chromium >/dev/null) && ok "chromium"

if [ "$(uname)" = Darwin ]; then
  echo "Mask tool:"
  mkdir -p "$DATA/bin" && swiftc -O "$ROOT/tools/masks.swift" -o "$DATA/bin/masks" 2>/dev/null && ok "$DATA/bin/masks"
fi

echo "Command:"
mkdir -p "$HOME/.local/bin"; chmod +x "$ROOT/bin/reelsmith"; ln -sf "$ROOT/bin/reelsmith" "$HOME/.local/bin/reelsmith"
ok "reelsmith → ~/.local/bin"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "  · add to your shell profile: export PATH=\"\$HOME/.local/bin:\$PATH\"";; esac

if [ "$LINK_SKILLS" = 1 ]; then
  echo "Skills (without the plugin system):"
  mkdir -p "$HOME/.claude/skills"
  for s in "$ROOT"/skills/*/; do n=$(basename "$s"); ln -sfn "$s" "$HOME/.claude/skills/$n"; ok "~/.claude/skills/$n"; done
fi
echo "Done. Next: open Claude Code and say \"make a reel from my clips\"."

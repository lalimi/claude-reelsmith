#!/usr/bin/env bash
# Fast, silent when ready: tells Claude once per session if reelsmith still needs `reelsmith setup`.
DATA="${REELSMITH_DATA:-$HOME/.local/share/reelsmith}"
[ -x "$DATA/venv/bin/python" ] && exit 0
echo "reelsmith: dependencies are not installed yet. Before building a reel, run \`reelsmith setup\` (takes 2-4 minutes, once)."

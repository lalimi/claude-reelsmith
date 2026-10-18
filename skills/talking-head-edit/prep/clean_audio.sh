#!/usr/bin/env bash
# Clean a talking-head voice track: light noise removal + gate, de-essing, gentle EQ + compression,
# two-pass loudness to -14 LUFS (what Instagram/TikTok expect). Mono 48 kHz WAV out.
# Usage: clean_audio.sh <clip> <out.wav> [--no-denoise]
# Ported from github.com/nicolapocock/claude-reel-editor (MIT, see LICENSE-claude-reel-editor).
set -euo pipefail
IN="$1"; OUT="$2"; DENOISE="${3:---denoise}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

ffmpeg -v error -y -i "$IN" -vn -ac 1 -ar 48000 "$TMP/raw.wav"
SRC="$TMP/raw.wav"

if [[ "$DENOISE" == "--denoise" ]]; then
  if command -v deepFilter >/dev/null 2>&1; then
    deepFilter -a "${DENOISE_DB:-30}" "$SRC" -o "$TMP/dfn" >/dev/null 2>&1   # capped at 30 dB: natural, no underwater artefacts
    SRC="$(ls "$TMP"/dfn/*.wav | head -1)"
  else
    ffmpeg -v error -y -i "$SRC" -af "afftdn=nf=-25" "$TMP/dn.wav"         # built-in denoiser (weaker on birds/traffic)
    SRC="$TMP/dn.wav"
  fi
fi

# Gate pulls leftover noise between words down ~12 dB; then rumble cut, less boxiness, more clarity and air,
# de-ess (the clarity boost exaggerates "с/ш/ч"), light 3:1 compression.
GATE="agate=threshold=0.015:ratio=3:range=0.25:attack=4:release=150,"
[[ "$DENOISE" == "--no-denoise" ]] && GATE=""
CHAIN="${GATE}highpass=f=85,equalizer=f=220:t=q:w=1:g=-2.5,equalizer=f=3200:t=q:w=1:g=2.5,highshelf=f=9000:g=2,deesser=i=0.4:m=0.5:f=0.5,acompressor=ratio=3:threshold=-20dB:attack=5:release=80"
LN="loudnorm=I=-14:TP=-1.5:LRA=7"

J="$(ffmpeg -hide_banner -i "$SRC" -af "$CHAIN,$LN:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')"
m() { printf '%s' "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['$1'])"; }

ffmpeg -v error -y -i "$SRC" -af "$CHAIN,$LN:measured_I=$(m input_i):measured_TP=$(m input_tp):measured_LRA=$(m input_lra):measured_thresh=$(m input_thresh):offset=$(m target_offset):linear=true" -ar 48000 "$OUT"

# The gaps between words must be quiet: 10th-percentile 50 ms level = the background.
FLOOR="$(python3 - "$OUT" <<'PY'
import array, math, sys, wave
w = wave.open(sys.argv[1]); sr = w.getframerate(); a = array.array("h"); a.frombytes(w.readframes(w.getnframes()))
hop = int(sr * 0.05)
lev = sorted(20 * math.log10(max(1.0, math.sqrt(sum(x * x for x in a[i:i + hop:4]) / (hop / 4))) / 32768) for i in range(0, len(a) - hop, hop))
print(round(lev[len(lev) // 10]))
PY
)"
echo "фон між словами: ${FLOOR} dB (треба -45 або тихіше)" >&2
[ "$FLOOR" -le -45 ] || echo "УВАГА: все ще шумно, перевір сирий запис (вітер і шурхіт до кінця не прибрати)" >&2
echo "$OUT"

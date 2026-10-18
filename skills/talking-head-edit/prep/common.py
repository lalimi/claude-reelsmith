"""Shared bits for the prep scripts: pacing presets, filler words (English + Ukrainian), audio level helpers.
Pacing presets and the pause/air idea are ported from github.com/nicolapocock/claude-reel-editor (MIT)."""
import json, os, re, subprocess, wave
from pathlib import Path
import numpy as np

# pauses longer than pause_min get shortened, leaving `air` seconds either side of the cut
PRESETS = {
    "natural": {"speed": 1.0, "pause_min": 0.6, "air": 0.15},
    "tight":   {"speed": 1.1, "pause_min": 0.3, "air": 0.07},
    "fast":    {"speed": 1.15, "pause_min": 0.22, "air": 0.05},
}

def pacing(edl):
    p = dict(PRESETS.get(edl.get("pacing", "natural"), PRESETS["natural"]))
    if edl.get("speed"): p["speed"] = float(edl["speed"])
    return p

# "hard" fillers are pure hesitation sounds: cut automatically by tighten.py.
# "soft" fillers are real words that are often filler: only flagged in the rough-cut table, cut if the person agrees.
HARD = {"е", "ем", "м", "хм", "э", "эм", "um", "uh", "erm", "hmm", "mm", "ah", "eh"}
SOFT = {"ну", "типу", "коротше", "значить", "ось", "от", "взагалі", "фактично", "просто", "загалом",
        "like", "basically", "actually", "literally", "so", "well", "right"}

# Whisper language: REELSMITH_LANG=uk / en / pl … or unset = auto-detect
LANG = os.environ.get("REELSMITH_LANG") or None
# a hesitation-rich prompt makes Whisper keep fillers in the transcript (so prep can cut them)
FILLER_PROMPT = {"uk": "Ееее, ну, мм, я тут, ем, типу, ееее, хм, ну от, значить.",
                 "en": "Umm, so, uh, I mean, like, umm, hmm, you know, er."}

def norm(w):
    return re.sub(r"[^\w' ]", "", w.lower().replace("’", "'")).replace("_", "").strip()

def filler_kind(w):
    n = norm(w)
    c = re.sub(r"(.)\1+", r"\1", n)            # еее -> е, ммм -> м, емм -> ем
    if c in HARD: return "hard"
    if c == "а" and len(n) >= 2: return "hard"  # "аа" is a hesitation, "а" is a real word
    if n in SOFT: return "soft"
    return None

def load_wav(path):
    w = wave.open(str(path)); sr = w.getframerate(); ch = w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if ch > 1: a = a.reshape(-1, ch).mean(axis=1)
    return a, sr

def level_db(a, sr, t0, t1):
    i0, i1 = max(0, int(t0 * sr)), min(len(a), int(t1 * sr))
    if i1 <= i0: return -120.0
    return float(20 * np.log10(max(1e-6, np.sqrt(np.mean(a[i0:i1] ** 2)))))

def floor_db(a, sr, pct=10):
    hop = int(sr * 0.05); n = len(a) // hop
    lev = 20 * np.log10(np.maximum(1e-6, np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(axis=1))))
    return float(np.percentile(lev, pct))

def snap(a, sr, t, lo, hi, win=0.02):
    """Move a cut edge to the quietest 20 ms window in [lo, hi] (the gap between words), staying near t."""
    lo, hi = max(0.0, lo), min(len(a) / sr - win, hi)
    if hi <= lo: return t
    best, bt = None, t
    for c in np.arange(lo, hi, 0.005):
        l = level_db(a, sr, c, c + win) + 2.0 * abs(c - t) / max(1e-3, hi - lo)   # tie-break towards t
        if best is None or l < best: best, bt = l, c + win / 2
    return round(float(bt), 3)

def probe(path, entries, stream="v:0"):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", entries, "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)

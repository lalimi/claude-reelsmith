"""Tighten an approved rough cut: snap span edges into the quiet between words, remove hesitation fillers
(raw_words.json, "hard" kind) and shorten pauses inside the kept spans, as hard as edl.json "pacing" says.
Usage: "$(reelsmith py)" -I prep/tighten.py <job-dir>
Reads edl.json {"source","audio","pacing","keep":[[s,e],...],"cut":[[s,e],...]?}; the approved version is kept as
edl_rough.json and re-runs start from it, so tightening twice never double-cuts.
Approach (filler prompt, silencedetect above this clip's own noise floor, air at every edge) ported from
github.com/nicolapocock/claude-reel-editor (MIT)."""
import json, re, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import floor_db, load_wav, pacing, snap

job = Path(sys.argv[1]).expanduser().resolve()
rough = job / "edl_rough.json"
if not rough.exists(): shutil.copy(job / "edl.json", rough)
edl = json.load(open(rough))
P = pacing(edl); AIR, MIN_PAUSE = P["air"], P["pause_min"]
voice = job / edl.get("audio", "voice.wav")
a, sr = load_wav(voice)

# 1. approved span edges -> the quietest point next to them
keep = [[snap(a, sr, s, s - 0.12, s + 0.04), snap(a, sr, e, e - 0.04, e + 0.12)] for s, e in edl["keep"]]

# 2. hesitation fillers, with the gap around them, leaving AIR either side
cuts, nf = [], 0
wp = job / "raw_words.json"
words = json.load(open(wp)) if wp.exists() else []
if not words: print("raw_words.json немає: паразити не ріжу (спершу prep/lines.py)")
for k, w in enumerate(words):
    if w.get("filler") != "hard": continue
    lo = words[k - 1]["e"] if k else 0.0
    hi = words[k + 1]["s"] if k + 1 < len(words) else len(a) / sr
    ca = max(lo + 0.02, min(w["s"] - 0.01, lo + AIR))
    cb = min(hi - 0.02, max(w["e"] + 0.01, hi - AIR))
    ca, cb = snap(a, sr, ca, lo + 0.02, w["s"]), snap(a, sr, cb, w["e"], hi - 0.02)
    if cb - ca > 0.06: cuts.append((ca, cb)); nf += 1

# 3. extra cuts the person approved (soft fillers, a restarted half-sentence inside a kept line)
for s, e in edl.get("cut", []):
    cuts.append((snap(a, sr, s, s - 0.08, s + 0.03), snap(a, sr, e, e - 0.03, e + 0.08)))

# 4. pauses: silencedetect just above THIS clip's background (noisy rooms never reach a fixed -40 dB).
#    floor is a 50 ms RMS, silencedetect looks at sample peaks (~10 dB higher on noise), hence +15
fl = floor_db(a, sr); th = min(fl + 15, -30)
err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(voice), "-af", f"silencedetect=noise={th:.1f}dB:d={MIN_PAUSE}", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
pauses = [(s + AIR, e - AIR) for s, e in zip(st, en) if e - s > MIN_PAUSE]
cuts = sorted(cuts + pauses)

def subtract(span):
    s, e = span; parts, cur = [], s
    for ca, cb in cuts:
        if cb <= cur or ca >= e: continue
        if ca > cur + 0.05: parts.append([round(cur, 3), round(ca, 3)])
        cur = max(cur, cb)
    if e > cur + 0.05: parts.append([round(cur, 3), round(e, 3)])
    return parts

# a sliver between two cuts (< 0.25 s, no real word in it) would flash as a 2-6 frame jump: drop it
real = [(w["s"] + w["e"]) / 2 for w in words if w.get("filler") != "hard"]
def worth(p):
    return p[1] - p[0] >= 0.25 or any(p[0] <= m <= p[1] for m in real) if real else p[1] - p[0] >= 0.12

before = sum(e - s for s, e in edl["keep"])
edl["keep"] = [p for span in keep for p in subtract(span) if worth(p)]
after = sum(e - s for s, e in edl["keep"])
json.dump(edl, open(job / "edl.json", "w"), ensure_ascii=False)
print(f"фон {fl:.0f} dB -> поріг пауз {th:.0f} dB · pacing {edl.get('pacing', 'natural')}")
print(f"паразитів вирізано {nf} · пауз скорочено {len(pauses)} · ручних вирізок {len(edl.get('cut', []))}")
print(f"{before:.1f} с -> {after:.1f} с ({len(edl['keep'])} шматків, швидкість {P['speed']}x -> {after / P['speed']:.1f} с)")

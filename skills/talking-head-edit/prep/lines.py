"""Rough-cut table: transcribe the cleaned voice so that fillers get written down, group words into spoken lines,
flag fillers and repeats, and grab head/tail contact sheets to spot camera setup at the start and end.
Usage: "$(reelsmith py)" -I prep/lines.py <job-dir> [model]      needs <job>/raw.* and <job>/voice.wav
Writes raw_words.json, lines.json, head.jpg, tail.jpg; prints the numbered table to propose cuts from."""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FILLER_PROMPT, LANG, filler_kind, norm, probe
from faster_whisper import WhisperModel

job = Path(sys.argv[1]).expanduser().resolve()
size = sys.argv[2] if len(sys.argv) > 2 else "small"
raw = next((p for p in sorted(job.glob("raw.*"))), None)
voice = job / "voice.wav"
if not raw or not voice.exists(): sys.exit("need <job>/raw.<ext> (copy of the clip) and <job>/voice.wav (prep/clean_audio.sh)")

# A prompt full of hesitations makes Whisper write them down instead of hiding them inside neighbouring words.
m = WhisperModel(size, device="cpu", compute_type="int8")
segs, _ = m.transcribe(str(voice), language=LANG, word_timestamps=True, vad_filter=True, condition_on_previous_text=False,
                       initial_prompt=FILLER_PROMPT.get(LANG or "", FILLER_PROMPT["en"]))
words = []
for s in segs:
    for w in s.words:
        t = w.word.strip()
        if t: words.append({"w": t, "s": round(w.start, 3), "e": round(w.end, 3), "filler": filler_kind(t)})
if not words: sys.exit("Whisper не почув мови у voice.wav")
for a, b in zip(words, words[1:]):              # "я я", "це це": a stutter, propose cutting the first one
    if norm(a["w"]) and norm(a["w"]) == norm(b["w"]) and b["s"] - a["e"] < 0.6 and not a["filler"]: a["repeat"] = True
json.dump(words, open(job / "raw_words.json", "w"), ensure_ascii=False, indent=0)

lines, cur = [], []
for i, w in enumerate(words):
    cur.append(i)
    nxt = words[i + 1] if i + 1 < len(words) else None
    if not nxt or nxt["s"] - w["e"] > 0.4 or w["w"][-1] in ".?!…" or len(cur) >= 14:
        lines.append({"n": len(lines) + 1, "s": words[cur[0]]["s"], "e": w["e"], "words": cur}); cur = []
def show(i):
    w = words[i]
    if w["filler"] == "hard": return f"[{w['w']}]"
    if w["filler"] == "soft": return f"({w['w']})"
    if w.get("repeat"): return f"«{w['w']}»"
    return w["w"]
for L in lines: L["text"] = " ".join(words[i]["w"] for i in L["words"])
json.dump(lines, open(job / "lines.json", "w"), ensure_ascii=False, indent=1)

# contact sheets: a frame every 0.5 s over the first and last 4 s (camera setup, reaching for the phone)
dur = float(probe(raw, "format=duration")["format"]["duration"])
for name, ss in (("head", 0), ("tail", max(0, dur - 4))):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", "4", "-i", str(raw), "-vf",
                    "fps=2,scale=216:-2,tile=8x1:padding=4", "-frames:v", "1", str(job / f"{name}.jpg")], check=True)

for L in lines:
    print(f"{L['n']:>3}  {L['s']:6.2f}–{L['e']:6.2f}  " + " ".join(show(i) for i in L["words"]))
hard = sum(w["filler"] == "hard" for w in words); soft = sum(w["filler"] == "soft" for w in words)
gaps = sum(b["s"] - a["e"] > 0.6 for a, b in zip(words, words[1:]))
print(f"\nсирий запис {dur:.1f} с · мова {words[-1]['e'] - words[0]['s']:.1f} с · [паразити-звуки] {hard} (ріже tighten.py)"
      f" · (можливі паразити) {soft} · «повтори» {sum(bool(w.get('repeat')) for w in words)} · паузи > 0.6 с: {gaps}")
print(f"head.jpg / tail.jpg: {job}  (кадр кожні 0.5 с, перші та останні 4 с)")

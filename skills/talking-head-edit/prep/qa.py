"""QA gate for a reel: size, length, loudness, true peak, quiet between words, joins not inside a word,
and that no words were lost: the reference is the raw transcript (raw_words.json) of what edl.json keeps,
or <job>/expected.txt when it exists.
Usage: "$(reelsmith py)" -I prep/qa.py <job-dir> [video]     default video: out.mp4. Exit 1 if anything fails.
Based on qa.py from github.com/nicolapocock/claude-reel-editor (MIT)."""
import difflib, json, re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import LANG, floor_db, level_db, load_wav, norm, probe

job = Path(sys.argv[1]).expanduser().resolve()
video = job / (sys.argv[2] if len(sys.argv) > 2 else "out.mp4")
fails, warns = [], []
ed = json.load(open(job / "edit.json")) if (job / "edit.json").exists() else {}
want = [ed.get("width", 1080), ed.get("height", 1920)]

info = probe(video, "stream=width,height:format=duration")
w, h = info["streams"][0]["width"], info["streams"][0]["height"]; dur = float(info["format"]["duration"])
print(f"розмір     {w}x{h}  (треба {want[0]}x{want[1]})")
if [w, h] != want: fails.append("розмір")
print(f"довжина    {dur:.1f} с  (рілс краще до 60 с, максимум 90)")
if dur > 90: fails.append("довжина")
elif dur > 60: warns.append("довше 60 с")

ebu = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebu)[-1])
peak = float((re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebu) or ["-99"])[-1])
print(f"гучність   {lufs:.1f} LUFS  (треба від -15 до -12.5) · пік {peak:.1f} dBTP (треба ≤ -1)")
if not -15 <= lufs <= -12.5: fails.append("гучність")
if peak > -1: warns.append("пік вище -1 dBTP")

with tempfile.TemporaryDirectory() as tmp:
    wav = Path(tmp) / "a.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "48000", str(wav)], check=True)
    a, sr = load_wav(wav)
    fl = floor_db(a, sr, 3)   # a tightened cut has little silence left: look at the quietest 3 %
    print(f"фон        {fl:.0f} dB між словами  (треба -45 або тихіше)")
    if fl > -45: warns.append("шумний фон")

    # a join inside a word is loud on both sides of the cut: listen to those
    jp = job / "joins.json"
    if jp.exists() and video.name in ("aroll.mp4", "out.mp4"):
        off = float(ed.get("sourceOffset", 0)) if video.name == "out.mp4" else 0.0
        bad = [t for t in json.load(open(jp)) if min(level_db(a, sr, t - off - 0.03, t - off), level_db(a, sr, t - off, t - off + 0.03)) > fl + 25]
        print(f"склейки    {len(json.load(open(jp)))} шт." + (f", можливо обрізане слово на: {bad}" if bad else ", всі в тиші"))
        if bad: warns.append("склейки посеред слова")

    exp, rw, el = job / "expected.txt", job / "raw_words.json", job / "edl.json"
    ref = None
    if exp.exists(): ref = exp.read_text()
    elif rw.exists() and el.exists():   # same Whisper on both sides, so "5" / "five" spellings match
        keep = json.load(open(el))["keep"]
        ref = " ".join(w["w"] for w in json.load(open(rw)) if w.get("filler") != "hard"
                       and any(s <= (w["s"] + w["e"]) / 2 <= e for s, e in keep))
    if ref:
        from faster_whisper import WhisperModel
        segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(str(wav), language=LANG, vad_filter=True)
        tok = lambda s: [t for t in norm(re.sub(r"[-–—]", " ", s)).split() if t]
        heard, expected = tok(" ".join(s.text for s in segs)), tok(ref)
        sm = difflib.SequenceMatcher(None, expected, heard, autojunk=False)
        missing = [" ".join(expected[i1:i2]) for op, i1, i2, _, _ in sm.get_opcodes() if op in ("delete", "replace")]
        print(f"слова      {sm.ratio():.0%} збіг" + (f"; перевір на слух: {missing[:8]}" if missing else ""))
        if sm.ratio() < 0.9: fails.append("слова")
    else:
        print("слова      пропущено (немає raw_words.json + edl.json чи expected.txt)")

if warns: print("увага:", ", ".join(warns))
print("PASS" if not fails else f"FAIL: {', '.join(fails)}")
sys.exit(1 if fails else 0)

"""Build a voice-over reel from <job>/reel.json in one command.

voice (ElevenLabs mp3) -> timed voice (offset + breathing gaps) -> word timings (faster-whisper)
-> subtitles from the script (<em> = accent words, auto-chunked to <= subs_words words (5), 1-2 lines)
-> punch-ins on accent words -> footage frames -> page render (template.html) -> music shaped by the
structure -> mix to -14 LUFS -> safe-zone QA sheet, cover, caption.

Usage:
  reelsmith build <reel-dir> [--stills] [--capcut]
  (= $(reelsmith py) $(reelsmith root)/engine/build.py <reel-dir> ...)
  --stills  only resolve + frames + QA sheet (fast preview, no video)
  --capcut  also render a no-subtitles video and a music track without SFX for the CapCut draft
  --lint    only the retention checks (first seconds, pace, CTA length, voice pace, subtitles; plus the
            rendered out/reel.mp4 if it exists), no frames or render. Evidence: docs/retention.md
reel.json format: skills/reel-builder/SKILL.md"""
import difflib, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
import numpy as np

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parent                                   # repo root
RENDER = ROOT / "tools" / "render.mjs"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ROOT / "skills/talking-head-edit/prep"))
from common import load_wav, snap                       # noqa: E402
import music                                            # noqa: E402

FPS, W, H = 30, 1080, 1920


def sh(*a, **k):
    return subprocess.run([str(x) for x in a], check=True, **k)


def resolve(job, p):
    p = os.path.expanduser(str(p))
    cands = [Path(p)] if os.path.isabs(p) else [job / p, Path.cwd() / p, ROOT / p]
    for q in cands:
        if q.exists(): return q
    sys.exit(f"file not found: {p}")


def fresh(out, key):
    """True when `out` was built from exactly this `key` (cache)."""
    k = out.with_name(out.name + ".key")
    return out.exists() and k.exists() and k.read_text() == key


def mark(out, key):
    out.with_name(out.name + ".key").write_text(key)


# ---------------------------------------------------------------- voice
def time_voice(job, vo):
    """Place the voice at `offset`, insert breathing gaps [[vo_time, extra_s]] at the quietest point nearby."""
    src = resolve(job, vo["file"]); out = job / "out/vo_timed.wav"
    key = json.dumps(vo, sort_keys=True) + str(src.stat().st_mtime)
    if fresh(out, key): return out
    raw = job / "out/vo_raw.wav"                     # speed: atempo first, so gap times are on the sped-up voice
    sh("ffmpeg", "-v", "error", "-y", "-i", src, *(["-af", f"atempo={vo['speed']}"] if vo.get("speed") else []), "-ar", "48000", "-ac", "1", raw)
    a, sr = load_wav(raw); raw.unlink()
    shift, prev, parts = vo.get("offset", 0.05), 0.0, []   # voice from the first frames (skip rate)
    for t, extra in sorted(vo.get("gaps", [])):
        c = snap(a, sr, t, t - 0.25, t + 0.25)
        parts.append((prev, c, shift)); shift += extra; prev = c
    parts.append((prev, len(a) / sr, shift))
    buf = np.zeros(int((parts[-1][1] + parts[-1][2] + 0.1) * sr)); f = np.linspace(0, 1, int(0.02 * sr))
    for s, e, d in parts:
        seg = a[int(s * sr):int(e * sr)].copy()
        if len(seg) > 2 * len(f): seg[:len(f)] *= f; seg[-len(f):] *= f[::-1]
        i = int((s + d) * sr); buf[i:i + len(seg)] += seg[:len(buf) - i]
    import wave
    with wave.open(str(out), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    mark(out, key)
    return out


def transcribe(wav, lang=None):
    out = wav.with_name("words.json"); key = str(wav.stat().st_mtime) + str(lang)
    if fresh(out, key): return json.load(open(out))
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    for vad in (True, False):                          # word alignment occasionally crashes with VAD on
        try:
            segs, _ = m.transcribe(str(wav), language=lang, word_timestamps=True, vad_filter=vad)
            words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words if w.word.strip()]
            break
        except IndexError:
            continue
    json.dump(words, open(out, "w"), ensure_ascii=False); mark(out, key)
    return words


# ---------------------------------------------------------------- subtitles
norm = lambda w: re.sub(r"[^\w']", "", w.lower().replace("’", "'")).replace("_", "")


def script_tokens(script):
    toks, em, glued = [], False, False
    for part in re.split(r"(<em>|</em>)", script):
        if part in ("<em>", "</em>"): em = part == "<em>"; continue
        words = part.split()
        if words and toks and glued and not part[:1].isspace():   # "…</em>." : punctuation sticks to the accent word
            toks[-1]["t"] += words.pop(0)
        toks += [{"t": w, "em": em} for w in words]
        glued = bool(part) and not part[-1:].isspace()
    return toks


def align(toks, words):
    sm = difflib.SequenceMatcher(None, [norm(t["t"]) for t in toks], [norm(w["w"]) for w in words], autojunk=False)
    for b in sm.get_matching_blocks():
        for k in range(b.size):
            toks[b.a + k].update(s=words[b.b + k]["s"], e=words[b.b + k]["e"])
    known = [i for i, t in enumerate(toks) if "s" in t]
    for i, t in enumerate(toks):                       # unmatched words (numbers, names): spread between neighbours
        if "s" in t: continue
        p = max((j for j in known if j < i), default=None); n = min((j for j in known if j > i), default=None)
        lo = toks[p]["e"] if p is not None else (toks[n]["s"] - 0.3 if n is not None else 0)
        hi = toks[n]["s"] if n is not None else lo + 0.3 * (i - (p or 0) + 1)
        a0, b0 = (p if p is not None else -1), (n if n is not None else len(toks))
        t["s"] = lo + (hi - lo) * (i - a0) / (b0 - a0); t["e"] = t["s"] + 0.2
    return toks, sum(b.size for b in sm.get_matching_blocks()) / max(1, len(toks))


WEAK = set(("і й та а але в у з із зі до від на по за для про що як де бо чи не ні ж же "     # uk
             "and a an the of to in on at for with or but by from as that so not").split())        # en
TIME_KEYS = {"at", "to", "from", "out", "lines_at", "sub_at", "handle_at"}


def anchor(toks, v):
    """'@thousand' -> start of the first script word equal to (else beginning with) 'thousand'; '@again#2+0.2' = 2nd hit, +0.2 s."""
    if not (isinstance(v, str) and v.startswith("@")): return v
    m = re.fullmatch(r"@(.+?)(?:#(\d+))?([+-][\d.]+)?", v)
    w = norm(m[1]); hits = [t for t in toks if norm(t["t"]) == w] or [t for t in toks if norm(t["t"]).startswith(w)]
    if len(hits) < int(m[2] or 1): sys.exit(f"anchor {v}: no such word in the script")
    return round(hits[int(m[2] or 1) - 1]["s"] + float(m[3] or 0), 3)


def anchors(toks, o, key=None):
    if isinstance(o, dict): return {k: anchors(toks, v, k) for k, v in o.items()}
    if isinstance(o, list): return [anchors(toks, v, key) for v in o]
    return anchor(toks, o) if key in TIME_KEYS else o


def make_subs(toks, lo, hi, lower_first=True, maxw=7, maxc=46, skip=()):
    chunks, cur = [], []
    for t in toks:
        if t["s"] < lo - 0.05 or t["s"] >= hi or any(a <= t["s"] < b for a, b in skip):
            if cur: chunks.append(cur); cur = []
            continue
        if cur:
            p = cur[-1]; chars = sum(len(x["t"]) + 1 for x in cur) + len(t["t"])
            in_accent = t["em"] and p["em"] and len(cur) < maxw + 3      # never split an accent phrase
            if (re.search(r"[.!?…]$", p["t"]) or (re.search(r"[,;:]$", p["t"]) and len(cur) >= 4)
                    or (not in_accent and (len(cur) >= maxw or chars > maxc)) or t["s"] - p["e"] > 0.5):
                chunks.append(cur); cur = []
        cur.append(t)
    if cur: chunks.append(cur)
    for a, b in zip(chunks, chunks[1:]):              # "… for 99 and | then a discount": a line never ends on "and", "in", "of"
        while len(a) > 2 and norm(a[-1]["t"]) in WEAK and not re.search(r"[.!?…,;:]$", a[-1]["t"]) and b[0]["s"] - a[-1]["e"] < 0.5:
            b.insert(0, a.pop())
    merged, carry = [], []                             # no orphan 1-2 word subtitles
    for i, c in enumerate(chunks):
        c = carry + c; carry = []
        if len(c) <= 2 and i + 1 < len(chunks) and not re.search(r"[.!?…,;:]$", c[-1]["t"]):
            carry = c; continue                        # "but" belongs to what follows
        if len(c) <= 2 and merged and not re.search(r"[.!?…]$", merged[-1][-1]["t"]) and len(merged[-1]) + len(c) <= maxw + 1:
            merged[-1] = merged[-1] + c; continue
        merged.append(c)
    if carry: merged.append(carry)
    subs = []
    for i, c in enumerate(merged):
        words = [x["t"] for x in c]; total = len(" ".join(words)); brk = None
        if total > 24:
            best = None
            for k in range(1, len(words)):
                score = abs(len(" ".join(words[:k])) - total / 2) - (8 if words[k - 1].endswith(",") else 0)
                if best is None or score < best: best, brk = score, k
        s, inem = "", False
        for k, x in enumerate(c):
            w = x["t"]
            if k == 0 and lower_first and w[:1].isupper() and not (len(w) > 1 and w[1:2].isupper()): w = w[0].lower() + w[1:]
            if k == len(c) - 1: w = w.rstrip(".,;:")        # subtitles end without a dot or comma
            if inem and not x["em"]: s += "</em>"; inem = False
            if k: s += "<br>" if k == brk else " "
            if x["em"] and not inem: s += "<em>"; inem = True
            s += w
        if inem: s += "</em>"
        st = max(lo, c[0]["s"] - 0.08)
        nxt = merged[i + 1][0]["s"] - 0.08 if i + 1 < len(merged) else hi
        en = min(nxt - 0.02, max(c[-1]["e"] + 0.35, st + 0.6), hi)
        if en - st < 0.45: continue                    # would only flash (e.g. runs into the end card)
        subs.append([round(st, 2), round(en, 2), s])
    return subs


def auto_punch(toks, segs, max_n=4, gap=3.0):
    starts = [float(t["s"]) for i, t in enumerate(toks) if t["em"] and (i == 0 or not toks[i - 1]["em"])]
    out = []
    for t in starts:
        if out and t - out[-1][0] < gap: continue
        k = next((j for j, s in enumerate(segs) if s["t0"] <= t < s["t0"] + s["dur"]), None)
        if k is None: continue
        until = segs[k]["t0"] + segs[k]["dur"]                       # hold to the cut ...
        if until - t < 0.8 and k + 1 < len(segs):                    # ... unless the cut is too close
            until = min(t + 1.2, segs[k + 1]["t0"] + segs[k + 1]["dur"])
        out.append([round(t, 2), round(min(until, t + 2.5), 2)])
        if len(out) == max_n: break
    return out


# ---------------------------------------------------------------- footage
def frames(job, seg):
    out = job / "frames" / seg["id"]
    src_file = resolve(job, seg.get("img") or seg["clip"])
    key = json.dumps({**{k: seg.get(k) for k in ("clip", "img", "ss", "dur", "crop", "pos", "rate")},
                      "mtime": src_file.stat().st_mtime}, sort_keys=True)   # a replaced source file re-extracts
    if (out / ".key").exists() and (out / ".key").read_text() == key:
        return len(list(out.glob("*.jpg")))
    shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}:(iw-{W})*{seg.get('pos', 0.5)}:(ih-{H})/2"
    if seg.get("crop"):
        x, y, z = seg["crop"]; fit = f"crop=iw*{z}:ih*{z}:iw*{x}:ih*{y}," + fit
    if seg.get("img"):
        src = resolve(job, seg["img"]); tmp = out / "_src.jpg"
        sh("sips", "-s", "format", "jpeg", src, "--out", tmp, capture_output=True)
        sh("ffmpeg", "-v", "error", "-y", "-i", tmp, "-vf", fit, "-q:v", "2", out / "0001.jpg"); tmp.unlink()
    else:
        sh("ffmpeg", "-v", "error", "-y", "-ss", seg.get("ss", 0), "-i", resolve(job, seg["clip"]), "-frames:v", round(seg["dur"] * FPS) + 2,
           "-vf", (f"setpts=PTS/{seg['rate']}," if seg.get("rate") else "") + f"fps={FPS}," + fit, "-q:v", "3", out / "%04d.jpg")
    (out / ".key").write_text(key)
    return len(list(out.glob("*.jpg")))


def masks(job, seg):
    """Vision person masks for a segment's frames (alpha PNGs) + head positions, cached with the frames."""
    src, out = job / "frames" / seg["id"], job / "frames" / (seg["id"] + "_m")
    key = (src / ".key").read_text()
    if (out / ".key").exists() and (out / ".key").read_text() == key:
        return json.load(open(out / "meta.json"))
    shutil.rmtree(out, ignore_errors=True)
    data = Path(os.environ.get("REELSMITH_DATA", Path.home() / ".local/share/reelsmith"))
    tool, code = data / "bin" / "masks", ROOT / "tools" / "masks.swift"
    tool.parent.mkdir(parents=True, exist_ok=True)
    if not tool.exists() or tool.stat().st_mtime < code.stat().st_mtime:
        sh("swiftc", "-O", code, "-o", tool)
    sh(tool, src, out)
    (out / ".key").write_text(key)
    return json.load(open(out / "meta.json"))


# ---------------------------------------------------------------- audio out
def mix(job, video, voice, music_wav, out, dur, music_gain=0.16):
    ins = ["-i", video, "-i", voice] + (["-i", music_wav] if music_wav else [])
    if music_wav:
        fc = (f"[1:a]highpass=f=70,aformat=channel_layouts=stereo,asplit=2[v][sc];[2:a]volume={music_gain}[m];"
              "[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=380[md];[v][md]amix=inputs=2:normalize=0:duration=longest")
    else:
        fc = "[1:a]highpass=f=70,aformat=channel_layouts=stereo,apad"
    j = subprocess.run(["ffmpeg", "-hide_banner", *map(str, ins), "-filter_complex", fc + ",loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-t", str(dur), "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = json.loads(j[j.rindex("{"):j.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    sh("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", f"{fc},{ln},aresample=48000[a]", "-map", "0:v", "-map", "[a]",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", dur, "-movflags", "+faststart", out)


def loudness(f):
    e = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1]), float((re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e) or ["0"])[-1])


# ---------------------------------------------------------------- retention checks
# Evidence in docs/retention.md: Instagram counts views that leave within 3 s as skips; ~0.33 visual
# changes/s is the median and >0.5/s for long lowers rewatching; 42% of swipes fall in the last 20%;
# captions read comfortably at <= 17 chars/s.
def walls(spec):
    w = spec.get("wall")
    return w if isinstance(w, list) else [w] if w else []


def lint(spec, segs, words, subs, punch, dur):
    tips, hook, end = [], spec.get("hook"), spec.get("end")
    v0 = max(words[0]["s"], (spec.get("vo") or {}).get("offset", 0.05)) if words else 0   # whisper often says 0.0
    if v0 > 0.15:
        tips.append(f"the voice starts at {v0:.2f} s: start it in the first frames (vo.offset 0.05)")
    text0 = (hook and (not hook.get("at") or hook["at"][0] <= 0.3)) or any(w["from"] <= 0.3 for w in walls(spec)) \
        or (spec.get("cover") or {}).get("from", 9) <= 0.3
    if not text0:
        tips.append("no hook text in the first frame: the hook must work on mute from 0 s")
    if hook and re.search(r"comment|напиши|коментар", " ".join(hook.get("lines", [])), re.I):
        tips.append("code-word CTA inside the hook: put the CTA after the payoff")
    cuts = [x["t0"] for x in segs[1:]]
    ev = sorted(set([0.0] + cuts + [p[0] for p in punch] + [d["at"] for d in spec.get("doodles") or []]
                    + [w["from"] + i * w.get("every", 0.3) for w in walls(spec) for i in range(len(w["items"]))]
                    + [t for k in ("glass", "checklist") if spec.get(k) for t in (spec[k].get("at") or [])]
                    + [spec[k]["from"] for k in ("glass", "checklist", "orbit", "cover") if spec.get(k)]))
    stop = end["from"] if end else dur
    ev = [t for t in ev if t < stop] + [stop]
    rate = len(cuts) / dur if dur else 0
    dense = [t for t in cuts if sum(t <= c < t + 6 for c in cuts) > 3]
    print(f"pace: {len(cuts)} cuts in {dur:.1f} s = {rate:.2f}/s (target ~0.33)")
    if rate > 0.5: tips.append(f"too many cuts ({rate:.2f}/s): above 0.5/s lowers watch-through")
    if dense: tips.append(f"dense cutting (>0.5/s for over 6 s) from {dense[0]:.1f} s")
    for a, b in zip(ev, ev[1:]):
        if b - a > 4: tips.append(f"{a:.1f}–{b:.1f} s: {b - a:.1f} s with no visual change (punch-in, doodle or cut)")
    if len(words) > 20:
        wpm = len(words) / max(1, words[-1]["e"] - words[0]["s"]) * 60
        print(f"voice pace: {wpm:.0f} words/min")
        if wpm < 165 and (spec.get("vo") or {}).get("speed", 1) < 1.12:
            tips.append(f"slow voice ({wpm:.0f} words/min): try vo.speed 1.12–1.15")
    if end and dur - end["from"] > 3.5:
        tips.append(f"end card lasts {dur - end['from']:.1f} s (from {end['from']:.1f} s): keep it <= 3 s, most swipes happen at the end")
    if words and dur - words[-1]["e"] > 2:
        tips.append(f"{dur - words[-1]['e']:.1f} s after the last word: trim the tail")
    if dur > 60:
        tips.append(f"{dur:.1f} s: make a <= 59 s cut for YouTube Shorts (longer Shorts with a music claim are blocked)")
    fast = [x for x in subs if len(re.sub("<[^>]+>", "", x[2])) / max(0.1, x[1] - x[0]) > 17]
    if fast: tips.append(f"{len(fast)} subtitle(s) faster than 17 chars/s, e.g. \"{re.sub('<[^>]+>', ' ', fast[0][2])}\"")
    return tips


def ff_stats(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", *map(str, args), "-f", "null", "-"], capture_output=True, text=True).stderr


def qa_video(f):
    """Checks on the rendered file: first frame not dark, motion in the first 10 frames, no silent start, loop."""
    tips = []
    y = re.findall(r"YAVG=([\d.]+)", ff_stats("-i", f, "-frames:v", 1, "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG"))
    if y and float(y[0]) < 40: tips.append(f"dark first frame (luma {float(y[0]):.0f}/255)")
    m = re.findall(r"average:([\d.inf]+)", ff_stats("-i", f, "-i", f, "-filter_complex",
                   "[0:v]trim=end_frame=1[a];[1:v]trim=start_frame=9:end_frame=10,setpts=PTS-STARTPTS[b];[a][b]psnr"))
    if m and (m[0] == "inf" or float(m[0]) > 42): tips.append("the first 0.3 s are almost static: start the clip mid-motion")
    sd = ff_stats("-i", f, "-t", 1.5, "-af", "silencedetect=n=-45dB:d=0.15")
    sil = re.findall(r"silence_end: ([\d.]+)", sd)
    if sil and float(sil[0]) > 0.2 and "silence_start: 0" in sd: tips.append(f"silent start until {float(sil[0]):.2f} s")
    ss = re.findall(r"All:([\d.]+)", ff_stats("-i", f, "-sseof", -0.1, "-i", f, "-filter_complex", "[0:v]trim=end_frame=1[a];[1:v]trim=end_frame=1[b];[a][b]ssim"))
    if ss: print(f"loop: first vs last frame similarity {float(ss[0]):.2f}" + ("" if float(ss[0]) > 0.6 else " (loop not closed)"))
    return tips


def report(job, tips):
    print("RETENTION CHECKS:" + ("" if tips else " ✓ all good"))
    for t in tips: print("  •", t)
    (job / "out/lint.txt").write_text("\n".join(tips) + "\n")


# ---------------------------------------------------------------- main
def main():
    job = Path(sys.argv[1]).expanduser().resolve(); flags = set(sys.argv[2:])
    spec = json.load(open(job / "reel.json")); (job / "out").mkdir(exist_ok=True)
    warn = []

    # footage timeline
    segs, t0 = [], 0.0
    for s in spec["segments"]:
        s = dict(s); s["t0"] = round(t0, 4); t0 += s["dur"]; segs.append(s)
        if "--lint" in flags: continue
        s["n"] = frames(job, s)
        if s.get("cut"): s["head"] = masks(job, s)
    dur = round(t0, 3)
    print(f"frames: {len(segs)} segments, {dur} s")

    # voice -> words -> subtitles / punch
    voice, toks, words = None, [], []
    if spec.get("vo"):
        voice = time_voice(job, spec["vo"])
        words = transcribe(voice, spec.get("lang") or os.environ.get("REELSMITH_LANG") or None)   # None = auto-detect
        vo_end = words[-1]["e"] if words else 0
        if vo_end > dur - 0.8: warn.append(f"the voice ends at {vo_end:.1f} s but the video at {dur:.1f} s: make the last segment longer")
        if spec.get("script"):
            toks, ratio = align(script_tokens(spec["script"]), words)
            print(f"script ↔ voice: {ratio:.0%} of words matched")
            if ratio < 0.7: warn.append("the script differs a lot from the voice-over: check the text (or set \"lang\")")
    for k in ("hook", "end", "doodles", "glass", "checklist", "cover", "wall", "orbit"):   # "@word" times -> seconds
        if spec.get(k): spec[k] = anchors(toks, spec[k], k if k == "doodles" else None)
    for k in ("subs_skip", "punch", "subs_from", "subs_until"):
        if isinstance(spec.get(k), (list, str)): spec[k] = anchors(toks, spec[k], "at")
    hook, end = spec.get("hook"), spec.get("end")
    lo = spec.get("subs_from", hook.get("out", 0) + 0.15 if hook and hook.get("out") else 0)
    hi = spec.get("subs_until", end["from"] - 0.1 if end else dur)
    skip = [list(w) for w in spec.get("subs_skip", [])]                 # no subtitles under glass titles / checklists
    if spec.get("glass"): skip.append([spec["glass"]["from"] - 0.05, spec["glass"]["to"]])
    if spec.get("checklist"): skip.append([spec["checklist"]["from"] - 0.05, spec["checklist"]["to"]])
    sw = spec.get("subs_words", 5)                 # <= 17 chars/s reads comfortably
    subs = spec.get("subs") if spec.get("subs") not in (None, "auto") else (make_subs(toks, lo, hi, maxw=sw, maxc=sw * 7, skip=skip) if toks else [])
    punch = spec.get("punch") if spec.get("punch") not in (None, "auto") else (auto_punch(toks, segs) if toks else [])
    stamps = []
    for st in spec.get("stamps", []):
        if isinstance(st, dict):
            ids = st["seg"] if isinstance(st["seg"], list) else [st["seg"]]
            ss = [s for s in segs if s["id"] in ids]
            stamps.append([ss[0]["t0"], round(ss[-1]["t0"] + ss[-1]["dur"], 3), st["text"]])
        else:
            stamps.append(st)

    tips = lint(spec, segs, words, subs, punch, dur)
    if "--lint" in flags:
        if (job / "out/reel.mp4").exists(): tips += qa_video(job / "out/reel.mp4")
        report(job, tips); return

    # page
    page = {"fps": FPS, "duration": dur, "segments": [{k: s.get(k) for k in ("id", "dur", "n", "look", "move", "date", "t0", "in", "cut", "head")} for s in segs],
            "subs": subs, "punch": punch, "stamps": stamps, "hook": hook, "end": end, "colors": spec.get("colors"),
            "doodles": spec.get("doodles"), "glass": spec.get("glass"), "checklist": spec.get("checklist"),
            "cover": spec.get("cover"), "wall": spec.get("wall"), "orbit": spec.get("orbit")}
    (job / "spec.js").write_text("window.SPEC = " + json.dumps(page, ensure_ascii=False) + ";\n")
    shutil.copy(ENGINE / "template.html", job / "index.html")
    if not (job / "fonts").exists(): (job / "fonts").symlink_to(ENGINE / "fonts")
    json.dump(page, open(job / "out/resolved.json", "w"), ensure_ascii=False, indent=1)
    for a, b, s in subs: print(f"  {a:6.2f}–{b:6.2f}  {re.sub('<[^>]+>', ' ', s)}")
    print("punch-ins:", [[round(float(a), 2), round(float(b), 2)] for a, b in punch])

    # QA sheet: hook, a few subtitles, ending — with the Reels safe zone in red
    extra = [round(d["at"] + 0.5, 2) for d in spec.get("doodles") or [] if d["kind"] == "text"][:3]
    if spec.get("glass"): extra.append(round(spec["glass"]["to"] - 0.4, 2))
    if spec.get("checklist"): extra.append(round(spec["checklist"]["to"] - 0.4, 2))
    for k in ("cover", "orbit"):
        if spec.get(k): extra.append(round(min(spec[k]["from"] + 1.5, spec[k]["to"] - 0.3), 2))
    for w in (spec.get("wall") if isinstance(spec.get("wall"), list) else [spec.get("wall")] if spec.get("wall") else []):
        extra.append(round(w["from"] + 0.6 + 0.07 * len(w["items"]), 2))
    times = sorted(set(([0.5] if hook else []) + [round((a + b) / 2, 2) for a, b, _ in subs][::max(1, len(subs) // 5)] + extra
                       + ([round(end["from"] + 2, 2)] if end else [round(dur - 0.5, 2)])))
    shutil.rmtree(job / "stills", ignore_errors=True); (job / "stills").mkdir()
    env = dict(os.environ, W=str(W), H=str(H))
    sh("node", RENDER, job, "stills", ",".join(map(str, times)), env=env)
    zone = "drawbox=x=0:y=0:w=1080:h=280:color=red@0.22:t=fill,drawbox=x=0:y=1500:w=1080:h=420:color=red@0.22:t=fill,drawbox=x=910:y=900:w=170:h=600:color=red@0.22:t=fill"
    imgs = [job / "stills" / f"t_{t:.2f}.jpg" for t in times]
    fc = ";".join(f"[{i}:v]{zone},scale=270:-2[s{i}]" for i in range(len(imgs))) + ";" + "".join(f"[s{i}]" for i in range(len(imgs))) + f"hstack={len(imgs)}"
    sh("ffmpeg", "-v", "error", "-y", *sum([["-i", p] for p in imgs], []), "-filter_complex", fc, job / "out/qa_sheet.jpg")
    print("safe-zone check:", job / "out/qa_sheet.jpg")
    if "--stills" in flags:
        for w in warn: print("WARNING:", w)
        report(job, tips); return

    # video
    sh("node", RENDER, job, "video", job / "out/silent.mp4", FPS, env=env)
    if "--capcut" in flags:
        sh("node", RENDER, job, "video", job / "out/silent_nosubs.mp4", FPS, env=dict(env, PAGE="index.html?nosubs=1"))

    # music shaped by the structure
    bw = [s for s in segs if s.get("look") == "bw"]; burst = [s for s in segs if s.get("look") == "burst"]
    muffle = (bw[0]["t0"], bw[-1]["t0"] + bw[-1]["dur"]) if bw else None
    open_at = burst[0]["t0"] if burst else (muffle[1] if muffle else (hook.get("out", 0) if hook else 0))
    margs = dict(dur=dur, shutters=[s["t0"] for s in segs if s.get("look") == "memory"], muffle=muffle,
                 open_at=open_at, end_at=end["from"] if end else dur - 3, chime=bool(burst))
    mus = spec.get("music", "synth")
    if mus == "synth":
        music.make(job / "out/music.wav", **margs); mwav = job / "out/music.wav"
        if "--capcut" in flags: music.make(job / "out/music_nofx.wav", fx=False, **margs)
    elif mus:
        mwav = resolve(job, mus)
    else:
        mwav = None

    if voice:
        mix(job, job / "out/silent.mp4", voice, mwav, job / "out/reel.mp4", dur, spec.get("music_gain", 0.16))
        mix(job, job / "out/silent.mp4", voice, None, job / "out/reel_nomusic.mp4", dur)
        sh("ffmpeg", "-v", "error", "-y", "-ss", spec.get("cover_t", 0.5), "-i", job / "out/reel.mp4", "-frames:v", 1, "-q:v", 2, job / "out/cover.jpg")
        for f in ("reel.mp4", "reel_nomusic.mp4"):
            i, p = loudness(job / "out" / f)
            print(f"{f}: {i:.1f} LUFS, peak {p:.1f} dB")
            if not -15 <= i <= -13 or p > -1: warn.append(f"{f}: loudness out of range (-14 LUFS ±1, peak ≤ -1 dB)")
    if not voice:                                          # no voice-over: picture (+ music if any) is the reel
        if mwav:
            sh("ffmpeg", "-v", "error", "-y", "-i", job / "out/silent.mp4", "-i", mwav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
               "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",      # music-only reels were ~-20 LUFS
               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", job / "out/reel.mp4")
            i, p = loudness(job / "out/reel.mp4"); print(f"reel.mp4: {i:.1f} LUFS, peak {p:.1f} dB")
        else:
            shutil.copy(job / "out/silent.mp4", job / "out/reel.mp4")
        sh("ffmpeg", "-v", "error", "-y", "-ss", min(spec.get("cover_t", 0.5), dur - 0.05), "-i", job / "out/reel.mp4", "-frames:v", 1, "-q:v", 2, job / "out/cover.jpg")
    if spec.get("caption"): (job / "out/caption.txt").write_text(spec["caption"].strip() + "\n")
    tips += qa_video(job / "out/reel.mp4")
    for w in warn: print("WARNING:", w)
    report(job, tips)
    print("done:", job / "out/reel.mp4")


if __name__ == "__main__":
    main()

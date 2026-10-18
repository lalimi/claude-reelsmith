"""CapCut route for a built reel: editable CapCut Web draft = picture (everything baked in) + voice + music stems
+ sound effects as separate CapCut layers she can swap by ear.

  reelsmith capcut stems <reel-dir>   -> out/capcut/{video.mp4, voice.wav, music.wav} + files.json (what to upload)
  reelsmith capcut draft <reel-dir>   -> out/capcut/draft.json from out/capcut/upload.json + reel.json "sfx"

Between the two: capcut_asset_upload_credential(version 2) for the files, then
  printf '%s' <ticket> | node $CAPCUT_PLUGIN_DIR/x/plugins/codex/skills/capcut-upload/scripts/capcut-upload.mjs \
      --files '[{"client_id":"video","file":".../video.mp4"}, ...]' --upload-ticket-stdin --json > out/capcut/upload.json
After: start_stdraft_session -> push_stdraft_snapshot(base_package_id="", stdraft_json=draft.json).

reel.json "sfx": [{"name": "whoosh", "t": 6.95, "vol": 0.5, "dur": 1.2}] - names from SFX below (CapCut library,
ids tested by nicolapocock/claude-reel-editor) or a local audio file uploaded with client_id "sfx_<stem>" (path
relative to the reel or the repo). Library sounds have been seen to play silent: listen in the editor.
CAPCUT_PLUGIN_DIR (default ~/capcut-plugin) = CapCut's own plugin bundle, downloaded by the user (see docs/capcut.md)."""
import json, os, subprocess, sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))
PLUGIN = Path(os.environ.get("CAPCUT_PLUGIN_DIR", Path.home() / "capcut-plugin")).expanduser()
sys.path.insert(0, str(PLUGIN / "x/plugins/codex/skills/capcut-stdraft-builder/scripts"))

SFX = {"whoosh": ("sid://6993230936988977154", 566), "whoosh-short": ("sid://6993230936993204226", 566),
       "pop": ("sid://6926910425934071810", 700), "typing": ("sid://6990639268376905730", 1466),
       "click": ("sid://7005595075288532994", 333), "sparkle": ("sid://6995835233664763905", 1766),
       "coin": ("sid://6926878562561558530", 566), "chime": ("sid://6990639268369385474", 766),
       "impact": ("sid://7005595087811905537", 1000), "shutter": ("sid://6988031765445085185", 1000),
       "ding": ("sid://7005594836271958018", 1000)}


def sh(*a):
    return subprocess.run([str(x) for x in a], check=True, capture_output=True, text=True)


def local_sfx(job, spec):
    out = {}
    for e in spec.get("sfx", []):
        if e["name"] in SFX: continue
        p = next((q for q in (job / e["name"], ROOT / e["name"]) if q.exists()), None)
        if not p: sys.exit(f"sound not found: {e['name']}")
        out["sfx_" + p.stem] = p
    return out


def stems(job):
    import build, music
    spec = json.load(open(job / "reel.json")); cc = job / "out/capcut"; cc.mkdir(parents=True, exist_ok=True)
    res = json.load(open(job / "out/resolved.json")); segs, dur = res["segments"], res["duration"]
    bw = [s for s in segs if s.get("look") == "bw"]; burst = [s for s in segs if s.get("look") == "burst"]
    muffle = (bw[0]["t0"], bw[-1]["t0"] + bw[-1]["dur"]) if bw else None
    hook, end = spec.get("hook"), res.get("end")
    music.make(job / "out/music_nofx.wav", dur=dur, fx=False, muffle=muffle,
               shutters=[s["t0"] for s in segs if s.get("look") == "memory"],
               open_at=burst[0]["t0"] if burst else (muffle[1] if muffle else (hook.get("out", 0) if hook else 0)),
               end_at=end["from"] if end else dur - 3, chime=bool(burst))
    voice, mwav, g = job / "out/vo_timed.wav", job / "out/music_nofx.wav", spec.get("music_gain", 0.16)
    # same chain as build.mix (highpass voice, music ducked under it), then one gain so voice+music = -14 LUFS
    fc = (f"[0:a]highpass=f=70,aformat=channel_layouts=stereo,asplit=3[v][sc][vo];[1:a]volume={g}[m];"
          "[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=380[md];[md]asplit=2[mo][mm];[v][mm]amix=inputs=2:normalize=0:duration=longest[mix]")
    j = subprocess.run(["ffmpeg", "-hide_banner", "-i", voice, "-i", mwav, "-filter_complex", fc + ";[vo]anullsink;[mo]anullsink;[mix]loudnorm=I=-14:print_format=json[x]",
                        "-map", "[x]", "-t", str(dur), "-f", "null", "-"], capture_output=True, text=True, timeout=120).stderr
    gain = -14 - float(json.loads(j[j.rindex("{"):j.rindex("}") + 1])["input_i"])
    sh("ffmpeg", "-v", "error", "-y", "-i", voice, "-i", mwav, "-filter_complex", fc + f";[vo]volume={gain:.2f}dB,alimiter=limit=0.84:level=false[vx];[mo]volume={gain:.2f}dB,alimiter=limit=0.84:level=false[mx];[mix]anullsink",
       "-map", "[vx]", "-t", dur, "-ar", 48000, cc / "voice.wav", "-map", "[mx]", "-t", dur, "-ar", 48000, cc / "music.wav")
    sh("ffmpeg", "-v", "error", "-y", "-i", job / "out/reel.mp4", "-an", "-c:v", "copy", "-movflags", "+faststart", cc / "video.mp4")
    files = [{"client_id": k, "file": str(cc / f"{k}.{e}")} for k, e in (("video", "mp4"), ("voice", "wav"), ("music", "wav"))]
    files += [{"client_id": k, "file": str(p)} for k, p in local_sfx(job, spec).items()]
    json.dump(files, open(cc / "files.json", "w"), ensure_ascii=False, indent=1)
    print(f"stems gain {gain:+.1f} dB")
    for f in files: print(f"{Path(f['file']).name}\t{Path(f['file']).stat().st_size}")


def draft(job):
    from apply_materials import apply_video, apply_audio
    from _draft import load, finish
    spec = json.load(open(job / "reel.json")); cc = job / "out/capcut"
    up = {r["clientId"]: r["vid"] for r in json.load(open(cc / "upload.json"))["results"]}
    dur = int(round(json.load(open(job / "out/resolved.json"))["duration"] * 1000))
    d = {"version": "0.1.0", "segments": [{"id": "draft", "type": "DRAFT", "attributes": {"width": 1080, "height": 1920, "ratio_type": "custom"}}]}
    d = apply_video(d, source=f"vid://{up['video']}", start_ms=0, duration_ms=dur, volume=0.0, layer=0)["draft"]
    for name in ("voice", "music"):
        d = apply_audio(d, meta_type="MUSIC", source=f"vid://{up[name]}", start_ms=0, duration_ms=dur, volume=1.0)["draft"]
    loc = {f"sfx_{Path(e['name']).stem}": e["name"] for e in spec.get("sfx", []) if e["name"] not in SFX}
    n = 0
    for e in spec.get("sfx", []):
        t = int(round(e["t"] * 1000))
        if e["name"] in SFX: src, length = SFX[e["name"]]
        else:
            cid = f"sfx_{Path(e['name']).stem}"; src = f"vid://{up[cid]}"
            p = next(q for q in (job / loc[cid], ROOT / loc[cid]) if q.exists())
            length = int(float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p).stdout) * 1000)
        ln = min(length, int(e.get("dur", 99) * 1000), dur - t)
        if ln > 40:
            d = apply_audio(d, meta_type="SOUND", source=src, start_ms=t, duration_ms=ln, volume=e.get("vol", 0.4))["draft"]; n += 1
    model, _, _ = load(d)
    res = finish(model, d, [], [])
    json.dump(res["draft"], open(cc / "draft.json", "w"), ensure_ascii=False)
    print("sfx:", n, "| check:", json.dumps(res["check_result"], ensure_ascii=False)[:300])


if __name__ == "__main__":
    job = Path(sys.argv[1]).expanduser().resolve()
    {"stems": stems, "draft": draft}[sys.argv[2]](job)

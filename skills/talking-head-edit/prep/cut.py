"""Apply the approved (and tightened) rough cut in one pass: keep spans from edl.json in play order, cleaned voice
from voice.wav, optional speed-up, rotate/tone-map/scale to the reel size. Video and audio of each span are
concatenated together, so lip sync never drifts across joins; edges get 12 ms audio fades so cuts never click.
Usage: "$(reelsmith py)" -I prep/cut.py <job-dir> [WxH]          default 1080x1920
Writes aroll.mp4 (picture + clean voice: the "audio" for edit.json), aroll.webm (picture only, for the engine)
and joins.json (join times in the new timeline: put a layout change or a punch-in on each to hide the jump).
Based on cut.py from github.com/nicolapocock/claude-reel-editor (MIT)."""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import pacing, probe

job = Path(sys.argv[1]).expanduser().resolve()
W, H = map(int, (sys.argv[2] if len(sys.argv) > 2 else "1080x1920").split("x"))
edl = json.load(open(job / "edl.json"))
src, voice = job / edl["source"], job / edl.get("audio", "voice.wav")
speed = pacing(edl)["speed"]
FADE = 0.012

v = probe(src, "stream=r_frame_rate,color_transfer")["streams"][0]
num, den = map(int, v["r_frame_rate"].split("/")); fps = num / den
q = lambda t: round(round(t * fps) / fps, 4)      # span edges on the source frame grid
spans = [(q(s), q(e)) for s, e in edl["keep"] if q(e) > q(s)]

# iPhone HDR (HLG / Dolby Vision) looks washed out unless tone-mapped to SDR
hdr = v.get("color_transfer") in ("arib-std-b67", "smpte2084")
tone = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv," if hdr else ""
fit = f"{tone}scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1"

parts = []
for k, (s, e) in enumerate(spans):
    parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS,{fit}[v{k}]")
    parts.append(f"[1:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS,afade=t=in:d={FADE},"
                 f"afade=t=out:st={max(e - s - FADE, 0):.4f}:d={FADE}[a{k}]")
n = len(spans)
post_v = f"setpts=PTS/{speed},fps=30,format=yuv420p" if speed != 1 else "fps=30,format=yuv420p"
post_a = f"atempo={speed}" if speed != 1 else "anull"
parts.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[cv][ca]")
parts.append(f"[cv]{post_v}[vout]")
parts.append(f"[ca]{post_a}[aout]")
(job / "cut_filter.txt").write_text(";\n".join(parts))

kept = sum(e - s for s, e in spans)
print(f"{n} шматків, {kept:.1f} с -> {kept / speed:.1f} с при {speed}x, {W}x{H}{' · HDR -> SDR' if hdr else ''}")
subprocess.run(["nice", "-n", "10", "ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", str(voice),
                "-filter_complex_script", str(job / "cut_filter.txt"), "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                "-movflags", "+faststart", str(job / "aroll.mp4")], check=True)
# the engine's Chromium has no H.264: picture-only VP9 copy for it (same command as SKILL.md step 1)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(job / "aroll.mp4"), "-c:v", "libvpx-vp9", "-b:v", "6M", "-g", "15",
                "-deadline", "realtime", "-cpu-used", "8", "-an", str(job / "aroll.webm")], check=True)

joins, t = [], 0.0
for s, e in spans[:-1]:
    t += (e - s) / speed; joins.append(round(t, 2))
json.dump(joins, open(job / "joins.json", "w"))
print(f"склейки (с): {', '.join(map(str, joins)) or 'немає'}")
print(f"готово: {job / 'aroll.mp4'} + aroll.webm")

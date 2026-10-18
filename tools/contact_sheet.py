"""Contact sheets for picking moments: 10 evenly spaced frames per clip in one strip.

  reelsmith sheet src/*.MOV [-o sheets/]

Writes <out>/<clip-name>.jpg and prints the timestamp of every frame (left to right),
so you can read a strip and say "ss 12.4" in reel.json."""
import subprocess, sys, tempfile
from pathlib import Path

N = 10


def duration(clip):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def main():
    args, out = sys.argv[1:], Path("sheets")
    if "-o" in args:
        i = args.index("-o"); out = Path(args[i + 1]); del args[i:i + 2]
    if not args: sys.exit(__doc__)
    out.mkdir(parents=True, exist_ok=True)
    for clip in map(Path, args):
        d = duration(clip); ts = [round(d * (k + 0.5) / N, 2) for k in range(N)]
        with tempfile.TemporaryDirectory() as tmp:
            for k, t in enumerate(ts):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(clip), "-frames:v", "1",
                                "-vf", "scale=180:-2", f"{tmp}/{k:02d}.jpg"], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{tmp}/%02d.jpg", "-vf", f"tile={N}x1",
                            str(out / f"{clip.stem}.jpg")], check=True)
        print(f"{clip.name}  {d:.1f}s  frames at: {', '.join(map(str, ts))}")


if __name__ == "__main__":
    main()

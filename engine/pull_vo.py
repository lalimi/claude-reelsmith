"""Pull the newest ElevenLabs web-UI generations (v4 gives 2 takes per click) into <reel>/vo/.

  reelsmith voice <reel-dir> [n=2]

Saves <id>.mp3 + <id>.json (date, chars billed, model) for the n newest TTS history items and prints
their durations; the `_exp` take costs 0 chars. Pick one and copy it to vo/vo.mp3.
Key: ELEVENLABS_API_KEY from the environment, or from ~/.config/reelsmith/.env (KEY=value lines).
The key needs the speech_history_read permission."""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import os
ENV = Path.home() / ".config/reelsmith/.env"


def key():
    if os.environ.get("ELEVENLABS_API_KEY"): return os.environ["ELEVENLABS_API_KEY"]
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if line.startswith("ELEVENLABS_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit(f"ELEVENLABS_API_KEY is not set: export it or put it in {ENV}")


def get(url, k):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"xi-api-key": k})).read()


def main():
    reel, n = Path(sys.argv[1]).expanduser(), int(sys.argv[2]) if len(sys.argv) > 2 else 2
    out = reel / "vo"; out.mkdir(parents=True, exist_ok=True)
    k = key()
    hist = json.loads(get("https://api.elevenlabs.io/v1/history?page_size=20", k))["history"]
    items = sorted((h for h in hist if h.get("source") == "TTS"), key=lambda h: -h["date_unix"])[:n]
    for h in items:
        hid = h["history_item_id"]
        mp3 = out / f"{hid}.mp3"
        mp3.write_bytes(get(f"https://api.elevenlabs.io/v1/history/{hid}/audio", k))
        meta = {"id": hid, "date_unix": h["date_unix"], "model": h.get("model_id"),
                "chars": h["character_count_change_to"] - h["character_count_change_from"]}
        (out / f"{hid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                             capture_output=True, text=True).stdout.strip()
        print(f"{hid}  {float(dur):6.2f}s  chars {meta['chars']:4d}  {meta['model']}")


if __name__ == "__main__":
    main()

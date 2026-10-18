# Voice-over

Two options:

**Your own voice** (best for trust): record the approved script on your phone, drop it as `vo/vo.mp3`. For talking-to-camera videos use the `talking-head-edit` skill instead — it cleans the audio and cuts fillers.

**ElevenLabs TTS**
- Pick a voice in your language from the ElevenLabs library (multilingual v2/v3/v4 models handle Ukrainian, Polish, Spanish …). Write numbers as words and brand names phonetically in the TTS text; keep digits and real spelling in `script` for subtitles.
- Free plan: library voices work in the web UI but not via API — generate in the web Text-to-Speech page (Claude in Chrome can type the text and press Generate in your logged-in browser), then pull the takes:
  ```bash
  export ELEVENLABS_API_KEY=…            # or put ELEVENLABS_API_KEY=… in ~/.config/reelsmith/.env
  reelsmith voice reels/my-reel 2        # saves the 2 newest takes to vo/ and prints durations
  ```
  The key needs the *speech history read* permission. Newer models return two takes per click; an experimental one may cost 0 credits. Transcribe both (`reelsmith build … --stills` does it for `vo/vo.mp3`) and keep the cleaner one.
- ~150 words ≈ 60 s for a calm voice. `"speed": 1.07` in `vo` tightens without chipmunk sound.
- **Rights**: the ElevenLabs free plan does not grant commercial use and requires attribution. For reels that sell something, use a paid plan or your own voice.

"""Warm lo-fi bed (84 BPM, Fmaj7-Em7-Dm7-Cmaj7) shaped by the reel's structure.
keys + crackle from the start · shutter click on every montage cut · muffled over a "bw" (past) stretch ·
filter opens with a chime, drums + bass come in at `open_at` · drums drop out at `end_at`, last chord rings.
Used by build.py; `make(...)` writes a stereo 48 kHz WAV."""
import wave
import numpy as np

SR = 48000
CHORDS = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]   # Fmaj7 Em7 Dm7 Cmaj7
ROOTS = [41, 40, 38, 36]


def make(out, dur, shutters=(), muffle=None, open_at=0.0, end_at=None, chime=True, fx=True, bpm=84.0, seed=11):
    N = int(SR * dur); t_all = np.arange(N) / SR
    rng = np.random.default_rng(seed)
    beat = 60 / bpm; bar = 4 * beat
    end_at = dur - 3 if end_at is None else end_at
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)

    def put(dst, sig, t0, gain=1.0):
        i = int(t0 * SR)
        if i >= len(dst) or i < 0: return
        s = sig[: len(dst) - i] * gain; dst[i:i + len(s)] += s

    def rhodes(f, length):
        t = np.arange(int(length * SR)) / SR
        mod = np.sin(2 * np.pi * f * t) * 1.2 * np.exp(-t * 3.5)
        s = np.sin(2 * np.pi * f * t + mod) * 0.8 + np.sin(2 * np.pi * 2 * f * t) * 0.12 * np.exp(-t * 2)
        env = np.minimum(1, t / 0.008) * np.exp(-t * 0.9) * np.minimum(1, (length - t) / 0.35)
        return s * env * (1 + 0.12 * np.sin(2 * np.pi * 4.6 * t))

    def kick():
        t = np.arange(int(0.35 * SR)) / SR
        return np.sin(2 * np.pi * np.cumsum(45 + 75 * np.exp(-t * 28)) / SR) * np.exp(-t * 9)

    def noise_hit(length, decay, hp):
        n = rng.standard_normal(int(length * SR)); n = n - np.convolve(n, np.ones(hp) / hp, mode="same")
        return n * np.exp(-np.arange(len(n)) / SR * decay)

    def lowpass(x, cutoff, width=300):
        X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR)
        return np.fft.irfft(X / (1 + np.exp((fr - cutoff) / width * 4)), len(x))

    keys, bass, drums, sfx = (np.zeros(N) for _ in range(4))
    for b in range(int(np.ceil(dur / bar))):
        t0 = b * bar; ch = CHORDS[b % 4]; last = t0 + bar >= end_at
        for k, m in enumerate(ch):
            put(keys, rhodes(midi(m + 12), dur - t0 if last else bar + 0.4), t0 + k * 0.018, 0.16)
        if not last:
            for k, m in enumerate(ch[1:]):
                put(keys, rhodes(midi(m + 12), beat * 1.2), t0 + 2.5 * beat + k * 0.012, 0.07)
        for tt, m, l in ((0, ROOTS[b % 4], 1.6 * beat), (2.5 * beat, ROOTS[b % 4] + 7, 1.2 * beat)):
            t = np.arange(int(l * SR)) / SR
            put(bass, np.sin(2 * np.pi * midi(m) * t) * np.minimum(1, t / 0.01) * np.exp(-t * 1.6) * np.minimum(1, (l - t) / 0.05), t0 + tt, 0.5)
        for q in range(8):
            tt = t0 + q * beat / 2 + (0.06 if q % 2 else 0)
            if q in (0, 5): put(drums, kick(), tt, 0.75)
            if q in (2, 6): put(drums, noise_hit(0.18, 22, 6), tt, 0.10)
            put(drums, noise_hit(0.05, 90, 2), tt, 0.035 if q % 2 else 0.05)

    cr = np.zeros(N); idx = rng.choice(N, max(1, int(9 * dur)), replace=False); cr[idx] = rng.uniform(-0.25, 0.25, len(idx))
    cr = np.convolve(cr, np.exp(-np.arange(60) / 8), mode="same") + rng.standard_normal(N) * 0.004
    for tt in shutters:
        put(sfx, noise_hit(0.012, 400, 2), tt, 0.17); put(sfx, noise_hit(0.05, 120, 3), tt + 0.03, 0.06)
    if chime and open_at > 0.5:
        for k, m in enumerate([77, 81, 84, 88, 91]):
            t = np.arange(int(1.6 * SR)) / SR
            put(sfx, np.sin(2 * np.pi * midi(m) * t) * np.exp(-t * 3) * np.minimum(1, t / 0.004), open_at + 0.05 + k * 0.07, 0.06)

    ramp = lambda a, b, up=0.3: np.clip((t_all - a) / up, 0, 1) * np.clip((b - t_all) / up + 1, 0, 1)
    music = keys + bass * ramp(open_at, end_at + 1.4) + drums * ramp(open_at + 0.05, end_at, 0.25)
    if muffle:
        mid, half = sum(muffle) / 2, (muffle[1] - muffle[0]) / 2 + 0.25
        m = np.clip(1 - np.abs(t_all - mid) / half, 0, 1) ** 0.5
        music = music * (1 - m) + lowpass(music, 550) * m * 1.1
    music += (sfx if fx else 0) + cr * 0.5
    music *= np.minimum(1, t_all / 0.4) * np.minimum(1, (dur - t_all) / 1.6)
    L = music + np.roll(keys, int(0.011 * SR)) * 0.10; R = music - np.roll(keys, int(0.011 * SR)) * 0.10
    st = np.stack([L, R], 1); st /= np.abs(st).max() / 0.7
    with wave.open(str(out), "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

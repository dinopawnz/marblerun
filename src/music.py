"""THE GRAND MARBLE RUN - race music, composed and synthesised here (original, free to use).
An upbeat 150 BPM electronic race theme in A minor that loops seamlessly (96 s).
Writes out/race_theme.wav (then: ffmpeg -> race_theme.mp3)."""
import numpy as np

SR = 44100
BPM = 150
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(3)


def note_hz(n):          # MIDI note -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n, a=0.005, d=0.1, s=0.0, r=0.05, length=None):
    """attack / decay-to-sustain / release envelope over n samples"""
    t = np.arange(n) / SR
    e = np.ones(n) * s
    na, nd = int(a * SR), int(d * SR)
    e[:na] = np.linspace(0, 1, max(1, na))[:len(e[:na])]
    seg = e[na:na + nd]
    e[na:na + nd] = 1 - (1 - s) * (1 - np.exp(-5 * np.arange(len(seg)) / max(1, nd)))
    nr = int(r * SR)
    if nr and n > nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, cut):
    """one-pole low pass (cut in Hz; may be an array)"""
    a = np.exp(-2 * np.pi * np.asarray(cut, dtype=float) / SR) * np.ones(len(x))
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((t * f + phase) % 1.0) - 1


def square(f, n, duty=0.5):
    t = np.arange(n) / SR
    return np.where((t * f) % 1.0 < duty, 1.0, -1.0)


def tri(f, n):
    return 2 * np.abs(saw(f, n)) - 1


# ---------------------------------------------------------------- the song
# sections of bars; each bar has one chord (root MIDI note, minor/major)
Am, F, C, G, Em, Dm, E = (57, "m"), (53, "M"), (48, "M"), (55, "M"), (52, "m"), (50, "m"), (52, "M")
A = [Am, F, C, G] * 4
B = [F, G, Em, Am, F, G, E, E] * 2
BRK = [F, G, Am, Am, F, G, E, E]
FILL = [F, G, E, E]
SONG = [("A", A), ("B", B), ("brk", BRK), ("A2", A), ("fill", FILL)]
bars = [(name, ch) for name, sec in SONG for ch in sec]
NB = len(bars)
N = int(NB * BAR * SR)
mix = {k: np.zeros(N) for k in ("kick", "snare", "hat", "bass", "lead", "arp", "pad")}


def chord_notes(ch):
    r, q = ch
    return [r, r + (3 if q == "m" else 4), r + 7]


def put(track, start_s, sig):
    i = int(start_s * SR)
    j = min(N, i + len(sig))
    if i < N:
        mix[track][i:j] += sig[:j - i]


# drum one-shots
def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 1.0


def snare():
    n = int(0.22 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - lowpass(noise, 1800)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return (noise * 0.55 * np.exp(-t * 16) + tone * 0.5)


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - lowpass(noise, 7000)
    return noise * np.exp(-t * (14 if open_ else 70)) * 0.35


K, S, H, HO = kick(), snare(), hat(), hat(True)

# lead melody (scale degrees as MIDI offsets from A4=69), one phrase per 4 bars, 8ths; None = rest
PHRASE_A = [[0, None, 0, 3, 5, None, 7, 5], [3, None, 3, 5, 7, None, 8, 7], [7, None, 5, 3, 5, None, 3, 0], [-2, None, 0, 2, 3, 2, 0, -2]]
PHRASE_B = [[8, 7, 8, 10, 12, None, 10, 8], [10, 8, 7, 5, 7, None, 5, 3], [3, 5, 7, 8, 7, 5, 3, 2], [0, None, 2, None, 3, None, 5, 7]]

for b, (sec, ch) in enumerate(bars):
    t0 = b * BAR
    notes = chord_notes(ch)
    root = ch[0]
    full = sec in ("A", "B", "A2")
    # ---- drums
    if sec != "brk":
        for q in range(4):
            put("kick", t0 + q * BEAT, K)
        for q in (1, 3):
            put("snare", t0 + q * BEAT, S)
        for q in range(8):
            put("hat", t0 + q * BEAT / 2, HO if q % 2 else H * 0.8)
        if sec == "fill" or b % 8 == 7:          # a snare roll into the next part
            for q in range(8):
                put("snare", t0 + 2 * BEAT + q * BEAT / 4, S * (0.35 + 0.08 * q))
    else:
        if b - 32 >= 4:                          # the riser back in: kicks on every beat
            for q in range(4):
                put("kick", t0 + q * BEAT, K * 0.8)
        for q in range(16):
            put("hat", t0 + q * BEAT / 4, H * (0.2 + 0.6 * ((b - 32) * 16 + q) / 128))
    # ---- bass: pumping 8ths, root / octave
    if sec != "brk" or b - 32 >= 4:
        for q in range(8):
            f = note_hz(root - 24 + (12 if q % 2 else 0))
            n = int(BEAT / 2 * SR)
            sig = saw(f, n) * 0.6 + square(f * 0.5, n) * 0.25
            sig = lowpass(sig, 900 + 600 * (q % 2)) * env(n, 0.004, 0.12, 0.5, 0.03)
            put("bass", t0 + q * BEAT / 2, sig * 0.55)
    # ---- arp: 16ths over the chord, two octaves up
    seq = notes + [notes[0] + 12, notes[2], notes[1], notes[0] + 12, notes[1] + 12]
    for q in range(16):
        f = note_hz(seq[q % len(seq)] + 12)
        n = int(BEAT / 4 * SR)
        sig = square(f, n, 0.25) * env(n, 0.002, 0.08, 0.0, 0.01)
        put("arp", t0 + q * BEAT / 4, sig * (0.12 if full else 0.16))
    # ---- pad: the whole bar, detuned saws, soft
    n = int(BAR * SR)
    pad = sum(saw(note_hz(x), n, 0.1 * k) + saw(note_hz(x) * 1.006, n, 0.3) for k, x in enumerate(notes))
    pad = lowpass(pad, 1400 if sec == "brk" else 900) * env(n, 0.25, 0.4, 0.8, 0.2)
    put("pad", t0, pad * 0.06)
    # ---- lead
    if full:
        phrase = (PHRASE_B if sec == "B" else PHRASE_A)[b % 4]
        for q, deg in enumerate(phrase):
            if deg is None:
                continue
            f = note_hz(69 + deg)
            n = int(BEAT / 2 * SR * 0.95)
            t = np.arange(n) / SR
            vib = 1 + 0.004 * np.sin(2 * np.pi * 6 * t) * np.clip(t * 6, 0, 1)
            ph = np.cumsum(f * vib) / SR
            sig = (2 * (ph % 1) - 1) * 0.5 + np.where(ph % 1 < 0.5, 1, -1) * 0.3
            sig = lowpass(sig, 3200) * env(n, 0.005, 0.15, 0.6, 0.04)
            put("lead", t0 + q * BEAT / 2, sig * 0.22)

# sidechain: the kick ducks the pad and the bass
duck = np.ones(N)
for b in range(NB):
    for q in range(4):
        i = int((b * BAR + q * BEAT) * SR)
        n = int(BEAT * SR)
        t = np.arange(min(n, N - i)) / SR
        duck[i:i + len(t)] = np.minimum(duck[i:i + len(t)], 1 - 0.55 * np.exp(-t * 9))
mix["pad"] *= duck; mix["bass"] *= 0.6 + 0.4 * duck

# a simple echo on the lead and arp
def echo(x, delay, fb, wet):
    d = int(delay * SR); y = x.copy()
    for k in range(1, 4):
        y[d * k:] += x[:-d * k] * (fb ** k) * wet
    return y
mix["lead"] = echo(mix["lead"], BEAT * 0.75, 0.45, 0.6)
mix["arp"] = echo(mix["arp"], BEAT * 0.5, 0.35, 0.4)

out = (mix["kick"] * 0.9 + mix["snare"] * 0.55 + mix["hat"] * 0.5 + mix["bass"] + mix["lead"] + mix["arp"] + mix["pad"])
# the echo tails that run past the end wrap round to the start, so the loop is seamless
out = np.tanh(out * 1.3) / np.tanh(1.3)
out = out / np.max(np.abs(out)) * 0.89
import wave
w = wave.open("/home/claude/mr/out/race_theme.wav", "wb")
w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((out * 32767).astype(np.int16).tobytes())
w.close()
print("bars", NB, "seconds", round(N / SR, 2))

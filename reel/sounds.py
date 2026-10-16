"""Sound made in code, so there is nothing to license: short effects for the animation and a soft music bed.

Effects are written once to remotion/public/sfx/ (`python -m reel sounds`) and committed. The music bed is
made per Reel from its length and mood: a gentle four-chord loop (pads, bass, soft kick and hats, a few
pentatonic plucks), seeded by the title so each Reel sounds a little different.
"""
import wave
import zlib
from pathlib import Path

import numpy as np

RATE = 44100


def tone(freq, seconds, shape='sine'):
    t = np.arange(int(RATE * seconds)) / RATE
    freq = np.broadcast_to(freq, t.shape) if np.ndim(freq) else np.full(t.shape, float(freq))
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    if shape == 'triangle':
        return 2 / np.pi * np.arcsin(np.sin(phase))
    if shape == 'saw':
        return 2 * ((phase / (2 * np.pi)) % 1) - 1
    return np.sin(phase)


def envelope(n, attack=0.005, decay=None, release=0.05):
    """Attack then exponential decay (or hold) then a short release, as a gain curve of n samples."""
    t = np.arange(n) / RATE
    env = np.minimum(1, t / max(attack, 1e-4))
    if decay:
        env *= np.exp(-t / decay)
    tail = int(RATE * release)
    if tail and n > tail:
        env[-tail:] *= np.linspace(1, 0, tail)
    return env


def lowpass(x, cutoff):
    """One-pole low-pass filter (cutoff in Hz, may be a curve)."""
    cutoff = np.broadcast_to(cutoff, x.shape) if np.ndim(cutoff) else np.full(x.shape, float(cutoff))
    a = 1 - np.exp(-2 * np.pi * cutoff / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def noise(seconds, seed):
    return np.random.default_rng(seed).uniform(-1, 1, int(RATE * seconds))


def sweep(a, b, seconds):
    return np.geomspace(a, b, int(RATE * seconds))


def effects():
    """name -> mono float signal in -1..1"""
    out = {}
    n = noise(0.45, 1)
    out['whoosh'] = lowpass(n, np.concatenate([sweep(300, 4000, 0.2), sweep(4000, 500, 0.25)])) * envelope(len(n), 0.12, release=0.2) * 2.2
    n = noise(0.22, 2)
    out['whip'] = lowpass(n, sweep(6000, 800, 0.22)) * envelope(len(n), 0.01, 0.08) * 2.4
    out['pop'] = tone(sweep(900, 300, 0.12), 0.12) * envelope(int(RATE * 0.12), 0.002, 0.04)
    thud = tone(sweep(110, 40, 0.45), 0.45) * envelope(int(RATE * 0.45), 0.002, 0.12)
    click = lowpass(noise(0.45, 3), 1500) * envelope(int(RATE * 0.45), 0.001, 0.015)
    out['thud'] = thud + click * 0.8
    bell = sum(tone(f, 1.2) * g for f, g in ((1318.5, 1), (2637, 0.35), (3955.5, 0.15), (1975.5, 0.2)))
    out['ding'] = bell * envelope(len(bell), 0.002, 0.35) * 0.6
    notes = [523.25, 659.25, 783.99, 1046.5]
    tada = np.concatenate([tone(f, 0.11, 'triangle') * envelope(int(RATE * 0.11), 0.004, 0.08) for f in notes[:3]] +
                          [sum(tone(f, 0.7, 'triangle') for f in notes[1:]) / 2 * envelope(int(RATE * 0.7), 0.004, 0.3)])
    out['tada'] = tada * 0.7
    beat = tone(sweep(70, 45, 0.16), 0.16) * envelope(int(RATE * 0.16), 0.003, 0.05)
    gap = np.zeros(int(RATE * 0.12))
    out['heartbeat'] = np.concatenate([beat, gap, beat * 0.7, np.zeros(int(RATE * 0.2))]) * 1.4
    wah = np.concatenate([lowpass(tone(f, 0.42, 'saw'), 900) * envelope(int(RATE * 0.42), 0.03, release=0.1) for f in (233.1, 220.0)] +
                         [lowpass(tone(sweep(207.7, 185, 0.8), 0.8, 'saw'), 700) * envelope(int(RATE * 0.8), 0.03, 0.5)])
    out['sad'] = wah * 0.7
    tick = lowpass(noise(0.03, 4), 5000) * envelope(int(RATE * 0.03), 0.0005, 0.006)
    out['tick'] = np.concatenate([np.concatenate([tick, np.zeros(int(RATE * 0.47))]) * (1 if i % 2 else 0.7) for i in range(4)])
    beep = tone(1760, 0.09, 'triangle') * envelope(int(RATE * 0.09), 0.002, release=0.01)
    out['alarm'] = np.concatenate([np.concatenate([beep, np.zeros(int(RATE * 0.05))]) for _ in range(6)]) * 0.6
    n = noise(1.0, 5)
    out['riser'] = lowpass(n, sweep(200, 6000, 1.0)) * np.linspace(0, 1, len(n)) ** 2 * 1.6
    zap = tone(sweep(1400, 200, 0.25), 0.25, 'saw')
    out['angry'] = lowpass(zap, 2500) * envelope(len(zap), 0.002, 0.12) * 0.6
    out['swoosh_up'] = out['whoosh'][::-1].copy()
    return out


def write(path, signal, gain=1.0):
    pcm = np.clip(signal * gain, -1, 1)
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes((pcm * 32767).astype('<i2').tobytes())


def write_effects(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name, signal in effects().items():
        peak = max(np.max(np.abs(signal)), 1e-6)
        write(folder / f'{name}.wav', signal / peak * 0.8)
    return sorted(p.name for p in folder.glob('*.wav'))


SCALES = {'warm': (0, 2, 4, 7, 9), 'tense': (0, 3, 5, 7, 10)}
# vi-IV-I-V (emotional, lifts at the end) or i-VI-III-VII (tense); semitones from the key's root
PROGRESSIONS = {'warm': ((9, 'm'), (5, ''), (0, ''), (7, '')), 'tense': ((0, 'm'), (8, ''), (3, ''), (10, ''))}


def chord(root, quality):
    return [root, root + (3 if quality == 'm' else 4), root + 7]


def music(seconds, mood='warm', seed='reel', bpm=84):
    """A soft loop of `seconds`, about -20 dB under the voice once mixed."""
    rng = np.random.default_rng(zlib.crc32(seed.encode()))
    key = 48 + int(rng.integers(0, 5))  # C3..E3
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)  # noqa: E731
    beat = 60 / bpm
    bar = beat * 4
    n = int(RATE * (seconds + 0.5))
    mix = np.zeros(n)
    prog = PROGRESSIONS[mood]
    scale = SCALES[mood]

    def add(signal, at):
        start = int(at * RATE)
        end = min(n, start + len(signal))
        if start < n:
            mix[start:end] += signal[:end - start]

    bars = int(np.ceil(seconds / bar)) + 1
    pad_env = None
    for b in range(bars):
        root, quality = prog[b % 4]
        notes = chord(key + root, quality)
        pad = sum(tone(hz(m + 12), bar, 'triangle') for m in notes) / 3
        pad_env = pad_env if pad_env is not None and len(pad_env) == len(pad) else envelope(len(pad), 0.4, release=0.4)
        add(lowpass(pad, 1400) * pad_env * 0.28, b * bar)
        bass = tone(hz(key + root - 12), bar * 0.9) * envelope(int(RATE * bar * 0.9), 0.01, 1.2)
        add(bass * 0.32, b * bar)
        for k in range(4):
            t0 = b * bar + k * beat
            if k in (0, 2):
                kick = tone(sweep(120, 45, 0.25), 0.25) * envelope(int(RATE * 0.25), 0.002, 0.07)
                add(kick * 0.45, t0)
            hat = lowpass(noise(0.05, b * 4 + k), 9000) - lowpass(noise(0.05, b * 4 + k), 3000)
            add(hat * envelope(len(hat), 0.001, 0.015) * 0.1, t0 + beat / 2)
            if rng.random() < 0.45:
                m = key + 24 + scale[int(rng.integers(0, len(scale)))]
                pluck = tone(hz(m), 0.6, 'triangle') * envelope(int(RATE * 0.6), 0.003, 0.18)
                add(lowpass(pluck, 3000) * 0.16, t0 + (beat / 2 if rng.random() < 0.4 else 0))
    fade_in, fade_out = int(RATE * 0.6), int(RATE * 1.8)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)
    peak = max(np.max(np.abs(mix)), 1e-6)
    return mix / peak * 0.7


def write_music(path, seconds, mood='warm', seed='reel'):
    write(path, music(seconds, mood, seed))
    return path


if __name__ == '__main__':
    print(write_effects(Path(__file__).resolve().parents[1] / 'remotion' / 'public' / 'sfx'))

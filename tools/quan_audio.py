"""Synthesize and verify the Quán (evening) audio pack for Chợ Nổi.

Generate: python tools/quan_audio.py generate
Check:    python tools/quan_audio.py check
"""

import argparse
import hashlib
import json
import math
import wave
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "chonoi/web/assets/audio/quan"
MANIFEST = AUDIO_DIR / "manifest.json"
SR = 32000


def midi_to_hz(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


NOTE_OFFSETS = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}


def note_hz(name: str) -> float:
    octave = int(name[-1])
    pitch = name[:-1]
    return midi_to_hz((octave + 1) * 12 + NOTE_OFFSETS[pitch])


def smooth_env(n: int, attack_s: float, release_s: float, sr: int = SR) -> np.ndarray:
    env = np.ones(n, dtype=np.float64)
    a = min(n, max(1, int(attack_s * sr)))
    r = min(n, max(1, int(release_s * sr)))
    env[:a] = 0.5 * (1.0 - np.cos(np.pi * np.arange(a) / a))
    if r > 0:
        rel = 0.5 * (1.0 + np.cos(np.pi * np.arange(r) / r))
        env[-r:] *= rel
    return env


def pink_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.standard_normal(n)
    b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786])
    a = np.array([1.0, -2.494956002, 2.017265875, -0.522189400])
    out = signal.lfilter(b, a, white)
    peak = np.max(np.abs(out)) or 1.0
    return out / peak


def bandpass(x: np.ndarray, lo: float, hi: float, order: int = 3, sr: int = SR) -> np.ndarray:
    nyq = sr * 0.5
    sos = signal.butter(order, [max(20.0, lo) / nyq, min(nyq * 0.96, hi) / nyq], btype="bandpass", output="sos")
    return signal.sosfilt(sos, x)


def lowpass(x: np.ndarray, cutoff: float, order: int = 2, sr: int = SR) -> np.ndarray:
    nyq = sr * 0.5
    sos = signal.butter(order, min(nyq * 0.96, cutoff) / nyq, btype="lowpass", output="sos")
    return signal.sosfilt(sos, x)


def highpass(x: np.ndarray, cutoff: float, order: int = 2, sr: int = SR) -> np.ndarray:
    nyq = sr * 0.5
    sos = signal.butter(order, max(20.0, cutoff) / nyq, btype="highpass", output="sos")
    return signal.sosfilt(sos, x)


def synth_dan_tranh(
    freq: float,
    dur: float,
    vel: float = 0.85,
    bend_cents: float = 0.0,
    bend_s: float = 0.055,
    vib_hz: float = 5.2,
    vib_cents: float = 7.0,
    rng: np.random.Generator | None = None,
    sr: int = SR,
) -> np.ndarray:
    """Warm Vietnamese plucked zither/lute with gentle pitch inflection and wooden body."""
    if rng is None:
        rng = np.random.default_rng(0)
    n = max(1, int(round(dur * sr)))
    t = np.arange(n, dtype=np.float64) / sr

    # Pitch contour: optional Vietnamese 'nhan' scoop + delayed subtle vibrato
    cents = np.zeros(n, dtype=np.float64)
    if bend_cents != 0.0:
        bn = min(n, max(1, int(bend_s * sr)))
        cents[:bn] += bend_cents * np.exp(-5.0 * np.arange(bn) / bn)
    vib_ramp = np.clip((t - 0.12) / 0.16, 0.0, 1.0)
    cents += vib_cents * vib_ramp * np.sin(2.0 * np.pi * vib_hz * t)
    inst_freq = freq * (2.0 ** (cents / 1200.0))
    phase = 2.0 * np.pi * np.cumsum(inst_freq) / sr

    # Modal plucked string partials (warm wooden body roll-off)
    y = np.zeros(n, dtype=np.float64)
    partials = [
        (1.0, 1.00, 1.35),
        (2.001, 0.44 * (0.7 + 0.3 * vel), 2.1),
        (3.004, 0.20 * vel, 3.2),
        (4.009, 0.09 * vel, 4.8),
        (5.016, 0.04 * vel, 6.8),
    ]
    for ratio, amp, damp in partials:
        if freq * ratio >= sr * 0.44:
            continue
        decay = np.exp(-t * damp * (1.0 + freq / 900.0))
        y += amp * decay * np.sin(phase * ratio)

    # Tactile fingernail / silk-string transient pluck
    pn = min(n, int(0.014 * sr))
    pluck = bandpass(rng.standard_normal(pn), max(400.0, freq * 1.3), min(5200.0, freq * 6.0), order=2, sr=sr)
    pluck *= np.exp(-np.arange(pn) / (0.0035 * sr)) * 0.22 * vel
    y[:pn] += pluck

    # Warm wooden soundboard resonance + gentle de-click
    y = lowpass(y, min(6500.0, 1600.0 + freq * 4.0), order=2, sr=sr)
    y *= smooth_env(n, 0.004, min(0.08, dur * 0.28), sr=sr) * vel * 0.55
    return y


def synth_sao_truc(
    freq: float,
    dur: float,
    vel: float = 0.72,
    glide_from: float | None = None,
    rng: np.random.Generator | None = None,
    sr: int = SR,
) -> np.ndarray:
    """Warm bamboo flute with airy onset, legato portamento, and delayed vibrato."""
    if rng is None:
        rng = np.random.default_rng(1)
    n = max(1, int(round(dur * sr)))
    t = np.arange(n, dtype=np.float64) / sr

    f_curve = np.full(n, freq, dtype=np.float64)
    if glide_from is not None and glide_from > 0:
        gn = min(n, int(0.055 * sr))
        ratio = np.linspace(0.0, 1.0, gn)
        f_curve[:gn] = glide_from + (freq - glide_from) * (0.5 - 0.5 * np.cos(np.pi * ratio))

    vib = 1.0 + 0.0055 * np.clip((t - 0.14) / 0.18, 0.0, 1.0) * np.sin(2.0 * np.pi * 5.4 * t)
    phase = 2.0 * np.pi * np.cumsum(f_curve * vib) / sr

    y = 0.80 * np.sin(phase) + 0.18 * np.sin(2.0 * phase) + 0.06 * np.sin(3.0 * phase)
    breath = bandpass(rng.standard_normal(n), max(300.0, freq * 0.8), min(4500.0, freq * 3.2), order=2, sr=sr)
    breath_env = 0.09 * np.exp(-t / 0.09) + 0.025
    y += breath * breath_env

    y *= smooth_env(n, 0.045, min(0.11, dur * 0.3), sr=sr) * vel * 0.42
    return y


def synth_marimba(freq: float, dur: float, vel: float = 0.65, sr: int = SR) -> np.ndarray:
    """Soft wooden mallet bar chord tone (Dan T'rung / Marimba hybrid)."""
    n = max(1, int(round(dur * sr)))
    t = np.arange(n, dtype=np.float64) / sr
    y = (
        0.85 * np.exp(-t * 6.2) * np.sin(2.0 * np.pi * freq * t)
        + 0.24 * np.exp(-t * 24.0) * np.sin(2.0 * np.pi * freq * 3.98 * t)
    )
    y *= smooth_env(n, 0.003, min(0.05, dur * 0.25), sr=sr) * vel * 0.36
    return y


def synth_bass(freq: float, dur: float, vel: float = 0.85, sr: int = SR) -> np.ndarray:
    """Warm plucked upright/acoustic bass."""
    n = max(1, int(round(dur * sr)))
    t = np.arange(n, dtype=np.float64) / sr
    y = (
        0.82 * np.exp(-t * 2.5) * np.sin(2.0 * np.pi * freq * t)
        + 0.30 * np.exp(-t * 6.0) * np.sin(2.0 * np.pi * freq * 2.0 * t)
        + 0.11 * np.exp(-t * 11.0) * np.sin(2.0 * np.pi * freq * 3.0 * t)
    )
    y = lowpass(y, 820.0, order=2, sr=sr)
    y *= smooth_env(n, 0.006, min(0.07, dur * 0.3), sr=sr) * vel * 0.56
    return y


def synth_song_loan(vel: float = 0.8, pitch_mul: float = 1.0, sr: int = SR) -> np.ndarray:
    """Classic Southern Vietnamese wooden clapper (Song Loan)."""
    n = int(0.095 * sr)
    t = np.arange(n, dtype=np.float64) / sr
    y = (
        0.55 * np.exp(-t * 58.0) * np.sin(2.0 * np.pi * 960.0 * pitch_mul * t)
        + 0.42 * np.exp(-t * 72.0) * np.sin(2.0 * np.pi * 1510.0 * pitch_mul * t)
        + 0.25 * np.exp(-t * 110.0) * np.sin(2.0 * np.pi * 2340.0 * pitch_mul * t)
    )
    y *= smooth_env(n, 0.001, 0.025, sr=sr) * vel * 0.36
    return y


def synth_mo(vel: float = 0.75, pitch_hz: float = 540.0, sr: int = SR) -> np.ndarray:
    """Hollow bamboo woodblock (Mo)."""
    n = int(0.11 * sr)
    t = np.arange(n, dtype=np.float64) / sr
    y = (
        0.72 * np.exp(-t * 36.0) * np.sin(2.0 * np.pi * pitch_hz * t)
        + 0.32 * np.exp(-t * 54.0) * np.sin(2.0 * np.pi * pitch_hz * 1.49 * t)
    )
    y *= smooth_env(n, 0.0015, 0.03, sr=sr) * vel * 0.36
    return y


def synth_kick(vel: float = 0.8, sr: int = SR) -> np.ndarray:
    """Soft felt low drum thump."""
    n = int(0.14 * sr)
    t = np.arange(n, dtype=np.float64) / sr
    f = 50.0 + 82.0 * np.exp(-t / 0.022)
    phase = 2.0 * np.pi * np.cumsum(f) / sr
    y = np.sin(phase) * np.exp(-t * 22.0)
    y *= smooth_env(n, 0.002, 0.03, sr=sr) * vel * 0.48
    return y


def synth_shaker(vel: float = 0.5, rng: np.random.Generator | None = None, sr: int = SR) -> np.ndarray:
    """Soft brushed shaker tick."""
    if rng is None:
        rng = np.random.default_rng(2)
    n = int(0.055 * sr)
    t = np.arange(n, dtype=np.float64) / sr
    noise = bandpass(rng.standard_normal(n), 3200.0, 8800.0, order=2, sr=sr)
    y = noise * np.exp(-t * 72.0) * smooth_env(n, 0.004, 0.015, sr=sr) * vel * 0.16
    return y


def add_at(buf: np.ndarray, start_sample: int, clip: np.ndarray) -> None:
    if start_sample >= len(buf):
        return
    if start_sample < 0:
        clip = clip[-start_sample:]
        start_sample = 0
    end = min(len(buf), start_sample + len(clip))
    if end > start_sample:
        buf[start_sample:end] += clip[: end - start_sample]


def apply_room_reverb(dry: np.ndarray, wet: float = 0.16, sr: int = SR) -> np.ndarray:
    """Lightweight Schroeder room reverb with warm high-frequency damping."""
    comb_delays = [int(ms * sr / 1000.0) for ms in (29.7, 37.1, 41.9, 47.3)]
    comb_gains = [0.68, 0.65, 0.62, 0.60]
    acc = np.zeros_like(dry)
    for d, g in zip(comb_delays, comb_gains):
        b = np.zeros(d + 1, dtype=np.float64)
        b[d] = 1.0
        a = np.zeros(d + 1, dtype=np.float64)
        a[0] = 1.0
        a[d] = -g
        acc += signal.lfilter(b, a, dry) * 0.25
    acc = lowpass(acc, 3600.0, order=1, sr=sr)
    for d in (int(5.3 * sr / 1000.0), int(1.9 * sr / 1000.0)):
        g = 0.5
        b = np.zeros(d + 1, dtype=np.float64)
        b[0], b[d] = -g, 1.0
        a = np.zeros(d + 1, dtype=np.float64)
        a[0], a[d] = 1.0, -g
        acc = signal.lfilter(b, a, acc)
    return (1.0 - wet) * dry + wet * acc


def finalize_audio(buf: np.ndarray, target_peak: float = 0.85, drive: float = 1.15) -> np.ndarray:
    """Gentle warm tape soft-clip + normalized 16-bit PCM conversion."""
    buf = np.tanh(buf * drive) / math.tanh(drive)
    peak = float(np.max(np.abs(buf)))
    if peak > 1e-8:
        buf = buf * (target_peak / peak)
    return np.clip(buf, -0.98, 0.98)


def write_wav(path: Path, samples: np.ndarray, sr: int = SR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.round(np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def loop_wrap(render_buf: np.ndarray, loop_samples: int, sr: int = SR) -> np.ndarray:
    """Wrap reverb/release tail back onto loop start for click-free seamless looping."""
    wet = apply_room_reverb(render_buf, wet=0.17, sr=sr)
    out = wet[:loop_samples].copy()
    tail = wet[loop_samples:]
    n_tail = min(loop_samples, len(tail))
    out[:n_tail] += tail[:n_tail]
    return out


# ---------- BGM Compositions ----------

def build_bgm_quan_night() -> np.ndarray:
    """16-bar Southern Vietnamese floating-market evening theme (~111.1 BPM, 34.56s loop)."""
    rng = np.random.default_rng(42)
    beat_samples = 17280  # 0.54s at 32kHz -> exact 111.111 BPM
    beat_s = beat_samples / SR
    bars = 16
    loop_samples = bars * 4 * beat_samples
    buf = np.zeros(loop_samples + int(2.6 * SR), dtype=np.float64)

    def swing_sample(beat_pos: float) -> int:
        # Subtle cozy human swing on 8th-note offbeats (0.5 -> ~0.55)
        whole = math.floor(beat_pos * 2.0) / 2.0
        frac = beat_pos - whole
        if abs(frac - 0.5) < 0.02:
            beat_pos = whole + 0.545
        elif abs((beat_pos % 1.0) - 0.5) < 0.02:
            beat_pos = math.floor(beat_pos) + 0.545
        return int(round(beat_pos * beat_samples))

    chords = [
        # Section A: warm lantern opening
        ("F2", ["A3", "C4", "E4"]),   # 1 Fmaj7
        ("D2", ["F3", "A3", "C4"]),   # 2 Dm7
        ("G2", ["Bb3", "D4", "F4"]),  # 3 Gm7
        ("C2", ["G3", "Bb3", "E4"]),  # 4 C9/C7
        ("F2", ["A3", "C4", "E4"]),   # 5 Fmaj7
        ("A2", ["C4", "E4", "G4"]),   # 6 Am7
        ("Bb2", ["D4", "F4", "G4"]),  # 7 Bb6
        ("C2", ["G3", "Bb3", "D4"]),  # 8 C9sus4 -> F
        # Section B: bustling guests under lanterns
        ("Bb2", ["D4", "F4", "A4"]),  # 9 Bbmaj7
        ("C2", ["G3", "Bb3", "E4"]),  # 10 C7
        ("D2", ["F3", "A3", "C4"]),   # 11 Dm7
        ("G2", ["D4", "F4", "A4"]),   # 12 Gm9 -> C
        ("F2", ["A3", "C4", "E4"]),   # 13 Fmaj7
        ("D2", ["F3", "A3", "C4"]),   # 14 Dm7
        ("G2", ["Bb3", "D4", "F4"]),  # 15 Gm7
        ("C2", ["G3", "Bb3", "E4"]),  # 16 C7 turnaround
    ]

    for bar, (bass_root, tones) in enumerate(chords):
        b0 = bar * 4.0
        root_hz = note_hz(bass_root)
        fifth_hz = root_hz * 1.4983
        # Warm bouncing bass (root - fifth - octave/approach)
        add_at(buf, int(b0 * beat_samples), synth_bass(root_hz, 1.3 * beat_s, 0.88))
        add_at(buf, int((b0 + 1.5) * beat_samples), synth_bass(fifth_hz, 0.85 * beat_s, 0.72))
        add_at(buf, int((b0 + 2.0) * beat_samples), synth_bass(root_hz * (2.0 if bar % 2 else 1.0), 1.05 * beat_s, 0.80))
        add_at(buf, int((b0 + 3.5) * beat_samples), synth_bass(fifth_hz, 0.55 * beat_s, 0.64))

        # Cozy syncopated wooden marimba comping
        comp_beats = [(0.5, 0.55), (1.5, 0.62), (2.5, 0.52), (3.25, 0.58)]
        for offset, vel in comp_beats:
            pos = swing_sample(b0 + offset)
            for idx, tn in enumerate(tones):
                add_at(buf, pos + idx * 280, synth_marimba(note_hz(tn), 0.34, vel * (0.95 - 0.1 * idx)))

        # Wooden percussion: soft kick, bamboo mo, brushed shaker, song loan accents
        add_at(buf, int(b0 * beat_samples), synth_kick(0.72))
        add_at(buf, int((b0 + 2.0) * beat_samples), synth_kick(0.56))
        add_at(buf, int((b0 + 1.0) * beat_samples), synth_mo(0.58, 520.0))
        add_at(buf, int((b0 + 3.0) * beat_samples), synth_mo(0.64, 590.0))
        for step in range(8):
            s_beat = b0 + step * 0.5
            s_vel = 0.52 if step % 2 == 0 else 0.36
            add_at(buf, swing_sample(s_beat), synth_shaker(s_vel, rng=rng))
        if bar % 2 == 1:
            add_at(buf, swing_sample(b0 + 2.5), synth_song_loan(0.68, 1.0))
        if bar in (3, 7, 11, 15):
            add_at(buf, int((b0 + 3.5) * beat_samples), synth_song_loan(0.75, 1.08))
            add_at(buf, int((b0 + 3.75) * beat_samples), synth_song_loan(0.60, 0.94))

    # Main melody: (beat_pos, note, dur_beats, vel, bend_cents)
    melody_a = [
        # Bar 0 (Fmaj7): cheerful Mekong welcome
        (0.0, "C5", 0.75, 0.85, -35), (0.75, "D5", 0.5, 0.78, 0), (1.25, "F5", 0.75, 0.90, -40),
        (2.0, "G5", 0.75, 0.86, 0), (2.75, "A5", 1.25, 0.92, -30),
        # Bar 1 (Dm7): gentle answer
        (4.25, "G5", 0.5, 0.80, 0), (4.75, "F5", 0.75, 0.84, 0), (5.5, "D5", 0.75, 0.82, -25),
        (6.25, "C5", 0.75, 0.78, 0), (7.0, "A4", 1.0, 0.76, 0),
        # Bar 2 (Gm7): playful bounce
        (8.0, "D5", 0.5, 0.82, -25), (8.5, "F5", 0.5, 0.85, 0), (9.0, "G5", 0.75, 0.88, -35),
        (9.75, "F5", 0.5, 0.80, 0), (10.25, "D5", 0.75, 0.82, 0), (11.0, "C5", 1.0, 0.78, 0),
        # Bar 3 (C9): warm question cadence
        (12.0, "G4", 0.75, 0.76, 0), (12.75, "A4", 0.75, 0.80, -25), (13.5, "C5", 1.25, 0.86, 0),
        (15.0, "D5", 0.5, 0.74, 0), (15.5, "E5", 0.5, 0.76, 0),
        # Bar 4 (Fmaj7): brighter lift
        (16.0, "F5", 0.75, 0.90, -35), (16.75, "A5", 0.75, 0.92, 0), (17.5, "C6", 0.75, 0.90, -30),
        (18.25, "A5", 0.75, 0.86, 0), (19.0, "G5", 0.5, 0.82, 0), (19.5, "F5", 0.5, 0.80, 0),
        # Bar 5 (Am7): soft cozy flow
        (20.0, "E5", 0.75, 0.82, 0), (20.75, "D5", 0.75, 0.80, -25), (21.5, "C5", 1.0, 0.84, 0),
        (22.75, "A4", 0.5, 0.74, 0), (23.25, "C5", 0.75, 0.78, 0),
        # Bar 6 (Bb6): southern folk turn
        (24.0, "D5", 0.5, 0.82, -30), (24.5, "F5", 0.5, 0.86, 0), (25.0, "D5", 0.5, 0.80, 0),
        (25.5, "C5", 0.5, 0.78, 0), (26.0, "A4", 0.75, 0.80, -25), (26.75, "G4", 0.75, 0.78, 0),
        (27.5, "A4", 0.5, 0.76, 0),
        # Bar 7 (C9sus4 -> F6): warm landing
        (28.0, "G4", 0.75, 0.82, -25), (28.75, "F4", 1.25, 0.85, 0),
        (30.5, "C5", 0.5, 0.70, 0), (31.0, "D5", 0.5, 0.74, 0), (31.5, "F5", 0.5, 0.78, 0),
    ]

    # Section B: Bamboo flute takes warm melody + Dan Tranh plays delicate sparkling answers
    flute_b = [
        (32.0, "D5", 1.0, 0.74, None), (33.0, "F5", 1.0, 0.78, "D5"), (34.0, "A5", 1.75, 0.82, "F5"),
        (36.0, "G5", 1.0, 0.76, "A5"), (37.0, "E5", 1.0, 0.72, "G5"), (38.0, "C5", 1.75, 0.74, "E5"),
        (40.0, "F5", 0.75, 0.76, None), (40.75, "A5", 0.75, 0.80, "F5"), (41.5, "G5", 1.0, 0.78, "A5"),
        (42.5, "F5", 0.75, 0.74, "G5"), (43.25, "D5", 0.75, 0.72, "F5"),
        (44.0, "G5", 1.25, 0.80, "D5"), (45.5, "E5", 1.0, 0.75, "G5"), (46.5, "C5", 1.25, 0.72, "E5"),
        # Bars 12-15: lively climax & turnaround
        (48.0, "A5", 1.0, 0.82, None), (49.0, "C6", 1.25, 0.84, "A5"), (50.5, "A5", 0.75, 0.78, "C6"),
        (51.25, "G5", 0.75, 0.76, "A5"),
        (52.0, "F5", 1.0, 0.78, "G5"), (53.0, "D5", 1.0, 0.74, "F5"), (54.0, "C5", 1.75, 0.74, "D5"),
        (56.0, "D5", 0.75, 0.74, None), (56.75, "F5", 0.75, 0.78, "D5"), (57.5, "G5", 1.0, 0.80, "F5"),
        (58.5, "F5", 0.75, 0.76, "G5"), (59.25, "D5", 0.75, 0.72, "F5"),
        (60.0, "C5", 1.5, 0.76, "D5"), (62.0, "A4", 1.5, 0.70, "C5"),
    ]
    zither_b_fills = [
        (35.0, "G5", 0.5, 0.68, 0), (35.5, "F5", 0.5, 0.64, 0),
        (39.0, "G4", 0.5, 0.65, 0), (39.5, "A4", 0.5, 0.68, -25),
        (47.0, "D5", 0.5, 0.68, -25), (47.5, "E5", 0.5, 0.72, 0),
        (48.0, "F5", 0.75, 0.76, -30), (49.5, "G5", 0.5, 0.70, 0), (50.0, "A5", 0.5, 0.74, 0),
        (54.5, "A4", 0.5, 0.66, 0), (55.0, "C5", 0.5, 0.70, 0), (55.5, "D5", 0.5, 0.72, 0),
        (58.0, "Bb5", 0.5, 0.68, 0), (59.0, "G5", 0.5, 0.66, 0),
        (61.5, "G4", 0.5, 0.70, 0), (62.5, "A4", 0.5, 0.72, -25), (63.25, "Bb4", 0.75, 0.74, 0),
    ]

    for b_pos, nt, d_beats, vel, bend in melody_a + zither_b_fills:
        add_at(buf, swing_sample(b_pos), synth_dan_tranh(note_hz(nt), max(0.35, d_beats * beat_s * 1.35), vel, bend_cents=bend, rng=rng))
    for b_pos, nt, d_beats, vel, glide in flute_b:
        gf = note_hz(glide) if glide else None
        add_at(buf, swing_sample(b_pos), synth_sao_truc(note_hz(nt), d_beats * beat_s * 0.96, vel, glide_from=gf, rng=rng))

    loop = loop_wrap(buf, loop_samples)
    return finalize_audio(loop, target_peak=0.84, drive=1.12)


def build_bgm_quan_rush() -> np.ndarray:
    """8-bar energetic final-25s rush loop (~133.3 BPM, 14.40s loop, G Major Pentatonic)."""
    rng = np.random.default_rng(108)
    beat_samples = 14400  # 0.45s at 32kHz -> exact 133.333 BPM
    beat_s = beat_samples / SR
    bars = 8
    loop_samples = bars * 4 * beat_samples
    buf = np.zeros(loop_samples + int(2.0 * SR), dtype=np.float64)

    chords = [
        ("G2", ["B3", "D4", "F#4"]),
        ("E2", ["G3", "B3", "D4"]),
        ("A2", ["C4", "E4", "G4"]),
        ("D2", ["A3", "C4", "F#4"]),
        ("G2", ["B3", "D4", "F#4"]),
        ("B2", ["D4", "F#4", "A4"]),
        ("C2", ["E3", "G3", "A3"]),
        ("D2", ["A3", "C4", "F#4"]),
    ]

    for bar, (bass_root, tones) in enumerate(chords):
        b0 = bar * 4.0
        root_hz = note_hz(bass_root)
        fifth_hz = root_hz * 1.4983
        # Driving walking bass
        for step, hz, vel in ((0.0, root_hz, 0.90), (1.0, fifth_hz, 0.74), (2.0, root_hz * 2.0, 0.84), (3.0, fifth_hz, 0.76)):
            add_at(buf, int((b0 + step) * beat_samples), synth_bass(hz, 0.85 * beat_s, vel))

        # Brisk off-beat marimba stabs
        for off in (0.5, 1.5, 2.5, 3.5):
            pos = int((b0 + off) * beat_samples)
            for idx, tn in enumerate(tones):
                add_at(buf, pos + idx * 180, synth_marimba(note_hz(tn), 0.22, 0.62))

        # Energetic bamboo/song-loan groove
        for b in range(4):
            add_at(buf, int((b0 + b) * beat_samples), synth_kick(0.76 if b % 2 == 0 else 0.48))
            add_at(buf, int((b0 + b + 0.5) * beat_samples), synth_song_loan(0.68 if b % 2 else 0.50, 1.05))
        add_at(buf, int((b0 + 1.0) * beat_samples), synth_mo(0.68, 560.0))
        add_at(buf, int((b0 + 3.0) * beat_samples), synth_mo(0.75, 650.0))
        for step in range(8):
            add_at(buf, int((b0 + step * 0.5) * beat_samples), synth_shaker(0.55 if step % 2 == 0 else 0.40, rng=rng))

    melody = [
        (0.0, "D5", 0.5, 0.92, -30), (0.5, "E5", 0.5, 0.86, 0), (1.0, "G5", 0.5, 0.94, -35), (1.5, "A5", 0.5, 0.90, 0),
        (2.0, "B5", 0.75, 0.95, -25), (2.75, "A5", 0.5, 0.86, 0), (3.25, "G5", 0.75, 0.88, 0),
        (4.0, "E5", 0.5, 0.86, 0), (4.5, "G5", 0.5, 0.88, -25), (5.0, "A5", 0.75, 0.90, 0),
        (5.75, "G5", 0.5, 0.84, 0), (6.25, "E5", 0.75, 0.84, 0), (7.0, "D5", 1.0, 0.86, 0),
        (8.0, "E5", 0.5, 0.88, -25), (8.5, "G5", 0.5, 0.90, 0), (9.0, "A5", 0.5, 0.92, 0), (9.5, "B5", 0.5, 0.90, 0),
        (10.0, "A5", 0.75, 0.88, 0), (10.75, "G5", 0.5, 0.82, 0), (11.25, "E5", 0.75, 0.84, 0),
        (12.0, "D5", 0.5, 0.84, 0), (12.5, "E5", 0.5, 0.86, 0), (13.0, "G5", 0.75, 0.90, -30),
        (13.75, "A5", 0.75, 0.88, 0), (14.5, "F#5", 0.75, 0.84, 0), (15.25, "D5", 0.75, 0.80, 0),
        # Second 4 bars: double brightness + flute reinforcement
        (16.0, "G5", 0.5, 0.94, -30), (16.5, "A5", 0.5, 0.90, 0), (17.0, "B5", 0.5, 0.95, 0), (17.5, "D6", 0.5, 0.94, -25),
        (18.0, "B5", 0.75, 0.90, 0), (18.75, "A5", 0.5, 0.86, 0), (19.25, "G5", 0.75, 0.88, 0),
        (20.0, "F#5", 0.5, 0.86, 0), (20.5, "A5", 0.5, 0.88, 0), (21.0, "B5", 0.75, 0.92, -30),
        (21.75, "A5", 0.5, 0.84, 0), (22.25, "F#5", 0.75, 0.82, 0), (23.0, "D5", 1.0, 0.82, 0),
        (24.0, "E5", 0.5, 0.90, -25), (24.5, "G5", 0.5, 0.92, 0), (25.0, "A5", 0.5, 0.94, 0), (25.5, "G5", 0.5, 0.88, 0),
        (26.0, "E5", 0.5, 0.88, 0), (26.5, "G5", 0.5, 0.90, 0), (27.0, "A5", 1.0, 0.92, 0),
        (28.0, "B5", 0.5, 0.92, -25), (28.5, "A5", 0.5, 0.88, 0), (29.0, "G5", 0.5, 0.86, 0), (29.5, "E5", 0.5, 0.84, 0),
        (30.0, "D5", 0.75, 0.88, 0), (30.75, "E5", 0.5, 0.84, 0), (31.25, "F#5", 0.75, 0.86, 0),
    ]
    for b_pos, nt, d_beats, vel, bend in melody:
        add_at(buf, int(b_pos * beat_samples), synth_dan_tranh(note_hz(nt), max(0.28, d_beats * beat_s * 1.15), vel, bend_cents=bend, rng=rng))
    for b_pos, nt, d_beats, vel, _ in melody[::2]:
        if b_pos >= 16.0:
            add_at(buf, int(b_pos * beat_samples), synth_sao_truc(note_hz(nt), d_beats * beat_s * 1.35, vel * 0.62, rng=rng))

    loop = loop_wrap(buf, loop_samples)
    return finalize_audio(loop, target_peak=0.78, drive=1.12)


def build_amb_river_night() -> np.ndarray:
    """12-second seamless Mekong river night ambience (lapping water, gentle crickets, cozy embers)."""
    rng = np.random.default_rng(777)
    dur = 12.0
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float64) / SR
    # Render 14s and crossfade wrap 2s for periodic seamless texture
    pad = int(2.0 * SR)
    raw_water = pink_noise(n + pad, rng)
    water = lowpass(bandpass(raw_water, 120.0, 950.0, order=2), 750.0, order=1)
    wave_lfo = 0.55 + 0.35 * np.sin(2.0 * np.pi * t / 4.0) + 0.15 * np.sin(2.0 * np.pi * t / 2.4 + 1.1)
    # Periodic crossfade on water
    out = water[:n] * wave_lfo * 0.24
    fade = np.linspace(0.0, 1.0, pad)
    out[:pad] = out[:pad] * fade + (water[n : n + pad] * wave_lfo[:pad] * 0.24) * (1.0 - fade)

    # Gentle boat plank water lap bloops
    for drop_t in (0.9, 2.3, 4.1, 5.8, 7.4, 9.2, 10.7):
        dn = int(0.11 * SR)
        dt = np.arange(dn, dtype=np.float64) / SR
        f0 = 320.0 + rng.uniform(-40.0, 70.0)
        bloop = np.sin(2.0 * np.pi * (f0 + 180.0 * dt) * dt) * np.exp(-dt * 42.0) * smooth_env(dn, 0.004, 0.04) * 0.045
        add_at(out, int(drop_t * SR), bloop)

    # Distant soothing Mekong crickets (soft pulses, high-Q warm harmonic)
    for c_start in (1.4, 3.8, 6.6, 8.9, 10.9):
        for p_idx in range(3):
            pn = int(0.048 * SR)
            pt = np.arange(pn, dtype=np.float64) / SR
            pulse = np.sin(2.0 * np.pi * 4050.0 * pt) * (0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(pn) / pn))
            pulse *= (0.65 + 0.35 * np.sin(2.0 * np.pi * 65.0 * pt)) * 0.028
            add_at(out, int((c_start + p_idx * 0.075) * SR), pulse)

    # Soft charcoal hearth crackles
    for cr_t in (0.4, 2.8, 5.1, 6.2, 8.1, 10.1):
        cn = int(0.025 * SR)
        crack = bandpass(rng.standard_normal(cn), 1400.0, 4200.0, order=2)
        crack *= np.exp(-np.arange(cn) / (0.004 * SR)) * 0.055
        add_at(out, int(cr_t * SR), crack)

    return finalize_audio(out, target_peak=0.45, drive=1.02)


def build_jingle_end() -> np.ndarray:
    """Warm celebratory Southern Vietnamese pentatonic end-of-shift fanfare."""
    rng = np.random.default_rng(19)
    n = int(3.0 * SR)
    buf = np.zeros(n, dtype=np.float64)
    notes = [
        (0.00, "C5", 0.35, 0.82),
        (0.16, "D5", 0.35, 0.84),
        (0.32, "F5", 0.45, 0.88),
        (0.50, "A5", 0.50, 0.90),
        (0.70, "C6", 1.35, 0.95),
    ]
    for ts, nt, d, v in notes:
        add_at(buf, int(ts * SR), synth_dan_tranh(note_hz(nt), d, v, bend_cents=-25 if nt in ("F5", "C6") else 0, rng=rng))
    for nt in ("F4", "A4", "C5", "F5"):
        add_at(buf, int(0.70 * SR), synth_marimba(note_hz(nt), 0.9, 0.55))
    add_at(buf, int(0.70 * SR), synth_sao_truc(note_hz("C6"), 1.35, 0.65, glide_from=note_hz("A5"), rng=rng))
    add_at(buf, int(0.70 * SR), synth_bass(note_hz("F2"), 1.5, 0.85))
    add_at(buf, int(0.00 * SR), synth_song_loan(0.75, 1.0))
    add_at(buf, int(0.70 * SR), synth_song_loan(0.85, 1.12))
    wet = apply_room_reverb(buf, wet=0.22)
    wet *= smooth_env(len(wet), 0.004, 0.35)
    return finalize_audio(wet, target_peak=0.88)


# ---------- SFX Palette ----------

def build_sfx_customer_arrive() -> np.ndarray:
    """Wooden boat bump + bamboo shop chime greeting."""
    rng = np.random.default_rng(101)
    n = int(0.65 * SR)
    buf = np.zeros(n, dtype=np.float64)
    # Soft wooden boat bump
    add_at(buf, 0, synth_kick(0.55))
    add_at(buf, int(0.03 * SR), synth_mo(0.50, 380.0))
    # Bamboo/brass shop bell chime (F5 -> C6)
    for ts, hz, v in ((0.06, note_hz("F5"), 0.85), (0.19, note_hz("C6"), 0.92)):
        cn = int(0.42 * SR)
        t = np.arange(cn, dtype=np.float64) / SR
        bell = (0.75 * np.sin(2.0 * np.pi * hz * t) + 0.25 * np.sin(2.0 * np.pi * hz * 2.0 * t)) * np.exp(-t * 7.5)
        bell *= smooth_env(cn, 0.002, 0.08) * v * 0.55
        add_at(buf, int(ts * SR), bell)
    return finalize_audio(apply_room_reverb(buf, wet=0.14), target_peak=0.86)


def build_sfx_cook_start() -> np.ndarray:
    """Charcoal puff + hot pan sizzle + pot clink."""
    rng = np.random.default_rng(102)
    n = int(0.72 * SR)
    buf = np.zeros(n, dtype=np.float64)
    add_at(buf, 0, synth_mo(0.60, 440.0))
    sn = int(0.64 * SR)
    t = np.arange(sn, dtype=np.float64) / SR
    sizzle = bandpass(rng.standard_normal(sn), 2400.0, 9200.0, order=2)
    sizzle *= (0.35 + 0.65 * np.exp(-t * 4.5)) * smooth_env(sn, 0.025, 0.22) * 0.45
    add_at(buf, int(0.03 * SR), sizzle)
    # Charcoal puff thump
    pn = int(0.14 * SR)
    puff = lowpass(rng.standard_normal(pn), 360.0) * smooth_env(pn, 0.01, 0.08) * 0.45
    add_at(buf, 0, puff)
    return finalize_audio(buf, target_peak=0.85)


def build_sfx_fridge_open() -> np.ndarray:
    """Fridge seal pop + fizzy cold ice clink for Coca."""
    rng = np.random.default_rng(103)
    n = int(0.48 * SR)
    buf = np.zeros(n, dtype=np.float64)
    # Rubber seal pop
    pn = int(0.06 * SR)
    pt = np.arange(pn, dtype=np.float64) / SR
    pop = np.sin(2.0 * np.pi * (140.0 + 380.0 * pt) * pt) * np.exp(-pt * 48.0) * 0.55
    add_at(buf, 0, pop)
    # Ice clinks
    for ts, hz in ((0.08, 2200.0), (0.14, 2850.0), (0.21, 3300.0)):
        cn = int(0.14 * SR)
        ct = np.arange(cn, dtype=np.float64) / SR
        clink = (0.7 * np.sin(2.0 * np.pi * hz * ct) + 0.3 * np.sin(2.0 * np.pi * hz * 1.41 * ct)) * np.exp(-ct * 26.0) * 0.40
        add_at(buf, int(ts * SR), clink)
    fizz = bandpass(rng.standard_normal(int(0.28 * SR)), 4200.0, 11000.0) * smooth_env(int(0.28 * SR), 0.02, 0.14) * 0.18
    add_at(buf, int(0.12 * SR), fizz)
    return finalize_audio(buf, target_peak=0.84)


def build_sfx_dish_ready() -> np.ndarray:
    """Crisp ceramic kitchen bell ding + joyful 2-note chime."""
    n = int(0.68 * SR)
    buf = np.zeros(n, dtype=np.float64)
    for ts, hz, amp in ((0.0, note_hz("A5"), 0.52), (0.09, note_hz("D6"), 0.65)):
        ln = int(0.55 * SR)
        t = np.arange(ln, dtype=np.float64) / SR
        tone = (
            0.70 * np.sin(2.0 * np.pi * hz * t) * np.exp(-t * 6.5)
            + 0.25 * np.sin(2.0 * np.pi * hz * 2.0 * t) * np.exp(-t * 14.0)
            + 0.12 * np.sin(2.0 * np.pi * hz * 3.01 * t) * np.exp(-t * 24.0)
        )
        tone *= smooth_env(ln, 0.0015, 0.08) * amp
        add_at(buf, int(ts * SR), tone)
    return finalize_audio(apply_room_reverb(buf, wet=0.14), target_peak=0.88)


def build_sfx_dish_pickup() -> np.ndarray:
    """Tactile ceramic plate + wooden tray upward pop."""
    n = int(0.22 * SR)
    t = np.arange(n, dtype=np.float64) / SR
    f = 340.0 + 360.0 * (1.0 - np.exp(-t * 28.0))
    buf = np.sin(2.0 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18.0) * 0.58
    add_at(buf, 0, synth_mo(0.45, 760.0))
    return finalize_audio(buf * smooth_env(n, 0.002, 0.04), target_peak=0.82)


def build_sfx_serve() -> np.ndarray:
    """Warm plate set down + cute satisfied chirp."""
    n = int(0.45 * SR)
    buf = np.zeros(n, dtype=np.float64)
    add_at(buf, 0, synth_mo(0.65, 420.0))
    for ts, nt in ((0.06, "F5"), (0.14, "A5")):
        cn = int(0.22 * SR)
        t = np.arange(cn, dtype=np.float64) / SR
        hz = note_hz(nt)
        chirp = (0.8 * np.sin(2.0 * np.pi * hz * t) + 0.2 * np.sin(4.0 * np.pi * hz * t)) * np.exp(-t * 12.0) * 0.45
        add_at(buf, int(ts * SR), chirp * smooth_env(cn, 0.004, 0.05))
    return finalize_audio(buf, target_peak=0.84)


def build_sfx_coin_pay() -> np.ndarray:
    """Crisp metallic coin clink + cheerful cash chime."""
    n = int(0.54 * SR)
    buf = np.zeros(n, dtype=np.float64)
    for ts, hz in ((0.0, note_hz("C6")), (0.07, note_hz("F6"))):
        cn = int(0.42 * SR)
        t = np.arange(cn, dtype=np.float64) / SR
        coin = (0.72 * np.sin(2.0 * np.pi * hz * t) + 0.28 * np.sin(2.0 * np.pi * hz * 2.5 * t)) * np.exp(-t * 10.5)
        add_at(buf, int(ts * SR), coin * smooth_env(cn, 0.001, 0.05) * 0.55)
    return finalize_audio(apply_room_reverb(buf, wet=0.12), target_peak=0.88)


def build_sfx_coin_tip() -> np.ndarray:
    """Sparkly double coin + ascending pentatonic tip chime (boa!)."""
    n = int(0.78 * SR)
    buf = np.zeros(n, dtype=np.float64)
    for ts, nt in ((0.0, "C6"), (0.06, "D6"), (0.12, "F6"), (0.19, "A6")):
        cn = int(0.48 * SR)
        t = np.arange(cn, dtype=np.float64) / SR
        hz = note_hz(nt)
        coin = (0.75 * np.sin(2.0 * np.pi * hz * t) + 0.25 * np.sin(2.0 * np.pi * hz * 2.0 * t)) * np.exp(-t * 8.5)
        add_at(buf, int(ts * SR), coin * smooth_env(cn, 0.001, 0.06) * 0.48)
    return finalize_audio(apply_room_reverb(buf, wet=0.16), target_peak=0.88)


def build_sfx_customer_angry() -> np.ndarray:
    """Cute grumpy wooden warning ('uh-oh!')."""
    n = int(0.42 * SR)
    buf = np.zeros(n, dtype=np.float64)
    for ts, f0, f1 in ((0.0, 260.0, 220.0), (0.14, 210.0, 165.0)):
        ln = int(0.14 * SR)
        f = np.linspace(f0, f1, ln)
        phase = 2.0 * np.pi * np.cumsum(f) / SR
        tone = (0.65 * np.sin(phase) + 0.35 * np.sin(2.0 * phase) + 0.15 * np.sin(3.0 * phase))
        tone = lowpass(tone, 820.0) * smooth_env(ln, 0.010, 0.045) * 0.45
        add_at(buf, int(ts * SR), tone)
    return finalize_audio(buf, target_peak=0.60)


def build_sfx_customer_leave() -> np.ndarray:
    """Sad descending woodwind slide + soft water splash."""
    rng = np.random.default_rng(109)
    n = int(0.75 * SR)
    buf = np.zeros(n, dtype=np.float64)
    sn = int(0.45 * SR)
    t = np.arange(sn, dtype=np.float64) / SR
    f = 420.0 * (0.58 ** (t / 0.45))
    slide = np.sin(2.0 * np.pi * np.cumsum(f) / SR) * smooth_env(sn, 0.015, 0.14) * 0.48
    add_at(buf, 0, slide)
    splash = bandpass(rng.standard_normal(int(0.32 * SR)), 380.0, 2600.0) * smooth_env(int(0.32 * SR), 0.02, 0.18) * 0.38
    add_at(buf, int(0.28 * SR), splash)
    add_at(buf, int(0.28 * SR), synth_kick(0.45))
    return finalize_audio(buf, target_peak=0.82)


def build_sfx_dish_waste() -> np.ndarray:
    """Hollow deflated wooden thud."""
    rng = np.random.default_rng(110)
    n = int(0.38 * SR)
    t = np.arange(n, dtype=np.float64) / SR
    f = 190.0 * np.exp(-t * 5.0) + 75.0
    thud = np.sin(2.0 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9.0) * 0.58
    puff = bandpass(rng.standard_normal(n), 250.0, 1200.0) * np.exp(-t * 14.0) * 0.25
    return finalize_audio((thud + puff) * smooth_env(n, 0.004, 0.08), target_peak=0.80)


def build_sfx_buy() -> np.ndarray:
    """Ong Hai supply basket rustle + coin exchange."""
    rng = np.random.default_rng(111)
    n = int(0.44 * SR)
    buf = np.zeros(n, dtype=np.float64)
    rustle = bandpass(rng.standard_normal(int(0.18 * SR)), 1200.0, 4800.0) * smooth_env(int(0.18 * SR), 0.01, 0.08) * 0.28
    add_at(buf, 0, rustle)
    add_at(buf, int(0.05 * SR), synth_song_loan(0.45, 0.92))
    cn = int(0.26 * SR)
    t = np.arange(cn, dtype=np.float64) / SR
    hz = note_hz("G5")
    add_at(buf, int(0.11 * SR), np.sin(2.0 * np.pi * hz * t) * np.exp(-t * 11.0) * smooth_env(cn, 0.002, 0.05) * 0.55)
    return finalize_audio(buf, target_peak=0.84)


def build_sfx_upgrade() -> np.ndarray:
    """Joyful rising Vietnamese pentatonic power-up sparkle."""
    rng = np.random.default_rng(112)
    n = int(0.84 * SR)
    buf = np.zeros(n, dtype=np.float64)
    for ts, nt, d in ((0.0, "F5", 0.30), (0.09, "G5", 0.30), (0.18, "A5", 0.35), (0.27, "C6", 0.42), (0.37, "F6", 0.45)):
        add_at(buf, int(ts * SR), synth_dan_tranh(note_hz(nt), d, 0.86, rng=rng))
        add_at(buf, int(ts * SR), synth_marimba(note_hz(nt), d * 0.8, 0.52))
    return finalize_audio(apply_room_reverb(buf, wet=0.18), target_peak=0.72)


def build_sfx_error() -> np.ndarray:
    """Soft gentle wooden double-tap."""
    n = int(0.24 * SR)
    buf = np.zeros(n, dtype=np.float64)
    add_at(buf, 0, synth_mo(0.65, 290.0))
    add_at(buf, int(0.085 * SR), synth_mo(0.55, 235.0))
    return finalize_audio(buf, target_peak=0.78)


def build_sfx_step_wood() -> np.ndarray:
    """Subtle warm wooden boat plank footstep."""
    rng = np.random.default_rng(114)
    n = int(0.11 * SR)
    t = np.arange(n, dtype=np.float64) / SR
    knock = (0.7 * np.sin(2.0 * np.pi * 175.0 * t) + 0.3 * np.sin(2.0 * np.pi * 310.0 * t)) * np.exp(-t * 48.0)
    grain = bandpass(rng.standard_normal(n), 400.0, 2200.0) * np.exp(-t * 65.0) * 0.25
    return finalize_audio((knock + grain) * smooth_env(n, 0.002, 0.03), target_peak=0.65)


def build_sfx_ui_click() -> np.ndarray:
    """Crisp bamboo UI tap."""
    return finalize_audio(synth_mo(0.70, 680.0), target_peak=0.72)


SPECS = [
    ("bgm_quan_night.wav", "bgm", True, "Cozy Mekong floating market evening loop (16 bars, ~111 BPM, F pentatonic)", build_bgm_quan_night),
    ("bgm_quan_rush.wav", "bgm", True, "Energetic final-25s rush loop (8 bars, ~133 BPM, G pentatonic)", build_bgm_quan_rush),
    ("amb_quan_river_night.wav", "ambience", True, "Mekong night river water lap, crickets & hearth ambience loop", build_amb_river_night),
    ("jingle_quan_end.wav", "jingle", False, "Shift complete celebratory Vietnamese pentatonic fanfare", build_jingle_end),
    ("sfx_customer_arrive.wav", "sfx", False, "Boat nudge + bamboo shop chime greeting", build_sfx_customer_arrive),
    ("sfx_cook_start.wav", "sfx", False, "Charcoal flame puff + hot pan sizzle", build_sfx_cook_start),
    ("sfx_fridge_open.wav", "sfx", False, "Cold fridge door pop + fizzy ice clink (Coca)", build_sfx_fridge_open),
    ("sfx_dish_ready.wav", "sfx", False, "Kitchen bell ding + 2-note ready chime", build_sfx_dish_ready),
    ("sfx_dish_pickup.wav", "sfx", False, "Ceramic plate & tray pickup pop", build_sfx_dish_pickup),
    ("sfx_serve.wav", "sfx", False, "Plate set on table + happy chirp", build_sfx_serve),
    ("sfx_coin_pay.wav", "sfx", False, "Coin clink + cash chime", build_sfx_coin_pay),
    ("sfx_coin_tip.wav", "sfx", False, "Double sparkly coin + tip arpeggio (boa)", build_sfx_coin_tip),
    ("sfx_customer_angry.wav", "sfx", False, "Grumpy warning double-tone", build_sfx_customer_angry),
    ("sfx_customer_leave.wav", "sfx", False, "Descending slide + paddle splash", build_sfx_customer_leave),
    ("sfx_dish_waste.wav", "sfx", False, "Hollow deflated thud", build_sfx_dish_waste),
    ("sfx_buy.wav", "sfx", False, "Supply basket rustle + coin clink (Ông Hai)", build_sfx_buy),
    ("sfx_upgrade.wav", "sfx", False, "Rising pentatonic upgrade sparkle", build_sfx_upgrade),
    ("sfx_error.wav", "sfx", False, "Soft wooden double-tap error", build_sfx_error),
    ("sfx_step_wood.wav", "sfx", False, "Soft wooden boat plank footstep", build_sfx_step_wood),
    ("sfx_ui_click.wav", "sfx", False, "Crisp bamboo UI click", build_sfx_ui_click),
]


def generate():
    records = []
    for filename, category, loop, desc, fn in SPECS:
        out_path = AUDIO_DIR / filename
        samples = fn()
        write_wav(out_path, samples, SR)
        rms = float(np.sqrt(np.mean(samples ** 2)))
        peak = float(np.max(np.abs(samples)))
        records.append({
            "path": filename,
            "category": category,
            "loop": loop,
            "sample_rate": SR,
            "duration_s": round(len(samples) / SR, 4),
            "peak": round(peak, 4),
            "rms_db": round(20.0 * math.log10(max(rms, 1e-8)), 2),
            "description": desc,
            "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        })
        print(f"Wrote {filename:28s} {len(samples)/SR:6.2f}s | peak={peak:.3f} | rms={records[-1]['rms_db']:6.2f} dB")
    MANIFEST.write_text(json.dumps({"sample_rate": SR, "assets": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    seen = set()
    for entry in manifest["assets"]:
        path = AUDIO_DIR / entry["path"]
        assert entry["path"] not in seen, f"Duplicate: {path}"
        seen.add(entry["path"])
        assert path.exists(), f"Missing: {path}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], f"Hash mismatch: {path}"
        with wave.open(str(path), "rb") as wf:
            assert wf.getnchannels() == 1, f"Expected mono: {path}"
            assert wf.getsampwidth() == 2, f"Expected 16-bit: {path}"
            assert wf.getframerate() == SR, f"Sample rate mismatch: {path}"
            n_frames = wf.getnframes()
            data = np.frombuffer(wf.readframes(n_frames), dtype="<i2").astype(np.float64) / 32768.0
        peak = float(np.max(np.abs(data)))
        rms = float(np.sqrt(np.mean(data ** 2)))
        assert 0.05 < peak <= 0.99, f"Bad peak {peak}: {path}"
        assert rms > 0.005, f"Too quiet {rms}: {path}"
        if entry["loop"]:
            # Check loop seam continuity (last sample vs first sample step)
            seam_diff = abs(float(data[0]) - float(data[-1]))
            assert seam_diff < 0.06, f"Loop seam click ({seam_diff:.4f}): {path}"
    actual = {p.name for p in AUDIO_DIR.glob("*.wav")}
    assert actual == seen, f"Manifest mismatch: {actual ^ seen}"
    print(f"PASS: {len(seen)} WAVs verified (mono, 16-bit, {SR}Hz, peaks, RMS, loop seams, sha256)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check"))
    args = parser.parse_args()
    if args.command == "generate":
        generate()
    check()

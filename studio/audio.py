"""Mix a film's cues, optional song, and narration into one stereo wav."""

import array
import math
import random
import re
import subprocess
import wave
from pathlib import Path

from voice import synthesize

RATE = 44100
PITCH = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5,
    "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11,
}


def note_freq(note):
    match = re.fullmatch(r"([A-Ga-g][#b]?)(-?\d)", str(note).strip())
    if not match:
        raise ValueError(f"bad note: {note}")
    pitch = PITCH[match.group(1).upper()]
    octave = int(match.group(2))
    midi = (octave + 1) * 12 + pitch
    return 440.0 * (2 ** ((midi - 69) / 12))


def build_soundtrack(meta, dest, music_path=None):
    duration = float(meta["duration"])
    frames = max(1, int(round(duration * RATE)))
    samples = array.array("f", [0.0]) * (frames * 2)
    for cue in meta.get("sound") or []:
        _add_cue(samples, cue)
    if music_path:
        gain = float((meta.get("music") or {}).get("gain") or 0.8)
        _add_array(samples, _read_music(music_path, duration, gain), 0)
    voices = _prepare_voice(meta.get("voice") or [], frames)
    _duck(samples, [(start, end) for start, end, _spoken, _level in voices], frames)
    for start, _end, spoken, level in voices:
        for i, sample in enumerate(spoken):
            frame = start + i
            if frame >= frames:
                break
            samples[frame * 2] += sample * level
            samples[frame * 2 + 1] += sample * level
    _peak(samples, 0.89)
    _write_wav(dest, samples)
    return {"rate": RATE, "frames": frames, "voices": len(voices)}


def _add_cue(samples, cue):
    kind = cue.get("kind")
    start = float(cue.get("t") or 0)
    gain = float(cue.get("gain") or 0.2)
    if kind == "pad":
        mono = _pad(cue, gain)
    elif kind == "pluck":
        mono = _pluck(cue, gain)
    elif kind == "water":
        mono = _water(cue, gain, start)
    elif kind == "whoosh":
        mono = _whoosh(cue, gain, start)
    elif kind == "tick":
        mono = _tick(gain)
    else:
        raise ValueError(f"unknown cue kind: {kind}")
    _add_array(samples, _stereo(mono), int(start * RATE))


def _tone(freq, seconds, gain, decay, attack=0.01):
    count = max(1, int(seconds * RATE))
    out = array.array("f")
    for i in range(count):
        t = i / RATE
        attack_gain = min(1.0, t / attack) if attack else 1.0
        out.append(math.sin(2 * math.pi * freq * t) * math.exp(-decay * t) * attack_gain * gain)
    return out


def _pad(cue, gain):
    freq = note_freq(cue.get("note") or "A2")
    seconds = float(cue.get("dur") or 2)
    count = max(1, int(seconds * RATE))
    out = array.array("f")
    for i in range(count):
        t = i / RATE
        edge = min(1.0, t / 0.4) * min(1.0, (seconds - t) / 0.6)
        tremolo = 0.9 + 0.1 * math.sin(2 * math.pi * 0.18 * t)
        wave_a = math.sin(2 * math.pi * freq * t)
        wave_b = math.sin(2 * math.pi * freq * 1.003 * t)
        out.append((wave_a + wave_b) * 0.5 * edge * tremolo * gain)
    return out


def _pluck(cue, gain):
    freq = note_freq(cue.get("note") or "A4")
    seconds = float(cue.get("dur") or 0.85)
    count = max(1, int(seconds * RATE))
    out = array.array("f")
    for i in range(count):
        t = i / RATE
        bent = freq * (1 + 0.03 * math.exp(-18 * t))
        body = math.sin(2 * math.pi * bent * t) + 0.25 * math.sin(2 * math.pi * bent * 2 * t)
        out.append(body * math.exp(-3.4 * t) * gain)
    return out


def _water(cue, gain, start):
    seconds = float(cue.get("dur") or 2)
    count = max(1, int(seconds * RATE))
    rng = random.Random(int(start * 1000) + 17)
    out = array.array("f")
    acc = 0.0
    for i in range(count):
        t = i / RATE
        acc = acc * 0.985 + (rng.random() * 2 - 1) * 0.02
        lfo = 0.65 + 0.35 * math.sin(2 * math.pi * 0.13 * t)
        out.append(acc * 9 * lfo * gain)
    return out


def _whoosh(cue, gain, start):
    seconds = float(cue.get("dur") or 0.42)
    count = max(1, int(seconds * RATE))
    rng = random.Random(int(start * 1000) + 3)
    out = array.array("f")
    phase = 0.0
    for i in range(count):
        u = i / count
        env = math.sin(math.pi * u) ** 2
        phase += (280 + 1600 * u) / RATE
        noise = rng.random() * 2 - 1
        out.append((math.sin(2 * math.pi * phase) * 0.35 + noise * 0.65) * env * gain)
    return out


def _tick(gain):
    return _tone(880, 0.07, gain, 28, attack=0.002)


def _stereo(mono):
    out = array.array("f")
    for sample in mono:
        out.append(sample)
        out.append(sample)
    return out


def _add_array(dest, src, start_frame):
    frames = len(dest) // 2
    for i in range(0, len(src), 2):
        frame = start_frame + i // 2
        if frame >= frames:
            break
        if frame < 0:
            continue
        dest[frame * 2] += src[i]
        dest[frame * 2 + 1] += src[i + 1]


def _read_music(path, seconds, gain):
    proc = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path), "-t", f"{seconds:.3f}",
            "-ac", "2", "-ar", str(RATE), "-f", "f32le", "pipe:1",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    data = array.array("f")
    data.frombytes(proc.stdout)
    for i in range(len(data)):
        data[i] *= gain
    return data


def _prepare_voice(lines, frames):
    prepared = []
    for line in lines:
        spoken = synthesize(line, RATE)
        start = int(float(line.get("t") or 0) * RATE)
        end = min(frames, start + len(spoken))
        if end > start:
            prepared.append((start, end, spoken, float(line.get("gain") or 0.72)))
    return prepared


def _duck(samples, spans, frames):
    if not spans:
        return
    gain = array.array("f", [1.0]) * frames
    for start, end in spans:
        a = max(0, start - int(0.05 * RATE))
        b = min(frames, end + int(0.14 * RATE))
        for i in range(a, b):
            if i < start:
                ramp = (i - a) / max(1, start - a)
            elif i > end:
                ramp = 1 - (i - end) / max(1, b - end)
            else:
                ramp = 1.0
            gain[i] = min(gain[i], 1 - 0.62 * max(0.0, min(1.0, ramp)))
    for i in range(frames):
        samples[i * 2] *= gain[i]
        samples[i * 2 + 1] *= gain[i]


def _peak(samples, limit):
    peak = 0.0
    for sample in samples:
        peak = max(peak, abs(sample))
    if peak < 1e-5:
        return
    scale = limit / peak
    for i in range(len(samples)):
        samples[i] *= scale


def _write_wav(path, samples):
    pcm = array.array("h")
    for sample in samples:
        clipped = max(-1.0, min(1.0, sample))
        pcm.append(int(clipped * 32767))
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(pcm.tobytes())

"""Narration. eSpeak NG is the default. ElevenLabs is used only when a line asks for it."""

import array
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
MAX_CHARS = 600


def choose_engine(line, environ=None):
    environ = os.environ if environ is None else environ
    engine = (line.get("engine") or "espeak").strip().lower()
    if engine == "espeak":
        return "espeak"
    if engine == "elevenlabs":
        if not str(environ.get("ELEVENLABS_API_KEY", "")).strip():
            raise RuntimeError("ELEVENLABS_API_KEY is empty in .env")
        if not str(environ.get("ELEVENLABS_VOICE_ID", "")).strip():
            raise RuntimeError("ELEVENLABS_VOICE_ID is empty in .env")
        return "elevenlabs"
    raise RuntimeError(f"unknown voice engine: {engine}")


def synthesize(line, rate):
    load_dotenv(ROOT / ".env")
    text = str(line.get("text", "")).strip()
    if not text:
        raise RuntimeError("voice line is empty")
    if len(text) > MAX_CHARS:
        raise RuntimeError(f"voice line is longer than {MAX_CHARS} characters")
    engine = choose_engine(line)
    if engine == "espeak":
        samples, src_rate = _espeak(text, line.get("lang") or "en")
    else:
        samples, src_rate = _elevenlabs(text)
    return _resample(samples, src_rate, rate)


def _espeak(text, lang):
    voice = {"ru": "ru", "en": "en"}.get(lang, lang)
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "line.wav"
        try:
            subprocess.run(
                ["espeak-ng", "-v", voice, "-s", "148", "-w", str(dest), text],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("espeak-ng is not installed") from exc
        except subprocess.CalledProcessError as exc:
            tail = (exc.stderr or "").strip().splitlines()[-1:] or ["espeak-ng failed"]
            raise RuntimeError(tail[0]) from exc
        return _read_wav_mono(dest)


def _elevenlabs(text):
    key = os.environ["ELEVENLABS_API_KEY"].strip()
    voice_id = os.environ["ELEVENLABS_VOICE_ID"].strip()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ElevenLabs returned HTTP {exc.code}") from exc
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "line.mp3"
        dest = Path(tmp) / "line.wav"
        src.write_bytes(audio)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "44100", str(dest)],
            check=True,
        )
        return _read_wav_mono(dest)


def _read_wav_mono(path):
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        src_rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if width != 2:
        raise RuntimeError("narration wav is not 16-bit")
    ints = array.array("h")
    ints.frombytes(frames)
    if sys.byteorder != "little":
        ints.byteswap()
    count = len(ints) // channels
    mono = array.array("f")
    for i in range(count):
        total = 0
        for channel in range(channels):
            total += ints[i * channels + channel]
        mono.append(total / channels / 32768.0)
    return mono, src_rate


def _resample(samples, src_rate, dst_rate):
    if src_rate == dst_rate or len(samples) == 0:
        return samples
    out_len = max(1, int(round(len(samples) * dst_rate / src_rate)))
    out = array.array("f")
    last = len(samples) - 1
    for i in range(out_len):
        pos = i * src_rate / dst_rate
        i0 = min(int(pos), last)
        i1 = min(i0 + 1, last)
        frac = pos - i0
        out.append(samples[i0] * (1 - frac) + samples[i1] * frac)
    return out

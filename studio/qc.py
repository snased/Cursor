"""Checks a rendered MP4: picture, motion, and audible sound."""

import hashlib
import json
import re
import shutil
import subprocess


def check_film(path, duration):
    problems = []
    info = _probe(path)
    video = next((stream for stream in info["streams"] if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in info["streams"] if stream.get("codec_type") == "audio"), None)
    if video is None:
        problems.append("no video stream")
    if audio is None:
        problems.append("no audio stream")
    actual = float(info["format"].get("duration") or 0)
    if abs(actual - float(duration)) > 0.45:
        problems.append(f"duration {actual:.2f}s, expected about {float(duration):.2f}s")
    if video is not None:
        luma = _mean_luma(path, 0)
        if luma < 6:
            problems.append(f"opening frame is almost black ({luma:.1f})")
        later = min(float(duration) * 0.5, 0.5)
        if later > 0 and _frame_hash(path, 0) == _frame_hash(path, later):
            problems.append("picture does not change in the first half second")
    if audio is not None:
        volume = _mean_volume(path)
        if volume < -36:
            problems.append(f"soundtrack is very quiet ({volume:.1f} dB)")
    return problems


def _probe(path):
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return json.loads(proc.stdout)


def _frame_hash(path, seconds):
    proc = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(path),
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    return hashlib.sha256(proc.stdout).hexdigest()


def _mean_luma(path, seconds):
    proc = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(path),
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    data = proc.stdout
    if not data:
        raise RuntimeError(f"could not read a frame from {path}")
    return sum(data) / len(data)


def _mean_volume(path):
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", proc.stdout)
    if not match:
        raise RuntimeError("volumedetect did not report a level")
    return float(match.group(1))


def require_tools():
    missing = [name for name in ("node", "ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise SystemExit("missing tools: " + ", ".join(missing))

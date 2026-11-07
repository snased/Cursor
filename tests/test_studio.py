"""Studio tests that do not need Chrome, plus one short render."""

import array
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "studio"))

from audio import RATE, build_soundtrack, note_freq  # noqa: E402
from looks import look_names  # noqa: E402
from voice import choose_engine  # noqa: E402


class StudioTests(unittest.TestCase):
    def test_note_a4_is_concert_pitch(self):
        self.assertAlmostEqual(note_freq("A4"), 440.0, places=4)
        self.assertAlmostEqual(note_freq("Bb4"), note_freq("A#4"), places=4)

    def test_unknown_cue_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "mix.wav"
            with self.assertRaises(ValueError):
                build_soundtrack({"duration": 0.2, "sound": [{"t": 0, "kind": "nope"}]}, dest)

    def test_soundtrack_has_energy_and_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "mix.wav"
            info = build_soundtrack({
                "duration": 1.0,
                "sound": [{"t": 0, "kind": "pad", "note": "A3", "dur": 1, "gain": 0.25}],
                "voice": [{"t": 0.05, "text": "Hello.", "lang": "en", "engine": "espeak"}],
            }, dest)
            self.assertEqual(info["voices"], 1)
            self.assertGreater(self._rms(dest), 0.01)
            with wave.open(str(dest), "rb") as handle:
                self.assertEqual(handle.getframerate(), RATE)
                self.assertAlmostEqual(handle.getnframes() / RATE, 1.0, places=2)

    def test_music_file_is_mixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bed = Path(tmp) / "bed.wav"
            build_soundtrack({
                "duration": 0.4,
                "sound": [{"t": 0, "kind": "tick", "gain": 0.5}],
            }, bed)
            mixed = Path(tmp) / "mixed.wav"
            build_soundtrack({
                "duration": 0.4,
                "sound": [],
                "music": {"file": "bed.wav", "gain": 0.9},
            }, mixed, music_path=bed)
            self.assertGreater(self._rms(mixed), 0.01)

    def test_elevenlabs_needs_both_keys(self):
        with self.assertRaises(RuntimeError):
            choose_engine({"engine": "elevenlabs"}, {})
        with self.assertRaises(RuntimeError):
            choose_engine({"engine": "elevenlabs"}, {"ELEVENLABS_API_KEY": "x"})
        self.assertEqual(
            choose_engine({"engine": "elevenlabs"}, {"ELEVENLABS_API_KEY": "x", "ELEVENLABS_VOICE_ID": "y"}),
            "elevenlabs",
        )
        self.assertEqual(choose_engine({}, {}), "espeak")

    def test_looks_match_the_eight_families(self):
        self.assertEqual(
            look_names(),
            ["cinematic", "claymation", "anime-cel", "storybook", "papercut", "vhs", "glossy-ad", "ink"],
        )

    def test_init_writes_a_quick_film(self):
        folder = ROOT / "films" / "_test_harbor"
        shutil.rmtree(folder, ignore_errors=True)
        try:
            subprocess.run(
                [sys.executable, str(ROOT / "studio" / "init_film.py"), "_test_harbor", "--title", "Harbor", "--seconds", "4"],
                check=True,
                cwd=ROOT,
            )
            html = (folder / "film.html").read_text(encoding="utf-8")
            self.assertIn('"Harbor"', html)
            self.assertNotIn("__TITLE__", html)
            self.assertIn("Phase: plan", (folder / "STATE.md").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_concat_joins_two_clips(self):
        with tempfile.TemporaryDirectory() as tmp:
            parts = []
            for name, color in (("a.mp4", "red"), ("b.mp4", "blue")):
                dest = Path(tmp) / name
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-v", "error",
                        "-f", "lavfi", "-i", f"color=c={color}:s=320x180:d=0.4",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
                        "-shortest", dest,
                    ],
                    check=True,
                )
                parts.append(dest)
            out = Path(tmp) / "joined.mp4"
            subprocess.run(
                [sys.executable, str(ROOT / "studio" / "render.py"), "concat", *map(str, parts), "--out", str(out)],
                check=True,
                cwd=ROOT,
            )
            probe = json.loads(subprocess.check_output(
                ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(out)],
                text=True,
            ))
            self.assertGreater(float(probe["format"]["duration"]), 0.7)

    def test_safe_paths_stay_inside_the_repo(self):
        script = ROOT / "tests" / "safe-path.test.mjs"
        subprocess.run(["node", "--test", str(script)], check=True, cwd=ROOT)

    def test_short_render_passes_qc(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "blink.mp4"
            subprocess.run(
                [
                    sys.executable, str(ROOT / "studio" / "render.py"), "final",
                    "tests/fixtures/blink", "--out", str(out),
                ],
                check=True,
                cwd=ROOT,
            )
            self.assertGreater(out.stat().st_size, 1000)
            probe = json.loads(subprocess.check_output(
                ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(out)],
                text=True,
            ))
            video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
            self.assertEqual(video["width"], 320)
            self.assertEqual(video["height"], 180)

    def _rms(self, path):
        with wave.open(str(path), "rb") as handle:
            raw = handle.readframes(handle.getnframes())
        samples = array.array("h")
        samples.frombytes(raw)
        if not samples:
            return 0
        total = sum((sample / 32768) ** 2 for sample in samples)
        return (total / len(samples)) ** 0.5


if __name__ == "__main__":
    unittest.main()

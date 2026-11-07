"""Render a film folder to an MP4, a contact sheet, or a joined cut."""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from audio import build_soundtrack
from qc import check_film, require_tools

ROOT = Path(__file__).resolve().parent.parent
CAPTURE = ROOT / "studio" / "capture.mjs"


def main(argv=None):
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Render a code-made film to MP4")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("draft", "final"):
        command = sub.add_parser(name)
        command.add_argument("project")
        command.add_argument("--out")
    stills = sub.add_parser("stills")
    stills.add_argument("project")
    stills.add_argument("--at", required=True, help="comma-separated times in seconds")
    stills.add_argument("--out")
    joined = sub.add_parser("concat")
    joined.add_argument("parts", nargs="+")
    joined.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    require_tools()
    if args.cmd == "concat":
        concat_films([Path(part) for part in args.parts], Path(args.out))
        print(Path(args.out).resolve())
        return 0
    project, html = resolve_project(Path(args.project))
    if args.cmd == "stills":
        dest = Path(args.out) if args.out else project / "sheet.jpg"
        make_stills(html, args.at, dest)
        print(dest.resolve())
        return 0
    dest = Path(args.out) if args.out else default_out(project, args.cmd)
    render_film(project, html, dest, draft=args.cmd == "draft")
    print(dest.resolve())
    return 0


def resolve_project(path):
    path = path if path.is_absolute() else ROOT / path
    path = path.resolve()
    html = path / "film.html" if path.is_dir() else path
    if html.suffix != ".html" or not html.exists():
        raise SystemExit(f"missing film.html: {html}")
    try:
        html.resolve().relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit("the film must live inside this repository so the renderer can serve it") from exc
    return html.parent, html


def default_out(project, mode):
    if mode == "draft":
        return project / "draft.mp4"
    return project / f"{project.name}.mp4"


def render_film(project, html, dest, draft):
    width, height = declared_size(html)
    params = ""
    crf = "18"
    if draft:
        params = f"w={even(width // 2)}&h={even(height // 2)}"
        crf = "23"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="studio-render-") as tmp:
        picture = Path(tmp) / "picture.mp4"
        capture_video(html, picture, params, crf)
        meta = json.loads(picture.with_suffix(".mp4.json").read_text(encoding="utf-8"))
        wav = Path(tmp) / "mix.wav"
        build_soundtrack(meta, wav, music_file(project, meta))
        mux(picture, wav, dest)
    problems = check_film(dest, meta["duration"])
    if problems:
        raise SystemExit("qc failed: " + "; ".join(problems))
    print(
        f"{meta['title']} · {meta['width']}x{meta['height']} · {meta['duration']}s · {meta['look']}"
    )


def declared_size(html):
    text = html.read_text(encoding="utf-8")
    width = re.search(r"\bwidth\s*:\s*(\d+)", text)
    height = re.search(r"\bheight\s*:\s*(\d+)", text)
    if not width or not height:
        raise SystemExit("film.html needs numeric width and height fields")
    return int(width.group(1)), int(height.group(1))


def even(value):
    value = max(2, int(value))
    return value if value % 2 == 0 else value - 1


def capture_video(html, video, params, crf):
    rel = html.resolve().relative_to(ROOT).as_posix()
    command = ["node", str(CAPTURE), "--url", rel, "--video", str(video), "--crf", crf]
    if params:
        command.extend(["--params", params])
    subprocess.run(command, check=True)


def music_file(project, meta):
    music = meta.get("music") or None
    if not music or not music.get("file"):
        return None
    path = Path(music["file"])
    if not path.is_absolute():
        path = project / path
    if not path.exists():
        raise SystemExit(f"missing music file: {path}")
    return path


def mux(picture, wav, dest):
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(picture), "-i", str(wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(dest),
        ],
        check=True,
    )


def make_stills(html, times, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    rel = html.resolve().relative_to(ROOT).as_posix()
    with tempfile.TemporaryDirectory(prefix="studio-stills-") as tmp:
        subprocess.run(
            ["node", str(CAPTURE), "--url", rel, "--stills", times, "--out", tmp],
            check=True,
        )
        frames = sorted(Path(tmp).glob("*.jpg"))
        if not frames:
            raise SystemExit("no stills were captured")
        if len(frames) == 1:
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", str(frames[0]), "-vf", "scale=-2:360", str(dest)],
                check=True,
            )
            return
        command = ["ffmpeg", "-y", "-v", "error"]
        for frame in frames:
            command.extend(["-i", str(frame)])
        scaled = "".join(f"[{index}]scale=-2:360[s{index}];" for index in range(len(frames)))
        stack = "".join(f"[s{index}]" for index in range(len(frames))) + f"hstack={len(frames)}"
        command.extend(["-filter_complex", scaled + stack, str(dest)])
        subprocess.run(command, check=True)


def concat_films(parts, dest):
    missing = [str(part) for part in parts if not part.exists()]
    if missing:
        raise SystemExit("missing parts: " + ", ".join(missing))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="studio-concat-") as tmp:
        listing = Path(tmp) / "list.txt"
        lines = [f"file '{part.resolve()}'" for part in parts]
        listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-f", "concat", "-safe", "0", "-i", str(listing),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(dest),
            ],
            check=True,
        )


if __name__ == "__main__":
    sys.exit(main())

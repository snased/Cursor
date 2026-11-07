"""Create an empty film folder the renderer can already play."""

import argparse
import json
import sys
from pathlib import Path

from looks import look_names

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "film.html"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start a new film folder")
    parser.add_argument("name", help="folder name, lowercase ascii, for example harbor")
    parser.add_argument("--title", default="")
    parser.add_argument("--mode", choices=("quick", "film"), default="quick")
    parser.add_argument("--purpose", choices=("cinematic", "ad"), default="cinematic")
    parser.add_argument("--look", default="cinematic")
    parser.add_argument("--seconds", type=float, default=8)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    names = look_names()
    if args.look not in names:
        raise SystemExit(f"unknown look {args.look}. choose: {', '.join(names)}")
    if args.seconds <= 0:
        raise SystemExit("--seconds must be positive")
    if args.width < 2 or args.height < 2:
        raise SystemExit("frame size is too small")
    title = args.title.strip() or args.name
    if any(char in title for char in "<>&"):
        raise SystemExit("title cannot contain <, > or &")
    folder = ROOT / "films" / args.name
    html_path = folder / "film.html" if args.mode == "quick" else folder / "chapters" / "01" / "film.html"
    if html_path.exists() and not args.force:
        raise SystemExit(f"{html_path} already exists. pass --force to replace it")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    text = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__TITLE__": json.dumps(title, ensure_ascii=False),
        "__LOOK__": json.dumps(args.look),
        "__PURPOSE__": json.dumps(args.purpose),
        "__WIDTH__": str(args.width),
        "__HEIGHT__": str(args.height),
        "__SECONDS__": str(args.seconds),
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    html_path.write_text(text, encoding="utf-8")
    write_notes(folder, args, title, html_path)
    print(html_path.resolve())
    return 0


def write_notes(folder, args, title, html_path):
    state = folder / "STATE.md"
    if state.exists() and not args.force:
        return
    rel = html_path.relative_to(folder).as_posix()
    state.write_text(
        "\n".join([
            f"# {title}",
            "",
            f"- Mode: {args.mode}",
            f"- Purpose: {args.purpose}",
            f"- Look: {args.look}",
            f"- Format: {args.width}x{args.height}",
            f"- Duration: {args.seconds:g}s",
            "- Phase: plan",
            f"- Picture: {rel}",
            "",
            "## Logline",
            "",
            "(one sentence)",
            "",
            "## Beats",
            "",
            "| t | what the viewer sees change |",
            "|---|---|",
            "| 0.0 | motion already underway |",
            "",
            "## Next",
            "",
            "Show this plan, then two stills, then a draft.",
            "",
        ]),
        encoding="utf-8",
    )
    if args.mode == "film":
        (folder / "ROADMAP.md").write_text(
            "# Roadmap\n\nApprove this before the script.\n\n## Acts\n\n1. \n",
            encoding="utf-8",
        )
        (folder / "SCRIPT.md").write_text(
            "# Script\n\nApprove this before rendering.\n\n## Lines\n\n- \n",
            encoding="utf-8",
        )
    licenses = folder / "LICENSES.csv"
    if not licenses.exists():
        licenses.write_text("file,source,licence,notes\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

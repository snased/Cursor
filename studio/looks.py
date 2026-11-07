"""Look names declared in studio/engine.js. That file is the source of truth."""

import re
from pathlib import Path

ENGINE = Path(__file__).resolve().parent / "engine.js"


def look_names():
    text = ENGINE.read_text(encoding="utf-8")
    start = text.index("const LOOKS = {")
    block = text[start:text.index("\n};", start)]
    found = re.findall(r'^\s{2}(?:"([^"]+)"|([A-Za-z0-9-]+))\s*:', block, re.M)
    names = [quoted or bare for quoted, bare in found]
    if not names:
        raise RuntimeError("no looks found in engine.js")
    return names

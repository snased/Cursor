"""Собрать методику и рабочую карту оценки мастера."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from master_scorecard import build_scorecard
from methodology_document import build_methodology


def main() -> None:
    out = ROOT / "премирование-мастеров"
    handoff = ROOT / "marishka"
    build_methodology(
        out / "Методика премирования мастеров.md",
        out / "Методика премирования мастеров.docx",
    )
    build_scorecard(out / "Карта оценки премии мастера.xlsx")
    build_methodology(
        handoff / "Рабочий протокол разработки системы премирования мастеров.md",
        handoff / "Рабочий протокол разработки системы премирования мастеров.docx",
    )
    build_methodology(
        handoff / "Рабочий протокол разработки системы премирования мастеров.md",
        handoff / "master_bonus_working_protocol.docx",
    )
    print(out)


if __name__ == "__main__":
    main()

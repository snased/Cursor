"""Собрать положение и расчётный файл."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from bonus_document import build_document
from bonus_workbook import build_workbook


def main() -> None:
    out = ROOT / "премирование-мастеров"
    build_document(out / "Критерии премирования мастеров.docx")
    build_workbook(out / "Расчёт премии мастера.xlsx")
    print(out)


if __name__ == "__main__":
    main()

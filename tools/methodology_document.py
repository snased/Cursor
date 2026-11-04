"""Собрать читаемую DOCX-версию методики из Markdown-источника."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x1F, 0x4E, 0x79)
LIGHT_BLUE = "D9EAF7"
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def build_methodology(source: Path, target: Path) -> None:
    document = Document()
    _setup(document)
    lines = source.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            index += 1
            continue
        if line.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            _add_table(document, table_lines)
            continue
        if line.startswith("# "):
            _add_title(document, line[2:])
        elif line.startswith("## "):
            document.add_heading(line[3:], level=1)
        elif line.startswith("### "):
            document.add_heading(line[4:], level=2)
        elif re.match(r"^\d+\. ", line):
            _add_rich_paragraph(document, re.sub(r"^\d+\. ", "", line), "List Number")
        elif line.startswith("- "):
            _add_rich_paragraph(document, line[2:], "List Bullet")
        elif line.startswith("> "):
            paragraph = _add_rich_paragraph(document, line[2:])
            paragraph.paragraph_format.left_indent = Cm(1)
            paragraph.paragraph_format.right_indent = Cm(1)
            paragraph.runs[0].italic = True
            paragraph.runs[0].font.color.rgb = NAVY
        else:
            _add_rich_paragraph(document, line)
        index += 1

    target.parent.mkdir(parents=True, exist_ok=True)
    document.save(target)


def _setup(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.6)
    section.bottom_margin = Cm(1.6)

    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.08
    _font(normal.element.get_or_add_rPr(), "Arial")

    for name, size in (("Heading 1", 14), ("Heading 2", 12)):
        style = document.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = NAVY
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(4)
        _font(style.element.get_or_add_rPr(), "Arial")

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = footer.add_run("Рабочая методика. До утверждения локальным актом не применяется.    Стр. ")
    run.font.name = "Arial"
    run.font.size = Pt(8)
    run.italic = True
    _page_field(footer)


def _font(rpr, name: str) -> None:
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attribute in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attribute), name)


def _page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instruction, end))


def _add_title(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(14)
    run = paragraph.add_run(text.upper())
    run.font.name = "Arial"
    run.font.size = Pt(17)
    run.font.bold = True
    run.font.color.rgb = NAVY


def _add_rich_paragraph(document: Document, text: str, style: str | None = None):
    paragraph = document.add_paragraph(style=style)
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        value = part[2:-2] if bold else part
        run = paragraph.add_run(value)
        run.font.name = "Arial"
        run.font.size = Pt(10.5)
        run.bold = bold
    return paragraph


def _add_table(document: Document, lines: list[str]) -> None:
    parsed = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    if len(parsed) >= 2 and all(re.fullmatch(r":?-{3,}:?", item) for item in parsed[1]):
        parsed.pop(1)
    if not parsed:
        return
    column_count = max(len(row) for row in parsed)
    table = document.add_table(rows=len(parsed), cols=column_count)
    table.style = "Table Grid"
    table.autofit = True
    for row_index, row in enumerate(parsed):
        for column_index in range(column_count):
            value = row[column_index] if column_index < len(row) else ""
            cell = table.cell(row_index, column_index)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(value.replace("**", ""))
            run.font.name = "Arial"
            run.font.size = Pt(8.5)
            if row_index == 0:
                run.font.bold = True
                run.font.color.rgb = WHITE
                _shade(cell, "1F4E79")
            elif row_index % 2 == 0:
                _shade(cell, LIGHT_BLUE)
    document.add_paragraph()


def _shade(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[1]
    folder = repository / "премирование-мастеров"
    build_methodology(
        folder / "Методика премирования мастеров.md",
        folder / "Методика премирования мастеров.docx",
    )

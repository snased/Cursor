from decimal import Decimal
from pathlib import Path
import sys
import zipfile
from xml.etree import ElementTree

import formulas
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from master_scorecard import build_scorecard
from methodology_document import build_methodology


def test_default_month_is_full_and_empty_quarter_is_zero(tmp_path):
    path = tmp_path / "scorecard.xlsx"
    build_scorecard(path)
    solution = _calculate(path)
    assert _number(solution, path, "МЕСЯЦ", "D16") == Decimal("40500")
    assert _number(solution, path, "КВАРТАЛ", "B14") == 0


def test_month_averages_applicable_weeks(tmp_path):
    path = tmp_path / "scorecard.xlsx"
    build_scorecard(path)
    workbook = load_workbook(path)
    weeks = workbook["Недели"]
    # Четыре недели первого месяца. Блок 1: 1 / 1 / 0 / 1.
    for row in range(6, 10):
        weeks[f"B{row}"] = 1
        for column in ("G", "J", "M", "P"):
            weeks[f"{column}{row}"] = 1
    for row, value in zip(range(6, 10), (1, 1, 0, 1)):
        weeks[f"D{row}"] = value
    # Персональные задачи во второй неделе не применялись.
    weeks["J7"] = None
    workbook.save(path)

    solution = _calculate(path)
    assert _number(solution, path, "МЕСЯЦ", "C9") == Decimal("0.75")
    assert _number(solution, path, "МЕСЯЦ", "C11") == 1
    assert _number(solution, path, "МЕСЯЦ", "D16") == Decimal("38250")


def test_quarter_combines_personal_team_and_stretch(tmp_path):
    path = tmp_path / "scorecard.xlsx"
    build_scorecard(path)
    workbook = load_workbook(path)
    weeks = workbook["Недели"]
    for row, value in zip(range(6, 10), (1, 0.75, 0.5, 1)):
        weeks[f"S{row}"] = value
    quarter = workbook["Квартал"]
    quarter["B7"] = 0.75
    quarter["B8"] = 1
    workbook.save(path)

    solution = _calculate(path)
    assert _number(solution, path, "КВАРТАЛ", "B6") == Decimal("0.8125")
    # 35 000 × (60% × 0,8125 + 40% × 0,75) + 15 000.
    assert _number(solution, path, "КВАРТАЛ", "B14") == Decimal("42562.5")


def test_methodology_document_contains_all_blocks(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / "премирование-мастеров" / "Методика премирования мастеров.md"
    target = tmp_path / "methodology.docx"
    build_methodology(source, target)
    with zipfile.ZipFile(target) as archive:
        root_element = ElementTree.fromstring(archive.read("word/document.xml"))
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    text = "".join(node.text or "" for node in root_element.iter(f"{namespace}t"))
    for phrase in (
        "Управление качеством и производственным потоком",
        "Непрерывное совершенствование и проактивность",
        "Персональные задачи",
        "Инструменты бережливого производства",
        "Заполнение документации",
        "Квартальная командная премия",
        "Вопросы, которые необходимо утвердить до запуска",
    ):
        assert phrase in text


def test_working_protocol_preserves_questions_answers_and_decisions(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / "marishka" / "Рабочий протокол разработки системы премирования мастеров.md"
    target = tmp_path / "protocol.docx"
    build_methodology(source, target)
    with zipfile.ZipFile(target) as archive:
        root_element = ElementTree.fromstring(archive.read("word/document.xml"))
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    text = "".join(node.text or "" for node in root_element.iter(f"{namespace}t"))
    for phrase in (
        "Вопрос эксперта",
        "Ответ организации",
        "Подтверждённое понимание",
        "Открытые вопросы",
        "Реестр решений до запуска",
        "Предлагаемая повестка следующей встречи руководителей",
        "Как продолжать работу с документом",
    ):
        assert phrase in text


def _calculate(path: Path):
    model = formulas.ExcelModel().loads(str(path)).finish()
    return model.calculate()


def _number(solution, path: Path, sheet: str, address: str) -> Decimal:
    key = f"'[{path.name}]{sheet}'!{address}"
    value = solution[key].value
    while isinstance(value, (list, tuple)):
        value = value[0]
    if hasattr(value, "flat"):
        value = next(iter(value.flat))
    if hasattr(value, "item"):
        value = value.item()
    return Decimal(str(value))

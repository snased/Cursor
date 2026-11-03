import sys
from decimal import Decimal
from pathlib import Path

import formulas
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from bonus_model import calculate_month, fairness_example
from bonus_workbook import INPUT_KEYS, MONTH, ROW, build_workbook


def test_example_sheet_matches_the_regulation(tmp_path):
    path = tmp_path / "bonus.xlsx"
    build_workbook(path)
    solution = _calculate(path)
    assert _num(solution, path, "Пример", "D11") == Decimal("32703.75")
    assert "сходится" in _text(solution, path, "Пример", "D12")
    assert _num(solution, path, "Пример", "B26") == Decimal("38475")
    assert _num(solution, path, "Пример", "C26") == Decimal("34425")
    assert "сходится" in _text(solution, path, "Пример", "B27")
    assert "сходится" in _text(solution, path, "Пример", "C27")


def test_month_sheet_matches_model_for_external_loss(tmp_path):
    path = tmp_path / "bonus.xlsx"
    build_workbook(path)
    _fill_month(path, _fairness_inputs("Да"))
    solution = _calculate(path)
    expected = fairness_example("Да")
    _near(solution, path, MONTH, _addr("k_plan"), expected["k_plan"])
    _near(solution, path, MONTH, _addr("k1"), expected["k1"])
    _near(solution, path, MONTH, _addr("premium_final"), expected["premium_final"], "0.01")


def test_manual_block_and_scrap_cap(tmp_path):
    path = tmp_path / "bonus.xlsx"
    build_workbook(path)
    data = {
        "mode1": "Вручную",
        "manual1": 1,
        "mode2": "Авто",
        "minor": 0,
        "repeat": 0,
        "critical": "Да",
        "conceal": "Нет",
        "zero_quality": "Нет",
        "fpy": 1,
        "okk": 1,
        "dep_reason": "Нет",
        "dep_pct": 0,
    }
    _fill_month(path, data)
    solution = _calculate(path)
    expected = calculate_month(data)
    _near(solution, path, MONTH, _addr("k1"), Decimal("0.5"))
    _near(solution, path, MONTH, _addr("k_scrap"), Decimal("0"))
    _near(solution, path, MONTH, _addr("premium_final"), expected["premium_final"], "0.01")


def test_checklist_blank_counts_as_no(tmp_path):
    path = tmp_path / "bonus.xlsx"
    build_workbook(path)
    book = load_workbook(path)
    answers = ["Да", "Да", "Нет", "Не применимо", None, "Да"]
    for offset, answer in enumerate(answers):
        book["Чеклисты"].cell(5 + offset, 2, answer)
    book[MONTH]["B47"] = "Чек-лист"
    book.save(path)
    solution = _calculate(path)
    # 3 «Да» из 5 применимых: пустая ячейка остаётся в знаменателе.
    assert _num(solution, path, "Чеклисты", "B12") == Decimal("0.6")


def test_team_bonus_stops_when_multiplier_is_missing(tmp_path):
    path = tmp_path / "bonus.xlsx"
    build_workbook(path)
    book = load_workbook(path)
    book["Командная"]["B6"] = 1
    book["Командная"]["B7"] = 0.75
    book["Командная"]["B8"] = 0.5
    book["Командная"]["B11"] = "Нет"
    book.save(path)
    solution = _calculate(path)
    assert _num(solution, path, "Командная", "B15") == Decimal("23625")

    book = load_workbook(path)
    book["Командная"]["B11"] = "Да"
    book["Командная"]["B12"] = None
    book.save(path)
    solution = _calculate(path)
    assert _num(solution, path, "Командная", "B15") == 0


def _fairness_inputs(confirmed: str) -> dict:
    return {
        "mode1": "Авто",
        "plan": 1000,
        "fact": 850,
        "external": 150,
        "confirmed": confirmed,
        "ontime": 0.9,
        "wip_target": 100,
        "wip_fact": 100,
        "mode2": "Авто",
        "minor": 0,
        "repeat": 0,
        "critical": "Нет",
        "conceal": "Нет",
        "zero_quality": "Нет",
        "fpy": 0.98,
        "okk": 0.9,
        "mode3": "Авто",
        "journals": 0.9,
        "s5": 0.9,
        "walk_source": "Процент",
        "walk_manual": 0.9,
        "mode4": "Авто",
        "matrix": 0.95,
        "train_plan": 4,
        "train_fact": 4,
        "shift": 0.9,
        "mode5": "Авто",
        "task_plan": 5,
        "task_fact": 5,
        "idea_goal": 1,
        "idea_fact": 1,
        "mgmt_source": "Процент",
        "mgmt_manual": 0.9,
        "dep_reason": "Нет",
        "dep_pct": 0,
    }


def _fill_month(path: Path, data: dict) -> None:
    unknown = set(data) - INPUT_KEYS
    if unknown:
        raise AssertionError(f"Нет таких ячеек ввода: {unknown}")
    book = load_workbook(path)
    sheet = book[MONTH]
    for key, value in data.items():
        sheet.cell(ROW[key], 2, value)
    book.save(path)


def _addr(key: str) -> str:
    return f"B{ROW[key]}"


def _calculate(path: Path):
    model = formulas.ExcelModel().loads(str(path)).finish()
    return model.calculate()


def _ref(path: Path, sheet: str, addr: str) -> str:
    return f"'[{path.name}]{sheet.upper()}'!{addr}"


def _raw(solution, path: Path, sheet: str, addr: str):
    key = _ref(path, sheet, addr)
    if key not in solution:
        known = [item for item in solution if sheet.upper() in str(item) and addr in str(item)]
        raise AssertionError(f"Нет {key}. Похожие: {known[:8]}")
    value = solution[key]
    if hasattr(value, "value"):
        value = value.value
    while isinstance(value, (list, tuple)):
        value = value[0]
    if hasattr(value, "flat"):
        value = next(iter(value.flat))
    if hasattr(value, "item") and not isinstance(value, (str, bytes, int, float, Decimal)):
        value = value.item()
    return value


def _num(solution, path: Path, sheet: str, addr: str) -> Decimal:
    value = _raw(solution, path, sheet, addr)
    return Decimal(str(value))


def _near(solution, path: Path, sheet: str, addr: str, expected, tol: str = "0.000001") -> None:
    value = _num(solution, path, sheet, addr)
    assert abs(value - Decimal(expected)) <= Decimal(tol), (addr, value, expected)


def _text(solution, path: Path, sheet: str, addr: str) -> str:
    return str(_raw(solution, path, sheet, addr))

"""Рабочая карта оценки мастера: недели, месяц и квартал."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.page import PageMargins

NAVY = "1F4E79"
BLUE = "D9EAF7"
GREEN = "E2F0D9"
YELLOW = "FFF2CC"
RED = "F4CCCC"
GRAY = "E7E6E6"
WHITE = "FFFFFF"
LINE = "B7B7B7"

BLOCKS = (
    ("Качество и поток", 0.10),
    ("Развитие и проактивность", 0.10),
    ("Персональные задачи", 0.05),
    ("Инструменты БП", 0.10),
    ("Документация", 0.10),
)

MONTH_RULES = (
    "1 — выполнено; проблема своевременно обнаружена и выровнена",
    "1 с комментарием — единичный исправленный недочёт",
    "0 — существенное или повторное нарушение с описанием факта",
    "Пусто — не применимо; значение исключается из среднего",
)

OPEN_QUESTIONS = (
    ("Нормативы очередей и времени без движения по переделам", "ПДО, производство, старший мастер"),
    ("Комплектность и правило межоперационной передачи", "ПДО, склад, ОКК, производство"),
    ("Владелец матрицы компетенций и подтверждение уровня", "Производство, технологи, HR"),
    ("Индивидуальный план развития мастера", "Старший мастер, производство, HR"),
    ("Ресурсы и время на обучение", "Производство, HR"),
    ("Полномочия бригадира", "Начальник производства, старший мастер"),
    ("Расшифровка ПА и стандарт инструмента", "Лидер производственной системы"),
    ("Чек-листы 5С, АО, наставничества и доски", "Лидер БП, старший мастер"),
    ("Место фиксации персональных задач", "Начальник производства, старший мастер"),
    ("Учёт внешней причины срыва персональной задачи", "Комиссия"),
    ("Общий показатель квартала", "Команда мастеров, комиссия"),
    ("Фонд 35 000–50 000 руб. и формула", "Руководство, HR, экономика"),
    ("Правила ночных, переходных и выходных смен", "Старший мастер, производство"),
    ("Пропорция при отпуске и болезни", "HR, экономика"),
)

THIN = Border(
    left=Side(style="thin", color=LINE),
    right=Side(style="thin", color=LINE),
    top=Side(style="thin", color=LINE),
    bottom=Side(style="thin", color=LINE),
)


def build_scorecard(path: Path) -> None:
    workbook = Workbook()
    weeks = workbook.active
    weeks.title = "Недели"
    month = workbook.create_sheet("Месяц")
    quarter = workbook.create_sheet("Квартал")
    guide = workbook.create_sheet("Справочник")
    questions = workbook.create_sheet("Вопросы")
    lists = workbook.create_sheet("Списки")

    _lists(lists)
    _weeks(weeks)
    _month(month)
    _quarter(quarter)
    _guide(guide)
    _questions(questions)
    lists.sheet_state = "hidden"
    workbook.active = weeks
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.properties.title = "Карта оценки премии мастера"
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _setup(ws, widths: dict[str, float], landscape: bool = True) -> None:
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90 if landscape else 105
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins = PageMargins(left=0.35, right=0.35, top=0.5, bottom=0.5)
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    for column, width in widths.items():
        ws.column_dimensions[column].width = width


def _cell(ws, row: int, column: int, value=None, fill: str | None = None, bold: bool = False):
    item = ws.cell(row, column, value)
    item.font = Font(name="Calibri", size=10, bold=bold)
    item.alignment = Alignment(wrap_text=True, vertical="center")
    item.border = THIN
    if fill:
        item.fill = PatternFill("solid", fgColor=fill)
    return item


def _title(ws, text: str, last_column: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_column)
    item = ws.cell(1, 1, text)
    item.font = Font(name="Calibri", size=16, bold=True, color=NAVY)
    item.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 25


def _lists(ws) -> None:
    for row, value in enumerate((0, 1), start=1):
        ws.cell(row, 1, value)
    for row, value in enumerate((0, 0.5, 0.75, 1), start=1):
        ws.cell(row, 2, value)
    for row, value in enumerate((1, 2, 3), start=1):
        ws.cell(row, 3, value)


def _list_validation(ws, address: str, formula: str, allow_blank: bool = True) -> None:
    validation = DataValidation(type="list", formula1=formula, allow_blank=allow_blank)
    validation.error = "Выберите значение из списка"
    validation.errorTitle = "Недопустимое значение"
    validation.add(address)
    ws.add_data_validation(validation)


def _score_colors(ws, address: str) -> None:
    ws.conditional_formatting.add(
        address,
        CellIsRule(operator="equal", formula=["0"], fill=PatternFill("solid", fgColor=RED)),
    )
    ws.conditional_formatting.add(
        address,
        CellIsRule(operator="equal", formula=["1"], fill=PatternFill("solid", fgColor=GREEN)),
    )


def _weeks(ws) -> None:
    widths = {"A": 8, "B": 10}
    for column in ("C", "F", "I", "L", "O", "R"):
        widths[column] = 12
    for column in ("D", "G", "J", "M", "P", "S"):
        widths[column] = 12
    for column in ("E", "H", "K", "N", "Q", "T"):
        widths[column] = 34
    _setup(ws, widths)
    _title(ws, "Еженедельная карта мастера", 20)

    ws.merge_cells("A2:T2")
    ws["A2"] = (
        "Самооценка заполняется до разбора. Итог ставит старший мастер после обсуждения. "
        "0 требует факта; пусто означает Н/П. Жёлтое замечание фиксируется комментарием при итоге 1."
    )
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws["A2"].fill = PatternFill("solid", fgColor=BLUE)
    ws.row_dimensions[2].height = 32

    headers = ["Неделя", "Месяц квартала"]
    for title, _weight in BLOCKS:
        headers.extend((f"{title}\nсамооценка", f"{title}\nитог", "Факт / замечание / действие"))
    headers.extend(("Командность\nсамооценка", "Командность\nитог", "Пример поведения / обратная связь"))

    for column, header in enumerate(headers, start=1):
        item = _cell(ws, 5, column, header, NAVY, True)
        item.font = Font(name="Calibri", size=9, bold=True, color=WHITE)
        item.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[5].height = 52

    for offset in range(13):
        row = 6 + offset
        _cell(ws, row, 1, offset + 1, GRAY)
        _cell(ws, row, 2, None, YELLOW)
        _list_validation(ws, f"B{row}", "='Списки'!$C$1:$C$3")
        for start in (3, 6, 9, 12, 15):
            _cell(ws, row, start, None, YELLOW)
            _cell(ws, row, start + 1, None, YELLOW)
            _cell(ws, row, start + 2, None, YELLOW)
            _list_validation(ws, f"{ws.cell(row, start).coordinate}", "='Списки'!$A$1:$A$2")
            _list_validation(ws, f"{ws.cell(row, start + 1).coordinate}", "='Списки'!$A$1:$A$2")
            _score_colors(ws, f"{ws.cell(row, start + 1).coordinate}")
        _cell(ws, row, 18, None, YELLOW)
        _cell(ws, row, 19, None, YELLOW)
        _cell(ws, row, 20, None, YELLOW)
        _list_validation(ws, f"R{row}", "='Списки'!$B$1:$B$4")
        _list_validation(ws, f"S{row}", "='Списки'!$B$1:$B$4")
        _score_colors(ws, f"S{row}")
        ws.row_dimensions[row].height = 42

    ws.freeze_panes = "C6"
    ws.auto_filter.ref = "A5:T18"
    ws.print_title_rows = "1:5"
    ws.oddFooter.left.text = "Карта мастера — рабочий документ"
    ws.oddFooter.right.text = "Стр. &P"


def _month(ws) -> None:
    _setup(ws, {"A": 42, "B": 18, "C": 20, "D": 22, "E": 54}, False)
    _title(ws, "Расчёт месячной премии", 5)
    _cell(ws, 3, 1, "Мастер", BLUE, True)
    _cell(ws, 3, 2, None, YELLOW)
    _cell(ws, 4, 1, "Оклад, руб.", BLUE, True)
    _cell(ws, 4, 2, 90000, YELLOW)
    ws["B4"].number_format = "#,##0.00"
    _cell(ws, 5, 1, "Месяц квартала", BLUE, True)
    _cell(ws, 5, 2, 1, YELLOW)
    _list_validation(ws, "B5", "='Списки'!$C$1:$C$3", False)

    for column, header in enumerate(("Блок", "Вес", "K месяца", "Сумма, руб.", "Как получен K"), start=1):
        item = _cell(ws, 8, column, header, NAVY, True)
        item.font = Font(name="Calibri", size=10, bold=True, color=WHITE)

    result_columns = ("D", "G", "J", "M", "P")
    for offset, ((title, weight), result_column) in enumerate(zip(BLOCKS, result_columns)):
        row = 9 + offset
        _cell(ws, row, 1, title)
        _cell(ws, row, 2, weight, GRAY)
        ws.cell(row, 2).number_format = "0%"
        formula = (
            f'=IFERROR(AVERAGEIFS(\'Недели\'!${result_column}$6:${result_column}$18,'
            f'\'Недели\'!$B$6:$B$18,$B$5),1)'
        )
        _cell(ws, row, 3, formula, GREEN)
        ws.cell(row, 3).number_format = "0.00"
        _cell(ws, row, 4, f"=ROUND($B$4*B{row}*C{row},2)", GREEN)
        ws.cell(row, 4).number_format = "#,##0.00"
        _cell(
            ws,
            row,
            5,
            "Среднее применимых недель. Пустые недели исключены; если применимых оценок нет, K = 1.",
        )

    _cell(ws, 15, 1, "Максимум", BLUE, True)
    _cell(ws, 15, 2, "=SUM(B9:B13)", GRAY, True)
    ws["B15"].number_format = "0%"
    _cell(ws, 16, 1, "Премия к начислению, руб.", NAVY, True)
    ws["A16"].font = Font(name="Calibri", size=11, bold=True, color=WHITE)
    _cell(ws, 16, 4, "=SUM(D9:D13)", GREEN, True)
    ws["D16"].number_format = "#,##0.00"

    ws.merge_cells("A19:E19")
    ws["A19"] = (
        "0 нельзя ставить без описания факта на листе «Недели». "
        "Н/П не уменьшает премию, потому что мастер не отвечает за отсутствие поручения или не внедрённый инструмент."
    )
    ws["A19"].alignment = Alignment(wrap_text=True)
    ws["A19"].fill = PatternFill("solid", fgColor=YELLOW)
    ws.row_dimensions[19].height = 42


def _quarter(ws) -> None:
    _setup(ws, {"A": 52, "B": 20, "C": 65}, False)
    _title(ws, "Квартальная командная премия", 3)

    rows = (
        (3, "Целевой фонд, руб.", 35000, "Утверждается приказом"),
        (4, "Максимальное усиление, руб.", 15000, "До диапазона 50 000 руб."),
    )
    for row, label, value, note in rows:
        _cell(ws, row, 1, label, BLUE, True)
        _cell(ws, row, 2, value, YELLOW)
        ws.cell(row, 2).number_format = "#,##0.00"
        _cell(ws, row, 3, note)

    _cell(ws, 6, 1, "Личный командный K", BLUE, True)
    _cell(ws, 6, 2, '=IFERROR(AVERAGE(\'Недели\'!S6:S18),0)', GREEN)
    ws["B6"].number_format = "0.00"
    _cell(ws, 6, 3, "Среднее еженедельных итогов 1 / 0,75 / 0,50 / 0; пустые недели исключены.")

    _cell(ws, 7, 1, "Командный K", BLUE, True)
    _cell(ws, 7, 2, None, YELLOW)
    _list_validation(ws, "B7", "='Списки'!$B$1:$B$4", False)
    _cell(ws, 7, 3, "Ставит квартальная комиссия по заранее выбранному общему показателю.")

    _cell(ws, 8, 1, "K усиления", BLUE, True)
    _cell(ws, 8, 2, 0, YELLOW)
    _list_validation(ws, "B8", "='Списки'!$A$1:$A$2", False)
    _cell(ws, 8, 3, "1 только при достижении общей цели и выполнении защитных условий; иначе 0.")

    _cell(ws, 10, 1, "Личная доля целевого фонда", None, True)
    _cell(ws, 10, 2, "=$B$3*60%*B6", GRAY)
    ws["B10"].number_format = "#,##0.00"
    _cell(ws, 11, 1, "Командная доля целевого фонда", None, True)
    _cell(ws, 11, 2, "=$B$3*40%*B7", GRAY)
    ws["B11"].number_format = "#,##0.00"
    _cell(ws, 12, 1, "Усиление", None, True)
    _cell(ws, 12, 2, "=$B$4*B8", GRAY)
    ws["B12"].number_format = "#,##0.00"
    _cell(ws, 14, 1, "Итого за квартал, руб.", NAVY, True)
    ws["A14"].font = Font(name="Calibri", size=11, bold=True, color=WHITE)
    _cell(ws, 14, 2, "=ROUND(SUM(B10:B12),2)", GREEN, True)
    ws["B14"].number_format = "#,##0.00"

    ws.merge_cells("A17:C17")
    ws["A17"] = (
        "Рекомендуемый вариант до утверждения командой. Один исправленный недочёт не обнуляет всю команду. "
        "Сознательный повторный отказ после двух обратных связей обнуляет личную часть нарушителя."
    )
    ws["A17"].alignment = Alignment(wrap_text=True)
    ws["A17"].fill = PatternFill("solid", fgColor=YELLOW)
    ws.row_dimensions[17].height = 45


def _guide(ws) -> None:
    _setup(ws, {"A": 32, "B": 95}, False)
    _title(ws, "Справочник статусов и оснований", 2)
    for column, header in enumerate(("Статус / тема", "Правило"), start=1):
        item = _cell(ws, 3, column, header, NAVY, True)
        item.font = Font(name="Calibri", size=10, bold=True, color=WHITE)

    entries = (
        ("Зелёный — 1", MONTH_RULES[0]),
        ("Жёлтый — 1", MONTH_RULES[1]),
        ("Красный — 0", MONTH_RULES[2]),
        ("Н/П — пусто", MONTH_RULES[3]),
        ("Основание для 0", "Факт, отсутствовавшее обязательное действие, последствие или риск, предыдущая обратная связь при повторе."),
        ("Не является основанием", "Фраза «работал плохо», субъективное впечатление или проблема, которую мастер своевременно обнаружил и выровнял."),
        ("Качество и поток", "Компетенция исполнителя, контроль после пробной детали, быстрая реакция, очереди, НЗП и передача."),
        ("Развитие", "Запросил обучение, применил навык, принял обратную связь, проявил обоснованную инициативу."),
        ("Персональные задачи", "Только задачи сверх обычных обязанностей. Нет задач — Н/П; блок не уменьшается."),
        ("Инструменты БП", "Стандарт есть, состояние видно, отклонение имеет владельца и срок, действие проверено."),
        ("Документация", "Достоверность и возможность продолжить работу важнее формального заполнения."),
        ("Командность", "Общий результат, страхование коллег, межоперационная логистика, единые правила во всём производстве."),
    )
    for row, (topic, rule) in enumerate(entries, start=4):
        _cell(ws, row, 1, topic, BLUE, True)
        _cell(ws, row, 2, rule)
        ws.row_dimensions[row].height = 38


def _questions(ws) -> None:
    _setup(ws, {"A": 7, "B": 72, "C": 48, "D": 18, "E": 34}, False)
    _title(ws, "Решения до запуска", 5)
    for column, header in enumerate(("№", "Вопрос", "Владелец решения", "Срок", "Решение"), start=1):
        item = _cell(ws, 3, column, header, NAVY, True)
        item.font = Font(name="Calibri", size=10, bold=True, color=WHITE)
    for index, (question, owner) in enumerate(OPEN_QUESTIONS, start=1):
        row = 3 + index
        _cell(ws, row, 1, index, GRAY)
        _cell(ws, row, 2, question)
        _cell(ws, row, 3, owner)
        _cell(ws, row, 4, None, YELLOW)
        _cell(ws, row, 5, None, YELLOW)
        ws.row_dimensions[row].height = 40
    ws.freeze_panes = "A4"


if __name__ == "__main__":
    repository = Path(__file__).resolve().parents[1]
    build_scorecard(repository / "премирование-мастеров" / "Карта оценки премии мастера.xlsx")

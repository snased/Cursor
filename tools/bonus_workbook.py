"""Книга расчёта премии. Формулы читают пороги из листа «Параметры» и из модели."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.page import PageMargins

from bonus_model import (
    AUDIT_BANDS,
    DELIVERY_BANDS,
    MANAGEMENT_BANDS,
    MATRIX_BANDS,
    MGMT_ITEMS,
    MONTH_SHARE,
    PLAN_FLOOR,
    SALARY_DEFAULT,
    TASK_FLOOR,
    TEAM_POOL_DEFAULT,
    TRAIN_FLOOR,
    WALK_ITEMS,
    WEIGHTS,
    WIP_TOLERANCE,
)

MONTH = "Месяц"
TEAM = "Командная"
CHECKS = "Чеклисты"
EXAMPLE = "Пример"
PARAMS = "Параметры"
GUIDE = "Как считать"
LISTS = "Списки"
PS = "'Параметры'"
CS = "'Чеклисты'"

NAVY = "1F4E79"
YELLOW = "FFF2CC"
GRAY = "F2F2F2"
GREEN = "E2EFDA"
SECTION = "D6DCE4"
ORANGE = "FCE4D6"
WHITE = "FFFFFF"
LINE = "BFBFBF"

# Строки листа «Чеклисты» зафиксированы: на них ссылается «Месяц».
WALK_FIRST = 5
MGMT_FIRST = 16
WALK_PCT_ROW = 12
MGMT_PCT_ROW = 23

MONTH_ROWS = (
    "title",
    "master",
    "area",
    "period",
    "gap1",
    "h1",
    "mode1",
    "manual1",
    "plan",
    "fact",
    "external",
    "confirmed",
    "controllable",
    "ratio",
    "k_plan",
    "ontime",
    "k_ontime",
    "wip_target",
    "wip_fact",
    "k_wip",
    "k1_raw",
    "k1",
    "gap2",
    "h2",
    "mode2",
    "manual2",
    "minor",
    "repeat",
    "critical",
    "conceal",
    "zero_quality",
    "k_scrap",
    "fpy",
    "k_fpy",
    "okk",
    "k_okk",
    "k2_raw",
    "k2",
    "gap3",
    "h3",
    "mode3",
    "manual3",
    "journals",
    "k_journals",
    "s5",
    "k_s5",
    "walk_source",
    "walk_manual",
    "walk_pct",
    "k_walk",
    "k3_raw",
    "k3",
    "gap4",
    "h4",
    "mode4",
    "manual4",
    "matrix",
    "k_matrix",
    "train_plan",
    "train_fact",
    "k_train",
    "shift",
    "k_shift",
    "k4_raw",
    "k4",
    "gap5",
    "h5",
    "mode5",
    "manual5",
    "task_plan",
    "task_fact",
    "k_task",
    "idea_goal",
    "idea_fact",
    "k_idea",
    "mgmt_source",
    "mgmt_manual",
    "mgmt_pct",
    "k_mgmt",
    "k5_raw",
    "k5",
    "gap6",
    "hdep",
    "dep_reason",
    "dep_pct",
    "dep_applied",
    "gap7",
    "htot",
    "premium_before",
    "premium_cut",
    "premium_final",
    "gap8",
    "hsplit",
    "split_head",
    "line_result",
    "line_quality",
    "line_disc",
    "line_people",
    "line_improve",
    "line_total",
    "gap9",
    "hwarn",
    "warnings",
)

ROW = {key: index for index, key in enumerate(MONTH_ROWS, start=1)}

# Лист «Параметры».
P_SALARY = "$B$3"
P_SHARE = "$B$4"
P_POOL = "$B$5"
P_TEAM = "$B$6"
P_WEIGHTS = {"result": "$C$9", "quality": "$C$10", "discipline": "$C$11", "people": "$C$12", "improve": "$C$13"}
P_WEIGHT_SUM = "$C$14"
P_PLAN_FLOOR = "$B$17"
P_WIP = "$B$18"
P_TASK = "$B$19"
P_TRAIN = "$B$20"

INPUT_KEYS = {
    "master",
    "area",
    "period",
    "mode1",
    "manual1",
    "plan",
    "fact",
    "external",
    "confirmed",
    "ontime",
    "wip_target",
    "wip_fact",
    "mode2",
    "manual2",
    "minor",
    "repeat",
    "critical",
    "conceal",
    "zero_quality",
    "fpy",
    "okk",
    "mode3",
    "manual3",
    "journals",
    "s5",
    "walk_source",
    "walk_manual",
    "mode4",
    "manual4",
    "matrix",
    "train_plan",
    "train_fact",
    "shift",
    "mode5",
    "manual5",
    "task_plan",
    "task_fact",
    "idea_goal",
    "idea_fact",
    "mgmt_source",
    "mgmt_manual",
    "dep_reason",
    "dep_pct",
}

THIN = Border(
    left=Side(style="thin", color=LINE),
    right=Side(style="thin", color=LINE),
    top=Side(style="thin", color=LINE),
    bottom=Side(style="thin", color=LINE),
)


def cell(key: str, column: str = "B") -> str:
    return f"{column}{ROW[key]}"


def pref(key: str, column: str = "B") -> str:
    return f"'{MONTH}'!{cell(key, column)}"


def band_formula(value_cell: str, bands: tuple[tuple[object, object], ...]) -> str:
    expression = "0"
    for threshold, score in reversed(bands):
        expression = f"IF({value_cell}>={threshold},{score},{expression})"
    return expression


def blank_band(value_cell: str, bands: tuple[tuple[object, object], ...]) -> str:
    return f'IF({value_cell}="",0,{band_formula(value_cell, bands)})'


def build_workbook(path: Path) -> None:
    workbook = Workbook()
    workbook.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True)
    guide = workbook.active
    guide.title = GUIDE
    params = workbook.create_sheet(PARAMS)
    month = workbook.create_sheet(MONTH, 0)
    team = workbook.create_sheet(TEAM)
    checks = workbook.create_sheet(CHECKS)
    example = workbook.create_sheet(EXAMPLE)
    lists = workbook.create_sheet(LISTS)

    _lists(lists)
    _params(params)
    _checks(checks)
    _month(month)
    _team(team)
    _example(example)
    _guide(guide)
    lists.sheet_state = "hidden"
    workbook.active = guide
    workbook.properties.title = "Расчёт премии мастера"
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _style_sheet(ws, widths: dict[str, float], landscape: bool = False) -> None:
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_margins = PageMargins(left=0.5, right=0.5, top=0.6, bottom=0.6)
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.oddHeader.left.text = "Премирование мастеров"
    ws.oddFooter.left.text = "Проект. До приказа не применяется"
    ws.oddFooter.right.text = "Стр. &P"
    for column, width in widths.items():
        ws.column_dimensions[column].width = width
    ws.sheet_view.zoomScale = 110


def _put(ws, row: int, column: int, value, fill: str | None, fmt: str | None, bold: bool = False) -> None:
    item = ws.cell(row, column, value)
    item.font = Font(name="Calibri", size=11, bold=bold, color="000000")
    item.alignment = Alignment(wrap_text=True, vertical="center")
    if fill:
        item.fill = PatternFill("solid", fgColor=fill)
    if fmt:
        item.number_format = fmt
    item.border = THIN
    return item


def _lists(ws) -> None:
    columns = {
        "A": ("Да", "Нет"),
        "B": ("Авто", "Вручную"),
        "C": ("Чек-лист", "Процент"),
        "D": ("Нет", "Дисциплина и документация", "Сокрытие и журналы", "Охрана труда"),
        "E": ("Да", "Нет", "Не применимо"),
        "F": (0, 0.25, 0.5, 0.75, 1),
    }
    for column, values in columns.items():
        for index, value in enumerate(values, start=1):
            ws[f"{column}{index}"] = value
    ws.sheet_state = "hidden"


def _validation(ws, address: str, formula: str, kind: str = "list") -> None:
    if kind == "list":
        rule = DataValidation(type="list", formula1=formula, allow_blank=True)
    elif kind == "percent":
        rule = DataValidation(type="decimal", operator="between", formula1="0", formula2="1", allow_blank=True)
    elif kind == "whole":
        rule = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
    else:
        rule = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
    rule.error = "Проверьте значение"
    rule.errorTitle = "Ввод"
    rule.add(address)
    ws.add_data_validation(rule)


def _params(ws) -> None:
    _style_sheet(ws, {"A": 46, "B": 18, "C": 16, "D": 62})
    ws["A1"] = "Параметры расчёта"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=NAVY)
    ws.merge_cells("A1:D1")
    rows = [
        (3, "Оклад, руб.", float(SALARY_DEFAULT), "#,##0.00", "Меняется приказом. При 90 000 месячный пул равен 40 500."),
        (4, "Доля месячной премии", float(MONTH_SHARE), "0%", "45% оклада. Внутри этой доли веса блоков дают 100%."),
        (6, "Пул Team Bonus, руб.", float(TEAM_POOL_DEFAULT), "#,##0.00", "Отдельный пул на квартал или полугодие, не доля месяца."),
    ]
    for row, label, value, fmt, note in rows:
        _put(ws, row, 1, label, SECTION, None, True)
        _put(ws, row, 2, value, YELLOW, fmt)
        _put(ws, row, 4, note, None, None)
    _put(ws, 5, 1, "Пул месячной премии, руб.", SECTION, None, True)
    _put(ws, 5, 2, f"={P_SALARY}*{P_SHARE}", GREEN, "#,##0.00")
    _put(ws, 5, 4, "Считается сам: оклад × доля.", None, None)

    _put(ws, 8, 1, "Веса блоков, целые проценты", SECTION, None, True)
    _put(ws, 8, 3, "Вес", SECTION, None, True)
    for offset, (key, title, weight) in enumerate(WEIGHTS):
        _put(ws, 9 + offset, 1, title, None, None)
        _put(ws, 9 + offset, 3, weight, YELLOW, "0")
        assert P_WEIGHTS[key] == f"$C${9 + offset}"
    _put(ws, 14, 1, "Сумма весов", SECTION, None, True)
    _put(ws, 14, 3, "=SUM(C9:C13)", GREEN, "0")
    _put(ws, 14, 4, '=IF(C14=100,"Сумма 100%.","Сумма весов должна быть 100%.")', None, None)

    _put(ws, 16, 1, "Пороги", SECTION, None, True)
    thresholds = [
        (17, "План: ниже этой доли контролируемого плана k = 0", PLAN_FLOOR, "0%"),
        (18, "НЗП: превышение цели, при котором k = 0", WIP_TOLERANCE, "0%"),
        (19, "Задачи: ниже этой доли закрытых в срок k = 0", TASK_FLOOR, "0%"),
        (20, "Обучение: ниже этой доли k = 0", TRAIN_FLOOR, "0%"),
    ]
    for row, label, value, fmt in thresholds:
        _put(ws, row, 1, label, None, None)
        _put(ws, row, 2, float(value), YELLOW, fmt)
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A3"
    ws.oddHeader.center.text = "Параметры"


def _checks(ws) -> None:
    _style_sheet(ws, {"A": 88, "B": 20, "C": 36}, landscape=True)
    ws["A1"] = "Чек-листы"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=NAVY)
    ws.merge_cells("A1:C1")
    ws["A2"] = (
        "Да — подтверждено. Нет — не сделано. Не применимо — пункт снят до 25-го числа прошлого месяца "
        "и в знаменатель не входит. Пустая ячейка считается как Нет."
    )
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A2:C2")
    ws.row_dimensions[2].height = 32

    def section(title_row: int, items: tuple[str, ...], first: int, pct_row: int) -> None:
        _put(ws, title_row, 1, "Пункт", SECTION, None, True)
        _put(ws, title_row, 2, "Оценка", SECTION, None, True)
        _put(ws, title_row, 3, "Комментарий", SECTION, None, True)
        for offset, text in enumerate(items):
            _put(ws, first + offset, 1, text, None, None)
            _put(ws, first + offset, 2, None, YELLOW, None)
            _put(ws, first + offset, 3, None, YELLOW, None)
            _validation(ws, f"B{first + offset}", f"='{LISTS}'!$E$1:$E$3")
        last = first + len(items) - 1
        count = len(items)
        _put(ws, pct_row - 1, 1, "Применимых пунктов", SECTION, None, True)
        _put(ws, pct_row - 1, 2, f'=IF({count}-COUNTIF(B{first}:B{last},"Не применимо")=0,"",{count}-COUNTIF(B{first}:B{last},"Не применимо"))', GRAY, "0")
        _put(ws, pct_row, 1, "Доля «Да»", SECTION, None, True)
        _put(
            ws,
            pct_row,
            2,
            f'=IF(B{pct_row - 1}="","",COUNTIF(B{first}:B{last},"Да")/B{pct_row - 1})',
            GREEN,
            "0.0%",
        )

    ws["A3"] = "Обход участка — блок «Операционная дисциплина»"
    ws["A3"].font = Font(name="Calibri", size=13, bold=True, color=NAVY)
    section(4, WALK_ITEMS, WALK_FIRST, WALK_PCT_ROW)
    assert WALK_FIRST == 5 and WALK_PCT_ROW == 12

    ws["A14"] = "Управленческие действия — блок «Улучшения и управление»"
    ws["A14"].font = Font(name="Calibri", size=13, bold=True, color=NAVY)
    section(15, MGMT_ITEMS, MGMT_FIRST, MGMT_PCT_ROW)
    assert MGMT_FIRST == 16 and MGMT_PCT_ROW == 23
    ws.row_dimensions[14].height = 18


def _month(ws) -> None:
    _style_sheet(ws, {"A": 62, "B": 22, "C": 18, "D": 18, "E": 18, "F": 54}, landscape=True)
    labels = {
        "title": "Расчёт ежемесячной премии мастера",
        "master": "Мастер",
        "area": "Участок",
        "period": "Месяц",
        "h1": "1. Результат производства",
        "mode1": "Режим блока",
        "manual1": "K1, если режим «Вручную»",
        "plan": "План, нормо-часы",
        "fact": "Факт, нормо-часы",
        "external": "Внешний срыв, нормо-часы",
        "confirmed": "Срыв подтверждён актом и журналом решений",
        "controllable": "Контролируемый план",
        "ratio": "Факт / контролируемый план",
        "k_plan": "k плана",
        "ontime": "Доля заказов в срок",
        "k_ontime": "k срока",
        "wip_target": "Цель НЗП",
        "wip_fact": "Факт НЗП",
        "k_wip": "k НЗП",
        "k1_raw": "K1 по показателям",
        "k1": "K1 к выплате",
        "h2": "2. Качество",
        "mode2": "Режим блока",
        "manual2": "K2, если режим «Вручную»",
        "minor": "Незначительных случаев брака",
        "repeat": "Повторных случаев",
        "critical": "Критический брак",
        "conceal": "Сокрытие дефекта",
        "zero_quality": "Комиссия обнулила блок «Качество»",
        "k_scrap": "k брака",
        "fpy": "Сдача с первого предъявления",
        "k_fpy": "k сдачи с первого предъявления",
        "okk": "Аудит регламента ОКК",
        "k_okk": "k регламента ОКК",
        "k2_raw": "K2 по показателям",
        "k2": "K2 к выплате",
        "h3": "3. Операционная дисциплина",
        "mode3": "Режим блока",
        "manual3": "K3, если режим «Вручную»",
        "journals": "Аудит журналов",
        "k_journals": "k журналов",
        "s5": "Аудит 5С",
        "k_s5": "k 5С",
        "walk_source": "Откуда брать обход",
        "walk_manual": "Доля обхода, если источник «Процент»",
        "walk_pct": "Доля обхода к расчёту",
        "k_walk": "k обхода",
        "k3_raw": "K3 по показателям",
        "k3": "K3 к выплате",
        "h4": "4. Люди и наставничество",
        "mode4": "Режим блока",
        "manual4": "K4, если режим «Вручную»",
        "matrix": "Доля актуальных позиций матрицы",
        "k_matrix": "k матрицы",
        "train_plan": "План обучений и наставничества",
        "train_fact": "Факт обучений и наставничества",
        "k_train": "k обучения",
        "shift": "Аудит передачи смены и стенда",
        "k_shift": "k передачи смены",
        "k4_raw": "K4 по показателям",
        "k4": "K4 к выплате",
        "h5": "5. Улучшения и управление",
        "mode5": "Режим блока",
        "manual5": "K5, если режим «Вручную»",
        "task_plan": "План срочных и дополнительных задач",
        "task_fact": "Закрыто в срок",
        "k_task": "k задач",
        "idea_goal": "Цель внедрённых предложений",
        "idea_fact": "Внедрено с измеримым эффектом",
        "k_idea": "k предложений",
        "mgmt_source": "Откуда брать журнал решений",
        "mgmt_manual": "Доля журнала, если источник «Процент»",
        "mgmt_pct": "Доля журнала к расчёту",
        "k_mgmt": "k управления",
        "k5_raw": "K5 по показателям",
        "k5": "K5 к выплате",
        "hdep": "Депремирование",
        "dep_reason": "Основание",
        "dep_pct": "Запрошенная доля снижения",
        "dep_applied": "Применённая доля",
        "htot": "Итог",
        "premium_before": "Премия до депремирования, руб.",
        "premium_cut": "Сумма депремирования, руб.",
        "premium_final": "Премия к начислению, руб.",
        "hsplit": "Вклад блоков",
        "hwarn": "На что смотреть перед подписью",
        "warnings": "Замечания",
    }
    hints = {
        "master": "Один файл — один мастер за один месяц. Для следующего сохраните копию.",
        "confirmed": "Без «Да» введённые часы срыва из плана не вычитаются.",
        "k_plan": "Ниже порога с листа «Параметры» коэффициент плана равен 0. Выше 100% не поднимается.",
        "k1": "При критическом браке или сокрытии K1 не выше 0,50, в том числе в ручном режиме.",
        "k_scrap": "0 случаев = 1; один незначительный = 0,75; два или повтор = 0,50; критический брак или сокрытие = 0.",
        "zero_quality": "Это решение комиссии, а не автоматический штраф. Пустая ячейка здесь не обнуляет блок.",
        "walk_source": "«Чек-лист» берёт долю с листа «Чеклисты». «Процент» берёт число справа ниже.",
        "k_train": "Нет плана или выполнение ниже порога — коэффициент 0.",
        "k_idea": "Ноль внедрений при ненулевой цели — коэффициент 0. Потолка сверху нет, кроме 1.",
        "k_mgmt": "Ниже 80% коэффициент управления равен 0.",
        "dep_reason": "Критический брак сюда не дублируется: он уже обнулил k брака и ограничил результат.",
        "premium_final": "Team Bonus на этом листе не прибавляется.",
    }
    for key, label in labels.items():
        row = ROW[key]
        if key == "title":
            ws.cell(row, 1, label).font = Font(name="Calibri", size=16, bold=True, color=NAVY)
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            continue
        if key.startswith("h") or key in {"hsplit", "htot", "hdep", "hwarn"}:
            for column in range(1, 7):
                _put(ws, row, column, label if column == 1 else None, NAVY, None, True)
                ws.cell(row, column).font = Font(name="Calibri", size=12, bold=True, color=WHITE)
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            continue
        _put(ws, row, 1, label, None, None)
        if key in hints:
            _put(ws, row, 6, hints[key], None, None)

    def formula(key: str, expression: str, fmt: str, fill: str = GRAY) -> None:
        if not expression.startswith("="):
            expression = "=" + expression
        _put(ws, ROW[key], 2, expression, fill, fmt)

    def entry(key: str, value, fmt: str | None, validation: tuple[str, str] | None = None) -> None:
        _put(ws, ROW[key], 2, value, YELLOW, fmt)
        if validation:
            _validation(ws, cell(key), validation[1], validation[0])

    entry("master", None, None)
    entry("area", None, None)
    entry("period", None, "MMM YYYY")
    for key in ("mode1", "mode2", "mode3", "mode4", "mode5"):
        entry(key, "Авто", None, ("list", f"='{LISTS}'!$B$1:$B$2"))
    for key in ("manual1", "manual2", "manual3", "manual4", "manual5"):
        entry(key, None, "0.00", ("percent", ""))
    entry("plan", None, "#,##0.00", ("decimal", ""))
    entry("fact", None, "#,##0.00", ("decimal", ""))
    entry("external", None, "#,##0.00", ("decimal", ""))
    entry("confirmed", "Нет", None, ("list", f"='{LISTS}'!$A$1:$A$2"))
    formula(
        "controllable",
        f'=IF(OR({cell("plan")}="",{cell("fact")}=""),"",MAX(0,{cell("plan")}-IF(AND({cell("confirmed")}="Да",{cell("external")}<>""),MIN({cell("external")},{cell("plan")}),0)))',
        "#,##0.00",
    )
    formula(
        "ratio",
        f'=IF(OR({cell("controllable")}="",{cell("controllable")}=0),"",{cell("fact")}/{cell("controllable")})',
        "0.0%",
    )
    formula(
        "k_plan",
        (
            f'=IF(OR({cell("plan")}="",{cell("fact")}=""),0,'
            f'IF({cell("plan")}<=0,0,'
            f'IF({cell("controllable")}=0,IF(AND({cell("confirmed")}="Да",{cell("external")}<>"",{cell("external")}>={cell("plan")}),1,0),'
            f'IF({cell("ratio")}<{PS}!{P_PLAN_FLOOR},0,MIN(1,{cell("ratio")})))))'
        ),
        "0.00",
    )
    entry("ontime", None, "0.0%", ("percent", ""))
    formula("k_ontime", blank_band(cell("ontime"), DELIVERY_BANDS), "0.00")
    entry("wip_target", None, "#,##0.00", ("decimal", ""))
    entry("wip_fact", None, "#,##0.00", ("decimal", ""))
    formula(
        "k_wip",
        (
            f'=IF(OR({cell("wip_target")}="",{cell("wip_fact")}=""),0,'
            f'IF(AND({cell("wip_target")}=0,{cell("wip_fact")}=0),1,'
            f'IF({cell("wip_target")}=0,0,'
            f'IF({cell("wip_fact")}<={cell("wip_target")},1,'
            f'IF(({cell("wip_fact")}-{cell("wip_target")})/{cell("wip_target")}>={PS}!{P_WIP},0,'
            f'1-({cell("wip_fact")}-{cell("wip_target")})/{cell("wip_target")}/{PS}!{P_WIP})))))'
        ),
        "0.00",
    )
    formula("k1_raw", f'=({cell("k_plan")}+{cell("k_ontime")}+{cell("k_wip")})/3', "0.0000")
    formula(
        "k1",
        (
            f'=MIN(IF({cell("mode1")}="Вручную",IF({cell("manual1")}="",0,MEDIAN(0,{cell("manual1")},1)),{cell("k1_raw")}),'
            f'IF(OR({cell("critical")}="Да",{cell("conceal")}="Да"),0.5,1))'
        ),
        "0.0000",
        GREEN,
    )

    entry("minor", None, "0", ("whole", ""))
    entry("repeat", None, "0", ("whole", ""))
    entry("critical", "Нет", None, ("list", f"='{LISTS}'!$A$1:$A$2"))
    entry("conceal", "Нет", None, ("list", f"='{LISTS}'!$A$1:$A$2"))
    entry("zero_quality", "Нет", None, ("list", f"='{LISTS}'!$A$1:$A$2"))
    formula(
        "k_scrap",
        (
            f'=IF(OR({cell("minor")}="",{cell("repeat")}="",{cell("critical")}="",{cell("conceal")}=""),0,'
            f'IF(OR({cell("critical")}="Да",{cell("conceal")}="Да"),0,'
            f'IF(OR({cell("repeat")}>=1,{cell("minor")}>=2),0.5,'
            f'IF({cell("minor")}=1,0.75,IF(AND({cell("minor")}=0,{cell("repeat")}=0),1,0)))))'
        ),
        "0.00",
    )
    entry("fpy", None, "0.0%", ("percent", ""))
    formula("k_fpy", blank_band(cell("fpy"), DELIVERY_BANDS), "0.00")
    entry("okk", None, "0.0%", ("percent", ""))
    formula("k_okk", blank_band(cell("okk"), AUDIT_BANDS), "0.00")
    formula("k2_raw", f'=({cell("k_scrap")}+{cell("k_fpy")}+{cell("k_okk")})/3', "0.0000")
    formula(
        "k2",
        (
            f'=IF({cell("zero_quality")}="Да",0,'
            f'IF({cell("mode2")}="Вручную",IF({cell("manual2")}="",0,MEDIAN(0,{cell("manual2")},1)),{cell("k2_raw")}))'
        ),
        "0.0000",
        GREEN,
    )

    entry("journals", None, "0.0%", ("percent", ""))
    formula("k_journals", blank_band(cell("journals"), AUDIT_BANDS), "0.00")
    entry("s5", None, "0.0%", ("percent", ""))
    formula("k_s5", blank_band(cell("s5"), AUDIT_BANDS), "0.00")
    entry("walk_source", "Чек-лист", None, ("list", f"='{LISTS}'!$C$1:$C$2"))
    entry("walk_manual", None, "0.0%", ("percent", ""))
    formula(
        "walk_pct",
        f'=IF({cell("walk_source")}="Процент",IF({cell("walk_manual")}="", "",{cell("walk_manual")}),IF({CS}!B{WALK_PCT_ROW}="", "",{CS}!B{WALK_PCT_ROW}))',
        "0.0%",
    )
    formula("k_walk", blank_band(cell("walk_pct"), AUDIT_BANDS), "0.00")
    formula("k3_raw", f'=({cell("k_journals")}+{cell("k_s5")}+{cell("k_walk")})/3', "0.0000")
    formula(
        "k3",
        f'=IF({cell("mode3")}="Вручную",IF({cell("manual3")}="",0,MEDIAN(0,{cell("manual3")},1)),{cell("k3_raw")})',
        "0.0000",
        GREEN,
    )

    entry("matrix", None, "0.0%", ("percent", ""))
    formula("k_matrix", blank_band(cell("matrix"), MATRIX_BANDS), "0.00")
    entry("train_plan", None, "0.00", ("decimal", ""))
    entry("train_fact", None, "0.00", ("decimal", ""))
    formula(
        "k_train",
        (
            f'=IF(OR({cell("train_plan")}="",{cell("train_fact")}="",{cell("train_plan")}<=0),0,'
            f'IF({cell("train_fact")}/{cell("train_plan")}<{PS}!{P_TRAIN},0,MIN(1,{cell("train_fact")}/{cell("train_plan")})))'
        ),
        "0.00",
    )
    entry("shift", None, "0.0%", ("percent", ""))
    formula("k_shift", blank_band(cell("shift"), AUDIT_BANDS), "0.00")
    formula("k4_raw", f'=({cell("k_matrix")}+{cell("k_train")}+{cell("k_shift")})/3', "0.0000")
    formula(
        "k4",
        f'=IF({cell("mode4")}="Вручную",IF({cell("manual4")}="",0,MEDIAN(0,{cell("manual4")},1)),{cell("k4_raw")})',
        "0.0000",
        GREEN,
    )

    entry("task_plan", None, "0.00", ("decimal", ""))
    entry("task_fact", None, "0.00", ("decimal", ""))
    formula(
        "k_task",
        (
            f'=IF(OR({cell("task_plan")}="",{cell("task_fact")}="",{cell("task_plan")}<=0),0,'
            f'IF({cell("task_fact")}/{cell("task_plan")}<{PS}!{P_TASK},0,MIN(1,{cell("task_fact")}/{cell("task_plan")})))'
        ),
        "0.00",
    )
    entry("idea_goal", None, "0.00", ("decimal", ""))
    entry("idea_fact", None, "0.00", ("decimal", ""))
    formula(
        "k_idea",
        f'=IF(OR({cell("idea_goal")}="",{cell("idea_fact")}="",{cell("idea_goal")}<=0),0,MIN(1,{cell("idea_fact")}/{cell("idea_goal")}))',
        "0.00",
    )
    entry("mgmt_source", "Чек-лист", None, ("list", f"='{LISTS}'!$C$1:$C$2"))
    entry("mgmt_manual", None, "0.0%", ("percent", ""))
    formula(
        "mgmt_pct",
        f'=IF({cell("mgmt_source")}="Процент",IF({cell("mgmt_manual")}="", "",{cell("mgmt_manual")}),IF({CS}!B{MGMT_PCT_ROW}="", "",{CS}!B{MGMT_PCT_ROW}))',
        "0.0%",
    )
    formula("k_mgmt", blank_band(cell("mgmt_pct"), MANAGEMENT_BANDS), "0.00")
    formula("k5_raw", f'=({cell("k_task")}+{cell("k_idea")}+{cell("k_mgmt")})/3', "0.0000")
    formula(
        "k5",
        f'=IF({cell("mode5")}="Вручную",IF({cell("manual5")}="",0,MEDIAN(0,{cell("manual5")},1)),{cell("k5_raw")})',
        "0.0000",
        GREEN,
    )

    entry("dep_reason", "Нет", None, ("list", f"='{LISTS}'!$D$1:$D$4"))
    entry("dep_pct", 0, "0%", ("percent", ""))
    formula(
        "dep_applied",
        (
            f'=IF(OR({cell("dep_reason")}="",{cell("dep_reason")}="Нет"),0,'
            f'MIN(IF({cell("dep_reason")}="Дисциплина и документация",0.25,'
            f'IF({cell("dep_reason")}="Сокрытие и журналы",0.5,'
            f'IF({cell("dep_reason")}="Охрана труда",1,0))),'
            f'MAX(0,IF({cell("dep_pct")}="",0,{cell("dep_pct")}))))'
        ),
        "0%",
    )

    line_keys = ("line_result", "line_quality", "line_disc", "line_people", "line_improve")
    k_keys = ("k1", "k2", "k3", "k4", "k5")
    _put(ws, ROW["split_head"], 1, "Блок", SECTION, None, True)
    _put(ws, ROW["split_head"], 2, "Вес", SECTION, None, True)
    _put(ws, ROW["split_head"], 3, "K блока", SECTION, None, True)
    _put(ws, ROW["split_head"], 4, "Вклад в коэффициент", SECTION, None, True)
    _put(ws, ROW["split_head"], 5, "Рубли до депремирования", SECTION, None, True)
    for key, (weight_key, title, _weight), k_key in zip(line_keys, WEIGHTS, k_keys):
        row = ROW[key]
        _put(ws, row, 1, title, None, None)
        _put(ws, row, 2, f"={PS}!{P_WEIGHTS[weight_key]}/100", GRAY, "0%")
        _put(ws, row, 3, f"={cell(k_key)}", GRAY, "0.0000")
        _put(ws, row, 4, f"=B{row}*C{row}", GRAY, "0.0000")
        _put(ws, row, 5, f"={PS}!{P_POOL}*{PS}!{P_WEIGHTS[weight_key]}*C{row}/100", GRAY, "#,##0.00")
    total = ROW["line_total"]
    first_line = ROW["line_result"]
    last_line = ROW["line_improve"]
    _put(ws, total, 1, "Итого", SECTION, None, True)
    _put(ws, total, 2, f"=SUM(B{first_line}:B{last_line})", GREEN, "0%")
    _put(ws, total, 4, f"=SUM(D{first_line}:D{last_line})", GREEN, "0.0000")
    _put(ws, total, 5, f"=SUM(E{first_line}:E{last_line})", GREEN, "#,##0.00")

    formula("premium_before", f"=E{total}", "#,##0.00", GREEN)
    formula("premium_final", f"=ROUND({cell('premium_before')}*(1-{cell('dep_applied')}),2)", "#,##0.00", GREEN)
    formula("premium_cut", f"={cell('premium_before')}-{cell('premium_final')}", "#,##0.00", ORANGE)

    warning = (
        f'=TRIM('
        f'IF({PS}!{P_WEIGHT_SUM}<>100,"Веса блоков в сумме не 100%. ","")&'
        f'IF(AND({cell("confirmed")}<>"Да",{cell("external")}<>"",{cell("external")}>0),"Внешние часы не исключены: нет подтверждения. ","")&'
        f'IF(OR({cell("critical")}="Да",{cell("conceal")}="Да"),"Брак обнулён, результат не выше 0,50. ","")&'
        f'IF({cell("zero_quality")}="Да","Комиссия обнулила блок качества. ","")&'
        f'IF(AND({cell("dep_reason")}="Сокрытие и журналы",{cell("conceal")}="Да"),"Процент за сокрытие — дополнительное решение, показатель уже ограничен. ","")&'
        f'IF(AND({cell("walk_source")}="Чек-лист",{CS}!B{WALK_PCT_ROW}=""),"Чек-лист обхода без применимых пунктов. ","")&'
        f'IF(AND({cell("mgmt_source")}="Чек-лист",{CS}!B{MGMT_PCT_ROW}=""),"Чек-лист управления без применимых пунктов. ","")&'
        f'IF({cell("dep_pct")}>{cell("dep_applied")},"Запрошенное депремирование срезано до предела основания. ",""))'
    )
    formula("warnings", warning, None, ORANGE)
    ws.row_dimensions[ROW["warnings"]].height = 48
    ws.freeze_panes = "A6"
    ws.print_title_rows = "1:1"
    ws.oddHeader.center.text = '&A'


def _team(ws) -> None:
    _style_sheet(ws, {"A": 62, "B": 20, "C": 70})
    ws["A1"] = "Team Bonus"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=NAVY)
    ws.merge_cells("A1:C1")
    _put(ws, 2, 1, "Мастер", SECTION, None, True)
    _put(ws, 2, 2, f"={pref('master')}", GRAY, None)
    _put(ws, 3, 1, "Период месяца, для справки", SECTION, None, True)
    _put(ws, 3, 2, f"={pref('period')}", GRAY, "MMM YYYY")
    _put(ws, 4, 1, "Пул периода, руб.", SECTION, None, True)
    _put(ws, 4, 2, f"={PS}!{P_TEAM}", GRAY, "#,##0.00")

    labels = (
        (6, "k взаимодополняемости"),
        (7, "k межоперационной логистики"),
        (8, "k единых стандартов"),
    )
    for row, label in labels:
        _put(ws, row, 1, label, None, None)
        _put(ws, row, 2, None, YELLOW, "0.00")
        _validation(ws, f"B{row}", f"='{LISTS}'!$F$1:$F$5")
        _put(ws, row, 3, "Только 0 / 0,25 / 0,50 / 0,75 / 1 и только с фактом.", None, None)
    _put(ws, 9, 1, "Среднее трёх коэффициентов", SECTION, None, True)
    _put(ws, 9, 2, '=IF(OR(B6="",B7="",B8=""),"",(B6+B7+B8)/3)', GRAY, "0.0000")
    _put(ws, 11, 1, "Грубое нарушение охраны труда или сокрытие — решение комиссии", None, None)
    _put(ws, 11, 2, "Нет", YELLOW, None)
    _validation(ws, "B11", f"='{LISTS}'!$A$1:$A$2")
    _put(ws, 12, 1, "Множитель M, если слева стоит «Да» (от 0 до 0,50)", None, None)
    _put(ws, 12, 2, 1, YELLOW, "0.00")
    _validation(ws, "B12", "", "percent")
    _put(ws, 13, 1, "M к расчёту", SECTION, None, True)
    _put(ws, 13, 2, '=IF(B11<>"Да",1,IF(B12="",0,MEDIAN(0,B12,0.5)))', GREEN, "0.00")
    _put(ws, 15, 1, "Team Bonus, руб.", SECTION, None, True)
    _put(ws, 15, 2, f'=IF(B9="",0,ROUND({PS}!{P_TEAM}*B9*B13,2))', GREEN, "#,##0.00")
    _put(
        ws,
        17,
        1,
        "Предупреждение",
        SECTION,
        None,
        True,
    )
    _put(
        ws,
        17,
        2,
        f'=IF({pref("conceal")}="Да","На месячном листе отмечено сокрытие. Зафиксируйте M: либо ограничитель 0–0,50, либо явно 1 в протоколе.","")',
        ORANGE,
        None,
    )
    ws.merge_cells("B17:C17")
    ws["C6"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[17].height = 32


def _example(ws) -> None:
    _style_sheet(ws, {"A": 42, "B": 18, "C": 18, "D": 18, "E": 22, "F": 22, "G": 36}, landscape=True)
    ws["A1"] = "Контрольные примеры"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=NAVY)
    ws.merge_cells("A1:G1")
    ws["A2"] = "Лист ничего не начисляет. Он проверяет, что формулы дают суммы из положения."
    ws.merge_cells("A2:G2")

    ws["A4"] = "Пример 1. Оценки блоков заданы комиссией"
    ws["A4"].font = Font(name="Calibri", size=13, bold=True, color=NAVY)
    headers = ("Блок", "Вес, %", "K", "Рубли")
    for column, header in enumerate(headers, start=1):
        _put(ws, 5, column, header, SECTION, None, True)
    scores = (0.9, 0.8, 1, 0.75, 0.5)
    for index, ((key, title, _weight), score) in enumerate(zip(WEIGHTS, scores)):
        row = 6 + index
        _put(ws, row, 1, title, None, None)
        _put(ws, row, 2, f"={PS}!{P_WEIGHTS[key]}", GRAY, "0")
        _put(ws, row, 3, score, YELLOW, "0.00")
        _put(ws, row, 4, f"={PS}!{P_POOL}*B{row}*C{row}/100", GRAY, "#,##0.00")
    _put(ws, 11, 1, "Итого", SECTION, None, True)
    _put(ws, 11, 2, "=SUM(B6:B10)", GREEN, "0")
    _put(ws, 11, 4, "=SUM(D6:D10)", GREEN, "#,##0.00")
    _put(ws, 12, 1, "Контроль при пуле 40 500", None, None)
    _put(ws, 12, 4, f'=IF(AND(ABS({PS}!B5-40500)<0.01,ABS(D11-32703.75)<0.01),"32 703,75 — сходится","Пул или сумма отличаются от примера положения")', GREEN, None)
    ws.merge_cells("D12:G12")

    ws["A14"] = "Пример 2. Внешний срыв 150 нормо-часов при плане 1 000 и факте 850"
    ws["A14"].font = Font(name="Calibri", size=13, bold=True, color=NAVY)
    ws.merge_cells("A14:G14")
    for column, header in enumerate(("Показатель", "Подтверждён", "Не подтверждён"), start=1):
        _put(ws, 15, column, header, SECTION, None, True)
    _put(ws, 16, 1, "План", None, None)
    _put(ws, 16, 2, 1000, YELLOW, "#,##0.00")
    _put(ws, 16, 3, "=B16", GRAY, "#,##0.00")
    _put(ws, 17, 1, "Факт", None, None)
    _put(ws, 17, 2, 850, YELLOW, "#,##0.00")
    _put(ws, 17, 3, "=B17", GRAY, "#,##0.00")
    _put(ws, 18, 1, "Внешний срыв", None, None)
    _put(ws, 18, 2, 150, YELLOW, "#,##0.00")
    _put(ws, 18, 3, "=B18", GRAY, "#,##0.00")
    _put(ws, 19, 1, "Подтверждение", None, None)
    _put(ws, 19, 2, "Да", YELLOW, None)
    _put(ws, 19, 3, "Нет", YELLOW, None)
    _put(ws, 20, 1, "Доля в срок", None, None)
    _put(ws, 20, 2, 0.9, YELLOW, "0.0%")
    _put(ws, 20, 3, "=B20", GRAY, "0.0%")

    def plan_k(column: str) -> str:
        return (
            f'=IF(OR({column}16="",{column}17=""),0,IF({column}16<=0,0,'
            f'IF(MAX(0,{column}16-IF(AND({column}19="Да",{column}18<>""),MIN({column}18,{column}16),0))=0,'
            f'IF(AND({column}19="Да",{column}18<>"",{column}18>={column}16),1,0),'
            f'IF({column}17/MAX(0,{column}16-IF(AND({column}19="Да",{column}18<>""),MIN({column}18,{column}16),0))<{PS}!{P_PLAN_FLOOR},0,'
            f'MIN(1,{column}17/MAX(0,{column}16-IF(AND({column}19="Да",{column}18<>""),MIN({column}18,{column}16),0)))))))'
        )

    _put(ws, 21, 1, "k плана", None, None)
    _put(ws, 21, 2, plan_k("B"), GRAY, "0.0000")
    _put(ws, 21, 3, plan_k("C"), GRAY, "0.0000")
    _put(ws, 22, 1, "k срока", None, None)
    _put(ws, 22, 2, "=" + blank_band("B20", DELIVERY_BANDS), GRAY, "0.00")
    _put(ws, 22, 3, "=" + blank_band("C20", DELIVERY_BANDS), GRAY, "0.00")
    _put(ws, 23, 1, "k НЗП (в цели)", None, None)
    _put(ws, 23, 2, 1, YELLOW, "0.00")
    _put(ws, 23, 3, "=B23", GRAY, "0.00")
    _put(ws, 24, 1, "K1", None, None)
    _put(ws, 24, 2, "=(B21+B22+B23)/3", GREEN, "0.0000")
    _put(ws, 24, 3, "=(C21+C22+C23)/3", GREEN, "0.0000")
    _put(ws, 25, 1, "K остальных четырёх блоков", None, None)
    _put(ws, 25, 2, 1, YELLOW, "0.00")
    _put(ws, 25, 3, "=B25", GRAY, "0.00")
    _put(ws, 26, 1, "Премия, руб.", None, None)
    _put(
        ws,
        26,
        2,
        f"={PS}!{P_POOL}*('Параметры'!C9*B24+'Параметры'!C10*B25+'Параметры'!C11*B25+'Параметры'!C12*B25+'Параметры'!C13*B25)/100",
        GREEN,
        "#,##0.00",
    )
    _put(
        ws,
        26,
        3,
        f"={PS}!{P_POOL}*('Параметры'!C9*C24+'Параметры'!C10*C25+'Параметры'!C11*C25+'Параметры'!C12*C25+'Параметры'!C13*C25)/100",
        GREEN,
        "#,##0.00",
    )
    _put(ws, 27, 1, "Контроль при пуле 40 500", None, None)
    _put(
        ws,
        27,
        2,
        f'=IF(AND(ABS({PS}!B5-40500)<0.01,ABS(B26-38475)<0.01),"38 475 — сходится","не сходится")',
        GREEN,
        None,
    )
    _put(
        ws,
        27,
        3,
        f'=IF(AND(ABS({PS}!B5-40500)<0.01,ABS(C26-34425)<0.01),"34 425 — сходится","не сходится")',
        GREEN,
        None,
    )
    ws["A29"] = (
        "Разница 4 050 руб. — цена подтверждения. Часы срыва не вычитаются без акта и записи, что мастер сделал дальше. "
        "Остальные блоки в примере закрыты на 1, срок сдан на 90% (k = 0,50), НЗП в цели."
    )
    ws["A29"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A29:G29")
    ws.row_dimensions[29].height = 36


def _guide(ws) -> None:
    _style_sheet(ws, {"A": 110})
    ws["A1"] = "Как считать премию мастера"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color=NAVY)
    lines = [
        "Жёлтые ячейки заполняет человек. Серые и зелёные считаются. Зелёные — коэффициенты к выплате и деньги.",
        "Лист «Параметры». Оклад и пул Team Bonus меняются здесь. Месячный пул равен оклад × 45%. Сумма весов должна остаться 100.",
        "Лист «Месяц» — один мастер и один месяц. Для другого мастера сохраните копию книги и очистите жёлтые ячейки. Переключатели «Да / Нет» и режимы не очищайте в пустоту: пустой переключатель обнуляет связанный коэффициент.",
        "Нормо-часы внешнего срыва вычитаются из плана только если в строке подтверждения стоит «Да»: есть акт и есть запись в журнале решений. Иначе часы остаются в плане.",
        "Доля вводится как процент: 98% или 0,98. Шкалы зашиты в формулы и совпадают с положением.",
        "Чек-листы. Варианты: Да, Нет, Не применимо. Пустой пункт равен «Нет». «Не применимо» не входит в знаменатель и согласуется до 25-го числа предыдущего месяца, а не в день оценки.",
        "Режим «Вручную» подставляет коэффициент блока после калибровки. Ограничитель критического брака и сокрытия всё равно не даёт K1 подняться выше 0,50. Обнуление всего блока «Качество» — отдельное «Да» комиссии, само оно не включается.",
        "Депремирование режет уже посчитанную месячную премию в пределах основания: дисциплина до 25%, сокрытие и журналы до 50%, охрана труда до 100%. Основание «Нет» игнорирует введённый процент. Тот же критический брак вторым процентом не режется.",
        "Лист «Командная» считается отдельно и в месячную сумму не входит. Три коэффициента равны, каждый из шкалы 0 / 0,25 / 0,50 / 0,75 / 1. При «Да» в ограничителе множитель берётся от 0 до 0,50; если его не заполнили, командная премия равна 0.",
        "Лист «Пример» проверяет арифметику положения: 32 703,75 руб. по оценкам блоков и 38 475 против 34 425 руб. в сценарии внешнего срыва. Пока пул 40 500, в контрольных строках написано «сходится».",
        "Порядок месяца: цели до 25-го числа предыдущего месяца, самооценка мастера до 3-го, коэффициенты руководителя до 5-го, калибровка до 7-го, начисление до 10-го. Team Bonus — до 5-го числа после конца периода.",
    ]
    for index, line in enumerate(lines, start=3):
        ws.cell(index, 1, line).alignment = Alignment(wrap_text=True, vertical="center")
        ws.cell(index, 1).font = Font(name="Calibri", size=12)
        ws.row_dimensions[index].height = 36
    ws.row_dimensions[1].height = 24


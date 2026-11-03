"""Положение: критерии премирования мастеров."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from bonus_model import (
    MGMT_ITEMS,
    SALARY_DEFAULT,
    TEAM_POOL_DEFAULT,
    WALK_ITEMS,
    WEIGHTS,
    calibration_example,
    fairness_example,
    month_pool,
    team_bonus,
)

NAVY = RGBColor(0x1F, 0x4E, 0x79)


def rub(value: Decimal) -> str:
    quantized = Decimal(value).quantize(Decimal("0.01"))
    sign = "−" if quantized < 0 else ""
    whole, frac = f"{abs(quantized):,.2f}".split(".")
    whole = whole.replace(",", " ")
    if frac == "00":
        return f"{sign}{whole}"
    return f"{sign}{whole},{frac}"


def build_document(path: Path) -> None:
    pool = month_pool()
    example = calibration_example(pool)
    confirmed = fairness_example("Да", pool)
    unconfirmed = fairness_example("Нет", pool)
    _team_average, _team_m, team_amount = team_bonus(("1", "0.75", "0.5"), "Нет", "1")
    if example["premium_final"] != Decimal("32703.75"):
        raise RuntimeError("Контрольный пример положения разъехался с моделью.")
    if confirmed["premium_final"] != Decimal("38475.00"):
        raise RuntimeError("Пример внешнего срыва разъехался с моделью.")
    if unconfirmed["premium_final"] != Decimal("34425.00"):
        raise RuntimeError("Пример без подтверждения разъехался с моделью.")

    document = Document()
    _setup(document)
    _title(document)
    _intro(document, pool)
    _money(document, pool, team_amount)
    _blocks(document)
    _scale(document, pool)
    _indicators(document)
    _external(document, confirmed, unconfirmed)
    _quality_gate(document)
    _team(document, team_amount)
    _deprem(document)
    _calendar(document)
    _examples(document, example, confirmed, unconfirmed)
    _dont(document)
    _file(document)
    _checklists(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)


def _setup(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(1.7)
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.line_spacing = 1.08
    _font_rpr(normal.element.get_or_add_rPr())
    for style_name, size in (("Heading 1", 14), ("Heading 2", 13)):
        style = document.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = NAVY
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)
        _font_rpr(style.element.get_or_add_rPr())
    footer = section.footer
    footer.is_linked_to_previous = False
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run("Проект. До утверждения приказом не применяется.    ")
    run.font.name = "Times New Roman"
    run.font.size = Pt(9)
    run.italic = True
    _add_page_field(paragraph)


def _font_rpr(rpr) -> None:
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), "Times New Roman")


def _add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    run.font.name = "Times New Roman"
    run.font.size = Pt(9)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)


def _heading(document: Document, text: str, level: int = 1) -> None:
    document.add_heading(text, level=level)


def _p(document: Document, text: str, bold: bool = False) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    paragraph.paragraph_format.line_spacing = 1.08
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)


def _title(document: Document) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("КРИТЕРИИ ПРЕМИРОВАНИЯ МАСТЕРОВ")
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(16)
    run.font.color.rgb = NAVY
    for line in (
        "производственных участков",
        "расчётная модель месячной премии и Team Bonus",
    ):
        sub = document.add_paragraph()
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub.paragraph_format.space_after = Pt(0)
        run = sub.add_run(line)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.italic = True


def _intro(document: Document, pool: Decimal) -> None:
    _heading(document, "1. Для чего эта модель")
    _p(
        document,
        "Премия мастера считается по подтверждённым данным, а не по общему впечатлению в конце месяца. "
        "В месяце пять блоков. У каждого показателя есть формула, источник и порог. Веса — целые проценты, "
        "сумма строго 100%. Командная премия не смешивается с месячной.",
    )
    _p(
        document,
        "Мастер отвечает за то, на что влияет. Срыв из-за металла, поломки уникального станка или ошибки "
        "конструкторской документации не обнуляет премию, если причина подтверждена актом и мастер записал, "
        "что сделал в оставшихся условиях. Выработкой нельзя перекрыть брак: при критическом браке или "
        "сокрытии дефекта блок «Результат» не поднимается выше 0,50.",
    )
    _p(
        document,
        f"Цифры ниже заданы для оклада {rub(SALARY_DEFAULT)} руб. и месячного пула {rub(pool)} руб. "
        "Оклад и пул командной премии меняются на листе «Параметры» расчётного файла. Состав блоков и пороги "
        "меняются только вместе с этим текстом.",
    )


def _money(document: Document, pool: Decimal, team_amount: Decimal) -> None:
    _heading(document, "2. Из чего состоит выплата")
    _table(
        document,
        ["Часть", "Когда", "Максимум", "Как задан"],
        [
            [
                "Месячная премия",
                "каждый месяц",
                f"{rub(pool)} руб.",
                f"45% оклада {rub(SALARY_DEFAULT)} руб. Веса блоков — внутри этого пула",
            ],
            [
                "Team Bonus",
                "квартал или полугодие по приказу",
                f"{rub(TEAM_POOL_DEFAULT)} руб.",
                "отдельный пул, три равных критерия",
            ],
        ],
        [3.4, 4.2, 3.2, 6.2],
    )
    _p(
        document,
        f"Контрольная командная оценка 1 / 0,75 / 0,50 без ограничителя даёт {rub(team_amount)} руб. "
        "В месячную ведомость эта сумма не ставится, пока период не закрыт.",
    )


def _blocks(document: Document) -> None:
    _heading(document, "3. Пять блоков месяца")
    _table(
        document,
        ["Блок", "Вес", "Что защищает", "Источник"],
        [
            ["Результат производства", "30%", "Нормо-часы, срок, НЗП", "MES, 1С, диспетчер, акт на внешний срыв"],
            ["Качество", "25%", "Брак по вине участка, сдача с первого предъявления, регламент ОКК", "ОКК, акты брака"],
            ["Операционная дисциплина", "15%", "Журналы, 5С, обход участка", "Аудиты, чек-лист обхода"],
            ["Люди и наставничество", "15%", "Матрица компетенций, обучение, передача смены", "HR, чек-лист смены"],
            ["Улучшения и управление", "15%", "Задачи в срок, внедрённые предложения, журнал решений", "Реестры, чек-лист управления"],
        ],
        [4.2, 1.6, 6.2, 5.0],
    )
    _p(document, "Сумма весов — 100%. Внутри блока три показателя равны: коэффициент блока — их среднее, а не 33,3%.")
    _p(
        document,
        "Выработка и качество разведены: «сделал много» и «сделал без брака» — разные риски. "
        "Журналы и 5С собраны в одну дисциплину исполнения. Навыки людей и улучшения не дублируют друг друга. "
        "Team Bonus вынесен из месяца, чтобы индивидуальная и командная ответственность не складывались в одну оценку.",
    )


def _scale(document: Document, pool: Decimal) -> None:
    _heading(document, "4. Шкала и формула")
    _table(
        document,
        ["k", "Когда ставится"],
        [
            ["1,00", "Цель достигнута, есть подтверждение"],
            ["0,75", "Незначительное отклонение, оно подтверждено"],
            ["0,50", "Сделано частично"],
            ["0,25", "Фрагментарно, были замечания"],
            ["0,00", "Не сделано, нет подтверждения или грубое нарушение"],
        ],
        [2.5, 14.5],
    )
    _p(document, "Для количественных показателей k считается по формуле из раздела 5, а не «на глаз». Шкала выше — для командных критериев и для ручной оценки блока на калибровке.")
    _p(
        document,
        "K месяца = (30×K1 + 25×K2 + 15×K3 + 15×K4 + 15×K5) / 100. "
        f"Премия = {rub(pool)} × K × (1 − Д), где Д — доля депремирования от 0 до предела основания. "
        "Перевыполнение не поднимает ни один k выше 1 и не увеличивает премию выше пула.",
    )
    _p(document, "K блока = (k первого показателя + k второго + k третьего) / 3.")


def _indicators(document: Document) -> None:
    _heading(document, "5. Показатели")
    _heading(document, "5.1. Результат", 2)
    _p(
        document,
        "План в нормо-часах. Источник — MES или 1С. Контролируемый план = план − внешний срыв. "
        "Срыв вычитается только если стоит подтверждение: акт или служебная записка и запись в журнале решений. "
        "Без записи часы остаются в плане. Срыв больше плана обрезается до плана.",
    )
    _p(
        document,
        "Если после вычитания контролируемый план равен нулю и весь исходный план закрыт подтверждённым срывом, k плана = 1. "
        "Если план нулевой или пустой, k = 0. Иначе выполнение = факт / контролируемый план. "
        "Ниже 90% коэффициент равен 0. От 90% до 100% коэффициент равен выполнению. Выше 100% — единица.",
    )
    _p(
        document,
        "Срок. Доля заказов или позиций ДСЕ, сданных в срок. 98% и выше — 1,00. 95–97,9% — 0,75. "
        "90–94,9% — 0,50. 85–89,9% — 0,25. Ниже 85% — 0.",
    )
    _p(
        document,
        "НЗП. k = 1, если факт не выше цели. k = 0, если факт выше цели на 20% или больше. "
        "Между этими границами k = 1 − (факт − цель) / (0,20 × цель). Цель 0 и факт 0 дают 1. Цель 0 и факт больше нуля дают 0.",
    )
    _heading(document, "5.2. Качество", 2)
    _p(
        document,
        "Брак только по вине участка. Брак материала и ошибка чертежа оформляются актом и в этот показатель не входят; "
        "потерянные из-за них нормо-часы идут во внешний срыв. Нет случаев — 1,00. Один незначительный — 0,75. "
        "Два незначительных или любой повторный — 0,50. Критический брак или сокрытие — 0. Пустая клетка числа случаев — тоже 0: ноль надо вписать явно.",
    )
    _p(document, "Сдача с первого предъявления считается по той же шкале, что и срок: от 98% до порога ниже 85%.")
    _p(document, "Регламент перемещения на ОКК — по аудиту. 90–100% — 1,00. 80–89% — 0,75. 70–79% — 0,50. Ниже 70% — 0. Та же шкала у журналов, 5С и передачи смены.")
    _heading(document, "5.3. Операционная дисциплина", 2)
    _p(document, "Три аудита по шкале 90 / 80 / 70: журналы выработки, приёма и сдачи станков; 5С и порядок на участке; чек-лист обхода начальника цеха. Пункты обхода — в приложении. Число замечаний само по себе баллов не даёт.")
    _heading(document, "5.4. Люди и наставничество", 2)
    _p(
        document,
        "Матрица компетенций: 95% и выше — 1,00; 85–94% — 0,75; 75–84% — 0,50; 60–74% — 0,25; ниже 60% или матрица не ведётся — 0.",
    )
    _p(
        document,
        "Обучение и наставничество: k = факт / план, не выше 1. Ниже 50% или при пустом плане k = 0. "
        "В зачёт идут инструктаж с конкретной темой и закреплённое наставничество. Запись без темы не считается.",
    )
    _p(document, "Передача смены и информационный стенд — чек-лист по шкале аудита 90 / 80 / 70.")
    _heading(document, "5.5. Улучшения и управление", 2)
    _p(document, "Срочные и дополнительные задачи: доля закрытых в срок, не выше 1. Ниже 80% или при пустом реестре k = 0.")
    _p(
        document,
        "Внедрённые предложения: в зачёт идёт предложение этого месяца с измеримым эффектом — часы, брак, простой или инструмент. "
        "Цель по умолчанию — одно внедрение. k = факт / цель, не выше 1. Ноль внедрений даёт 0. Отдельного нижнего порога нет: одно из двух даёт 0,50.",
    )
    _p(
        document,
        "Журнал управленческих решений оценивается долей подтверждённых пунктов чек-листа. 90% и выше — 1,00. "
        "80–89% — 0,75. Ниже 80% — 0. В журнале фиксируется действие: остановка до брака, перераспределение людей, "
        "заявка механику со временем и причиной, задел перед узким местом, группировка переналадок, заявка на заготовки за 24 часа.",
    )


def _external(document: Document, confirmed: dict, unconfirmed: dict) -> None:
    _heading(document, "6. Внешний срыв")
    _p(
        document,
        "Если план сорван по подтверждённой внешней причине, её нормо-часы вычитаются из плана. Остальной объём оценивается как обычно. "
        "Журнал решений при этом показывает, что мастер сделал с оставшимся: перенос заготовки, переписывание программы, инструктаж, сдвиг приоритетов с диспетчером.",
    )
    _p(
        document,
        f"Пример. План 1 000 нормо-часов, подтверждённый срыв 150, факт 850, срок 90%, НЗП в цели, остальные блоки закрыты. "
        f"k плана = 1, k срока = 0,50, k НЗП = 1, K1 — их среднее. Премия = {rub(confirmed['premium_final'])} руб. "
        f"Без акта и записи те же 150 часов не вычитаются, выполнение 85% даёт k плана = 0, премия = {rub(unconfirmed['premium_final'])} руб. "
        f"Разница {rub(confirmed['premium_final'] - unconfirmed['premium_final'])} руб. держится на акте и на записи о действиях мастера.",
    )


def _quality_gate(document: Document) -> None:
    _heading(document, "7. Ограничитель брака и сокрытия")
    _p(
        document,
        "Критический брак или сокрытие дефекта обнуляют показатель брака. Коэффициент блока «Результат» после этого не выше 0,50, "
        "даже если комиссия поставила блок вручную. Остальные показатели качества — сдача с первого предъявления и регламент ОКК — "
        "сами не обнуляются. Весь блок «Качество» комиссия может обнулить отдельным решением. Это решение не включается автоматически.",
    )


def _team(document: Document, team_amount: Decimal) -> None:
    _heading(document, "8. Team Bonus")
    _p(
        document,
        f"Пул {rub(TEAM_POOL_DEFAULT)} руб. за период. Три критерия, вес каждого 1/3. "
        "Коэффициент каждого — только из шкалы 0 / 0,25 / 0,50 / 0,75 / 1,00 и только с фактом.",
    )
    _p(document, "Взаимодополняемость: помощь соседним участкам, подтверждённая диспетчером или служебной запиской.")
    _p(document, "Межоперационная логистика: нет простоев по принципу «это не моя операция». Источник — MES и диспетчер.")
    _p(document, "Единые стандарты: 5С, охрана труда и распорядок держатся на всём участке, без деления «моё / чужое».")
    _p(
        document,
        f"Team Bonus = {rub(TEAM_POOL_DEFAULT)} × (k1 + k2 + k3) / 3 × M. "
        f"При коэффициентах 1, 0,75 и 0,50 и M = 1 сумма равна {rub(team_amount)} руб. "
        "M = 1, пока комиссия не включила ограничитель. При грубом нарушении охраны труда или сокрытии брака комиссия ставит M от 0 до 0,50. "
        "Если ограничитель включён, а множитель не заполнен, выплата равна нулю.",
    )


def _deprem(document: Document) -> None:
    _heading(document, "9. Депремирование")
    _p(document, "Это точечная срезка уже посчитанной месячной премии, а не второй полный расчёт.")
    _table(
        document,
        ["Основание", "Предел срезки"],
        [
            ["Нет основания", "0%. Введённый процент игнорируется"],
            ["Незначительное нарушение дисциплины или документации", "до 25%"],
            ["Сокрытие проблемы на станке, недостоверные журналы", "до 50%"],
            ["Нарушение охраны труда, повторное грубое нарушение", "до 100%"],
        ],
        [12.0, 5.0],
    )
    _p(
        document,
        "Процент выше предела обрезается до предела. Одно событие — одно основание. Нужны письменная формулировка, "
        "ознакомление мастера и три рабочих дня на возражение. Критический брак сюда вторым процентом не копируется: "
        "он уже обнулил показатель брака и ограничил результат. Дополнительный процент за сокрытие комиссия ставит отдельно, если ограничения показателя недостаточно.",
    )


def _calendar(document: Document) -> None:
    _heading(document, "10. Сроки")
    _table(
        document,
        ["Когда", "Кто", "Что делает"],
        [
            ["до 25-го числа предыдущего месяца", "руководитель", "утверждает цели, пороги, источники и пункты «не применимо»"],
            ["каждый день и каждую неделю", "мастер и руководитель", "фиксируют факты, а не вспоминают их в конце месяца"],
            ["до 3-го числа", "мастер", "сдаёт самооценку с подтверждениями"],
            ["до 5-го числа", "руководитель", "ставит коэффициенты"],
            ["до 7-го числа", "производство, HR, ОКК", "калибруют: снимают одинаковые оценки без доказательств"],
            ["до 10-го числа", "бухгалтерия", "начисляет"],
            ["до 5-го числа после конца периода", "комиссия", "закрывает Team Bonus"],
        ],
        [5.5, 4.0, 7.5],
    )
    _p(document, "Руководитель не закрывает месяц один. Ручной коэффициент блока ставится на калибровке и не отменяет ограничитель брака.")


def _examples(document: Document, example: dict, confirmed: dict, unconfirmed: dict) -> None:
    _heading(document, "11. Примеры")
    _p(document, "Пример 1. Комиссия поставила блоки: результат 0,90, качество 0,80, дисциплина 1,00, люди 0,75, улучшения 0,50. Депремирования нет.")
    _table(
        document,
        ["Блок", "Вес", "K", "Вклад", "Рубли"],
        [
            ["Результат", "30%", "0,90", "0,270", rub(example["line_result"])],
            ["Качество", "25%", "0,80", "0,200", rub(example["line_quality"])],
            ["Дисциплина", "15%", "1,00", "0,150", rub(example["line_disc"])],
            ["Люди", "15%", "0,75", "0,1125", rub(example["line_people"])],
            ["Улучшения", "15%", "0,50", "0,075", rub(example["line_improve"])],
            ["Итого", "100%", "0,8075", "0,8075", rub(example["premium_final"])],
        ],
        [3.5, 2.2, 2.4, 2.6, 3.3],
    )
    _p(document, f"Премия = {rub(month_pool())} × 0,8075 = {rub(example['premium_final'])} руб. Team Bonus в эту сумму не входит.")
    _p(
        document,
        f"Пример 2. Подтверждённый внешний срыв из раздела 6 даёт {rub(confirmed['premium_final'])} руб. "
        f"Те же цифры без подтверждения дают {rub(unconfirmed['premium_final'])} руб.",
    )


def _dont(document: Document) -> None:
    _heading(document, "12. Чего не делать")
    for line in (
        "Не дробить месяц на шесть–восемь равных блоков: мастер перестаёт видеть приоритет, руководитель ставит формальные оценки.",
        "Не писать вес 33,3%. Три равные части — это 1/3. Если нужны целые проценты на троих, ставить 33 / 33 / 34.",
        "Не оценивать инициативность без реестра предложений и без измеримого эффекта.",
        "Не задавать норму «поведенческих замечаний». Оценивается обход и реакция, а не число записей.",
        "Не вычитать внешний срыв без акта и без записи, что мастер сделал дальше.",
        "Не платить Team Bonus формулировкой «все молодцы» и не начислять его каждый месяц.",
        "Не давать перевыполнению поднимать премию выше пула: иначе объём начинает выигрывать у качества.",
    ):
        _p(document, line)


def _file(document: Document) -> None:
    _heading(document, "13. Расчётный файл")
    _p(document, "Рядом лежит файл «Расчёт премии мастера.xlsx». Жёлтые ячейки — ввод, остальные считаются.")
    _p(document, "«Параметры» — оклад, доля 45%, пул Team Bonus, веса и пороги. Сумма весов проверяется.")
    _p(document, "«Месяц» — один мастер. Режим «Вручную» подставляет коэффициент блока вместо трёх показателей. Ограничитель брака при этом работает.")
    _p(document, "«Чеклисты» — обход и журнал решений. Пустой пункт равен «Нет». «Не применимо» в знаменатель не входит.")
    _p(document, "«Командная» — три коэффициента и множитель комиссии. В месяц не прибавляется.")
    _p(document, "«Пример» проверяет арифметику этого текста: 32 703,75 руб. и пара 38 475 / 34 425 руб. Пока пул равен 40 500, в контрольных строках написано «сходится».")


def _checklists(document: Document) -> None:
    _heading(document, "14. Чек-листы")
    _p(document, "Обход участка, блок дисциплины. Доля «Да» от применимых пунктов идёт в шкалу аудита.")
    for index, item in enumerate(WALK_ITEMS, start=1):
        _p(document, f"{index}. {item}")
    _p(document, "Журнал управленческих решений, блок улучшений. Ниже 80% коэффициент этого показателя равен нулю.")
    for index, item in enumerate(MGMT_ITEMS, start=1):
        _p(document, f"{index}. {item}")
    _p(
        document,
        "«Не применимо» согласуется до 25-го числа предыдущего месяца. В день оценки так пункт не помечается. "
        f"Веса блоков в этой редакции: {', '.join(str(weight) for _key, _title, weight in WEIGHTS)}.",
    )


def _table(document: Document, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    table = document.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.autofit = False
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = ""
        paragraph = cell.paragraphs[0]
        run = paragraph.add_run(header)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(255, 255, 255)
        _shade(cell, "1F4E79")
    for r_index, row in enumerate(rows, start=1):
        for c_index, value in enumerate(row):
            cell = table.rows[r_index].cells[c_index]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            run = paragraph.add_run(value)
            run.font.name = "Times New Roman"
            run.font.size = Pt(10)
            if r_index % 2 == 0:
                _shade(cell, "F3F6F9")
    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Cm(width)
    document.add_paragraph()


def _shade(cell, color: str) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    shd.set(qn("w:val"), "clear")
    tc_pr.append(shd)

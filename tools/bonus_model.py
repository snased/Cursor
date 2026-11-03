"""Расчёт премии мастера.

Одна модель для положения, книги Excel и проверок. Деньги считаются
в десятичных, чтобы контрольные суммы не расходились на копейку.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping, Optional, Sequence

SALARY_DEFAULT = Decimal("90000")
MONTH_SHARE = Decimal("0.45")
TEAM_POOL_DEFAULT = Decimal("31500")

WEIGHTS: tuple[tuple[str, str, int], ...] = (
    ("result", "Результат производства", 30),
    ("quality", "Качество", 25),
    ("discipline", "Операционная дисциплина", 15),
    ("people", "Люди и наставничество", 15),
    ("improve", "Улучшения и управление", 15),
)

PLAN_FLOOR = Decimal("0.90")
WIP_TOLERANCE = Decimal("0.20")
TASK_FLOOR = Decimal("0.80")
TRAIN_FLOOR = Decimal("0.50")

# Нижняя граница включена. Ниже последней границы коэффициент равен нулю.
DELIVERY_BANDS: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("0.98"), Decimal("1")),
    (Decimal("0.95"), Decimal("0.75")),
    (Decimal("0.90"), Decimal("0.50")),
    (Decimal("0.85"), Decimal("0.25")),
)
AUDIT_BANDS: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("0.90"), Decimal("1")),
    (Decimal("0.80"), Decimal("0.75")),
    (Decimal("0.70"), Decimal("0.50")),
)
MATRIX_BANDS: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("0.95"), Decimal("1")),
    (Decimal("0.85"), Decimal("0.75")),
    (Decimal("0.75"), Decimal("0.50")),
    (Decimal("0.60"), Decimal("0.25")),
)
MANAGEMENT_BANDS: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("0.90"), Decimal("1")),
    (Decimal("0.80"), Decimal("0.75")),
)

DEPREM_CAPS: dict[str, Decimal] = {
    "Нет": Decimal("0"),
    "Дисциплина и документация": Decimal("0.25"),
    "Сокрытие и журналы": Decimal("0.50"),
    "Охрана труда": Decimal("1"),
}

RESULT_CAP = Decimal("0.50")
KOPECK = Decimal("0.01")

WALK_ITEMS = (
    "На рабочих местах открыты актуальный чертёж и операционная карта",
    "В таре с заготовками нет перепутанного материала",
    "СОЖ используется по норме, ёмкости закрыты",
    "На замечания ОТК за прошлую смену есть реакция мастера",
    "Изношенная оснастка изъята или промаркирована до запуска",
    "Замечания по опасным действиям сделаны и зафиксированы",
)
MGMT_ITEMS = (
    "Перед узким местом есть задел или записано, почему в этом месяце он не нужен",
    "Переналадки сгруппированы, график переналадок есть",
    "Заявка на заготовки и тару подана не позднее чем за 24 часа, либо простоя по этой причине не было",
    "Первая деталь серии проверена до запуска партии",
    "Отказ инструмента передан со временем и причиной, а не только фактом остановки",
    "Отклонения разобраны у станка, либо записано, что отклонений не было",
)


def D(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    return value.quantize(KOPECK, rounding=ROUND_HALF_UP)


def month_pool(salary: Decimal = SALARY_DEFAULT, share: Decimal = MONTH_SHARE) -> Decimal:
    return money(salary * share)


def band(value: Optional[object], bands: Sequence[tuple[Decimal, Decimal]]) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    current = D(value)
    for threshold, score in bands:
        if current >= threshold:
            return score
    return Decimal("0")


def k_plan(
    plan: Optional[object],
    fact: Optional[object],
    external: Optional[object],
    confirmed: object,
    floor: Decimal = PLAN_FLOOR,
) -> Decimal:
    if plan is None or plan == "" or fact is None or fact == "":
        return Decimal("0")
    plan_d = D(plan)
    fact_d = D(fact)
    if plan_d <= 0:
        return Decimal("0")
    external_d = D(external) if external not in (None, "") else Decimal("0")
    excluded = min(external_d, plan_d) if confirmed == "Да" else Decimal("0")
    controllable = plan_d - excluded
    if controllable == 0:
        return Decimal("1") if confirmed == "Да" and external_d >= plan_d else Decimal("0")
    ratio = fact_d / controllable
    if ratio < floor:
        return Decimal("0")
    return min(Decimal("1"), ratio)


def k_wip(
    target: Optional[object],
    fact: Optional[object],
    tolerance: Decimal = WIP_TOLERANCE,
) -> Decimal:
    if target is None or target == "" or fact is None or fact == "":
        return Decimal("0")
    target_d = D(target)
    fact_d = D(fact)
    if target_d == 0 and fact_d == 0:
        return Decimal("1")
    if target_d == 0:
        return Decimal("0")
    if fact_d <= target_d:
        return Decimal("1")
    excess = (fact_d - target_d) / target_d
    if excess >= tolerance:
        return Decimal("0")
    return Decimal("1") - excess / tolerance


def k_scrap(
    minor: Optional[object],
    repeat: Optional[object],
    critical: object,
    concealment: object,
) -> Decimal:
    if minor is None or minor == "" or repeat is None or repeat == "":
        return Decimal("0")
    if critical not in ("Да", "Нет") or concealment not in ("Да", "Нет"):
        return Decimal("0")
    if critical == "Да" or concealment == "Да":
        return Decimal("0")
    minor_n = D(minor)
    repeat_n = D(repeat)
    if repeat_n >= 1 or minor_n >= 2:
        return Decimal("0.5")
    if minor_n == 1:
        return Decimal("0.75")
    if minor_n == 0 and repeat_n == 0:
        return Decimal("1")
    return Decimal("0")


def k_ratio(fact: Optional[object], plan: Optional[object], floor: Optional[Decimal]) -> Decimal:
    if fact is None or fact == "" or plan is None or plan == "":
        return Decimal("0")
    plan_d = D(plan)
    if plan_d <= 0:
        return Decimal("0")
    ratio = D(fact) / plan_d
    if floor is not None and ratio < floor:
        return Decimal("0")
    return min(Decimal("1"), ratio)


def checklist_percent(items: Optional[Sequence[object]]) -> Optional[Decimal]:
    if not items:
        return None
    applicable = [item for item in items if item != "Не применимо"]
    if not applicable:
        return None
    yes = sum(1 for item in applicable if item == "Да")
    return Decimal(yes) / Decimal(len(applicable))


def _clamp01(value: Optional[object]) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    current = D(value)
    return min(Decimal("1"), max(Decimal("0"), current))


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values))


def _percent_input(
    source: object,
    manual: Optional[object],
    items: Optional[Sequence[object]],
) -> Optional[Decimal]:
    if source == "Процент":
        if manual is None or manual == "":
            return None
        return D(manual)
    return checklist_percent(items)


def deprem_share(reason: object, requested: Optional[object]) -> Decimal:
    cap = DEPREM_CAPS.get(str(reason), Decimal("0"))
    if cap == 0:
        return Decimal("0")
    if requested is None or requested == "":
        return Decimal("0")
    requested_d = D(requested)
    if requested_d < 0:
        return Decimal("0")
    return min(requested_d, cap)


def team_multiplier(violation: object, requested: Optional[object]) -> Decimal:
    if violation != "Да":
        return Decimal("1")
    if requested is None or requested == "":
        return Decimal("0")
    return min(Decimal("0.5"), max(Decimal("0"), D(requested)))


def team_bonus(
    coefficients: Sequence[Optional[object]],
    violation: object,
    requested_multiplier: Optional[object],
    pool: Decimal = TEAM_POOL_DEFAULT,
) -> tuple[Decimal, Decimal, Decimal]:
    if any(value is None or value == "" for value in coefficients):
        return Decimal("0"), team_multiplier(violation, requested_multiplier), Decimal("0")
    average = _mean([_clamp01(value) for value in coefficients])
    multiplier = team_multiplier(violation, requested_multiplier)
    return average, multiplier, money(pool * average * multiplier)


def calculate_month(
    data: Mapping[str, object],
    pool: Decimal | None = None,
) -> dict[str, Decimal]:
    """Полный месяц одного мастера. Пустые факты дают коэффициент 0."""

    critical = data.get("critical", "Нет")
    concealment = data.get("conceal", "Нет")
    hard_limit = critical == "Да" or concealment == "Да"

    k_plan_value = k_plan(
        data.get("plan"),
        data.get("fact"),
        data.get("external"),
        data.get("confirmed", "Нет"),
    )
    k_ontime = band(data.get("ontime"), DELIVERY_BANDS)
    k_wip_value = k_wip(data.get("wip_target"), data.get("wip_fact"))
    k1_raw = _mean([k_plan_value, k_ontime, k_wip_value])
    k1 = _clamp01(data.get("manual1")) if data.get("mode1") == "Вручную" else k1_raw
    if hard_limit:
        k1 = min(k1, RESULT_CAP)

    k_scrap_value = k_scrap(
        data.get("minor"),
        data.get("repeat"),
        critical,
        concealment,
    )
    k_fpy = band(data.get("fpy"), DELIVERY_BANDS)
    k_okk = band(data.get("okk"), AUDIT_BANDS)
    k2_raw = _mean([k_scrap_value, k_fpy, k_okk])
    k2 = _clamp01(data.get("manual2")) if data.get("mode2") == "Вручную" else k2_raw
    if data.get("zero_quality") == "Да":
        k2 = Decimal("0")

    k_journals = band(data.get("journals"), AUDIT_BANDS)
    k_s5 = band(data.get("s5"), AUDIT_BANDS)
    walk = _percent_input(data.get("walk_source", "Процент"), data.get("walk_manual"), data.get("walk_items"))  # type: ignore[arg-type]
    k_walk = band(walk, AUDIT_BANDS)
    k3_raw = _mean([k_journals, k_s5, k_walk])
    k3 = _clamp01(data.get("manual3")) if data.get("mode3") == "Вручную" else k3_raw

    k_matrix = band(data.get("matrix"), MATRIX_BANDS)
    k_train = k_ratio(data.get("train_fact"), data.get("train_plan"), TRAIN_FLOOR)
    k_shift = band(data.get("shift"), AUDIT_BANDS)
    k4_raw = _mean([k_matrix, k_train, k_shift])
    k4 = _clamp01(data.get("manual4")) if data.get("mode4") == "Вручную" else k4_raw

    k_task = k_ratio(data.get("task_fact"), data.get("task_plan"), TASK_FLOOR)
    k_idea = k_ratio(data.get("idea_fact"), data.get("idea_goal"), None)
    managed = _percent_input(
        data.get("mgmt_source", "Процент"),
        data.get("mgmt_manual"),
        data.get("mgmt_items"),  # type: ignore[arg-type]
    )
    k_mgmt = band(managed, MANAGEMENT_BANDS)
    k5_raw = _mean([k_task, k_idea, k_mgmt])
    k5 = _clamp01(data.get("manual5")) if data.get("mode5") == "Вручную" else k5_raw

    coefficients = {
        "result": k1,
        "quality": k2,
        "discipline": k3,
        "people": k4,
        "improve": k5,
    }
    active_pool = month_pool() if pool is None else pool
    lines = []
    for key, _title, weight in WEIGHTS:
        lines.append(active_pool * Decimal(weight) * coefficients[key] / Decimal(100))
    before = sum(lines, Decimal("0"))
    share = deprem_share(data.get("dep_reason", "Нет"), data.get("dep_pct"))
    final = money(before * (Decimal("1") - share))
    before_money = money(before)
    return {
        "k_plan": k_plan_value,
        "k_ontime": k_ontime,
        "k_wip": k_wip_value,
        "k1_raw": k1_raw,
        "k1": k1,
        "k_scrap": k_scrap_value,
        "k_fpy": k_fpy,
        "k_okk": k_okk,
        "k2": k2,
        "k_journals": k_journals,
        "k_s5": k_s5,
        "k_walk": k_walk,
        "k3": k3,
        "k_matrix": k_matrix,
        "k_train": k_train,
        "k_shift": k_shift,
        "k4": k4,
        "k_task": k_task,
        "k_idea": k_idea,
        "k_mgmt": k_mgmt,
        "k5": k5,
        "premium_before": before_money,
        "deprem_share": share,
        "premium_cut": before_money - final,
        "premium_final": final,
        "line_result": money(lines[0]),
        "line_quality": money(lines[1]),
        "line_disc": money(lines[2]),
        "line_people": money(lines[3]),
        "line_improve": money(lines[4]),
    }


def calibration_example(pool: Decimal | None = None) -> dict[str, Decimal]:
    """Оценки блоков из примера: 0,90 / 0,80 / 1,00 / 0,75 / 0,50."""

    return calculate_month(
        {
            "mode1": "Вручную",
            "manual1": "0.9",
            "mode2": "Вручную",
            "manual2": "0.8",
            "mode3": "Вручную",
            "manual3": "1",
            "mode4": "Вручную",
            "manual4": "0.75",
            "mode5": "Вручную",
            "manual5": "0.5",
            "critical": "Нет",
            "conceal": "Нет",
            "zero_quality": "Нет",
            "dep_reason": "Нет",
        },
        pool=pool,
    )


def fairness_example(confirmed: str, pool: Decimal | None = None) -> dict[str, Decimal]:
    """План 1000, внешний срыв 150, факт 850, срок 90%, остальное закрыто."""

    data: dict[str, object] = {
        "mode1": "Авто",
        "plan": "1000",
        "fact": "850",
        "external": "150",
        "confirmed": confirmed,
        "ontime": "0.90",
        "wip_target": "100",
        "wip_fact": "100",
        "mode2": "Авто",
        "minor": "0",
        "repeat": "0",
        "critical": "Нет",
        "conceal": "Нет",
        "zero_quality": "Нет",
        "fpy": "0.98",
        "okk": "0.90",
        "mode3": "Авто",
        "journals": "0.90",
        "s5": "0.90",
        "walk_source": "Процент",
        "walk_manual": "0.90",
        "mode4": "Авто",
        "matrix": "0.95",
        "train_plan": "4",
        "train_fact": "4",
        "shift": "0.90",
        "mode5": "Авто",
        "task_plan": "5",
        "task_fact": "5",
        "idea_goal": "1",
        "idea_fact": "1",
        "mgmt_source": "Процент",
        "mgmt_manual": "0.90",
        "dep_reason": "Нет",
    }
    return calculate_month(data, pool=pool)

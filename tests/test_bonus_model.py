import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from bonus_model import (
    calculate_month,
    calibration_example,
    checklist_percent,
    deprem_share,
    fairness_example,
    k_plan,
    k_ratio,
    k_scrap,
    k_wip,
    month_pool,
    team_bonus,
)


def test_pool_and_calibration():
    assert month_pool() == Decimal("40500.00")
    example = calibration_example()
    assert example["k1"] == Decimal("0.9")
    assert example["premium_final"] == Decimal("32703.75")
    assert (
        example["line_result"]
        + example["line_quality"]
        + example["line_disc"]
        + example["line_people"]
        + example["line_improve"]
        == example["premium_final"]
    )


def test_plan_thresholds():
    assert k_plan(1000, 899, 0, "Нет") == 0
    assert k_plan(1000, 900, 0, "Нет") == Decimal("0.9")
    assert k_plan(1000, 1100, 0, "Нет") == 1
    assert k_plan(1000, 850, 150, "Да") == 1
    assert k_plan(1000, 850, 150, "Нет") == 0
    assert k_plan(1000, 700, 150, "Да") == 0
    assert k_plan(1000, 765, 150, "Да") == Decimal("0.9")
    assert k_plan(1000, 0, 1000, "Да") == 1
    assert k_plan(1000, 0, 5000, "Да") == 1
    assert k_plan(0, 0, 0, "Нет") == 0
    assert k_plan(None, 10, 0, "Нет") == 0


def test_wip_scrap_and_ratios():
    assert k_wip(100, 100) == 1
    assert k_wip(100, 110) == Decimal("0.5")
    assert k_wip(100, 120) == 0
    assert k_wip(100, 90) == 1
    assert k_wip(0, 0) == 1
    assert k_wip(0, 5) == 0
    assert k_scrap(0, 0, "Нет", "Нет") == 1
    assert k_scrap(1, 0, "Нет", "Нет") == Decimal("0.75")
    assert k_scrap(2, 0, "Нет", "Нет") == Decimal("0.5")
    assert k_scrap(0, 1, "Нет", "Нет") == Decimal("0.5")
    assert k_scrap(0, 0, "Да", "Нет") == 0
    assert k_scrap(0, 0, "Нет", "Да") == 0
    assert k_scrap(None, 0, "Нет", "Нет") == 0
    assert k_ratio(8, 10, Decimal("0.8")) == Decimal("0.8")
    assert k_ratio(7, 10, Decimal("0.8")) == 0
    assert k_ratio(0, 0, Decimal("0.8")) == 0
    assert k_ratio(2, 1, None) == 1
    assert k_ratio(0, 1, None) == 0


def test_critical_cap_survives_manual_score():
    result = calculate_month(
        {
            "mode1": "Вручную",
            "manual1": "1",
            "critical": "Да",
            "conceal": "Нет",
            "mode2": "Авто",
            "minor": "0",
            "repeat": "0",
            "fpy": "1",
            "okk": "1",
            "zero_quality": "Нет",
            "dep_reason": "Нет",
        }
    )
    assert result["k1"] == Decimal("0.5")
    assert result["k_scrap"] == 0
    assert result["k2"] > 0


def test_commission_can_zero_quality_without_a_second_percent():
    result = calculate_month(
        {
            "mode2": "Вручную",
            "manual2": "1",
            "zero_quality": "Да",
            "critical": "Нет",
            "conceal": "Нет",
            "dep_reason": "Нет",
            "dep_pct": "0.25",
        }
    )
    assert result["k2"] == 0
    assert result["deprem_share"] == 0


def test_deprem_is_capped_and_ignored_without_reason():
    assert deprem_share("Нет", "0.5") == 0
    assert deprem_share("Дисциплина и документация", "0.4") == Decimal("0.25")
    assert deprem_share("Охрана труда", "1") == 1
    cut = calculate_month({"mode1": "Вручную", "manual1": "1", "mode2": "Вручную", "manual2": "1", "mode3": "Вручную", "manual3": "1", "mode4": "Вручную", "manual4": "1", "mode5": "Вручную", "manual5": "1", "critical": "Нет", "conceal": "Нет", "dep_reason": "Дисциплина и документация", "dep_pct": "0.25"})
    assert cut["premium_before"] == Decimal("40500.00")
    assert cut["premium_final"] == Decimal("30375.00")


def test_fairness_pair_and_checklist():
    assert fairness_example("Да")["premium_final"] == Decimal("38475.00")
    assert fairness_example("Нет")["premium_final"] == Decimal("34425.00")
    assert checklist_percent(["Да", "Нет", "Не применимо", None]) == Decimal("1") / Decimal("3")
    assert checklist_percent(["Не применимо"]) is None


def test_team_bonus_does_not_pay_itself():
    average, multiplier, amount = team_bonus(("1", "0.75", "0.5"), "Нет", None)
    assert average == Decimal("0.75")
    assert multiplier == 1
    assert amount == Decimal("23625.00")
    average, multiplier, amount = team_bonus(("1", "1", "1"), "Да", None)
    assert amount == 0
    assert multiplier == 0
    _average, multiplier, amount = team_bonus(("1", "1", "1"), "Да", "0.5")
    assert multiplier == Decimal("0.5")
    assert amount == Decimal("15750.00")
    assert team_bonus((None, "1", "1"), "Нет", "1")[2] == 0

"""Carb and insulin math helpers with AU defaults."""

AU_PRE_MEAL_RANGE = (4.0, 8.0)
AU_POST_MEAL_RANGE = (5.0, 10.0)
AU_HYPO_THRESHOLD = 4.0
AU_HYPER_THRESHOLD = 10.0


def mgdl_to_mmoll(mgdl: float) -> float:
    return mgdl / 18


def mmoll_to_mgdl(mmoll: float) -> float:
    return mmoll * 18


def carb_exchanges(carbs_g: float) -> float:
    return carbs_g / 15


def default_targets() -> dict:
    return {
        "pre_meal_range_mmol_l": AU_PRE_MEAL_RANGE,
        "post_meal_range_mmol_l": AU_POST_MEAL_RANGE,
        "hypo_threshold_mmol_l": AU_HYPO_THRESHOLD,
        "hyper_threshold_mmol_l": AU_HYPER_THRESHOLD,
    }


def bolus_calc(
    icr: float,
    isf: float,
    target_bg: float,
    current_bg: float | None,
    carbs_g: float,
    iob: float = 0,
) -> dict:
    meal = carbs_g / icr
    corr = (current_bg - target_bg) / isf if current_bg is not None else 0
    total = meal + corr - iob

    warnings: list[str] = []
    if current_bg is not None:
        if current_bg < AU_HYPO_THRESHOLD:
            warnings.append("Current glucose is below the hypo threshold (<4.0 mmol/L).")
        if current_bg > AU_HYPER_THRESHOLD:
            warnings.append("Current glucose is above the hyper threshold (>10.0 mmol/L).")

    return {
        "meal_bolus": meal,
        "correction": corr,
        "total": total,
        "warnings": warnings,
        "default_targets": default_targets(),
        "medical_disclaimer": (
            "This is a calculator output. Confirm bolus decisions with your diabetes care team."
        ),
    }

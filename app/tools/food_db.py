"""Food database utilities with AFCD mock and USDA fallback."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FoodMacros:
    name: str
    carbs_per_g: float
    protein_per_g: float
    fat_per_g: float
    calories_per_g: float
    source: str


AFCD_MOCK_PER_100G = {
    "white rice cooked": {"carbs": 28.2, "protein": 2.7, "fat": 0.3, "calories": 130},
    "brown rice cooked": {"carbs": 23.0, "protein": 2.6, "fat": 0.9, "calories": 112},
    "pasta cooked": {"carbs": 30.7, "protein": 5.8, "fat": 0.9, "calories": 158},
    "bread": {"carbs": 49.0, "protein": 9.0, "fat": 3.2, "calories": 265},
    "chicken breast cooked": {"carbs": 0.0, "protein": 31.0, "fat": 3.6, "calories": 165},
    "salmon cooked": {"carbs": 0.0, "protein": 25.4, "fat": 13.0, "calories": 208},
    "apple": {"carbs": 13.8, "protein": 0.3, "fat": 0.2, "calories": 52},
    "banana": {"carbs": 22.8, "protein": 1.1, "fat": 0.3, "calories": 96},
    "milk whole": {"carbs": 4.8, "protein": 3.2, "fat": 3.3, "calories": 61},
    "oatmeal cooked": {"carbs": 12.0, "protein": 2.4, "fat": 1.4, "calories": 71},
    "yogurt plain": {"carbs": 4.7, "protein": 3.5, "fat": 3.3, "calories": 61},
    "potato baked": {"carbs": 20.1, "protein": 2.5, "fat": 0.1, "calories": 93},
    "pizza": {"carbs": 28.0, "protein": 11.0, "fat": 10.0, "calories": 266},
    "burger": {"carbs": 30.0, "protein": 17.0, "fat": 12.0, "calories": 250},
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("-", " ").split())


def _per_g(value_per_100g: float) -> float:
    return value_per_100g / 100.0


def _afcd_lookup(name: str) -> Optional[FoodMacros]:
    normalized = _normalize(name)
    for key, macros in AFCD_MOCK_PER_100G.items():
        if key in normalized:
            return FoodMacros(
                name=key,
                carbs_per_g=_per_g(macros["carbs"]),
                protein_per_g=_per_g(macros["protein"]),
                fat_per_g=_per_g(macros["fat"]),
                calories_per_g=_per_g(macros["calories"]),
                source="afcd_mock",
            )
    return None


def _usda_lookup(name: str) -> Optional[FoodMacros]:
    api_key = os.getenv("USDA_FDC_API_KEY")
    if not api_key:
        return None

    try:
        response = requests.get(
            "https://api.nal.usda.gov/fdc/v1/foods/search",
            params={"query": name, "pageSize": 1, "api_key": api_key},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("USDA lookup failed: %s", exc)
        return None

    foods = data.get("foods") or []
    if not foods:
        return None

    food = foods[0]
    nutrients = {n.get("nutrientName"): n.get("value") for n in food.get("foodNutrients", [])}

    carbs = nutrients.get("Carbohydrate, by difference") or nutrients.get(
        "Carbohydrate, by difference, NLEA"
    )
    protein = nutrients.get("Protein")
    fat = nutrients.get("Total lipid (fat)")
    calories = nutrients.get("Energy")

    def safe(value: Optional[float]) -> float:
        return float(value) if value is not None else 0.0

    return FoodMacros(
        name=food.get("description", name),
        carbs_per_g=_per_g(safe(carbs)),
        protein_per_g=_per_g(safe(protein)),
        fat_per_g=_per_g(safe(fat)),
        calories_per_g=_per_g(safe(calories)),
        source="usda_fdc",
    )


def lookup_food(name: str) -> Optional[FoodMacros]:
    return _afcd_lookup(name) or _usda_lookup(name)


def carb_exchanges(carbs_g: float) -> float:
    return carbs_g / 15.0


def macros_for_item(name: str, grams: float) -> dict:
    macros = lookup_food(name)
    if macros is None:
        macros = FoodMacros(
            name=name,
            carbs_per_g=0.1,
            protein_per_g=0.02,
            fat_per_g=0.02,
            calories_per_g=0.9,
            source="heuristic",
        )

    carbs_g = grams * macros.carbs_per_g
    protein_g = grams * macros.protein_per_g
    fat_g = grams * macros.fat_per_g
    calories = grams * macros.calories_per_g

    return {
        "carbs_g": carbs_g,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "calories": calories,
        "source": macros.source,
        "carbs_per_g": macros.carbs_per_g,
    }

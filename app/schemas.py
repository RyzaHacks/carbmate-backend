"""Pydantic models for CarbMate API."""

from __future__ import annotations

from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, ConfigDict


class PortionGuess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grams: int = Field(..., ge=0)
    range_grams: Tuple[int, int] = Field(..., min_length=2, max_length=2)


class MealEstimateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_guess: str
    portion_guess: PortionGuess
    confidence: float = Field(..., ge=0, le=1)
    notes: str


class MealEstimateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[MealEstimateItem]
    assumptions: List[str]


class MealEstimatePhotoItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    food: str
    grams: float = Field(..., ge=0)
    carbs: float = Field(..., gt=0)
    exchanges: float = Field(..., gt=0)
    confidence: float = Field(..., gt=0.1, le=1)
    notes: str


class MealEstimatePhotoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[MealEstimatePhotoItem]
    # Minimal schema: items only


class DietCompanionMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class DietCompanionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    history: Optional[List[DietCompanionMessage]] = None


class DietCompanionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
    suggested_prompts: List[str]
    mode: str


class MealConfirmItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    grams: float = Field(..., ge=0)
    carbs_g: Optional[float] = Field(default=None, ge=0)
    protein_g: Optional[float] = Field(default=None, ge=0)
    fat_g: Optional[float] = Field(default=None, ge=0)
    calories: Optional[float] = Field(default=None, ge=0)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    notes: Optional[str] = None
    range_grams: Optional[Tuple[int, int]] = None


class MealConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_text: Optional[str] = None
    source: Optional[str] = None
    items: List[MealConfirmItem] = Field(..., min_length=1)


class MealStoredItem(MealConfirmItem):
    id: int
    meal_id: int


class MealTotals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carbs_g: float
    protein_g: float
    fat_g: float
    calories: float
    carb_exchanges: float


class MealConfirmResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_id: int
    created_at: str
    totals: MealTotals
    items: List[MealStoredItem]


class MealHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_id: int
    created_at: str
    totals: MealTotals
    items: List[MealStoredItem]


class MealHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meals: List[MealHistoryItem]


class BolusCalcRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icr: float = Field(..., gt=0)
    isf: float = Field(..., gt=0)
    target_bg: float = Field(..., gt=0)
    current_bg: Optional[float] = Field(default=None, gt=0)
    carbs_g: float = Field(..., ge=0)
    iob: float = Field(default=0, ge=0)
    bg_unit: Literal["mg/dL", "mmol/L"] = "mmol/L"


class DefaultTargets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pre_meal_range_mmol_l: Tuple[float, float]
    post_meal_range_mmol_l: Tuple[float, float]
    hypo_threshold_mmol_l: float
    hyper_threshold_mmol_l: float


class BolusCalcResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_bolus: float
    correction: float
    total: float
    warnings: List[str]
    default_targets: DefaultTargets
    medical_disclaimer: str
    bg_unit: Literal["mg/dL", "mmol/L"]

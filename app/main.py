"""CarbMate FastAPI backend."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .agents.diet_companion_agent import DietCompanionAgent
from .agents.meal_vision_agent import MealVisionAgent
from .db import fetch_meals, init_db, insert_meal
from .schemas import (
    BolusCalcRequest,
    BolusCalcResponse,
    DietCompanionRequest,
    DietCompanionResponse,
    MealEstimatePhotoResponse,
    MealConfirmItem,
    MealConfirmRequest,
    MealConfirmResponse,
    MealEstimateResponse,
    MealHistoryResponse,
    MealTotals,
)
from .tools.food_db import carb_exchanges, macros_for_item
from .tools.t1d_math import bolus_calc, mgdl_to_mmoll

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("carbmate")

app = FastAPI(title="CarbMate API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

vision_agent = MealVisionAgent()
diet_companion_agent = DietCompanionAgent()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/v1/meals/estimate", response_model=MealEstimateResponse)
async def estimate_meal(
    images: List[UploadFile] = File(...),
    text: Optional[str] = Form(default=None),
) -> MealEstimateResponse:
    if not (1 <= len(images) <= 4):
        raise HTTPException(status_code=400, detail="Upload 1 to 4 images.")

    image_payloads = []
    for image in images:
        content = await image.read()
        if not content:
            raise HTTPException(status_code=400, detail="One or more images were empty.")
        image_payloads.append((content, image.content_type))

    try:
        payload = vision_agent.estimate(image_payloads, text)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return MealEstimateResponse(**payload)


@app.post("/v1/meals/estimate-photo", response_model=MealEstimatePhotoResponse)
async def estimate_meal_photo(
    images: List[UploadFile] = File(...),
    text: Optional[str] = Form(default=None),
    portion_count: Optional[int] = Form(default=None),
    portion_weight_g: Optional[float] = Form(default=None),
) -> MealEstimatePhotoResponse:
    if not (1 <= len(images) <= 4):
        raise HTTPException(status_code=400, detail="Upload 1 to 4 images.")

    image_payloads = []
    for image in images:
        content = await image.read()
        if not content:
            raise HTTPException(status_code=400, detail="One or more images were empty.")
        image_payloads.append((content, image.content_type))

    context_parts = []
    if portion_count is not None:
        context_parts.append(f"Detected count: {portion_count}.")
    if portion_weight_g is not None:
        context_parts.append(f"Total portion weight: {portion_weight_g} g.")
    if context_parts:
        text = (text + " " if text else "") + " ".join(context_parts)

    try:
        payload = vision_agent.estimate_photo(image_payloads, text)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        return MealEstimatePhotoResponse(**payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Invalid vision response schema.") from exc


@app.post("/v1/diet/companion", response_model=DietCompanionResponse)
async def diet_companion(request: DietCompanionRequest) -> DietCompanionResponse:
    try:
        payload = diet_companion_agent.chat(
            message=request.message,
            history=[entry.model_dump() for entry in request.history] if request.history else None,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DietCompanionResponse(**payload)


@app.post("/v1/meals/confirm", response_model=MealConfirmResponse)
def confirm_meal(request: MealConfirmRequest) -> MealConfirmResponse:
    computed_items: List[MealConfirmItem] = []
    for item in request.items:
        macros = None
        if item.carbs_g is None or item.protein_g is None or item.fat_g is None or item.calories is None:
            macros = macros_for_item(item.name, item.grams)

        computed_items.append(
            MealConfirmItem(
                name=item.name,
                grams=item.grams,
                carbs_g=item.carbs_g if item.carbs_g is not None else macros["carbs_g"],
                protein_g=item.protein_g if item.protein_g is not None else macros["protein_g"],
                fat_g=item.fat_g if item.fat_g is not None else macros["fat_g"],
                calories=item.calories if item.calories is not None else macros["calories"],
                confidence=item.confidence,
                notes=item.notes,
                range_grams=item.range_grams,
            )
        )

    total_carbs = sum(item.carbs_g or 0 for item in computed_items)
    total_protein = sum(item.protein_g or 0 for item in computed_items)
    total_fat = sum(item.fat_g or 0 for item in computed_items)
    total_calories = sum(item.calories or 0 for item in computed_items)

    totals = MealTotals(
        carbs_g=round(total_carbs, 2),
        protein_g=round(total_protein, 2),
        fat_g=round(total_fat, 2),
        calories=round(total_calories, 2),
        carb_exchanges=round(carb_exchanges(total_carbs), 2),
    )

    return insert_meal(
        user_text=request.user_text,
        source=request.source,
        items=computed_items,
        totals=totals,
    )


@app.get("/v1/meals/history", response_model=MealHistoryResponse)
def meal_history(limit: int = 20, offset: int = 0) -> MealHistoryResponse:
    return fetch_meals(limit=limit, offset=offset)


@app.post("/v1/bolus/calc", response_model=BolusCalcResponse)
def bolus_calc_endpoint(request: BolusCalcRequest) -> BolusCalcResponse:
    if request.bg_unit == "mg/dL":
        isf = mgdl_to_mmoll(request.isf)
        target_bg = mgdl_to_mmoll(request.target_bg)
        current_bg = mgdl_to_mmoll(request.current_bg) if request.current_bg is not None else None
    else:
        isf = request.isf
        target_bg = request.target_bg
        current_bg = request.current_bg

    result = bolus_calc(
        icr=request.icr,
        isf=isf,
        target_bg=target_bg,
        current_bg=current_bg,
        carbs_g=request.carbs_g,
        iob=request.iob,
    )

    return BolusCalcResponse(bg_unit=request.bg_unit, **result)

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Iterable, Optional, Sequence, Tuple

from mistralai import Mistral

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are MealVisionAgent. Analyze food images using pixel-based volume and mass approximation. "
    "Return ONLY strict JSON with visible foods, estimated grams, estimated carbs, confidence, and notes. "
    "Be as accurate as possible using object scale inference from bowls, plates, utensils, hands, or packaging. "
    "Do NOT use external nutrition databases, recipe assumptions, or invented medical claims. "
    "1 diabetes exchange = 15g carbs (AU standard)."
    "include brand information"
)

PHOTO_SCHEMA_INSTRUCTIONS = (
    "{\"items\":[{\"food\":str,\"grams\":number,\"carbs\":number,"
    "\"confidence\":number,\"notes\":str,\"brand\":str}]}"
)

class MealVisionAgent:
    """Mistral vision wrapper for carb estimation."""

    def __init__(self, model: Optional[str] = None) -> None:
        self.api_key = os.getenv("MISTRAL_API_KEY")
        self.client = Mistral(api_key=self.api_key) if self.api_key else None
        self.model = model or os.getenv("MISTRAL_VISION_MODEL", "pixtral-large-latest")

    @staticmethod
    def _image_to_data_url(image_bytes: bytes, mime_type: Optional[str]) -> str:
        mime = mime_type or "image/jpeg"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime};base64,{b64}"

    @staticmethod
    def _parse_json(content: str) -> dict[str, object]:
        return json.loads(content)

    @staticmethod
    def _sanitize_items(payload: dict[str, object]) -> dict[str, object]:
        if "items" not in payload or not isinstance(payload["items"], list):
            raise ValueError("Invalid vision response schema.")

        cleaned = []
        for item in payload["items"]:
            if not isinstance(item, dict):
                raise ValueError("Invalid vision response schema.")

            # Make sure core keys exist but DO NOT fail on missing brand
            food = item.get("food") or item.get("name_guess") or "unknown"
            grams = float(item.get("grams", 0))
            carbs = float(item.get("carbs", 0))
            confidence = float(item.get("confidence", 0.2))
            notes = item.get("notes", "")

            # Compute exchanges safely
            exchanges = carbs / 15.0 if carbs > 0 else 0.0

            cleaned.append({
                "food": str(food),
                "grams": grams,
                "carbs": carbs,
                "exchanges": exchanges,
                "confidence": confidence,
                "notes": str(notes),
            })

        return {"items": cleaned}

    def estimate_photo(self, images: Iterable[Tuple[bytes, Optional[str]]], user_text: Optional[str] = None) -> dict[str, object]:
        if not self.client:
            raise RuntimeError("MISTRAL_API_KEY is not set.")

        image_list = list(images)
        image_urls = [self._image_to_data_url(img, mime) for img, mime in image_list]

        user_content = [
            {"type": "text", "text": f"Return JSON exactly matching this schema:\n{PHOTO_SCHEMA_INSTRUCTIONS}"},
        ]
        if user_text:
            user_content.append({"type": "text", "text": f"User notes: {user_text}"})

        for url in image_urls:
            user_content.append({"type": "image_url", "image_url": {"url": url}})

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        response = self.client.chat.complete(
            model=self.model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        payload = self._parse_json(content)
        return self._sanitize_items(payload)

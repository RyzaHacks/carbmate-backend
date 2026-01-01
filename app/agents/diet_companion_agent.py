"""Diet companion agent wrapper."""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable, Optional

from mistralai import Mistral

logger = logging.getLogger(__name__)

DIET_COMPANION_SYSTEM_PROMPT = (
    "You are CarbMate Diet Companion, a supportive food and nutrition coach. "
    "Help with daily goals, food logging, meal ideas, progress summaries, and restaurant suggestions. "
    "Keep responses concise, practical, and friendly. Avoid medical advice or dosing guidance. "
    "Return ONLY strict JSON with this schema: "
    "{\"reply\":string,\"suggested_prompts\":[string],\"mode\":string}. "
    "Rules: no markdown, suggested_prompts must be 2 to 5 short items, "
    "mode must be one of: goals, log, recommend, progress, restaurant, general."
)

DEFAULT_PROMPTS = [
    "Set my goals for today",
    "Log my breakfast",
    "Recommend dinner ideas",
    "Show my daily progress",
]


class DietCompanionAgent:
    def __init__(self, model: Optional[str] = None) -> None:
        self.api_key = os.getenv("MISTRAL_API_KEY")
        self.client = Mistral(api_key=self.api_key) if self.api_key else None
        self.model = model or os.getenv("MISTRAL_DIET_MODEL", "mistral-medium-2505")

    @staticmethod
    def _parse_json(content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end > start:
                return json.loads(content[start : end + 1])
            raise

    @staticmethod
    def _sanitize_prompts(prompts: Iterable[str]) -> list[str]:
        cleaned = []
        for prompt in prompts:
            text = str(prompt).strip()
            if text:
                cleaned.append(text)
        return cleaned[:5]

    def chat(self, message: str, history: Optional[list[dict]]) -> dict:
        if not self.client:
            raise RuntimeError("MISTRAL_API_KEY is not set.")

        messages: list[dict] = [{"role": "system", "content": DIET_COMPANION_SYSTEM_PROMPT}]
        if history:
            for entry in history:
                role = entry.get("role")
                content = entry.get("content")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": str(content)})
        messages.append({"role": "user", "content": message})

        response = self.client.chat.complete(
            model=self.model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        payload = self._parse_json(content)
        if not isinstance(payload, dict):
            raise ValueError("Invalid diet companion payload format.")

        reply = str(payload.get("reply", "")).strip()
        if not reply:
            raise ValueError("Invalid diet companion payload format.")

        prompts = payload.get("suggested_prompts", [])
        if not isinstance(prompts, list):
            prompts = []
        prompts = self._sanitize_prompts(prompts)
        if len(prompts) < 2:
            prompts = DEFAULT_PROMPTS

        mode = str(payload.get("mode", "general")).strip() or "general"
        if mode not in {"goals", "log", "recommend", "progress", "restaurant", "general"}:
            mode = "general"

        return {"reply": reply, "suggested_prompts": prompts, "mode": mode}

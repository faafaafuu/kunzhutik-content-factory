from __future__ import annotations

import base64
import json
import logging
import time

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.providers.vision.base import VisionProvider
from app.providers.vision.schemas import VisionAnalysisResult

logger = logging.getLogger(__name__)

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
SUPPORTED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class OpenRouterVisionProvider(VisionProvider):
    provider_name = "openrouter-vision-v1"

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        context: dict | None = None,
    ) -> VisionAnalysisResult:
        if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
            raise ValueError(f"Unsupported image type for OpenRouter vision: {mime_type}")
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")
        if not settings.openrouter_vision_model:
            raise ValueError("OPENROUTER_VISION_MODEL is not configured")

        started_at = time.perf_counter()
        response_payload = self._call_openrouter(image_bytes=image_bytes, mime_type=mime_type)
        duration_ms = round((time.perf_counter() - started_at) * 1000)
        parsed = _parse_response_json(response_payload)

        try:
            result = VisionAnalysisResult.model_validate(
                {
                    **parsed,
                    "raw_response": {
                        "provider": self.provider_name,
                        "model": settings.openrouter_vision_model,
                        "duration_ms": duration_ms,
                        "response_id": response_payload.get("id"),
                        "parsed": parsed,
                    },
                }
            )
        except ValidationError:
            logger.exception(
                "OpenRouter vision response validation failed",
                extra={"provider": self.provider_name, "model": settings.openrouter_vision_model, "duration_ms": duration_ms},
            )
            raise

        logger.info(
            "Vision provider completed",
            extra={"provider": self.provider_name, "model": settings.openrouter_vision_model, "duration_ms": duration_ms},
        )
        return result

    def _call_openrouter(self, *, image_bytes: bytes, mime_type: str) -> dict:
        image_data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}"
        payload = {
            "model": settings.openrouter_vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _vision_prompt()},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.app_base_url,
            "X-Title": settings.app_name,
        }
        with httpx.Client(timeout=settings.openrouter_timeout_seconds) as client:
            response = client.post(OPENROUTER_CHAT_COMPLETIONS_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()


def _vision_prompt() -> str:
    return (
        "Проанализируй фото блюда для food-контента. Верни только JSON без markdown. "
        "Язык: русский. Поля: dish_name, likely_ingredients, plating, mood, "
        "visual_features, quality_score, warnings. "
        "quality_score должен быть числом от 0 до 1. "
        "Не выдумывай точный состав, если ингредиент визуально неочевиден."
    )


def _parse_response_json(response_payload: dict) -> dict:
    choices = response_payload.get("choices") or []
    if not choices:
        raise ValueError("OpenRouter response did not include choices")
    content = choices[0].get("message", {}).get("content")
    if isinstance(content, list):
        content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenRouter response did not include message content")
    return json.loads(_strip_json_fences(content.strip()))


def _strip_json_fences(content: str) -> str:
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return content

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.models.upload import Upload
from app.services.storage import download_bytes
from shared.enums import AssetKind

logger = logging.getLogger(__name__)

SUPPORTED_OPENAI_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@dataclass(frozen=True)
class VisionAnalysisPayload:
    provider: str
    dish_name: str | None
    ingredients: list[str]
    visual_mood: str | None
    plating_style: str | None
    features_json: dict
    raw_payload: dict

    def model_payload(self) -> dict:
        return {
            "provider": self.provider,
            "dish_name": self.dish_name,
            "ingredients": self.ingredients,
            "visual_mood": self.visual_mood,
            "plating_style": self.plating_style,
            "features_json": self.features_json,
            "raw_payload": self.raw_payload,
        }


class VisionAnalyzer:
    provider_name = "base"

    def analyze_upload(self, upload: Upload) -> VisionAnalysisPayload:
        raise NotImplementedError


class MockVisionAnalyzer(VisionAnalyzer):
    provider_name = "mock-vision-v1"

    def analyze_upload(self, upload: Upload) -> VisionAnalysisPayload:
        return VisionAnalysisPayload(
            provider=self.provider_name,
            dish_name="Авторское блюдо дня",
            ingredients=["кунжут", "соус", "свежая зелень"],
            visual_mood="аппетитный и тёплый",
            plating_style="аккуратная ресторанная подача",
            features_json={
                "lighting": "soft warm",
                "camera_angle": "close-up",
                "hero_element": "texture",
            },
            raw_payload={
                "note": "Mock analysis fallback. Configure VISION_ANALYSIS_PROVIDER=openai and OPENAI_API_KEY for real vision."
            },
        )


class OpenAIVisionAnalyzer(VisionAnalyzer):
    provider_name = "openai-vision-responses-v1"

    def analyze_upload(self, upload: Upload) -> VisionAnalysisPayload:
        source_asset = next((asset for asset in upload.media_assets if asset.kind == AssetKind.source_photo), None)
        if not source_asset:
            raise ValueError("Upload has no source photo asset")
        if source_asset.mime_type not in SUPPORTED_OPENAI_MIME_TYPES:
            raise ValueError(f"Unsupported image type for OpenAI vision: {source_asset.mime_type}")
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        image_bytes = download_bytes(source_asset.storage_key)
        data_url = f"data:{source_asset.mime_type};base64,{base64.b64encode(image_bytes).decode()}"
        response = self._call_openai(data_url)
        parsed = _extract_json_payload(response)
        return VisionAnalysisPayload(
            provider=self.provider_name,
            dish_name=parsed.get("dish_name"),
            ingredients=[str(item) for item in parsed.get("ingredients", [])][:12],
            visual_mood=parsed.get("visual_mood"),
            plating_style=parsed.get("plating_style"),
            features_json={
                "composition": parsed.get("composition", ""),
                "lighting": parsed.get("lighting", ""),
                "camera_angle": parsed.get("camera_angle", ""),
                "hero_element": parsed.get("hero_element", ""),
                "colors": parsed.get("colors", []),
                "content_warnings": parsed.get("content_warnings", []),
                "confidence": parsed.get("confidence", 0),
            },
            raw_payload={
                "provider_response_id": response.get("id"),
                "model": settings.openai_vision_model,
                "source_asset_id": str(source_asset.id),
                "parsed": parsed,
            },
        )

    def _call_openai(self, image_data_url: str) -> dict:
        prompt = (
            "Проанализируй фото блюда для ресторанного контент-пайплайна. "
            "Верни только JSON по схеме: название блюда, вероятные ингредиенты, настроение кадра, "
            "стиль подачи, композицию, свет, ракурс, главный визуальный элемент, цвета, предупреждения и confidence. "
            "Не выдумывай точный состав, если он визуально неочевиден."
        )
        payload = {
            "model": settings.openai_vision_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": image_data_url, "detail": settings.openai_vision_detail},
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "dish_visual_analysis",
                    "strict": True,
                    "schema": _analysis_schema(),
                }
            },
            "max_output_tokens": settings.openai_vision_max_output_tokens,
        }
        with httpx.Client(timeout=settings.openai_vision_timeout_seconds) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()


def analyze_upload_with_configured_provider(upload: Upload) -> VisionAnalysisPayload:
    provider = settings.vision_analysis_provider.lower().strip()
    analyzer: VisionAnalyzer = OpenAIVisionAnalyzer() if provider == "openai" else MockVisionAnalyzer()
    try:
        return analyzer.analyze_upload(upload)
    except Exception as exc:
        if provider != "mock":
            logger.exception("Vision analysis provider %s failed; falling back to mock", provider)
        fallback = MockVisionAnalyzer().analyze_upload(upload)
        fallback.raw_payload["fallback_reason"] = str(exc)
        fallback.raw_payload["requested_provider"] = provider
        return fallback


def _extract_json_payload(response: dict) -> dict:
    if response.get("output_text"):
        return json.loads(response["output_text"])
    for output in response.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return json.loads(content["text"])
    raise ValueError("OpenAI response did not include output JSON")


def _analysis_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "dish_name": {"type": "string"},
            "ingredients": {"type": "array", "items": {"type": "string"}},
            "visual_mood": {"type": "string"},
            "plating_style": {"type": "string"},
            "composition": {"type": "string"},
            "lighting": {"type": "string"},
            "camera_angle": {"type": "string"},
            "hero_element": {"type": "string"},
            "colors": {"type": "array", "items": {"type": "string"}},
            "content_warnings": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
        "required": [
            "dish_name",
            "ingredients",
            "visual_mood",
            "plating_style",
            "composition",
            "lighting",
            "camera_angle",
            "hero_element",
            "colors",
            "content_warnings",
            "confidence",
        ],
    }

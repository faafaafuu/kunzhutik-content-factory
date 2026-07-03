from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.providers.ai_video.base import AIVideoProvider
from app.providers.ai_video.fal import FalAIVideoProvider
from app.providers.ai_video.kling import KlingAIVideoProvider
from app.providers.ai_video.mock import MockAIVideoProvider
from app.providers.ai_video.runway import RunwayAIVideoProvider
from app.providers.ai_video.schemas import AIVideoSceneResult

logger = logging.getLogger(__name__)

_REQUIRED_KEYS = {
    "fal": lambda: settings.ai_video_fal_key,
    "kling": lambda: settings.kling_api_key,
    "runway": lambda: settings.runway_api_key,
}


class FallbackAIVideoProvider(AIVideoProvider):
    def __init__(self, primary: AIVideoProvider, fallback: AIVideoProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.provider_name = primary.provider_name

    def generate_scene(
        self,
        prompt: str,
        image_reference_url: str | None,
        character_reference_url: str | None,
        duration_sec: float,
        aspect_ratio: str,
        context: dict | None = None,
    ) -> AIVideoSceneResult:
        started_at = time.perf_counter()
        try:
            return self.primary.generate_scene(prompt, image_reference_url, character_reference_url, duration_sec, aspect_ratio, context)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "AI-video provider failed; falling back to mock",
                extra={"provider": self.primary.provider_name, "duration_ms": duration_ms, "error": str(exc)},
            )
            if not settings.enable_provider_fallback:
                raise
            result = self.fallback.generate_scene(prompt, image_reference_url, character_reference_url, duration_sec, aspect_ratio, context)
            result.raw_response["fallback_reason"] = str(exc)
            result.raw_response["requested_provider"] = self.primary.provider_name
            return result


def get_ai_video_provider() -> AIVideoProvider:
    provider = settings.ai_video_provider.lower().strip()
    if provider in {"mock", "fallback"}:
        return MockAIVideoProvider()
    if provider not in {"fal", "kling", "runway"}:
        raise ValueError(f"Unsupported AI_VIDEO_PROVIDER: {settings.ai_video_provider}")
    if not _REQUIRED_KEYS[provider]() and settings.enable_provider_fallback:
        logger.warning("AI_VIDEO_PROVIDER=%s has no API key configured; using mock fallback", provider)
        return MockAIVideoProvider()
    primary: AIVideoProvider
    if provider == "fal":
        primary = FalAIVideoProvider()
    elif provider == "kling":
        primary = KlingAIVideoProvider()
    else:
        primary = RunwayAIVideoProvider()
    if settings.enable_provider_fallback:
        return FallbackAIVideoProvider(primary, MockAIVideoProvider())
    return primary

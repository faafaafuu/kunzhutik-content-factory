from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.providers.vision.base import VisionProvider
from app.providers.vision.mock import MockVisionProvider
from app.providers.vision.openrouter import OpenRouterVisionProvider
from app.providers.vision.schemas import VisionAnalysisResult

logger = logging.getLogger(__name__)


class FallbackVisionProvider(VisionProvider):
    def __init__(self, primary: VisionProvider, fallback: VisionProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.provider_name = primary.provider_name

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        context: dict | None = None,
    ) -> VisionAnalysisResult:
        started_at = time.perf_counter()
        try:
            return self.primary.analyze_image(image_bytes=image_bytes, mime_type=mime_type, context=context)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "Vision provider failed; falling back to mock",
                extra={
                    "provider": self.primary.provider_name,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            )
            if not settings.enable_provider_fallback:
                raise
            result = self.fallback.analyze_image(image_bytes=image_bytes, mime_type=mime_type, context=context)
            result.raw_response["fallback_reason"] = str(exc)
            result.raw_response["requested_provider"] = self.primary.provider_name
            result.raw_response["provider"] = self.fallback.provider_name
            return result


def get_vision_provider() -> VisionProvider:
    provider = settings.vision_provider.lower().strip()
    if provider == "openrouter":
        return FallbackVisionProvider(OpenRouterVisionProvider(), MockVisionProvider())
    if provider in {"mock", "fallback"}:
        return MockVisionProvider()
    raise ValueError(f"Unsupported VISION_PROVIDER: {settings.vision_provider}")

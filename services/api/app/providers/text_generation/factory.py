from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.models.character_profile import CharacterProfile
from app.providers.text_generation.base import TextGenerationProvider
from app.providers.text_generation.mock import MockTextGenerationProvider
from app.providers.text_generation.openrouter import OpenRouterTextGenerationProvider
from app.providers.text_generation.schemas import GeneratedContent, GeneratedScenePlan
from app.providers.vision.schemas import VisionAnalysisResult

logger = logging.getLogger(__name__)


class FallbackTextGenerationProvider(TextGenerationProvider):
    def __init__(self, primary: TextGenerationProvider, fallback: TextGenerationProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.provider_name = primary.provider_name

    def generate_content(
        self,
        analysis: VisionAnalysisResult,
        character_profile: CharacterProfile,
        platform: str,
        kind: str,
        context: dict | None = None,
    ) -> GeneratedContent:
        started_at = time.perf_counter()
        try:
            return self.primary.generate_content(analysis, character_profile, platform, kind, context)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "Text generation provider failed; falling back to mock",
                extra={"provider": self.primary.provider_name, "duration_ms": duration_ms, "error": str(exc)},
            )
            if not settings.enable_provider_fallback:
                raise
            result = self.fallback.generate_content(analysis, character_profile, platform, kind, context)
            result.raw_response["fallback_reason"] = str(exc)
            result.raw_response["requested_provider"] = self.primary.provider_name
            result.raw_response["provider"] = self.fallback.provider_name
            return result

    def generate_scene_plan(
        self,
        draft_context: dict,
        character_prompt: str,
        style_prompt: str,
        scenes_count: int,
        total_duration_sec: int,
        context: dict | None = None,
    ) -> GeneratedScenePlan:
        started_at = time.perf_counter()
        try:
            return self.primary.generate_scene_plan(draft_context, character_prompt, style_prompt, scenes_count, total_duration_sec, context)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "Scene plan provider failed; falling back to mock",
                extra={"provider": self.primary.provider_name, "duration_ms": duration_ms, "error": str(exc)},
            )
            if not settings.enable_provider_fallback:
                raise
            result = self.fallback.generate_scene_plan(draft_context, character_prompt, style_prompt, scenes_count, total_duration_sec, context)
            result.provider = self.fallback.provider_name
            result.raw_response["fallback_reason"] = str(exc)
            result.raw_response["requested_provider"] = self.primary.provider_name
            return result


def get_text_generation_provider() -> TextGenerationProvider:
    provider = settings.text_provider.lower().strip()
    if provider == "openrouter":
        return FallbackTextGenerationProvider(OpenRouterTextGenerationProvider(), MockTextGenerationProvider())
    if provider in {"mock", "fallback"}:
        return MockTextGenerationProvider()
    raise ValueError(f"Unsupported TEXT_PROVIDER: {settings.text_provider}")

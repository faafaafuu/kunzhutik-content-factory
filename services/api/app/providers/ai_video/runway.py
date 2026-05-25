from __future__ import annotations

from app.providers.ai_video.base import AIVideoProvider
from app.providers.ai_video.schemas import AIVideoSceneResult


class RunwayAIVideoProvider(AIVideoProvider):
    provider_name = "runway"

    def generate_scene(self, prompt: str, image_reference_url: str | None, character_reference_url: str | None, duration_sec: float, aspect_ratio: str, context: dict | None = None) -> AIVideoSceneResult:
        raise NotImplementedError("Runway AI-video provider is not connected yet")

from __future__ import annotations

from abc import ABC, abstractmethod

from app.providers.ai_video.schemas import AIVideoSceneResult


class AIVideoProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate_scene(
        self,
        prompt: str,
        image_reference_url: str | None,
        character_reference_url: str | None,
        duration_sec: float,
        aspect_ratio: str,
        context: dict | None = None,
    ) -> AIVideoSceneResult:
        raise NotImplementedError

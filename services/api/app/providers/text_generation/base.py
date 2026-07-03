from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.character_profile import CharacterProfile
from app.providers.text_generation.schemas import GeneratedContent, GeneratedScenePlan
from app.providers.vision.schemas import VisionAnalysisResult


class TextGenerationProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate_content(
        self,
        analysis: VisionAnalysisResult,
        character_profile: CharacterProfile,
        platform: str,
        kind: str,
        context: dict | None = None,
    ) -> GeneratedContent:
        raise NotImplementedError

    @abstractmethod
    def generate_scene_plan(
        self,
        draft_context: dict,
        character_prompt: str,
        style_prompt: str,
        scenes_count: int,
        total_duration_sec: int,
        context: dict | None = None,
    ) -> GeneratedScenePlan:
        raise NotImplementedError

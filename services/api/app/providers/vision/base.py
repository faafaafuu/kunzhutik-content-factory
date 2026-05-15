from __future__ import annotations

from abc import ABC, abstractmethod

from app.providers.vision.schemas import VisionAnalysisResult


class VisionProvider(ABC):
    provider_name: str

    @abstractmethod
    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        context: dict | None = None,
    ) -> VisionAnalysisResult:
        raise NotImplementedError

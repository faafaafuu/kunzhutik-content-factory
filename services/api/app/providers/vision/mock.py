from __future__ import annotations

from app.providers.vision.base import VisionProvider
from app.providers.vision.schemas import VisionAnalysisResult


class MockVisionProvider(VisionProvider):
    provider_name = "mock-vision-v1"

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        context: dict | None = None,
    ) -> VisionAnalysisResult:
        return VisionAnalysisResult(
            dish_name="Авторское блюдо дня",
            likely_ingredients=["кунжут", "соус", "свежая зелень"],
            plating="аккуратная ресторанная подача",
            mood="аппетитный и тёплый",
            visual_features=["мягкий свет", "крупный план", "выразительная текстура"],
            quality_score=0.72,
            warnings=[],
            raw_response={
                "provider": self.provider_name,
                "mode": "mock",
                "mime_type": mime_type,
                "image_size_bytes": len(image_bytes),
                "note": "Mock vision provider for local development.",
            },
        )

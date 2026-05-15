from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class VisionAnalysisResult(BaseModel):
    dish_name: str = Field(min_length=1, max_length=255)
    likely_ingredients: list[str] = Field(default_factory=list)
    plating: str = Field(default="", max_length=255)
    mood: str = Field(default="", max_length=255)
    visual_features: list[str] = Field(default_factory=list)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    raw_response: dict = Field(default_factory=dict)

    @field_validator("likely_ingredients", "visual_features", "warnings", mode="before")
    @classmethod
    def _coerce_string_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item) for item in value]

    def to_analysis_model_payload(self, provider_name: str) -> dict:
        return {
            "provider": provider_name,
            "dish_name": self.dish_name,
            "ingredients": self.likely_ingredients,
            "visual_mood": self.mood,
            "plating_style": self.plating,
            "features_json": {
                "visual_features": self.visual_features,
                "quality_score": self.quality_score,
                "warnings": self.warnings,
            },
            "raw_payload": self.raw_response,
        }

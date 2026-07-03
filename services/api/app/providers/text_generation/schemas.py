from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class GeneratedContent(BaseModel):
    platform: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    hook: str = Field(min_length=1, max_length=255)
    caption: str = Field(min_length=1)
    cta: str = Field(default="", max_length=255)
    hashtags: list[str] = Field(default_factory=list)
    voice_script: str = Field(default="")
    duration_sec: int = Field(default=12, ge=0, le=90)
    raw_response: dict = Field(default_factory=dict)

    @field_validator("hashtags", mode="before")
    @classmethod
    def _coerce_hashtags(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split() if item.strip()]
        return [str(item).strip() for item in value if str(item).strip()]


class GeneratedScenePlan(BaseModel):
    provider: str
    scenes: list[dict]
    raw_response: dict = Field(default_factory=dict)

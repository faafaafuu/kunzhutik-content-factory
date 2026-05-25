from __future__ import annotations

from pydantic import BaseModel, Field


class AIVideoSceneResult(BaseModel):
    provider: str
    scene_id: str | None = None
    status: str
    video_url: str | None = None
    video_bytes: bytes | None = None
    duration_sec: float
    raw_response: dict = Field(default_factory=dict)
    error_message: str | None = None

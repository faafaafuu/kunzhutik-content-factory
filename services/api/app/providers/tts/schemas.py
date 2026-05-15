from __future__ import annotations

from pydantic import BaseModel, Field


class TTSResult(BaseModel):
    audio_bytes: bytes
    mime_type: str = "audio/wav"
    duration_sec: float | None = None
    provider: str
    voice_id: str | None = None
    raw_response: dict = Field(default_factory=dict)

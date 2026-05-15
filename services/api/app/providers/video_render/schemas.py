from __future__ import annotations

from pydantic import BaseModel, Field


class RenderContent(BaseModel):
    title: str
    subtitle: str
    platform: str
    kind: str


class VideoRenderResult(BaseModel):
    video_url: str | None = None
    video_bytes: bytes | None = None
    preview_url: str | None = None
    preview_bytes: bytes | None = None
    provider: str
    render_id: str | None = None
    status: str
    raw_response: dict = Field(default_factory=dict)

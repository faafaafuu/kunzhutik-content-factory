from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class VideoAssetRegenerateRequest(BaseModel):
    actor: str | None = None
    reason: str | None = None


class VideoAssetRegenerateResponse(BaseModel):
    previous_video_asset_id: UUID
    video_asset_id: UUID
    media_asset_id: UUID
    preview_asset_id: UUID
    provider: str
    template_name: str

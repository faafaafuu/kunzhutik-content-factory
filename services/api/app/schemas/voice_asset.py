from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class VoiceAssetRegenerateRequest(BaseModel):
    actor: str | None = None
    reason: str | None = None


class VoiceAssetRegenerateResponse(BaseModel):
    previous_voice_asset_id: UUID
    voice_asset_id: UUID
    media_asset_id: UUID
    provider: str
    voice_name: str

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_operator
from app.models.operator_user import OperatorUser
from app.schemas.voice_asset import VoiceAssetRegenerateRequest, VoiceAssetRegenerateResponse
from app.services.voice_assets import regenerate_voice_asset

router = APIRouter(prefix="/voice-assets", tags=["voice-assets"])


@router.post("/{voice_asset_id}/regenerate", response_model=VoiceAssetRegenerateResponse)
def regenerate_voice(
    voice_asset_id: UUID,
    payload: VoiceAssetRegenerateRequest,
    db: Session = Depends(get_db),
    user: OperatorUser = Depends(require_operator),
) -> VoiceAssetRegenerateResponse:
    actor = payload.actor or f"dashboard:{user.username}"
    voice_asset = regenerate_voice_asset(db, voice_asset_id, actor=actor, reason=payload.reason)
    return VoiceAssetRegenerateResponse(
        previous_voice_asset_id=voice_asset_id,
        voice_asset_id=voice_asset.id,
        media_asset_id=voice_asset.asset_id,
        provider=voice_asset.provider,
        voice_name=voice_asset.voice_name,
    )

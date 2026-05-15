from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_operator
from app.models.media_asset import MediaAsset
from app.models.operator_user import OperatorUser
from app.schemas.video_asset import VideoAssetRegenerateRequest, VideoAssetRegenerateResponse
from app.services.video_assets import regenerate_video_asset

router = APIRouter(prefix="/video-assets", tags=["video-assets"])


@router.post("/{video_asset_id}/regenerate", response_model=VideoAssetRegenerateResponse)
def regenerate_video(
    video_asset_id: UUID,
    payload: VideoAssetRegenerateRequest,
    db: Session = Depends(get_db),
    user: OperatorUser = Depends(require_operator),
) -> VideoAssetRegenerateResponse:
    actor = payload.actor or f"dashboard:{user.username}"
    video_asset = regenerate_video_asset(db, video_asset_id, actor=actor, reason=payload.reason)
    media_asset = db.query(MediaAsset).filter(MediaAsset.id == video_asset.asset_id).first()
    return VideoAssetRegenerateResponse(
        previous_video_asset_id=video_asset_id,
        video_asset_id=video_asset.id,
        media_asset_id=video_asset.asset_id,
        preview_asset_id=video_asset.preview_asset_id,
        provider=(media_asset.metadata_json or {}).get("provider", "video-render") if media_asset else "video-render",
        template_name=video_asset.template_name,
    )

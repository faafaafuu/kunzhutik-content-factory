from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.project import Project
from app.models.voice_asset import VoiceAsset
from app.providers.tts.factory import get_tts_provider
from app.services.audit import log_event
from app.services.media_generation import _audio_suffix
from app.services.storage import upload_bytes
from shared.enums import AssetKind, PipelineStatus


def regenerate_voice_asset(
    db: Session,
    voice_asset_id: UUID,
    *,
    actor: str,
    reason: str | None = None,
) -> VoiceAsset:
    previous = db.query(VoiceAsset).filter(VoiceAsset.id == voice_asset_id).first()
    if not previous:
        raise HTTPException(status_code=404, detail="Voice asset not found")
    draft = db.query(ContentDraft).filter(ContentDraft.id == previous.content_draft_id).first()
    if not draft:
        raise HTTPException(status_code=409, detail="Voice asset has no content draft")
    project = db.query(Project).filter(Project.id == draft.project_id).first()
    if not project:
        raise HTTPException(status_code=409, detail="Draft project not found")

    transcript = draft.script_text or draft.long_text or draft.caption
    if not transcript:
        raise HTTPException(status_code=409, detail="Content draft has no script or caption")

    tts_result = get_tts_provider().synthesize(transcript, {"voice_name": previous.voice_name or "ru", "speed": "155"})
    suffix = _audio_suffix(tts_result.mime_type)
    storage_key = f"projects/{project.slug}/uploads/{draft.upload_id}/drafts/{draft.id}/voice-{uuid4().hex}{suffix}"
    upload_bytes(storage_key, tts_result.audio_bytes, tts_result.mime_type)

    media_asset = MediaAsset(
        project_id=draft.project_id,
        upload_id=draft.upload_id,
        kind=AssetKind.voice,
        storage_key=storage_key,
        bucket_name=settings.s3_bucket,
        mime_type=tts_result.mime_type,
        file_name=f"{draft.kind.value}-voice{suffix}",
        file_size=len(tts_result.audio_bytes),
        duration_seconds=Decimal(str(tts_result.duration_sec)).quantize(Decimal("0.01")) if tts_result.duration_sec is not None else None,
        metadata_json={
            **tts_result.raw_response,
            "regenerated_from_voice_asset_id": str(previous.id),
            "regenerate_reason": reason,
        },
    )
    db.add(media_asset)
    db.flush()

    voice_asset = VoiceAsset(
        project_id=draft.project_id,
        content_draft_id=draft.id,
        status=PipelineStatus.completed,
        provider=tts_result.provider,
        voice_name=tts_result.voice_id or previous.voice_name or "ru",
        speaking_rate=previous.speaking_rate,
        asset_id=media_asset.id,
        transcript=transcript,
    )
    db.add(voice_asset)
    db.flush()
    log_event(
        db,
        draft.project_id,
        "upload",
        str(draft.upload_id),
        "voice.regenerated",
        actor,
        {
            "previous_voice_asset_id": str(previous.id),
            "new_voice_asset_id": str(voice_asset.id),
            "media_asset_id": str(media_asset.id),
            "content_draft_id": str(draft.id),
            "provider": voice_asset.provider,
            "reason": reason,
        },
    )
    db.commit()
    db.refresh(voice_asset)
    return voice_asset

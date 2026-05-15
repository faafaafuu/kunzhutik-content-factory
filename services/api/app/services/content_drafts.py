from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analysis_result import AnalysisResult
from app.models.character_profile import CharacterProfile
from app.models.content_draft import ContentDraft
from app.providers.text_generation.factory import get_text_generation_provider
from app.services.audit import log_event
from app.services.content_generation import _analysis_to_vision_result, _generated_to_content_draft_payload
from shared.enums import PipelineStatus


def regenerate_content_draft(
    db: Session,
    content_draft_id: UUID,
    *,
    actor: str,
    reason: str | None = None,
) -> ContentDraft:
    previous = db.query(ContentDraft).filter(ContentDraft.id == content_draft_id).first()
    if not previous:
        raise HTTPException(status_code=404, detail="Content draft not found")

    analysis = None
    if previous.analysis_result_id:
        analysis = db.query(AnalysisResult).filter(AnalysisResult.id == previous.analysis_result_id).first()
    if not analysis:
        raise HTTPException(status_code=409, detail="Content draft has no analysis result")

    character = (
        db.query(CharacterProfile)
        .filter(CharacterProfile.project_id == previous.project_id, CharacterProfile.name == previous.persona_name)
        .order_by(CharacterProfile.is_default.desc(), CharacterProfile.created_at.asc())
        .first()
    )
    if not character:
        character = (
            db.query(CharacterProfile)
            .filter(CharacterProfile.project_id == previous.project_id, CharacterProfile.is_default.is_(True))
            .first()
        )
    if not character:
        raise HTTPException(status_code=409, detail="Project has no character profile")

    next_version = _next_draft_version(db, previous)
    generated = get_text_generation_provider().generate_content(
        analysis=_analysis_to_vision_result(analysis),
        character_profile=character,
        platform=previous.platform.value,
        kind=previous.kind.value,
        context={
            "mode": "regenerate",
            "reason": reason,
            "previous_draft_id": str(previous.id),
            "previous_version": previous.version,
            "analysis_result_id": str(analysis.id),
        },
    )
    payload = _generated_to_content_draft_payload(generated, analysis.provider)
    metadata = payload.pop("metadata_json")
    metadata.update(
        {
            "regenerated_from_draft_id": str(previous.id),
            "regenerate_reason": reason,
        }
    )

    draft = ContentDraft(
        project_id=previous.project_id,
        upload_id=previous.upload_id,
        analysis_result_id=analysis.id,
        status=PipelineStatus.completed,
        version=next_version,
        persona_name=character.name,
        metadata_json=metadata,
        **payload,
    )
    db.add(draft)
    db.flush()
    log_event(
        db,
        previous.project_id,
        "upload",
        str(previous.upload_id),
        "content.regenerated",
        actor,
        {
            "previous_draft_id": str(previous.id),
            "new_draft_id": str(draft.id),
            "platform": previous.platform.value,
            "kind": previous.kind.value,
            "version": next_version,
            "reason": reason,
        },
    )
    db.commit()
    db.refresh(draft)
    return draft


def _next_draft_version(db: Session, previous: ContentDraft) -> int:
    current_max = (
        db.query(func.max(ContentDraft.version))
        .filter(
            ContentDraft.upload_id == previous.upload_id,
            ContentDraft.platform == previous.platform,
            ContentDraft.kind == previous.kind,
        )
        .scalar()
    )
    return int(current_max or previous.version or 1) + 1

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_operator
from app.models.operator_user import OperatorUser
from app.schemas.content_draft import ContentDraftRegenerateRequest, ContentDraftRegenerateResponse
from app.schemas.upload import UploadDraftRead
from app.services.content_drafts import regenerate_content_draft

router = APIRouter(prefix="/content-drafts", tags=["content-drafts"])


@router.post("/{content_draft_id}/regenerate", response_model=ContentDraftRegenerateResponse)
def regenerate_draft(
    content_draft_id: UUID,
    payload: ContentDraftRegenerateRequest,
    db: Session = Depends(get_db),
    user: OperatorUser = Depends(require_operator),
) -> ContentDraftRegenerateResponse:
    actor = payload.actor or f"dashboard:{user.username}"
    draft = regenerate_content_draft(db, content_draft_id, actor=actor, reason=payload.reason)
    return ContentDraftRegenerateResponse(
        previous_draft_id=content_draft_id,
        draft=UploadDraftRead.model_validate(draft),
    )

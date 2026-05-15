from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.schemas.upload import UploadDraftRead


class ContentDraftRegenerateRequest(BaseModel):
    actor: str | None = None
    reason: str | None = None


class ContentDraftRegenerateResponse(BaseModel):
    previous_draft_id: UUID
    draft: UploadDraftRead

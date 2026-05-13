from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel
from shared.enums import ContentPlatform, PublicationStatus


class PublicationResultRead(ORMModel):
    id: UUID
    publication_task_id: UUID
    status: PublicationStatus
    remote_id: str | None = None
    remote_url: str | None = None
    error_message: str | None = None
    payload: dict
    created_at: datetime


class PublicationTaskRead(ORMModel):
    id: UUID
    project_id: UUID
    upload_id: UUID
    content_draft_id: UUID
    platform: ContentPlatform
    status: PublicationStatus
    scheduled_for: datetime | None = None
    attempt_count: int
    idempotency_key: str
    created_at: datetime
    updated_at: datetime


class PublicationTaskWithResults(PublicationTaskRead):
    results: list[PublicationResultRead] = []


class PublicationTaskListResponse(BaseModel):
    publication_tasks: list[PublicationTaskWithResults]


class PublicationRunRequest(BaseModel):
    actor: str = "api"

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel
from shared.enums import PipelineStatus


class UploadRead(ORMModel):
    id: UUID
    project_id: UUID
    status: PipelineStatus
    created_by: str
    source_count: int
    source_type: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class UploadTimelineEvent(BaseModel):
    event_type: str
    actor: str
    created_at: datetime
    payload: dict


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


class UploadAssetRead(BaseModel):
    id: UUID
    kind: str
    mime_type: str
    file_name: str
    file_size: int
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    storage_key: str
    content_draft_id: UUID | None = None
    draft_kind: str | None = None
    platform: str | None = None
    voice_asset_id: UUID | None = None
    video_asset_id: UUID | None = None
    download_url: str


class UploadAssetsResponse(BaseModel):
    upload_id: UUID
    assets: list[UploadAssetRead]

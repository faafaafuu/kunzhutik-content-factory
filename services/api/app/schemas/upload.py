from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.publication import PublicationTaskWithResults
from app.schemas.scene_plan import ScenePlanDetail
from shared.enums import ApprovalStatus, ContentPlatform, DraftKind
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


class UploadListResponse(BaseModel):
    uploads: list[UploadRead]


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
    metadata_json: dict
    download_url: str


class UploadAssetsResponse(BaseModel):
    upload_id: UUID
    assets: list[UploadAssetRead]


class UploadAnalysisRead(ORMModel):
    id: UUID
    status: PipelineStatus
    provider: str
    dish_name: str | None = None
    ingredients: list
    visual_mood: str | None = None
    plating_style: str | None = None
    features_json: dict
    created_at: datetime


class UploadDraftRead(ORMModel):
    id: UUID
    platform: ContentPlatform
    kind: DraftKind
    status: PipelineStatus
    version: int
    title: str | None = None
    caption: str
    cta: str | None = None
    short_text: str | None = None
    long_text: str | None = None
    script_text: str | None = None
    persona_name: str
    metadata_json: dict
    created_at: datetime


class UploadApprovalRead(ORMModel):
    id: UUID
    status: ApprovalStatus
    stage: str = "video"
    telegram_chat_id: str | None = None
    telegram_message_id: str | None = None
    preview_payload: dict
    decision_note: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    created_at: datetime


class UploadPipelineSummary(BaseModel):
    upload: UploadRead
    analysis_results: list[UploadAnalysisRead]
    drafts: list[UploadDraftRead]
    approvals: list[UploadApprovalRead]
    publication_tasks: list[PublicationTaskWithResults]
    scene_plans: list[ScenePlanDetail] = []
    assets: list[UploadAssetRead]
    timeline: list[UploadTimelineEvent]

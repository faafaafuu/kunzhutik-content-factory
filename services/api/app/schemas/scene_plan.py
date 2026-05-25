from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ScenePlanCreateRequest(BaseModel):
    content_draft_id: UUID | None = None
    total_duration_sec: int | None = None
    aspect_ratio: str | None = None
    scenes_count: int | None = Field(default=None, ge=1, le=8)
    style_reference: str | None = None


class ScenePlanRegenerateRequest(BaseModel):
    reason: str | None = None
    scenes_count: int | None = Field(default=None, ge=1, le=8)


class SceneRegenerateRequest(BaseModel):
    reason: str | None = None


class AIVideoSceneRead(ORMModel):
    id: UUID
    project_id: UUID
    upload_id: UUID
    scene_plan_id: UUID
    content_draft_id: UUID
    scene_number: int
    status: str
    provider: str
    provider_scene_id: str | None = None
    duration_sec: float
    visual_prompt: str
    voice_text: str | None = None
    subtitle_text: str | None = None
    camera: str | None = None
    emotion: str | None = None
    asset_id: UUID | None = None
    raw_response: dict
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ScenePlanRead(ORMModel):
    id: UUID
    project_id: UUID
    upload_id: UUID
    content_draft_id: UUID
    status: str
    total_duration_sec: float
    aspect_ratio: str
    style_prompt: str
    character_prompt: str
    scenes_json: list
    metadata_json: dict
    created_at: datetime
    updated_at: datetime


class ScenePlanDetail(ScenePlanRead):
    scenes: list[AIVideoSceneRead] = []


class ScenePlanListResponse(BaseModel):
    scene_plans: list[ScenePlanDetail]


class SceneGenerationResponse(BaseModel):
    scene_plan: ScenePlanDetail


class FinalVideoRenderResponse(BaseModel):
    scene_plan_id: UUID
    video_asset_id: UUID
    media_asset_id: UUID
    preview_asset_id: UUID
    status: str

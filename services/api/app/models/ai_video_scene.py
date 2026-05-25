import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AIVideoScene(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_video_scenes"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scene_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    content_draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued", index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="mock")
    provider_scene_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_sec: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    visual_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    voice_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtitle_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True)
    raw_response: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

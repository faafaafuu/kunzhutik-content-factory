import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ScenePlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_plans"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    content_draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", index=True)
    total_duration_sec: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False, default="9:16")
    style_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    character_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    scenes_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from shared.enums import ContentPlatform, DraftKind, PipelineStatus


class ContentDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_drafts"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("analysis_results.id", ondelete="SET NULL"), nullable=True)
    platform: Mapped[ContentPlatform] = mapped_column(Enum(ContentPlatform, name="content_platform"), nullable=False)
    kind: Mapped[DraftKind] = mapped_column(Enum(DraftKind, name="draft_kind"), nullable=False)
    status: Mapped[PipelineStatus] = mapped_column(Enum(PipelineStatus, name="pipeline_status"), default=PipelineStatus.pending, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    cta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    short_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_name: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

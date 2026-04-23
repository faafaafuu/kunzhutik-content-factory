import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from shared.enums import PipelineStatus


class VideoAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "video_assets"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    content_draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[PipelineStatus] = mapped_column(Enum(PipelineStatus, name="pipeline_status"), default=PipelineStatus.pending, nullable=False)
    template_name: Mapped[str] = mapped_column(String(120), nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True)
    preview_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True)

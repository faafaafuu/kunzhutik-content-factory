import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from shared.enums import PipelineStatus


class VoiceAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "voice_assets"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    content_draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[PipelineStatus] = mapped_column(Enum(PipelineStatus, name="pipeline_status"), default=PipelineStatus.pending, nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    voice_name: Mapped[str] = mapped_column(String(120), nullable=False)
    speaking_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

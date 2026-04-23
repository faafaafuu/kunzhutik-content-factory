import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from shared.enums import PipelineStatus


class AnalysisResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_results"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[PipelineStatus] = mapped_column(Enum(PipelineStatus, name="pipeline_status"), default=PipelineStatus.pending, nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    dish_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ingredients: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    visual_mood: Mapped[str | None] = mapped_column(String(120), nullable=True)
    plating_style: Mapped[str | None] = mapped_column(String(120), nullable=True)
    features_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

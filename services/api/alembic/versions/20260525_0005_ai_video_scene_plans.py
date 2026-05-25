"""add ai video scene plans

Revision ID: 20260525_0005
Revises: 20260514_0004
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260525_0005"
down_revision = "20260514_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scene_plans",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("total_duration_sec", sa.Numeric(8, 2), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("style_prompt", sa.Text(), nullable=False),
        sa.Column("character_prompt", sa.Text(), nullable=False),
        sa.Column("scenes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["content_draft_id"], ["content_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scene_plans_content_draft_id"), "scene_plans", ["content_draft_id"], unique=False)
    op.create_index(op.f("ix_scene_plans_status"), "scene_plans", ["status"], unique=False)
    op.create_index(op.f("ix_scene_plans_upload_id"), "scene_plans", ["upload_id"], unique=False)

    op.create_table(
        "ai_video_scenes",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_scene_id", sa.String(length=255), nullable=True),
        sa.Column("duration_sec", sa.Numeric(8, 2), nullable=False),
        sa.Column("visual_prompt", sa.Text(), nullable=False),
        sa.Column("voice_text", sa.Text(), nullable=True),
        sa.Column("subtitle_text", sa.Text(), nullable=True),
        sa.Column("camera", sa.Text(), nullable=True),
        sa.Column("emotion", sa.String(length=120), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_draft_id"], ["content_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_plan_id"], ["scene_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_video_scenes_content_draft_id"), "ai_video_scenes", ["content_draft_id"], unique=False)
    op.create_index(op.f("ix_ai_video_scenes_scene_plan_id"), "ai_video_scenes", ["scene_plan_id"], unique=False)
    op.create_index(op.f("ix_ai_video_scenes_status"), "ai_video_scenes", ["status"], unique=False)
    op.create_index(op.f("ix_ai_video_scenes_upload_id"), "ai_video_scenes", ["upload_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_video_scenes_upload_id"), table_name="ai_video_scenes")
    op.drop_index(op.f("ix_ai_video_scenes_status"), table_name="ai_video_scenes")
    op.drop_index(op.f("ix_ai_video_scenes_scene_plan_id"), table_name="ai_video_scenes")
    op.drop_index(op.f("ix_ai_video_scenes_content_draft_id"), table_name="ai_video_scenes")
    op.drop_table("ai_video_scenes")
    op.drop_index(op.f("ix_scene_plans_upload_id"), table_name="scene_plans")
    op.drop_index(op.f("ix_scene_plans_status"), table_name="scene_plans")
    op.drop_index(op.f("ix_scene_plans_content_draft_id"), table_name="scene_plans")
    op.drop_table("scene_plans")

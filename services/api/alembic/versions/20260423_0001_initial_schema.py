"""initial schema"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_0001"
down_revision = None
branch_labels = None
depends_on = None


pipeline_status = sa.Enum(
    "pending",
    "queued",
    "processing",
    "completed",
    "failed",
    "needs_review",
    name="pipeline_status",
)
content_platform = sa.Enum("instagram", "vk", "yandex_maps", name="content_platform")
draft_kind = sa.Enum("post", "story", "reel", "clip", "news", name="draft_kind")
asset_kind = sa.Enum("source_photo", "derived_image", "voice", "video", "preview", name="asset_kind")
approval_status = sa.Enum(
    "pending",
    "dispatched",
    "approved",
    "rejected",
    "regenerate_requested",
    name="approval_status",
)
approval_trigger = sa.Enum("telegram", "dashboard", "system", name="approval_trigger")
publication_status = sa.Enum(
    "pending",
    "scheduled",
    "publishing",
    "published",
    "failed",
    "cancelled",
    name="publication_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    pipeline_status.create(bind, checkfirst=True)
    content_platform.create(bind, checkfirst=True)
    draft_kind.create(bind, checkfirst=True)
    asset_kind.create(bind, checkfirst=True)
    approval_status.create(bind, checkfirst=True)
    approval_trigger.create(bind, checkfirst=True)
    publication_status.create(bind, checkfirst=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "character_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("appearance", sa.Text(), nullable=False),
        sa.Column("tone", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("voice_style", sa.Text(), nullable=False),
        sa.Column("persona_prompt", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", pipeline_status, nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", asset_kind, nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False, unique=True),
        sa.Column("bucket_name", sa.String(length=128), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(8, 2), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", pipeline_status, nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("dish_name", sa.String(length=255), nullable=True),
        sa.Column("ingredients", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("visual_mood", sa.String(length=120), nullable=True),
        sa.Column("plating_style", sa.String(length=120), nullable=True),
        sa.Column("features_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "content_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_result_id", sa.Uuid(), sa.ForeignKey("analysis_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("platform", content_platform, nullable=False),
        sa.Column("kind", draft_kind, nullable=False),
        sa.Column("status", pipeline_status, nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("cta", sa.String(length=255), nullable=True),
        sa.Column("short_text", sa.Text(), nullable=True),
        sa.Column("long_text", sa.Text(), nullable=True),
        sa.Column("script_text", sa.Text(), nullable=True),
        sa.Column("persona_name", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "voice_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_draft_id", sa.Uuid(), sa.ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", pipeline_status, nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("voice_name", sa.String(length=120), nullable=False),
        sa.Column("speaking_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "video_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_draft_id", sa.Uuid(), sa.ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", pipeline_status, nullable=False, server_default="pending"),
        sa.Column("template_name", sa.String(length=120), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("preview_asset_id", sa.Uuid(), sa.ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "approval_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", approval_status, nullable=False, server_default="pending"),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("telegram_message_id", sa.String(length=64), nullable=True),
        sa.Column("preview_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(length=255), nullable=True),
        sa.Column("decided_via", approval_trigger, nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "publication_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_draft_id", sa.Uuid(), sa.ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", content_platform, nullable=False),
        sa.Column("status", publication_status, nullable=False, server_default="pending"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "publication_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("publication_task_id", sa.Uuid(), sa.ForeignKey("publication_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", publication_status, nullable=False),
        sa.Column("remote_id", sa.String(length=255), nullable=True),
        sa.Column("remote_url", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_uploads_project_id", "uploads", ["project_id"])
    op.create_index("ix_media_assets_upload_id", "media_assets", ["upload_id"])
    op.create_index("ix_analysis_results_upload_id", "analysis_results", ["upload_id"])
    op.create_index("ix_content_drafts_upload_id", "content_drafts", ["upload_id"])
    op.create_index("ix_approval_tasks_upload_id", "approval_tasks", ["upload_id"])
    op.create_index("ix_publication_tasks_upload_id", "publication_tasks", ["upload_id"])
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_index("ix_publication_tasks_upload_id", table_name="publication_tasks")
    op.drop_index("ix_approval_tasks_upload_id", table_name="approval_tasks")
    op.drop_index("ix_content_drafts_upload_id", table_name="content_drafts")
    op.drop_index("ix_analysis_results_upload_id", table_name="analysis_results")
    op.drop_index("ix_media_assets_upload_id", table_name="media_assets")
    op.drop_index("ix_uploads_project_id", table_name="uploads")

    op.drop_table("audit_events")
    op.drop_table("publication_results")
    op.drop_table("publication_tasks")
    op.drop_table("approval_tasks")
    op.drop_table("video_assets")
    op.drop_table("voice_assets")
    op.drop_table("content_drafts")
    op.drop_table("analysis_results")
    op.drop_table("media_assets")
    op.drop_table("uploads")
    op.drop_table("character_profiles")
    op.drop_table("projects")

    bind = op.get_bind()
    publication_status.drop(bind, checkfirst=True)
    approval_trigger.drop(bind, checkfirst=True)
    approval_status.drop(bind, checkfirst=True)
    asset_kind.drop(bind, checkfirst=True)
    draft_kind.drop(bind, checkfirst=True)
    content_platform.drop(bind, checkfirst=True)
    pipeline_status.drop(bind, checkfirst=True)


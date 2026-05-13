from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from fastapi import HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis_result import AnalysisResult
from app.models.approval_task import ApprovalTask
from app.models.content_draft import ContentDraft
from app.models.project import Project
from app.models.media_asset import MediaAsset
from app.models.upload import Upload
from app.models.video_asset import VideoAsset
from app.models.voice_asset import VoiceAsset
from app.schemas.upload import UploadTimelineEvent
from app.services.audit import log_event
from app.services.publications import list_publication_results, list_publication_tasks
from app.services.storage import download_bytes, upload_bytes
from shared.enums import AssetKind, PipelineStatus


def get_upload_or_404(db: Session, upload_id: UUID) -> Upload:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


def list_uploads(db: Session, limit: int = 30) -> list[Upload]:
    return db.query(Upload).order_by(Upload.created_at.desc()).limit(limit).all()


async def create_upload_with_file(
    db: Session,
    project_id: UUID,
    created_by: str,
    notes: str | None,
    incoming_file: UploadFile,
) -> Upload:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_bytes = await incoming_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    mime_type = incoming_file.content_type or mimetypes.guess_type(incoming_file.filename or "")[0] or "application/octet-stream"
    extension = Path(incoming_file.filename or "upload.bin").suffix or ".bin"

    upload = Upload(
        project_id=project_id,
        status=PipelineStatus.queued,
        created_by=created_by,
        notes=notes,
        source_count=1,
        source_type="manual",
    )
    db.add(upload)
    db.flush()

    storage_key = f"projects/{project.slug}/uploads/{upload.id}/source-{uuid4().hex}{extension}"
    upload_bytes(storage_key, file_bytes, mime_type)

    asset = MediaAsset(
        project_id=project_id,
        upload_id=upload.id,
        kind=AssetKind.source_photo,
        storage_key=storage_key,
        bucket_name=settings.s3_bucket,
        mime_type=mime_type,
        file_name=incoming_file.filename or f"{upload.id}{extension}",
        file_size=len(file_bytes),
        metadata_json={"stage": "original_upload"},
    )
    db.add(asset)
    log_event(db, project_id, "upload", str(upload.id), "upload.created", created_by, {"file_name": asset.file_name})
    db.commit()

    from app.services.workflow import enqueue_upload_pipeline

    enqueue_upload_pipeline(upload.id)
    db.refresh(upload)
    return upload


def get_upload_timeline(db: Session, upload_id: UUID) -> list[UploadTimelineEvent]:
    rows = (
        db.execute(
            text(
                """
            SELECT event_type, actor, created_at, payload
            FROM audit_events
            WHERE entity_type = 'upload' AND entity_id = :entity_id
            ORDER BY created_at ASC
            """
            ),
            {"entity_id": str(upload_id)},
        )
        .mappings()
        .all()
    )
    return [UploadTimelineEvent(**row) for row in rows]


def get_upload_assets(db: Session, upload_id: UUID) -> list[dict]:
    draft_rows = db.execute(
        select(ContentDraft.id, ContentDraft.kind, ContentDraft.platform).where(ContentDraft.upload_id == upload_id)
    ).all()
    draft_map = {
        draft_id: {"draft_kind": kind.value, "platform": platform.value}
        for draft_id, kind, platform in draft_rows
    }

    voice_map: dict[UUID, dict] = {}
    for asset_id, voice_asset_id, content_draft_id in db.execute(
        select(VoiceAsset.asset_id, VoiceAsset.id, VoiceAsset.content_draft_id)
        .join(ContentDraft, VoiceAsset.content_draft_id == ContentDraft.id)
        .where(ContentDraft.upload_id == upload_id, VoiceAsset.asset_id.is_not(None))
    ):
        voice_map[asset_id] = {
            "voice_asset_id": voice_asset_id,
            "content_draft_id": content_draft_id,
            **draft_map.get(content_draft_id, {}),
        }

    video_map: dict[UUID, dict] = {}
    preview_map: dict[UUID, dict] = {}
    for asset_id, preview_asset_id, video_asset_id, content_draft_id in db.execute(
        select(VideoAsset.asset_id, VideoAsset.preview_asset_id, VideoAsset.id, VideoAsset.content_draft_id)
        .join(ContentDraft, VideoAsset.content_draft_id == ContentDraft.id)
        .where(ContentDraft.upload_id == upload_id)
    ):
        base = {
            "video_asset_id": video_asset_id,
            "content_draft_id": content_draft_id,
            **draft_map.get(content_draft_id, {}),
        }
        if asset_id:
            video_map[asset_id] = base
        if preview_asset_id:
            preview_map[preview_asset_id] = base

    assets = (
        db.query(MediaAsset)
        .filter(MediaAsset.upload_id == upload_id)
        .order_by(MediaAsset.created_at.asc())
        .all()
    )

    result: list[dict] = []
    for asset in assets:
        relation = {}
        if asset.kind == AssetKind.voice:
            relation = voice_map.get(asset.id, {})
        elif asset.kind in {AssetKind.video, AssetKind.preview}:
            relation = (video_map if asset.kind == AssetKind.video else preview_map).get(asset.id, {})

        result.append(
            {
                "id": asset.id,
                "kind": asset.kind.value,
                "mime_type": asset.mime_type,
                "file_name": asset.file_name,
                "file_size": asset.file_size,
                "width": asset.width,
                "height": asset.height,
                "duration_seconds": float(asset.duration_seconds) if asset.duration_seconds is not None else None,
                "storage_key": asset.storage_key,
                "content_draft_id": relation.get("content_draft_id"),
                "draft_kind": relation.get("draft_kind"),
                "platform": relation.get("platform"),
                "voice_asset_id": relation.get("voice_asset_id"),
                "video_asset_id": relation.get("video_asset_id"),
            }
        )
    return result


def get_upload_pipeline_summary(db: Session, upload_id: UUID) -> dict:
    upload = get_upload_or_404(db, upload_id)
    analysis_results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.upload_id == upload_id)
        .order_by(AnalysisResult.created_at.asc())
        .all()
    )
    drafts = (
        db.query(ContentDraft)
        .filter(ContentDraft.upload_id == upload_id)
        .order_by(ContentDraft.created_at.asc())
        .all()
    )
    approvals = (
        db.query(ApprovalTask)
        .filter(ApprovalTask.upload_id == upload_id)
        .order_by(ApprovalTask.created_at.asc())
        .all()
    )
    publication_tasks = list_publication_tasks(db, upload_id=upload_id)
    return {
        "upload": upload,
        "analysis_results": analysis_results,
        "drafts": drafts,
        "approvals": approvals,
        "publication_tasks": publication_tasks,
        "publication_results": list_publication_results(db, [task.id for task in publication_tasks]),
        "assets": get_upload_assets(db, upload_id),
        "timeline": get_upload_timeline(db, upload_id),
    }


def get_upload_asset_bytes(db: Session, upload_id: UUID, asset_id: UUID) -> tuple[MediaAsset, bytes]:
    asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.id == asset_id, MediaAsset.upload_id == upload_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset, download_bytes(asset.storage_key)

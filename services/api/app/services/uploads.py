from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.media_asset import MediaAsset
from app.models.upload import Upload
from app.schemas.upload import UploadTimelineEvent
from app.services.audit import log_event
from app.services.storage import upload_bytes
from shared.enums import AssetKind, PipelineStatus


def get_upload_or_404(db: Session, upload_id: UUID) -> Upload:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


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

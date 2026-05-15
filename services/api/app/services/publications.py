from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.publication_result import PublicationResult
from app.models.publication_task import PublicationTask
from app.providers.publishing.factory import get_publisher_provider
from app.services.audit import log_event
from app.services.workflow import enqueue_publication_task
from shared.enums import AssetKind
from shared.enums import PublicationStatus


def create_publication_tasks_for_upload(db: Session, upload_id: UUID, *, actor: str) -> list[PublicationTask]:
    drafts = (
        db.query(ContentDraft)
        .filter(ContentDraft.upload_id == upload_id)
        .order_by(ContentDraft.created_at.asc())
        .all()
    )
    tasks: list[PublicationTask] = []
    for draft in drafts:
        idempotency_key = build_publication_idempotency_key(draft.id, draft.version, draft.platform.value)
        task = db.query(PublicationTask).filter(PublicationTask.idempotency_key == idempotency_key).first()
        if not task:
            task = PublicationTask(
                project_id=draft.project_id,
                upload_id=draft.upload_id,
                content_draft_id=draft.id,
                platform=draft.platform,
                status=PublicationStatus.pending,
                idempotency_key=idempotency_key,
            )
            db.add(task)
            db.flush()
            log_event(
                db,
                draft.project_id,
                "upload",
                str(draft.upload_id),
                "publication_task.created",
                actor,
                {
                    "publication_task_id": str(task.id),
                    "content_draft_id": str(draft.id),
                    "platform": draft.platform.value,
                    "idempotency_key": idempotency_key,
                },
            )
        tasks.append(task)
    return tasks


def list_publication_tasks(db: Session, upload_id: UUID | None = None) -> list[PublicationTask]:
    query = db.query(PublicationTask).order_by(PublicationTask.created_at.desc())
    if upload_id:
        query = query.filter(PublicationTask.upload_id == upload_id)
    return query.all()


def list_publication_results(db: Session, task_ids: list[UUID]) -> dict[UUID, list[PublicationResult]]:
    if not task_ids:
        return {}
    rows = (
        db.query(PublicationResult)
        .filter(PublicationResult.publication_task_id.in_(task_ids))
        .order_by(PublicationResult.created_at.asc())
        .all()
    )
    results: dict[UUID, list[PublicationResult]] = {}
    for row in rows:
        results.setdefault(row.publication_task_id, []).append(row)
    return results


def enqueue_publication(db: Session, publication_task_id: UUID, *, actor: str) -> PublicationTask:
    task = get_publication_task_or_404(db, publication_task_id)
    if task.status not in {PublicationStatus.pending, PublicationStatus.scheduled, PublicationStatus.failed}:
        raise HTTPException(status_code=409, detail=f"Publication task is {task.status.value}")
    log_event(
        db,
        task.project_id,
        "upload",
        str(task.upload_id),
        "publication_task.enqueued",
        actor,
        {"publication_task_id": str(task.id), "status": task.status.value},
    )
    db.commit()
    enqueue_publication_task(task.id)
    return task


def publish_task_with_provider(db: Session, publication_task_id: UUID) -> PublicationTask:
    task = get_publication_task_or_404(db, publication_task_id)
    if task.status == PublicationStatus.published:
        return task

    draft = db.query(ContentDraft).filter(ContentDraft.id == task.content_draft_id).first()
    if not draft:
        raise HTTPException(status_code=409, detail="Publication task has no content draft")
    assets = _publication_assets_for_task(db, task, draft)

    task.status = PublicationStatus.publishing
    task.attempt_count += 1
    db.flush()
    log_event(
        db,
        task.project_id,
        "upload",
        str(task.upload_id),
        "publication_task.publishing",
        "publishing-worker",
        {"publication_task_id": str(task.id), "attempt_count": task.attempt_count},
    )

    provider = get_publisher_provider(task.platform)
    try:
        publish_result = provider.publish(task, assets, draft, {"attempt_count": task.attempt_count})
    except Exception as exc:
        result = PublicationResult(
            publication_task_id=task.id,
            status=PublicationStatus.failed,
            error_message=str(exc),
            payload={
                "provider": provider.provider_name,
                "platform": task.platform.value,
                "idempotency_key": task.idempotency_key,
                "asset_count": len(assets),
            },
        )
        task.status = PublicationStatus.failed
        db.add(result)
        log_event(
            db,
            task.project_id,
            "upload",
            str(task.upload_id),
            "publication_task.failed",
            "publishing-worker",
            {
                "publication_task_id": str(task.id),
                "publication_result_id": str(result.id),
                "provider": provider.provider_name,
                "error": str(exc),
            },
        )
        db.commit()
        raise

    status = _publication_status_from_provider(publish_result.status)
    result = PublicationResult(
        publication_task_id=task.id,
        status=status,
        remote_id=publish_result.remote_id,
        remote_url=publish_result.remote_url,
        error_message=publish_result.error_message,
        payload={**publish_result.raw_response, "idempotency_key": task.idempotency_key},
    )
    task.status = status
    db.add(result)
    log_event(
        db,
        task.project_id,
        "upload",
        str(task.upload_id),
        "publication_task.published",
        "publishing-worker",
        {
            "publication_task_id": str(task.id),
            "publication_result_id": str(result.id),
            "provider": publish_result.raw_response.get("provider", provider.provider_name),
            "remote_url": publish_result.remote_url,
            "status": status.value,
        },
    )
    db.commit()
    db.refresh(task)
    return task


def get_publication_task_or_404(db: Session, publication_task_id: UUID) -> PublicationTask:
    task = db.query(PublicationTask).filter(PublicationTask.id == publication_task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Publication task not found")
    return task


def build_publication_idempotency_key(content_draft_id: UUID, version: int, platform: str) -> str:
    return f"draft:{content_draft_id}:v{version}:{platform}"


def _publication_assets_for_task(db: Session, task: PublicationTask, draft: ContentDraft) -> list[MediaAsset]:
    rows = (
        db.query(MediaAsset)
        .filter(MediaAsset.upload_id == task.upload_id)
        .order_by(MediaAsset.created_at.desc())
        .all()
    )
    draft_key_part = f"/drafts/{draft.id}/"
    selected: list[MediaAsset] = []
    for asset in rows:
        if asset.kind == AssetKind.source_photo or draft_key_part in asset.storage_key:
            selected.append(asset)
    return selected


def _publication_status_from_provider(status: str) -> PublicationStatus:
    normalized = status.lower().strip()
    if normalized in PublicationStatus.__members__:
        return PublicationStatus[normalized]
    try:
        return PublicationStatus(normalized)
    except ValueError:
        return PublicationStatus.failed

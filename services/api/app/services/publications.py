from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.content_draft import ContentDraft
from app.models.publication_result import PublicationResult
from app.models.publication_task import PublicationTask
from app.services.audit import log_event
from app.services.workflow import enqueue_publication_task
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


def publish_task_with_mock_adapter(db: Session, publication_task_id: UUID) -> PublicationTask:
    task = get_publication_task_or_404(db, publication_task_id)
    if task.status == PublicationStatus.published:
        return task

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

    remote_id = f"mock-{task.platform.value}-{uuid4().hex[:12]}"
    remote_url = f"https://example.local/{task.platform.value}/posts/{remote_id}"
    result = PublicationResult(
        publication_task_id=task.id,
        status=PublicationStatus.published,
        remote_id=remote_id,
        remote_url=remote_url,
        payload={
            "adapter": "mock-publication-v1",
            "platform": task.platform.value,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": task.idempotency_key,
        },
    )
    task.status = PublicationStatus.published
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
            "remote_url": remote_url,
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

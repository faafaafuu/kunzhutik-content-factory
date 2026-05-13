from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.approval_task import ApprovalTask
from app.models.upload import Upload
from app.services.audit import log_event
from app.services.workflow import enqueue_approval_dispatch
from shared.enums import ApprovalStatus, ApprovalTrigger, PipelineStatus


def get_approval_task(db: Session, approval_task_id: UUID) -> ApprovalTask | None:
    return db.query(ApprovalTask).filter(ApprovalTask.id == approval_task_id).first()


def dispatch_approval_task(db: Session, approval_task_id: UUID) -> ApprovalTask:
    task = get_approval_task(db, approval_task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Approval task not found")
    enqueue_approval_dispatch(task.id)
    return task


def apply_approval_decision(
    db: Session,
    task: ApprovalTask,
    decision: str,
    actor: str,
    note: str | None,
    via: ApprovalTrigger,
) -> ApprovalTask:
    task.status = ApprovalStatus(decision)
    task.decided_by = actor
    task.decision_note = note
    task.decided_via = via
    task.decided_at = datetime.now(timezone.utc)
    log_event(
        db,
        task.project_id,
        "upload",
        str(task.upload_id),
        f"approval.{decision}",
        actor,
        {"approval_task_id": str(task.id), "note": note, "via": via.value},
    )
    upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
    if upload:
        if task.status == ApprovalStatus.approved:
            upload.status = PipelineStatus.completed
        elif task.status in {ApprovalStatus.rejected, ApprovalStatus.regenerate_requested}:
            upload.status = PipelineStatus.needs_review
        log_event(
            db,
            task.project_id,
            "upload",
            str(task.upload_id),
            "upload.status_updated",
            "approval-service",
            {"status": upload.status.value, "approval_task_id": str(task.id)},
        )
    db.commit()
    db.refresh(task)
    return task

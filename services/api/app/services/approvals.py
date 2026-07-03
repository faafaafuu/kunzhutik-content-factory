from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.approval_task import ApprovalTask
from app.models.upload import Upload
from app.services.audit import log_event
from app.services.publications import create_publication_tasks_for_upload
from app.services.workflow import enqueue_approval_dispatch, enqueue_video_stage
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
    video_stage_plan_id: str | None = None
    if upload:
        if task.status == ApprovalStatus.approved:
            if task.stage == "content":
                # Scenario approved: the only paid step (video generation) starts now.
                video_stage_plan_id = (task.preview_payload or {}).get("scene_plan_id")
                if not video_stage_plan_id:
                    raise HTTPException(status_code=409, detail="Content approval has no scene_plan_id to produce video from")
                upload.status = PipelineStatus.processing
                log_event(
                    db,
                    task.project_id,
                    "upload",
                    str(task.upload_id),
                    "video_stage.enqueued",
                    "approval-service",
                    {"scene_plan_id": video_stage_plan_id, "approval_task_id": str(task.id)},
                )
            else:
                upload.status = PipelineStatus.completed
                publication_tasks = create_publication_tasks_for_upload(db, task.upload_id, actor=actor)
                log_event(
                    db,
                    task.project_id,
                    "upload",
                    str(task.upload_id),
                    "publication_tasks.ready",
                    "approval-service",
                    {"count": len(publication_tasks), "approval_task_id": str(task.id)},
                )
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
    if video_stage_plan_id:
        enqueue_video_stage(task.upload_id, UUID(video_stage_plan_id))
    return task

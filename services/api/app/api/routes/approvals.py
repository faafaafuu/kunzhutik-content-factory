from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.approval import ApprovalDecisionRequest, ApprovalRead
from app.services.approvals import apply_approval_decision, dispatch_approval_task, get_approval_task

router = APIRouter(prefix="/approval-tasks", tags=["approval-tasks"])


@router.post("/{approval_task_id}/dispatch", response_model=ApprovalRead)
def dispatch(approval_task_id: UUID, db: Session = Depends(get_db)) -> ApprovalRead:
    task = dispatch_approval_task(db, approval_task_id)
    return ApprovalRead.model_validate(task)


@router.post("/{approval_task_id}/decision", response_model=ApprovalRead)
def decide(approval_task_id: UUID, payload: ApprovalDecisionRequest, db: Session = Depends(get_db)) -> ApprovalRead:
    task = get_approval_task(db, approval_task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Approval task not found")
    task = apply_approval_decision(
        db=db,
        task=task,
        decision=payload.decision,
        actor=payload.actor,
        note=payload.note,
        via=payload.via,
    )
    return ApprovalRead.model_validate(task)


from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_operator
from app.models.operator_user import OperatorUser
from app.schemas.publication import PublicationRunRequest, PublicationTaskListResponse, PublicationTaskRead, PublicationTaskWithResults
from app.services.publications import enqueue_publication, list_publication_results, list_publication_tasks

router = APIRouter(prefix="/publication-tasks", tags=["publication-tasks"])


@router.get("", response_model=PublicationTaskListResponse)
def get_publication_tasks(
    upload_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: OperatorUser = Depends(require_operator),
) -> PublicationTaskListResponse:
    tasks = list_publication_tasks(db, upload_id=upload_id)
    result_map = list_publication_results(db, [task.id for task in tasks])
    return PublicationTaskListResponse(
        publication_tasks=[
            PublicationTaskWithResults(
                **PublicationTaskRead.model_validate(task).model_dump(),
                results=result_map.get(task.id, []),
            )
            for task in tasks
        ]
    )


@router.post("/{publication_task_id}/run", response_model=PublicationTaskRead)
def run_publication_task(
    publication_task_id: UUID,
    payload: PublicationRunRequest,
    db: Session = Depends(get_db),
    user: OperatorUser = Depends(require_operator),
) -> PublicationTaskRead:
    task = enqueue_publication(db, publication_task_id, actor=f"dashboard:{user.username}")
    return PublicationTaskRead.model_validate(task)

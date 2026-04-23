from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.upload import UploadRead, UploadTimelineEvent
from app.services.uploads import create_upload_with_file, get_upload_or_404, get_upload_timeline

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadRead, status_code=status.HTTP_201_CREATED)
async def create_upload(
    project_id: UUID = Form(...),
    created_by: str = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadRead:
    upload = await create_upload_with_file(
        db=db,
        project_id=project_id,
        created_by=created_by,
        notes=notes,
        incoming_file=file,
    )
    return UploadRead.model_validate(upload)


@router.get("/{upload_id}", response_model=UploadRead)
def get_upload(upload_id: UUID, db: Session = Depends(get_db)) -> UploadRead:
    upload = get_upload_or_404(db, upload_id)
    return UploadRead.model_validate(upload)


@router.get("/{upload_id}/timeline", response_model=list[UploadTimelineEvent])
def get_timeline(upload_id: UUID, db: Session = Depends(get_db)) -> list[UploadTimelineEvent]:
    upload = get_upload_or_404(db, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return get_upload_timeline(db, upload_id)


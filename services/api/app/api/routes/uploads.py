from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.publication import PublicationTaskRead, PublicationTaskWithResults
from app.schemas.upload import UploadAssetsResponse, UploadAssetRead, UploadListResponse, UploadPipelineSummary, UploadRead, UploadTimelineEvent
from app.services.uploads import (
    create_upload_with_file,
    get_upload_asset_bytes,
    get_upload_assets,
    get_upload_or_404,
    get_upload_pipeline_summary,
    get_upload_timeline,
    list_uploads,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("", response_model=UploadListResponse)
def get_uploads(limit: int = Query(default=30, ge=1, le=100), db: Session = Depends(get_db)) -> UploadListResponse:
    return UploadListResponse(uploads=[UploadRead.model_validate(upload) for upload in list_uploads(db, limit=limit)])


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


@router.get("/{upload_id}/pipeline", response_model=UploadPipelineSummary)
def get_pipeline(upload_id: UUID, request: Request, db: Session = Depends(get_db)) -> UploadPipelineSummary:
    summary = get_upload_pipeline_summary(db, upload_id)
    assets = [
        UploadAssetRead(
            **asset,
            download_url=str(request.url_for("download_upload_asset", upload_id=upload_id, asset_id=asset["id"])),
        )
        for asset in summary["assets"]
    ]
    return UploadPipelineSummary(
        upload=UploadRead.model_validate(summary["upload"]),
        analysis_results=summary["analysis_results"],
        drafts=summary["drafts"],
        approvals=summary["approvals"],
        publication_tasks=[
            PublicationTaskWithResults(
                **PublicationTaskRead.model_validate(task).model_dump(),
                results=summary["publication_results"].get(task.id, []),
            )
            for task in summary["publication_tasks"]
        ],
        assets=assets,
        timeline=summary["timeline"],
    )


@router.get("/{upload_id}/assets", response_model=UploadAssetsResponse)
def list_assets(upload_id: UUID, request: Request, db: Session = Depends(get_db)) -> UploadAssetsResponse:
    get_upload_or_404(db, upload_id)
    assets = []
    for asset in get_upload_assets(db, upload_id):
        assets.append(
            UploadAssetRead(
                **asset,
                download_url=str(request.url_for("download_upload_asset", upload_id=upload_id, asset_id=asset["id"])),
            )
        )
    return UploadAssetsResponse(upload_id=upload_id, assets=assets)


@router.get("/{upload_id}/assets/{asset_id}/download", name="download_upload_asset")
def download_asset(upload_id: UUID, asset_id: UUID, db: Session = Depends(get_db)) -> Response:
    asset, content = get_upload_asset_bytes(db, upload_id, asset_id)
    headers = {"Content-Disposition": f'inline; filename="{asset.file_name}"'}
    return Response(content=content, media_type=asset.mime_type, headers=headers)

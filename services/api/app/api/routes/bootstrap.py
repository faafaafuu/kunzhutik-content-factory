from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.schemas.project import BootstrapResponse
from app.services.bootstrap import ensure_default_project

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


@router.post("/default", response_model=BootstrapResponse)
def bootstrap_default(db: Session = Depends(get_db)) -> BootstrapResponse:
    return ensure_default_project(db)


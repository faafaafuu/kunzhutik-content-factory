from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.audit import log_event
from app.services.character import create_default_character

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return [ProjectRead.model_validate(project) for project in db.query(Project).order_by(Project.created_at.desc()).all()]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    existing = db.query(Project).filter(Project.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Project slug already exists")

    project = Project(name=payload.name, slug=payload.slug, description=payload.description)
    db.add(project)
    db.flush()
    create_default_character(db=db, project=project, name=payload.character_name)
    log_event(db, project.id, "project", str(project.id), "project.created", payload.created_by, {"slug": payload.slug})
    db.commit()
    db.refresh(project)
    return ProjectRead.model_validate(project)


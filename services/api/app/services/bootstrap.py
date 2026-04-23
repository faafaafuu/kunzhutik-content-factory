from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.character_profile import CharacterProfile
from app.models.project import Project
from app.schemas.project import BootstrapResponse
from app.services.audit import log_event
from app.services.character import create_default_character


def ensure_default_project(db: Session) -> BootstrapResponse:
    project = db.query(Project).filter(Project.slug == settings.default_project_slug).first()
    if not project:
        project = Project(name=settings.default_project_name, slug=settings.default_project_slug)
        db.add(project)
        db.flush()
        character = create_default_character(db, project, settings.default_character_name)
        log_event(db, project.id, "project", str(project.id), "project.bootstrapped", "system", {})
        db.commit()
        return BootstrapResponse(project_id=project.id, character_profile_id=character.id, project_slug=project.slug)

    character = (
        db.query(CharacterProfile)
        .filter(CharacterProfile.project_id == project.id, CharacterProfile.is_default.is_(True))
        .first()
    )
    if not character:
        character = create_default_character(db, project, settings.default_character_name)
        db.commit()
    return BootstrapResponse(project_id=project.id, character_profile_id=character.id, project_slug=project.slug)


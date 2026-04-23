from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel, Timestamped


class ProjectCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    created_by: str
    character_name: str = "Кунжутик"


class ProjectRead(Timestamped):
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool


class BootstrapResponse(BaseModel):
    project_id: UUID
    character_profile_id: UUID
    project_slug: str


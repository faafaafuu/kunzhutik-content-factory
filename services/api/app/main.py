from fastapi import FastAPI

from app.api.routes import approvals, bootstrap, health, projects, uploads
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(health.router)
app.include_router(bootstrap.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")


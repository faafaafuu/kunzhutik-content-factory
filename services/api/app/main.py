from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import approvals, bootstrap, health, projects, storefront, uploads
from app.core.config import settings

app = FastAPI(title=settings.app_name)

WEB_DIR = Path(__file__).resolve().parent / "web"

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

app.include_router(storefront.router)
app.include_router(health.router)
app.include_router(bootstrap.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")

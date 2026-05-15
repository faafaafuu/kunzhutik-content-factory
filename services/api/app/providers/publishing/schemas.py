from __future__ import annotations

from pydantic import BaseModel, Field


class PublishResult(BaseModel):
    status: str
    remote_id: str | None = None
    remote_url: str | None = None
    error_message: str | None = None
    raw_response: dict = Field(default_factory=dict)

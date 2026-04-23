from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel
from shared.enums import ApprovalStatus, ApprovalTrigger


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected", "regenerate_requested"]
    actor: str
    note: str | None = None
    via: ApprovalTrigger = ApprovalTrigger.dashboard


class ApprovalRead(ORMModel):
    id: UUID
    project_id: UUID
    upload_id: UUID
    status: ApprovalStatus
    telegram_chat_id: str | None = None
    telegram_message_id: str | None = None
    preview_payload: dict
    decision_note: str | None = None
    decided_by: str | None = None
    decided_via: ApprovalTrigger | None = None
    dispatched_at: datetime | None = None
    decided_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def log_event(
    db: Session,
    project_id,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor: str,
    payload: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
    )
    db.add(event)
    db.flush()
    return event


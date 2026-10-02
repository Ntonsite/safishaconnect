import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core import context
from app.core.logging import get_logger
from app.models import AuditLog, User

log = get_logger("audit")


def record(
    db: Session,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details,
            # Defaults to the caller of the current request (already resolved through trusted proxies only).
            ip_address=ip_address or context.client_ip(),
        )
    )
    log.info(
        action, extra={"actor_id": str(actor.id) if actor else None, "entity": entity_type, "entity_id": str(entity_id)}
    )

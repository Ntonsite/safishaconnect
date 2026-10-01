import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update

from app.core.errors import NotFoundError
from app.models import Notification
from app.schemas.common import ORMModel
from app.security.deps import CurrentUser, DbSession
from app.utils.clock import utcnow

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(ORMModel):
    id: uuid.UUID
    type: str
    title: str
    body: str
    booking_id: uuid.UUID | None
    booking_reference: str | None
    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]


@router.get("", response_model=NotificationList)
def list_notifications(
    user: CurrentUser, db: DbSession, limit: int = Query(default=30, ge=1, le=100)
) -> NotificationList:
    items = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    ).all()
    unread = db.scalar(
        select(func.count(Notification.id)).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return NotificationList(unread=unread or 0, items=[NotificationOut.model_validate(n) for n in items])


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: uuid.UUID, user: CurrentUser, db: DbSession) -> NotificationOut:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise NotFoundError("Notification not found.")
    if not n.is_read:
        n.is_read, n.read_at = True, utcnow()
        db.commit()
    return NotificationOut.model_validate(n)


@router.post("/read-all", response_model=NotificationList)
def mark_all_read(user: CurrentUser, db: DbSession) -> NotificationList:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=utcnow())
    )
    db.commit()
    return list_notifications(user, db, limit=30)

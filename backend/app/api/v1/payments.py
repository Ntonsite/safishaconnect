"""Payment endpoints shared by providers and admins."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.models import Provider, User
from app.models.enums import RoleCode
from app.schemas.booking import PaymentSummary
from app.security.deps import DbSession, require_roles
from app.services import payments
from app.services.locks import lock_booking

router = APIRouter(prefix="/payments", tags=["payments"])


class CashConfirmIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


@router.post("/bookings/{booking_id}/confirm-cash", response_model=PaymentSummary)
def confirm_cash(
    booking_id: uuid.UUID,
    data: CashConfirmIn,
    db: DbSession,
    user: Annotated[User, Depends(require_roles(RoleCode.PROVIDER, RoleCode.ADMIN))],
) -> PaymentSummary:
    booking = lock_booking(db, booking_id)  # serialises provider + admin confirmations of the same cash
    if user.role_code == RoleCode.PROVIDER:
        provider_id = db.scalar(select(Provider.id).where(Provider.user_id == user.id))
        # Only the provider who did the job can confirm they collected the cash.
        if booking.provider_id is None or booking.provider_id != provider_id:
            raise NotFoundError("Booking not found.")
    payment = payments.confirm_cash(db, booking, user, data.note)
    db.commit()
    out = PaymentSummary.model_validate(payment)
    out.confirmed_by_name = user.full_name
    return out

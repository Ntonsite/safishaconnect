import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PaymentStatus, ProviderType, SettlementStatus, VerificationStatus


class StatsOut(BaseModel):
    currency: str
    total_customers: int
    active_providers: int
    providers_awaiting_verification: int
    total_bookings: int
    todays_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    gross_booking_value: Decimal
    platform_commission: Decimal
    pending_assignments: int
    open_complaints: int
    cash_awaiting_confirmation: int
    settlements_pending_amount: Decimal
    bookings_by_status: dict[str, int]


class CustomerRow(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    phone: str
    email: str | None
    is_active: bool
    bookings_count: int
    total_spent: Decimal
    created_at: datetime


class ProviderRow(BaseModel):
    id: uuid.UUID
    display_name: str
    provider_type: ProviderType
    phone: str
    email: str | None
    verification_status: VerificationStatus
    is_active: bool
    is_accepting_jobs: bool
    rating_average: Decimal
    rating_count: int
    completed_jobs: int
    area_names: list[str]
    service_names: list[str]
    created_at: datetime


class VerificationAction(BaseModel):
    action: str = Field(pattern="^(APPROVE|REJECT|SUSPEND|REACTIVATE)$")
    notes: str | None = Field(default=None, max_length=1000)


class ActiveToggle(BaseModel):
    is_active: bool


class SettingOut(BaseModel):
    key: str
    value: str
    description: str


class SettingUpdate(BaseModel):
    value: str = Field(min_length=1, max_length=40)


class AuditOut(BaseModel):
    id: uuid.UUID
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any] | None
    created_at: datetime


class PaymentRow(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    booking_reference: str
    booking_status: str
    customer_name: str
    provider_name: str | None
    method: PaymentMethod
    status: PaymentStatus
    amount: Decimal
    currency: str
    paid_at: datetime | None
    confirmed_by_name: str | None
    created_at: datetime


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus
    note: str | None = Field(default=None, max_length=500)


class SettlementRow(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    booking_reference: str
    provider_id: uuid.UUID
    provider_name: str
    gross_amount: Decimal
    commission_amount: Decimal
    provider_earning: Decimal
    cash_collected_by_provider: bool
    status: SettlementStatus
    settled_at: datetime | None
    reference: str | None
    note: str | None
    created_at: datetime


class SettleIn(BaseModel):
    reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)

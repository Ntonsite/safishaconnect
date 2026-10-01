import uuid
from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ProviderType, SettlementStatus, VerificationDecision, VerificationStatus
from app.schemas.catalog import AreaOut
from app.schemas.common import ORMModel


class AvailabilityDay(ORMModel):
    day_of_week: int = Field(ge=1, le=7)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def _window(self) -> "AvailabilityDay":
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time.")
        return self


class VerificationEvent(ORMModel):
    decision: VerificationDecision
    notes: str | None
    created_at: datetime


class ServiceBrief(BaseModel):
    id: uuid.UUID
    slug: str
    name_en: str
    name_sw: str


class ProviderProfile(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    provider_type: ProviderType
    display_name: str
    contact_person: str | None
    full_name: str
    phone: str
    email: str | None
    bio: str
    years_experience: int
    registration_number: str | None
    verification_status: VerificationStatus
    verified_at: datetime | None
    is_accepting_jobs: bool
    capacity: int
    rating_average: Decimal
    rating_count: int
    is_active: bool
    services: list[ServiceBrief]
    areas: list[AreaOut]
    availability: list[AvailabilityDay]
    verification_history: list[VerificationEvent]
    created_at: datetime


class ProviderUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    contact_person: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    years_experience: int | None = Field(default=None, ge=0, le=60)
    is_accepting_jobs: bool | None = None
    capacity: int | None = Field(default=None, ge=1, le=50)


class IdList(BaseModel):
    ids: list[uuid.UUID] = Field(max_length=100)


class AvailabilityUpdate(BaseModel):
    days: list[AvailabilityDay] = Field(max_length=7)


class ProviderDashboard(BaseModel):
    verification_status: VerificationStatus
    is_accepting_jobs: bool
    open_offers: int
    active_jobs: int
    completed_jobs: int
    rating_average: Decimal
    rating_count: int
    earnings_total: Decimal
    earnings_pending: Decimal
    currency: str
    setup_complete: bool
    missing_setup: list[str]


class EarningRow(BaseModel):
    booking_id: uuid.UUID
    reference: str
    service_name: str
    scheduled_date: datetime | str
    status: str
    total_amount: Decimal
    commission_amount: Decimal
    provider_earning: Decimal
    payment_status: str | None
    settlement_status: SettlementStatus | None
    settled_at: datetime | None
    settlement_reference: str | None


class EarningsOut(BaseModel):
    currency: str
    total_earned: Decimal
    pending_settlement: Decimal
    settled: Decimal
    awaiting_completion: Decimal
    rows: list[EarningRow]

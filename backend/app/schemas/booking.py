import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AssignmentStatus, BookingStatus, PaymentMethod, PaymentStatus, ProviderType
from app.schemas.common import ORMModel


class AddonSelection(BaseModel):
    option_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=50)


class QuoteRequest(BaseModel):
    service_id: uuid.UUID
    property_type_option_id: uuid.UUID | None = None
    size_option_id: uuid.UUID | None = None
    bedrooms: int = Field(default=0, ge=0, le=30)
    bathrooms: int = Field(default=0, ge=0, le=30)
    addons: list[AddonSelection] = Field(default_factory=list, max_length=20)


class QuoteLine(BaseModel):
    kind: str
    code: str
    label_en: str
    label_sw: str
    quantity: int
    unit_amount: Decimal
    amount: Decimal


class QuoteOut(BaseModel):
    service_id: uuid.UUID
    currency: str
    lines: list[QuoteLine]
    base_amount: Decimal
    adjustments_amount: Decimal
    total_amount: Decimal
    estimated_duration_minutes: int


class SlotOut(BaseModel):
    start_time: time
    end_time: time
    available: bool


class AvailabilityOut(BaseModel):
    date: date
    duration_minutes: int
    slots: list[SlotOut]


class BookingCreate(QuoteRequest):
    area_id: uuid.UUID
    address_line: str = Field(min_length=3, max_length=255)
    landmark: str | None = Field(default=None, max_length=255)
    special_instructions: str | None = Field(default=None, max_length=1000)
    scheduled_date: date
    scheduled_start_time: time
    payment_method: PaymentMethod = PaymentMethod.CASH
    confirm: bool = Field(default=True, description="Confirm immediately and start provider matching.")

    @field_validator("address_line", "landmark", "special_instructions", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return (value.strip() or None) if isinstance(value, str) else value


class ReasonIn(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class ProviderPublic(BaseModel):
    id: uuid.UUID
    display_name: str
    provider_type: ProviderType
    rating_average: Decimal
    rating_count: int
    years_experience: int
    phone: str | None = None


class PartyContact(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None = None
    email: str | None = None


class StatusEvent(BaseModel):
    from_status: BookingStatus | None
    to_status: BookingStatus
    note: str | None
    actor_name: str | None
    actor_role: str | None
    created_at: datetime


class PaymentSummary(ORMModel):
    id: uuid.UUID
    method: PaymentMethod
    status: PaymentStatus
    amount: Decimal
    currency: str
    paid_at: datetime | None
    confirmed_by_name: str | None = None


class ReviewSummary(ORMModel):
    id: uuid.UUID
    rating: int
    comment: str | None
    is_hidden: bool
    created_at: datetime


class AssignmentSummary(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str
    status: AssignmentStatus
    is_manual: bool
    offered_at: datetime
    expires_at: datetime | None
    responded_at: datetime | None
    response_note: str | None


class OptionRef(BaseModel):
    id: uuid.UUID
    code: str
    name_en: str
    name_sw: str


class ServiceRef(BaseModel):
    id: uuid.UUID
    slug: str
    name_en: str
    name_sw: str
    icon: str


class BookingSummary(BaseModel):
    id: uuid.UUID
    reference: str
    status: BookingStatus
    service: ServiceRef
    service_name: str
    area_id: uuid.UUID
    area_name: str
    scheduled_date: date
    scheduled_start_time: time
    estimated_duration_minutes: int
    total_amount: Decimal
    currency: str
    payment_method: PaymentMethod
    payment_status: PaymentStatus | None
    provider_name: str | None
    customer_name: str | None = None
    created_at: datetime


class BookingDetail(BookingSummary):
    address_line: str | None
    landmark: str | None
    bedrooms: int
    bathrooms: int
    property_type: OptionRef | None
    size: OptionRef | None
    special_instructions: str | None
    base_amount: Decimal
    adjustments_amount: Decimal
    # Economics are hidden (null) for customers.
    commission_percent: Decimal | None = None
    commission_amount: Decimal | None = None
    provider_earning: Decimal | None = None
    price_items: list[QuoteLine]
    history: list[StatusEvent]
    provider: ProviderPublic | None
    customer: PartyContact | None
    payment: PaymentSummary | None
    review: ReviewSummary | None
    assignments: list[AssignmentSummary] | None = None
    has_open_complaint: bool = False
    allowed_actions: list[str]
    confirmed_at: datetime | None
    completed_at: datetime | None
    customer_confirmed_at: datetime | None
    closed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None


class JobOut(BaseModel):
    """A provider's view of an assignment (offer or accepted job)."""

    assignment_id: uuid.UUID
    assignment_status: AssignmentStatus
    offered_at: datetime
    expires_at: datetime | None
    responded_at: datetime | None
    booking: BookingDetail


class ManualAssignIn(BaseModel):
    provider_id: uuid.UUID
    direct: bool = Field(
        default=True, description="Assign immediately (provider already agreed) instead of sending an offer."
    )
    note: str | None = Field(default=None, max_length=255)


class AdminStatusIn(BaseModel):
    status: BookingStatus
    note: str | None = Field(default=None, max_length=255)


class EligibleProviderOut(BaseModel):
    id: uuid.UUID
    display_name: str
    provider_type: ProviderType
    rating_average: Decimal
    rating_count: int
    jobs_that_day: int

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ComplaintCategory, ComplaintStatus


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    booking_reference: str
    service_name: str
    provider_id: uuid.UUID
    provider_name: str
    customer_name: str
    rating: int
    comment: str | None
    is_hidden: bool
    moderation_note: str | None
    created_at: datetime


class PublicReview(BaseModel):
    rating: int
    comment: str | None
    customer_first_name: str
    area_name: str
    service_name: str
    created_at: datetime


class ReviewModerate(BaseModel):
    is_hidden: bool
    moderation_note: str | None = Field(default=None, max_length=255)


class ComplaintCreate(BaseModel):
    booking_id: uuid.UUID
    category: ComplaintCategory
    description: str = Field(min_length=10, max_length=2000)


class ComplaintOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    booking_reference: str
    booking_status: str
    customer_name: str
    provider_name: str | None
    category: ComplaintCategory
    description: str
    status: ComplaintStatus
    admin_notes: str | None
    resolution: str | None
    resolved_at: datetime | None
    created_at: datetime


class ComplaintUpdate(BaseModel):
    status: ComplaintStatus
    admin_notes: str | None = Field(default=None, max_length=2000)
    resolution: str | None = Field(default=None, max_length=2000)

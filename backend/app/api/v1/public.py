"""Unauthenticated catalogue endpoints: config, services, areas, quotes, slots."""

import uuid
from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models import City, Review, Service, ServiceArea
from app.schemas.booking import AvailabilityOut, QuoteLine, QuoteOut, QuoteRequest
from app.schemas.catalog import AreaOut, ServiceOut
from app.schemas.feedback import PublicReview
from app.security.deps import DbSession
from app.services import bookings as booking_service
from app.services import payments
from app.services.pricing import calculate_quote

router = APIRouter(tags=["catalog"])


class PaymentMethodOut(BaseModel):
    method: str
    available: bool
    status: str


class BrandOut(BaseModel):
    app_name: str
    tagline: str
    logo_url: str
    support_email: str
    support_phone: str
    support_whatsapp: str
    office_address: str


class DemoAccount(BaseModel):
    role: str
    email: str
    password: str


class PublicConfig(BaseModel):
    brand: BrandOut
    currency: str
    default_locale: str
    supported_locales: list[str]
    timezone: str
    demo_mode: bool
    payment_methods: list[PaymentMethodOut]
    booking_slot_start_hour: int
    booking_slot_end_hour: int
    # Only populated when DEMO_MODE is on (never in production, which refuses demo mode).
    demo_accounts: list[DemoAccount] = []


DEMO_ACCOUNTS = (
    ("admin", "admin@safishacon.local"),
    ("customer", "customer@safishacon.local"),
    ("cleaner", "cleaner@safishacon.local"),
    ("company", "provider@safishacon.local"),
)


@router.get("/config", response_model=PublicConfig)
def public_config() -> PublicConfig:
    s = get_settings()
    return PublicConfig(
        brand=BrandOut(
            app_name=s.app_name,
            tagline=s.app_tagline,
            logo_url=s.app_logo_url,
            support_email=s.support_email,
            support_phone=s.support_phone,
            support_whatsapp=s.support_whatsapp,
            office_address=s.office_address,
        ),
        currency=s.default_currency,
        default_locale=s.default_locale,
        supported_locales=["en", "sw"],
        timezone=s.timezone,
        demo_mode=s.demo_mode,
        payment_methods=[
            PaymentMethodOut(method=m.method, available=m.available, status=m.status)
            for m in payments.payment_methods()
        ],
        booking_slot_start_hour=s.booking_slot_start_hour,
        booking_slot_end_hour=s.booking_slot_end_hour,
        demo_accounts=[DemoAccount(role=r, email=e, password=s.seed_demo_password) for r, e in DEMO_ACCOUNTS]
        if s.demo_mode
        else [],
    )


def _with_active_options(service: Service) -> ServiceOut:
    out = ServiceOut.model_validate(service)
    out.options = [o for o in out.options if o.is_active]
    return out


@router.get("/services", response_model=list[ServiceOut])
def list_services(db: DbSession) -> list[ServiceOut]:
    services = db.scalars(
        select(Service)
        .where(Service.is_active.is_(True))
        .options(selectinload(Service.options))
        .order_by(Service.display_order)
    ).all()
    return [_with_active_options(s) for s in services]


@router.get("/services/{key}", response_model=ServiceOut)
def get_service(key: str, db: DbSession) -> ServiceOut:
    try:
        cond = Service.id == uuid.UUID(key)
    except ValueError:
        cond = Service.slug == key
    service = db.scalar(select(Service).where(cond, Service.is_active.is_(True)))
    if service is None:
        raise NotFoundError("Service not found.", code="SERVICE_NOT_FOUND")
    return _with_active_options(service)


@router.get("/areas", response_model=list[AreaOut])
def list_areas(db: DbSession, city_id: uuid.UUID | None = None) -> list[AreaOut]:
    stmt = (
        select(ServiceArea)
        .join(City)
        .where(ServiceArea.is_active.is_(True), City.is_active.is_(True))
        .order_by(City.name, ServiceArea.name)
    )
    if city_id:
        stmt = stmt.where(ServiceArea.city_id == city_id)
    return [AreaOut.model_validate(a) for a in db.scalars(stmt)]


@router.post("/quotes", response_model=QuoteOut)
def quote(data: QuoteRequest, db: DbSession) -> QuoteOut:
    q = calculate_quote(db, data)
    return QuoteOut(
        service_id=q.service.id,
        currency=q.currency,
        lines=[
            QuoteLine(
                kind=ln.kind,
                code=ln.code,
                label_en=ln.label_en,
                label_sw=ln.label_sw,
                quantity=ln.quantity,
                unit_amount=ln.unit_amount,
                amount=ln.amount,
            )
            for ln in q.lines
        ],
        base_amount=q.base_amount,
        adjustments_amount=q.adjustments_amount,
        total_amount=q.total_amount,
        estimated_duration_minutes=q.duration_minutes,
    )


@router.get("/availability", response_model=AvailabilityOut)
def availability(
    db: DbSession,
    service_id: uuid.UUID,
    area_id: uuid.UUID,
    day: date = Query(alias="date"),
    duration_minutes: int = Query(ge=30, le=16 * 60),
) -> AvailabilityOut:
    return booking_service.slots(db, service_id, area_id, day, duration_minutes)


@router.get("/reviews/public", response_model=list[PublicReview])
def public_reviews(db: DbSession, limit: int = Query(default=6, ge=1, le=20)) -> list[PublicReview]:
    reviews = db.scalars(
        select(Review)
        .where(Review.is_hidden.is_(False), Review.rating >= 4, Review.comment.is_not(None))
        .order_by(Review.created_at.desc())
        .limit(limit)
    ).all()
    return [
        PublicReview(
            rating=r.rating,
            comment=r.comment,
            customer_first_name=r.customer.user.full_name.split()[0],
            area_name=r.booking.area.name,
            service_name=r.booking.service_name_snapshot,
            created_at=r.created_at,
        )
        for r in reviews
    ]

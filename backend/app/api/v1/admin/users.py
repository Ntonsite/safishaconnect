"""Admin: customers and providers."""

import uuid
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, or_, select

from app.api.v1.admin.common import PagingDep, admin_only, paginate
from app.core.errors import NotFoundError
from app.models import Booking, Customer, Provider, ProviderServiceArea, Review, ServiceArea, User
from app.models.enums import BookingStatus, ProviderType, RoleCode, VerificationStatus
from app.schemas.admin import ActiveToggle, CustomerRow, ProviderRow, VerificationAction
from app.schemas.booking import BookingSummary
from app.schemas.common import Page
from app.schemas.feedback import ReviewOut
from app.schemas.provider import ProviderProfile
from app.security.deps import AdminUser, DbSession
from app.services import audit, booking_views, feedback, provider_profile

router = APIRouter(dependencies=admin_only)


def _search(term: str | None):
    if not term:
        return None
    like = f"%{term.strip()}%"
    return or_(User.full_name.ilike(like), User.email.ilike(like), User.phone.ilike(like))


def _customer_rows(db, customers: list[Customer]) -> list[CustomerRow]:
    ids = [c.id for c in customers]
    agg = {
        cid: (count, spent)
        for cid, count, spent in db.execute(
            select(
                Booking.customer_id,
                func.count(Booking.id),
                func.coalesce(func.sum(Booking.total_amount).filter(Booking.status == BookingStatus.CLOSED), 0),
            )
            .where(Booking.customer_id.in_(ids))
            .group_by(Booking.customer_id)
        )
    }
    return [
        CustomerRow(
            id=c.id,
            user_id=c.user_id,
            full_name=c.user.full_name,
            phone=c.user.phone,
            email=c.user.email,
            is_active=c.user.is_active,
            bookings_count=agg.get(c.id, (0, 0))[0],
            total_spent=Decimal(agg.get(c.id, (0, 0))[1]),
            created_at=c.user.created_at,
        )
        for c in customers
    ]


@router.get("/customers", response_model=Page[CustomerRow], tags=["admin: customers"])
def list_customers(db: DbSession, paging: PagingDep, q: str | None = None) -> Page[CustomerRow]:
    stmt = select(Customer).join(User, User.id == Customer.user_id).order_by(User.created_at.desc())
    if (cond := _search(q)) is not None:
        stmt = stmt.where(cond)
    customers, total = paginate(db, stmt, paging)
    items = _customer_rows(db, customers)
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@router.get("/customers/{customer_id}/bookings", response_model=list[BookingSummary], tags=["admin: customers"])
def customer_bookings(customer_id: uuid.UUID, db: DbSession) -> list[BookingSummary]:
    rows = db.scalars(
        select(Booking).where(Booking.customer_id == customer_id).order_by(Booking.scheduled_date.desc())
    ).unique()
    return [booking_views.summary(b, include_customer=True) for b in rows]


def _set_user_active(db, admin: User, user: User, active: bool, entity: str, entity_id) -> None:
    if user.role_code == RoleCode.ADMIN:
        raise NotFoundError("User not found.")
    user.is_active = active
    audit.record(
        db,
        admin,
        "ADMIN_ACTIVATED_USER" if active else "ADMIN_DEACTIVATED_USER",
        entity,
        entity_id,
        {"name": user.full_name},
    )


@router.patch("/customers/{customer_id}", response_model=CustomerRow, tags=["admin: customers"])
def toggle_customer(customer_id: uuid.UUID, data: ActiveToggle, db: DbSession, admin: AdminUser) -> CustomerRow:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found.")
    _set_user_active(db, admin, customer.user, data.is_active, "customer", customer.id)
    db.commit()
    return _customer_rows(db, [customer])[0]


def _provider_row(db, p: Provider) -> ProviderRow:
    return ProviderRow(
        id=p.id,
        display_name=p.display_name,
        provider_type=p.provider_type,
        phone=p.user.phone,
        email=p.user.email,
        verification_status=p.verification_status,
        is_active=p.user.is_active,
        is_accepting_jobs=p.is_accepting_jobs,
        rating_average=p.rating_average,
        rating_count=p.rating_count,
        completed_jobs=provider_profile.completed_jobs_count(db, p.id),
        area_names=sorted(a.area.name for a in p.areas),
        service_names=[s.service.name_en for s in sorted(p.services, key=lambda s: s.service.display_order)],
        created_at=p.created_at,
    )


@router.get("/providers", response_model=Page[ProviderRow], tags=["admin: providers"])
def list_providers(
    db: DbSession,
    paging: PagingDep,
    q: str | None = None,
    verification_status: VerificationStatus | None = None,
    provider_type: ProviderType | None = None,
    area_id: uuid.UUID | None = None,
) -> Page[ProviderRow]:
    stmt = select(Provider).join(User, User.id == Provider.user_id).order_by(Provider.created_at.desc())
    if q:
        stmt = stmt.where(or_(_search(q), Provider.display_name.ilike(f"%{q.strip()}%")))
    if verification_status:
        stmt = stmt.where(Provider.verification_status == verification_status)
    if provider_type:
        stmt = stmt.where(Provider.provider_type == provider_type)
    if area_id:
        stmt = stmt.where(Provider.areas.any(ProviderServiceArea.area_id == area_id))
    providers, total = paginate(db, stmt, paging)
    return Page(
        items=[_provider_row(db, p) for p in providers], total=total, page=paging.page, page_size=paging.page_size
    )


def _provider(db, provider_id: uuid.UUID) -> Provider:
    provider = db.get(Provider, provider_id)
    if provider is None:
        raise NotFoundError("Provider not found.")
    return provider


@router.get("/providers/{provider_id}", response_model=ProviderProfile, tags=["admin: providers"])
def get_provider(provider_id: uuid.UUID, db: DbSession) -> ProviderProfile:
    return provider_profile.profile_out(_provider(db, provider_id))


@router.get("/providers/{provider_id}/bookings", response_model=list[BookingSummary], tags=["admin: providers"])
def provider_bookings(provider_id: uuid.UUID, db: DbSession) -> list[BookingSummary]:
    rows = db.scalars(
        select(Booking).where(Booking.provider_id == provider_id).order_by(Booking.scheduled_date.desc())
    ).unique()
    return [booking_views.summary(b, include_customer=True) for b in rows]


@router.get("/providers/{provider_id}/reviews", response_model=list[ReviewOut], tags=["admin: providers"])
def provider_reviews(provider_id: uuid.UUID, db: DbSession) -> list[ReviewOut]:
    rows = db.scalars(select(Review).where(Review.provider_id == provider_id).order_by(Review.created_at.desc()))
    return [feedback.review_out(r) for r in rows.unique()]


@router.post("/providers/{provider_id}/verification", response_model=ProviderProfile, tags=["admin: providers"])
def verify_provider(
    provider_id: uuid.UUID, data: VerificationAction, db: DbSession, admin: AdminUser
) -> ProviderProfile:
    provider = _provider(db, provider_id)
    provider_profile.apply_verification(db, admin, provider, data.action, data.notes)
    db.commit()
    db.refresh(provider)
    return provider_profile.profile_out(provider)


@router.patch("/providers/{provider_id}", response_model=ProviderProfile, tags=["admin: providers"])
def toggle_provider(provider_id: uuid.UUID, data: ActiveToggle, db: DbSession, admin: AdminUser) -> ProviderProfile:
    provider = _provider(db, provider_id)
    _set_user_active(db, admin, provider.user, data.is_active, "provider", provider.id)
    db.commit()
    return provider_profile.profile_out(provider)


@router.get("/areas/{area_id}/providers", response_model=list[ProviderRow], tags=["admin: providers"])
def providers_in_area(area_id: uuid.UUID, db: DbSession) -> list[ProviderRow]:
    if db.get(ServiceArea, area_id) is None:
        raise NotFoundError("Area not found.")
    rows = db.scalars(select(Provider).where(Provider.areas.any(ProviderServiceArea.area_id == area_id))).unique()
    return [_provider_row(db, p) for p in rows]

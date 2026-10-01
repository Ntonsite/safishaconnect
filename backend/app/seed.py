"""Idempotent seed command.

    python -m app.seed                 # reference data + demo accounts/bookings (DEMO_MODE)
    python -m app.seed --reference-only  # roles, settings, areas and services only (production)

Running it repeatedly never duplicates records: everything is looked up by a natural key
(role code, email, slug, option code, booking reference) before being created.
"""

import argparse
import re
from datetime import time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.models import (
    Booking,
    BookingStatusHistory,
    City,
    Customer,
    Payment,
    PlatformSetting,
    Provider,
    ProviderAssignment,
    ProviderAvailability,
    ProviderService,
    ProviderServiceArea,
    ProviderVerification,
    Review,
    Role,
    Service,
    ServiceArea,
    ServiceOption,
    User,
)
from app.models.enums import (
    AssignmentStatus,
    BookingStatus,
    OptionGroup,
    PaymentMethod,
    PaymentStatus,
    ProviderType,
    RoleCode,
    VerificationDecision,
    VerificationStatus,
)
from app.schemas.booking import QuoteRequest
from app.security.passwords import hash_password
from app.seed_data import AREAS, CITY, SERVICES
from app.services import payments, platform_settings
from app.services.pricing import calculate_quote, split_commission
from app.services.provider_profile import recalculate_rating
from app.utils.clock import local_today, utcnow

log = get_logger("seed")


def _slug(*parts: str) -> str:
    return "-".join(re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-") for p in parts)


# ---------------------------------------------------------------------------- reference


def seed_roles(db: Session) -> None:
    for code, name in ((RoleCode.CUSTOMER, "Customer"), (RoleCode.PROVIDER, "Provider"), (RoleCode.ADMIN, "Admin")):
        if not db.scalar(select(Role).where(Role.code == code)):
            db.add(Role(code=code, name=name))
    db.flush()


def seed_settings(db: Session) -> None:
    for key, spec in platform_settings.SPECS.items():
        if db.get(PlatformSetting, key) is None:
            db.add(PlatformSetting(key=key, value=spec.default(), description=spec.description))


def seed_areas(db: Session) -> dict[str, ServiceArea]:
    city = db.scalar(select(City).where(City.name == CITY["name"], City.country_code == CITY["country_code"]))
    if city is None:
        city = City(**CITY)
        db.add(city)
        db.flush()
    areas = {}
    for name in AREAS:
        area = db.scalar(select(ServiceArea).where(ServiceArea.city_id == city.id, ServiceArea.name == name))
        if area is None:
            area = ServiceArea(city_id=city.id, name=name, slug=_slug(city.name, name))
            db.add(area)
        areas[name] = area
    db.flush()
    return areas


def seed_services(db: Session) -> dict[str, Service]:
    services = {}
    for spec in SERVICES:
        spec = dict(spec)
        property_types = spec.pop("property_types", [])
        sizes = spec.pop("sizes", [])
        addons = spec.pop("addons", [])
        service = db.scalar(select(Service).where(Service.slug == spec["slug"]))
        if service is None:
            service = Service(**spec)
            db.add(service)
            db.flush()
        existing = {o.code for o in db.scalars(select(ServiceOption).where(ServiceOption.service_id == service.id))}
        order = 0
        for group, rows in ((OptionGroup.PROPERTY_TYPE, property_types), (OptionGroup.SIZE, sizes)):
            for code, en, sw, price, minutes in rows:
                order += 1
                if code not in existing:
                    db.add(
                        ServiceOption(
                            service_id=service.id,
                            group=group,
                            code=code,
                            name_en=en,
                            name_sw=sw,
                            price_amount=Decimal(price),
                            duration_minutes=minutes,
                            display_order=order,
                        )
                    )
        for code, en, sw, price, minutes, max_qty in addons:
            order += 1
            if code not in existing:
                db.add(
                    ServiceOption(
                        service_id=service.id,
                        group=OptionGroup.ADDON,
                        code=code,
                        name_en=en,
                        name_sw=sw,
                        price_amount=price,
                        duration_minutes=minutes,
                        max_quantity=max_qty,
                        display_order=order,
                    )
                )
        services[service.slug] = service
    db.flush()
    for s in services.values():
        db.refresh(s)
    return services


def seed_reference(db: Session) -> tuple[dict[str, ServiceArea], dict[str, Service]]:
    seed_roles(db)
    seed_settings(db)
    areas = seed_areas(db)
    services = seed_services(db)
    return areas, services


# ---------------------------------------------------------------------------- demo


def _user(db: Session, *, email: str, phone: str, name: str, role: RoleCode, password: str, locale: str = "en") -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            phone=phone,
            full_name=name,
            password_hash=hash_password(password),
            role=db.scalar(select(Role).where(Role.code == role)),
            preferred_locale=locale,
        )
        db.add(user)
        db.flush()
    return user


def _provider(
    db: Session,
    user: User,
    *,
    provider_type: ProviderType,
    display_name: str,
    bio: str,
    years: int,
    capacity: int,
    services: list[Service],
    areas: list[ServiceArea],
    hours: dict[int, tuple[time, time]],
    status: VerificationStatus,
    contact_person: str | None = None,
    admin: User | None = None,
) -> Provider:
    provider = db.scalar(select(Provider).where(Provider.user_id == user.id))
    if provider is not None:
        return provider
    provider = Provider(
        user_id=user.id,
        provider_type=provider_type,
        display_name=display_name,
        contact_person=contact_person,
        bio=bio,
        years_experience=years,
        capacity=capacity,
        verification_status=status,
        verified_at=utcnow() if status == VerificationStatus.VERIFIED else None,
    )
    db.add(provider)
    db.flush()
    db.add_all(ProviderService(provider_id=provider.id, service_id=s.id) for s in services)
    db.add_all(ProviderServiceArea(provider_id=provider.id, area_id=a.id) for a in areas)
    db.add_all(
        ProviderAvailability(provider_id=provider.id, day_of_week=d, start_time=s, end_time=e)
        for d, (s, e) in hours.items()
    )
    db.add(
        ProviderVerification(
            provider_id=provider.id,
            decision=VerificationDecision.SUBMITTED,
            notes="Application submitted",
            created_at=utcnow(),
        )
    )
    if status == VerificationStatus.VERIFIED:
        db.add(
            ProviderVerification(
                provider_id=provider.id,
                decision=VerificationDecision.APPROVED,
                notes="ID, references and equipment checked (demo data)",
                reviewed_by_id=admin.id if admin else None,
                created_at=utcnow(),
            )
        )
    db.flush()
    return provider


def _demo_booking(
    db: Session,
    *,
    reference: str,
    customer: Customer,
    provider: Provider,
    service: Service,
    area: ServiceArea,
    days_from_today: int,
    start: time,
    bedrooms: int,
    bathrooms: int,
    path: list[BookingStatus],
    address: str,
) -> Booking | None:
    if db.scalar(select(Booking).where(Booking.reference == reference)):
        return None
    apartment = next(o for o in service.options if o.code == "apartment")
    quote = calculate_quote(
        db,
        QuoteRequest(
            service_id=service.id, property_type_option_id=apartment.id, bedrooms=bedrooms, bathrooms=bathrooms
        ),
    )
    econ = split_commission(quote.total_amount, platform_settings.commission_percent(db))
    booking = Booking(
        reference=reference,
        customer_id=customer.id,
        service_id=service.id,
        area_id=area.id,
        provider_id=provider.id,
        status=path[-1],
        address_line=address,
        landmark="Near the main road",
        property_type_option_id=apartment.id,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        scheduled_date=local_today() + timedelta(days=days_from_today),
        scheduled_start_time=start,
        estimated_duration_minutes=quote.duration_minutes,
        currency=quote.currency,
        service_name_snapshot=service.name_en,
        base_amount=quote.base_amount,
        adjustments_amount=quote.adjustments_amount,
        total_amount=quote.total_amount,
        commission_percent=econ.commission_percent,
        commission_amount=econ.commission_amount,
        provider_earning=econ.provider_earning,
        payment_method=PaymentMethod.CASH,
    )
    from app.services.bookings import price_items_from_quote

    booking.price_items = price_items_from_quote(quote)
    db.add(booking)
    db.flush()
    stamp = utcnow() - timedelta(days=max(1, -days_from_today) + 1)
    previous = None
    for status in path:
        stamp += timedelta(minutes=20)
        db.add(
            BookingStatusHistory(
                booking_id=booking.id,
                from_status=previous,
                to_status=status,
                changed_by_id=None,
                note="Demo data",
                created_at=stamp,
            )
        )
        previous = status
    db.add(
        ProviderAssignment(
            booking_id=booking.id,
            provider_id=provider.id,
            status=AssignmentStatus.ACCEPTED,
            offered_at=stamp,
            responded_at=stamp,
        )
    )
    db.add(
        Payment(
            booking_id=booking.id,
            method=PaymentMethod.CASH,
            status=PaymentStatus.PENDING,
            amount=booking.total_amount,
            currency=booking.currency,
            gateway="cash",
        )
    )
    db.flush()
    db.refresh(booking)
    return booking


def seed_demo(db: Session, areas: dict[str, ServiceArea], services: dict[str, Service]) -> None:
    pw = get_settings().seed_demo_password
    admin = _user(
        db,
        email="admin@safishacon.local",
        phone="+255700000001",
        name="Safisha Admin",
        role=RoleCode.ADMIN,
        password=pw,
    )
    cust_user = _user(
        db,
        email="customer@safishacon.local",
        phone="+255712000001",
        name="Neema Mwakyusa",
        role=RoleCode.CUSTOMER,
        password=pw,
    )
    customer = db.scalar(select(Customer).where(Customer.user_id == cust_user.id))
    if customer is None:
        customer = Customer(
            user_id=cust_user.id,
            default_area_id=areas["Mikocheni"].id,
            default_address="Plot 45, Mikocheni B, Old Bagamoyo Road",
        )
        db.add(customer)
        db.flush()

    weekdays = {d: (time(8, 0), time(18, 0)) for d in range(1, 7)}
    cleaner_user = _user(
        db,
        email="cleaner@safishacon.local",
        phone="+255713000002",
        name="Rehema Juma",
        role=RoleCode.PROVIDER,
        password=pw,
        locale="sw",
    )
    cleaner = _provider(
        db,
        cleaner_user,
        provider_type=ProviderType.INDIVIDUAL,
        display_name="Rehema Juma",
        bio="Professional home cleaner with 6 years' experience in Kinondoni and Mikocheni homes. "
        "Careful, punctual and great with deep cleans.",
        years=6,
        capacity=1,
        services=[services["general-home-cleaning"], services["deep-cleaning"], services["move-in-move-out"]],
        areas=[areas[n] for n in ("Mikocheni", "Kinondoni", "Sinza", "Mwenge", "Kijitonyama", "Msasani")],
        hours=weekdays,
        status=VerificationStatus.VERIFIED,
        admin=admin,
    )

    company_user = _user(
        db,
        email="provider@safishacon.local",
        phone="+255714000003",
        name="Joseph Kimaro",
        role=RoleCode.PROVIDER,
        password=pw,
    )
    company_hours = {d: (time(7, 0), time(19, 0)) for d in range(1, 7)} | {7: (time(9, 0), time(15, 0))}
    company = _provider(
        db,
        company_user,
        provider_type=ProviderType.COMPANY,
        display_name="Usafi Bora Cleaning Services Ltd",
        contact_person="Joseph Kimaro",
        bio="Registered cleaning company serving homes and offices across Dar es Salaam with three trained teams "
        "and commercial-grade equipment.",
        years=9,
        capacity=3,
        services=list(services.values()),
        areas=list(areas.values()),
        hours=company_hours,
        status=VerificationStatus.VERIFIED,
        admin=admin,
    )
    if company.registration_number is None:
        company.registration_number = "BRELA-DEMO-0001"

    pending_user = _user(
        db,
        email="pending@safishacon.local",
        phone="+255715000004",
        name="Baraka Said",
        role=RoleCode.PROVIDER,
        password=pw,
        locale="sw",
    )
    _provider(
        db,
        pending_user,
        provider_type=ProviderType.INDIVIDUAL,
        display_name="Baraka Said",
        bio="Experienced cleaner looking to join the platform. Available weekdays in Sinza and Mwenge.",
        years=3,
        capacity=1,
        services=[services["general-home-cleaning"]],
        areas=[areas["Sinza"], areas["Mwenge"]],
        hours={d: (time(8, 0), time(17, 0)) for d in range(1, 6)},
        status=VerificationStatus.PENDING,
    )

    # A completed, paid and reviewed booking so dashboards and earnings have history.
    done = _demo_booking(
        db,
        reference="SC-DEMO01",
        customer=customer,
        provider=cleaner,
        service=services["general-home-cleaning"],
        area=areas["Mikocheni"],
        days_from_today=-7,
        start=time(9, 0),
        bedrooms=2,
        bathrooms=1,
        address="Plot 45, Mikocheni B, Old Bagamoyo Road",
        path=[
            BookingStatus.PENDING_CONFIRMATION,
            BookingStatus.CONFIRMED,
            BookingStatus.FINDING_PROVIDER,
            BookingStatus.PROVIDER_ASSIGNED,
            BookingStatus.PROVIDER_EN_ROUTE,
            BookingStatus.PROVIDER_ARRIVED,
            BookingStatus.SERVICE_IN_PROGRESS,
            BookingStatus.COMPLETED_BY_PROVIDER,
            BookingStatus.CUSTOMER_CONFIRMED,
            BookingStatus.CLOSED,
        ],
    )
    if done is not None:
        now = utcnow() - timedelta(days=7)
        done.confirmed_at, done.completed_at, done.customer_confirmed_at, done.closed_at = now, now, now, now
        done.payment.status = PaymentStatus.PAID
        done.payment.paid_at = now
        done.payment.confirmed_by_id = cleaner_user.id
        db.flush()
        db.refresh(done)
        payments.ensure_settlement(db, done)
        db.add(
            Review(
                booking_id=done.id,
                customer_id=customer.id,
                provider_id=cleaner.id,
                rating=5,
                comment="Rehema was on time and left the flat spotless. (Demo review)",
            )
        )
        db.flush()
        recalculate_rating(db, cleaner)

    # An upcoming job already assigned to the company, visible in both portals.
    upcoming = _demo_booking(
        db,
        reference="SC-DEMO02",
        customer=customer,
        provider=company,
        service=services["deep-cleaning"],
        area=areas["Masaki"],
        days_from_today=3,
        start=time(13, 0),
        bedrooms=2,
        bathrooms=2,
        address="Apartment 7B, Chole Road, Masaki",
        path=[
            BookingStatus.PENDING_CONFIRMATION,
            BookingStatus.CONFIRMED,
            BookingStatus.FINDING_PROVIDER,
            BookingStatus.PROVIDER_ASSIGNED,
        ],
    )
    if upcoming is not None:
        upcoming.confirmed_at = utcnow()


def run(reference_only: bool = False) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        areas, services = seed_reference(db)
        if not reference_only:
            if not settings.demo_mode:
                raise SystemExit("Refusing to create demo accounts with DEMO_MODE=false. Use --reference-only.")
            seed_demo(db, areas, services)
        db.commit()
    log.info("seed.completed", extra={"reference_only": reference_only})


if __name__ == "__main__":
    configure_logging(get_settings().log_level, json_output=False)
    parser = argparse.ArgumentParser(description="Seed the database (idempotent).")
    parser.add_argument("--reference-only", action="store_true", help="Skip demo accounts and bookings.")
    run(parser.parse_args().reference_only)
    print("Seed complete.")

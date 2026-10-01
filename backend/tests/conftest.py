"""Test harness: a real PostgreSQL database, migrated with Alembic, reset per test."""

import os
from datetime import time, timedelta

os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://safisha:safisha@localhost:5432/safishacon_test"),
)
os.environ["ENVIRONMENT"] = "test"
os.environ["BACKGROUND_JOBS_ENABLED"] = "false"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["LOG_JSON"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["DIGITAL_PAYMENTS_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Customer,
    Provider,
    ProviderAvailability,
    ProviderService,
    ProviderServiceArea,
    Role,
    Service,
    ServiceArea,
    User,
)
from app.models.enums import ProviderType, RoleCode, VerificationStatus  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402
from app.security.rate_limit import limiter  # noqa: E402
from app.security.tokens import create_access_token  # noqa: E402
from app.seed import seed_reference  # noqa: E402
from app.utils.clock import local_today  # noqa: E402

PASSWORD = "Passw0rd!"
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    cfg = Config(os.path.join(_BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(_BACKEND_DIR, "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_database(migrated_database):
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        seed_reference(db)
        db.commit()
    limiter.reset()
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class World:
    """Factory helpers that create real rows and return auth headers."""

    def __init__(self, db):
        self.db = db
        self._n = 0

    def _phone(self) -> str:
        self._n += 1
        return f"+25571{self._n:07d}"

    def service(self, slug: str = "deep-cleaning") -> Service:
        return self.db.scalar(select(Service).where(Service.slug == slug))

    def area(self, name: str = "Mikocheni") -> ServiceArea:
        return self.db.scalar(select(ServiceArea).where(ServiceArea.name == name))

    def option(self, service: Service, code: str):
        return next(o for o in service.options if o.code == code)

    def user(self, role: RoleCode, name: str, email: str | None = None) -> User:
        user = User(
            email=email or f"{name.lower().replace(' ', '.')}.{self._n}@test.local",
            phone=self._phone(),
            full_name=name,
            password_hash=hash_password(PASSWORD),
            role=self.db.scalar(select(Role).where(Role.code == role)),
        )
        self.db.add(user)
        self.db.flush()
        return user

    def customer(self, name: str = "Test Customer") -> tuple[Customer, dict]:
        user = self.user(RoleCode.CUSTOMER, name)
        customer = Customer(user_id=user.id)
        self.db.add(customer)
        self.db.commit()
        return customer, self.headers(user)

    def admin(self) -> tuple[User, dict]:
        user = self.user(RoleCode.ADMIN, "Test Admin")
        self.db.commit()
        return user, self.headers(user)

    def provider(
        self,
        name: str = "Test Cleaner",
        *,
        status: VerificationStatus = VerificationStatus.VERIFIED,
        services: list[str] | None = None,
        areas: list[str] | None = None,
        start: time = time(7, 0),
        end: time = time(20, 0),
        capacity: int = 1,
        provider_type: ProviderType = ProviderType.INDIVIDUAL,
    ) -> tuple[Provider, dict]:
        user = self.user(RoleCode.PROVIDER, name)
        provider = Provider(
            user_id=user.id,
            provider_type=provider_type,
            display_name=name,
            capacity=capacity,
            verification_status=status,
        )
        self.db.add(provider)
        self.db.flush()
        for slug in services or ["deep-cleaning", "general-home-cleaning"]:
            self.db.add(ProviderService(provider_id=provider.id, service_id=self.service(slug).id))
        for area in areas or ["Mikocheni"]:
            self.db.add(ProviderServiceArea(provider_id=provider.id, area_id=self.area(area).id))
        for day in range(1, 8):
            self.db.add(ProviderAvailability(provider_id=provider.id, day_of_week=day, start_time=start, end_time=end))
        self.db.commit()
        return provider, self.headers(user)

    @staticmethod
    def headers(user: User) -> dict:
        token, _ = create_access_token(user.id, user.role_code.value)
        return {"Authorization": f"Bearer {token}"}

    def booking_payload(
        self,
        *,
        slug: str = "deep-cleaning",
        area: str = "Mikocheni",
        days: int = 1,
        start: str = "10:00",
        bedrooms: int = 3,
        bathrooms: int = 2,
        **extra,
    ) -> dict:
        service = self.service(slug)
        payload = {
            "service_id": str(service.id),
            "area_id": str(self.area(area).id),
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "address_line": "Plot 12, Mikocheni B",
            "scheduled_date": (local_today() + timedelta(days=days)).isoformat(),
            "scheduled_start_time": start,
            "payment_method": "CASH",
        }
        if service.uses_rooms:
            payload["property_type_option_id"] = str(self.option(service, "apartment").id)
        payload.update(extra)
        return payload


@pytest.fixture
def world(db) -> World:
    return World(db)

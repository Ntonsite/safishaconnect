"""Admin: services, pricing options, cities and service areas."""

import re
import uuid

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.admin.common import admin_only
from app.core.errors import ConflictError, NotFoundError
from app.models import City, Service, ServiceArea, ServiceOption
from app.schemas.catalog import (
    AreaOut,
    AreaUpdate,
    AreaWrite,
    CityOut,
    CityWrite,
    ServiceOptionOut,
    ServiceOptionUpdate,
    ServiceOptionWrite,
    ServiceOut,
    ServiceUpdate,
    ServiceWrite,
)
from app.security.deps import AdminUser, DbSession
from app.services import audit

router = APIRouter(dependencies=admin_only)

PRICE_FIELDS = {"base_price", "price_per_extra_bedroom", "price_per_extra_bathroom", "price_amount"}


def _changes(obj, data: dict) -> dict:
    changes = {}
    for field, value in data.items():
        old = getattr(obj, field)
        if old != value:
            changes[field] = {"from": str(old), "to": str(value)}
            setattr(obj, field, value)
    return changes


def _service(db, service_id: uuid.UUID) -> Service:
    service = db.get(Service, service_id)
    if service is None:
        raise NotFoundError("Service not found.")
    return service


@router.get("/services", response_model=list[ServiceOut], tags=["admin: services"])
def list_services(db: DbSession) -> list[ServiceOut]:
    rows = db.scalars(select(Service).options(selectinload(Service.options)).order_by(Service.display_order))
    return [ServiceOut.model_validate(s) for s in rows]


@router.post("/services", response_model=ServiceOut, status_code=status.HTTP_201_CREATED, tags=["admin: services"])
def create_service(data: ServiceWrite, db: DbSession, admin: AdminUser) -> ServiceOut:
    if db.scalar(select(Service.id).where(Service.slug == data.slug)):
        raise ConflictError("A service with this slug already exists.", code="SLUG_TAKEN")
    service = Service(**data.model_dump())
    db.add(service)
    db.flush()
    audit.record(
        db,
        admin,
        "ADMIN_CREATED_SERVICE",
        "service",
        service.id,
        {"name": service.name_en, "base_price": str(service.base_price)},
    )
    db.commit()
    db.refresh(service)
    return ServiceOut.model_validate(service)


@router.patch("/services/{service_id}", response_model=ServiceOut, tags=["admin: services"])
def update_service(service_id: uuid.UUID, data: ServiceUpdate, db: DbSession, admin: AdminUser) -> ServiceOut:
    service = _service(db, service_id)
    changes = _changes(service, data.model_dump(exclude_unset=True, exclude_none=True))
    if changes:
        action = "ADMIN_CHANGED_SERVICE_PRICE" if PRICE_FIELDS & changes.keys() else "ADMIN_UPDATED_SERVICE"
        audit.record(db, admin, action, "service", service.id, {"name": service.name_en, "changes": changes})
    db.commit()
    db.refresh(service)
    return ServiceOut.model_validate(service)


@router.post(
    "/services/{service_id}/options",
    response_model=ServiceOptionOut,
    status_code=status.HTTP_201_CREATED,
    tags=["admin: services"],
)
def create_option(service_id: uuid.UUID, data: ServiceOptionWrite, db: DbSession, admin: AdminUser) -> ServiceOptionOut:
    service = _service(db, service_id)
    if db.scalar(
        select(ServiceOption.id).where(ServiceOption.service_id == service.id, ServiceOption.code == data.code)
    ):
        raise ConflictError("An option with this code already exists for the service.", code="OPTION_CODE_TAKEN")
    option = ServiceOption(service_id=service.id, **data.model_dump())
    db.add(option)
    db.flush()
    audit.record(
        db,
        admin,
        "ADMIN_CREATED_SERVICE_OPTION",
        "service_option",
        option.id,
        {"service": service.name_en, "code": option.code, "price": str(option.price_amount)},
    )
    db.commit()
    return ServiceOptionOut.model_validate(option)


@router.patch("/options/{option_id}", response_model=ServiceOptionOut, tags=["admin: services"])
def update_option(option_id: uuid.UUID, data: ServiceOptionUpdate, db: DbSession, admin: AdminUser) -> ServiceOptionOut:
    option = db.get(ServiceOption, option_id)
    if option is None:
        raise NotFoundError("Option not found.")
    changes = _changes(option, data.model_dump(exclude_unset=True, exclude_none=True))
    if changes:
        action = "ADMIN_CHANGED_SERVICE_PRICE" if PRICE_FIELDS & changes.keys() else "ADMIN_UPDATED_SERVICE_OPTION"
        audit.record(db, admin, action, "service_option", option.id, {"code": option.code, "changes": changes})
    db.commit()
    return ServiceOptionOut.model_validate(option)


@router.get("/cities", response_model=list[CityOut], tags=["admin: areas"])
def list_cities(db: DbSession) -> list[CityOut]:
    return [CityOut.model_validate(c) for c in db.scalars(select(City).order_by(City.name))]


@router.post("/cities", response_model=CityOut, status_code=status.HTTP_201_CREATED, tags=["admin: areas"])
def create_city(data: CityWrite, db: DbSession, admin: AdminUser) -> CityOut:
    if db.scalar(select(City.id).where(City.name == data.name, City.country_code == data.country_code.upper())):
        raise ConflictError("This city already exists.", code="CITY_EXISTS")
    city = City(
        name=data.name.strip(),
        region=data.region.strip(),
        country_code=data.country_code.upper(),
        is_active=data.is_active,
    )
    db.add(city)
    db.flush()
    audit.record(db, admin, "ADMIN_CREATED_CITY", "city", city.id, {"name": city.name})
    db.commit()
    return CityOut.model_validate(city)


@router.get("/areas", response_model=list[AreaOut], tags=["admin: areas"])
def list_areas(db: DbSession) -> list[AreaOut]:
    rows = db.scalars(select(ServiceArea).join(City).order_by(City.name, ServiceArea.name))
    return [AreaOut.model_validate(a) for a in rows]


def _slug(*parts: str) -> str:
    return "-".join(re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-") for p in parts)


@router.post("/areas", response_model=AreaOut, status_code=status.HTTP_201_CREATED, tags=["admin: areas"])
def create_area(data: AreaWrite, db: DbSession, admin: AdminUser) -> AreaOut:
    city = db.get(City, data.city_id)
    if city is None:
        raise NotFoundError("City not found.")
    name = data.name.strip()
    if db.scalar(select(ServiceArea.id).where(ServiceArea.city_id == city.id, ServiceArea.name == name)):
        raise ConflictError("This area already exists.", code="AREA_EXISTS")
    area = ServiceArea(city_id=city.id, name=name, slug=_slug(city.name, name), is_active=data.is_active)
    db.add(area)
    db.flush()
    audit.record(db, admin, "ADMIN_CREATED_AREA", "service_area", area.id, {"name": name, "city": city.name})
    db.commit()
    db.refresh(area)
    return AreaOut.model_validate(area)


@router.patch("/areas/{area_id}", response_model=AreaOut, tags=["admin: areas"])
def update_area(area_id: uuid.UUID, data: AreaUpdate, db: DbSession, admin: AdminUser) -> AreaOut:
    area = db.get(ServiceArea, area_id)
    if area is None:
        raise NotFoundError("Area not found.")
    payload = data.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in payload:
        payload["name"] = payload["name"].strip()
    changes = _changes(area, payload)
    if changes:
        audit.record(db, admin, "ADMIN_UPDATED_AREA", "service_area", area.id, {"name": area.name, "changes": changes})
    db.commit()
    return AreaOut.model_validate(area)

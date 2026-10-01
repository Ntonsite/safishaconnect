from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.core.errors import ValidationFailedError
from app.models import Customer, ServiceArea
from app.schemas.auth import (
    CustomerRegister,
    LoginRequest,
    MeOut,
    PasswordChange,
    ProfileUpdate,
    ProviderRegister,
    RefreshRequest,
    TokenPair,
)
from app.schemas.common import Message
from app.security.deps import CurrentUser, DbSession
from app.security.rate_limit import auth_rate_limit
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth_rate_limit)]
)
def register_customer(data: CustomerRegister, db: DbSession) -> TokenPair:
    user = auth_service.register_customer(db, data)
    tokens = auth_service.issue_tokens(db, user)
    db.commit()
    return tokens


@router.post(
    "/register/provider",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
def register_provider(data: ProviderRegister, db: DbSession) -> TokenPair:
    user = auth_service.register_provider(db, data)
    tokens = auth_service.issue_tokens(db, user)
    db.commit()
    return tokens


@router.post("/login", response_model=TokenPair, dependencies=[Depends(auth_rate_limit)])
def login(data: LoginRequest, db: DbSession) -> TokenPair:
    user = auth_service.authenticate(db, data.identifier, data.password)
    tokens = auth_service.issue_tokens(db, user)
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair, dependencies=[Depends(auth_rate_limit)])
def refresh(data: RefreshRequest, db: DbSession) -> TokenPair:
    tokens = auth_service.rotate_refresh_token(db, data.refresh_token)
    db.commit()
    return tokens


@router.post("/logout", response_model=Message)
def logout(data: RefreshRequest, db: DbSession) -> Message:
    auth_service.revoke_refresh_token(db, data.refresh_token)
    db.commit()
    return Message(message="Signed out")


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser, db: DbSession) -> MeOut:
    return auth_service.me_out(db, user)


@router.patch("/me", response_model=MeOut)
def update_me(data: ProfileUpdate, user: CurrentUser, db: DbSession) -> MeOut:
    email = str(data.email).lower() if data.email else None
    auth_service.ensure_unique_contact(db, data.phone, email, exclude_user_id=user.id)
    if data.full_name:
        user.full_name = data.full_name.strip()
    if email:
        user.email = email
    if data.phone:
        user.phone = data.phone
    if data.preferred_locale:
        user.preferred_locale = data.preferred_locale
    customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
    if customer is not None:
        if data.default_area_id:
            area = db.get(ServiceArea, data.default_area_id)
            if area is None or not area.is_active:
                raise ValidationFailedError("We don't serve this area yet.", code="AREA_NOT_SERVED")
            customer.default_area_id = area.id
        if data.default_address is not None:
            customer.default_address = data.default_address.strip() or None
    db.commit()
    return auth_service.me_out(db, user)


@router.post("/change-password", response_model=Message, dependencies=[Depends(auth_rate_limit)])
def change_password(data: PasswordChange, user: CurrentUser, db: DbSession) -> Message:
    auth_service.change_password(db, user, data.current_password, data.new_password)
    db.commit()
    return Message(message="Password updated")

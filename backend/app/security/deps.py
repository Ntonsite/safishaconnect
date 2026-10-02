"""Authentication and role-based authorization dependencies."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import context
from app.core.errors import AuthenticationError, NotFoundError, PermissionDeniedError
from app.db.session import get_db
from app.models import Customer, Provider, User
from app.models.enums import RoleCode
from app.security.tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Please sign in to continue.", code="NOT_AUTHENTICATED")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Invalid authentication token.", code="TOKEN_INVALID") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("This account is not active.", code="ACCOUNT_INACTIVE")
    context.set_user(user.id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: RoleCode) -> Callable[[User], User]:
    def checker(user: CurrentUser) -> User:
        if user.role_code not in roles:
            raise PermissionDeniedError("You do not have access to this resource.")
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(RoleCode.ADMIN))]


def get_current_customer(db: DbSession, user: Annotated[User, Depends(require_roles(RoleCode.CUSTOMER))]) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
    if customer is None:
        raise NotFoundError("Customer profile not found.")
    return customer


def get_current_provider(db: DbSession, user: Annotated[User, Depends(require_roles(RoleCode.PROVIDER))]) -> Provider:
    provider = db.scalar(select(Provider).where(Provider.user_id == user.id))
    if provider is None:
        raise NotFoundError("Provider profile not found.")
    return provider


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
CurrentProvider = Annotated[Provider, Depends(get_current_provider)]

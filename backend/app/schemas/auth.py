import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field, field_validator

from app.models.enums import ProviderType
from app.schemas.common import ORMModel
from app.schemas.provider import AvailabilityDay
from app.utils.phone import normalise_tz_phone

PASSWORD_HINT = "Password must be at least 8 characters and include a letter and a number."


def _check_password(value: str) -> str:
    if len(value) < 8 or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError(PASSWORD_HINT)
    return value


Password = Annotated[str, Field(min_length=8, max_length=128), AfterValidator(_check_password)]


class _PhoneMixin(BaseModel):
    @field_validator("phone", check_fields=False)
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalise_tz_phone(value)

    @field_validator("email", check_fields=False, mode="before")
    @classmethod
    def _email(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value


class CustomerRegister(_PhoneMixin):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str
    email: EmailStr | None = None
    password: Password
    preferred_locale: Literal["en", "sw"] = "en"


class ProviderRegister(_PhoneMixin):
    provider_type: ProviderType
    full_name: str = Field(min_length=2, max_length=120, description="Cleaner's name or the company contact person")
    business_name: str | None = Field(default=None, max_length=120)
    phone: str
    email: EmailStr
    password: Password
    bio: str = Field(default="", max_length=2000)
    years_experience: int = Field(default=0, ge=0, le=60)
    registration_number: str | None = Field(default=None, max_length=60)
    capacity: int = Field(default=1, ge=1, le=50)
    service_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    area_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    availability: list[AvailabilityDay] = Field(default_factory=list, max_length=7)
    preferred_locale: Literal["en", "sw"] = "en"


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255, description="Email address or phone number")
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class UserOut(ORMModel):
    id: uuid.UUID
    email: str | None
    phone: str
    full_name: str
    role: str
    is_active: bool
    preferred_locale: str
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ProfileUpdate(_PhoneMixin):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    preferred_locale: Literal["en", "sw"] | None = None
    default_area_id: uuid.UUID | None = None
    default_address: str | None = Field(default=None, max_length=255)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalise_tz_phone(value) if value else None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password


class MeOut(UserOut):
    customer_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    default_area_id: uuid.UUID | None = None
    default_address: str | None = None

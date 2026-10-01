import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPk
from app.models.enums import RoleCode, db_enum


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[RoleCode] = mapped_column(db_enum(RoleCode, "role_code"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class User(UUIDPk, Timestamped, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferred_locale: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped[Role] = relationship(lazy="joined")
    customer: Mapped["Customer | None"] = relationship(back_populates="user", uselist=False)
    provider: Mapped["Provider | None"] = relationship(back_populates="user", uselist=False)  # noqa: F821

    @property
    def role_code(self) -> RoleCode:
        return self.role.code


class RefreshToken(UUIDPk, Base):
    """Refresh tokens are stored hashed and rotated on every use."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Customer(UUIDPk, Timestamped, Base):
    __tablename__ = "customers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    default_area_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("service_areas.id", ondelete="SET NULL"))
    default_address: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="customer", lazy="joined")

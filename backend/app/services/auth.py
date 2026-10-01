"""Registration, login and token lifecycle."""

from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.models import Customer, Provider, ProviderVerification, RefreshToken, Role, User
from app.models.enums import RoleCode, VerificationDecision, VerificationStatus
from app.schemas.auth import CustomerRegister, MeOut, ProviderRegister, TokenPair, UserOut
from app.security.passwords import DUMMY_HASH, hash_password, verify_password
from app.security.tokens import create_access_token, hash_refresh_token, new_refresh_token
from app.services import provider_profile
from app.services.notifications import notify_admins
from app.utils.clock import utcnow
from app.utils.phone import normalise_tz_phone

log = get_logger("auth")


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role_code.value,
        is_active=user.is_active,
        preferred_locale=user.preferred_locale,
        created_at=user.created_at,
    )


def me_out(db: Session, user: User) -> MeOut:
    base = user_out(user).model_dump()
    customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
    provider_id = db.scalar(select(Provider.id).where(Provider.user_id == user.id))
    return MeOut(
        **base,
        customer_id=customer.id if customer else None,
        provider_id=provider_id,
        default_area_id=customer.default_area_id if customer else None,
        default_address=customer.default_address if customer else None,
    )


def _role(db: Session, code: RoleCode) -> Role:
    return db.scalar(select(Role).where(Role.code == code))


def ensure_unique_contact(db: Session, phone: str | None, email: str | None, exclude_user_id=None) -> None:
    if phone:
        q = select(User.id).where(User.phone == phone)
        if exclude_user_id:
            q = q.where(User.id != exclude_user_id)
        if db.scalar(q):
            raise ConflictError("An account with this phone number already exists.", code="PHONE_TAKEN")
    if email:
        q = select(User.id).where(User.email == email.lower())
        if exclude_user_id:
            q = q.where(User.id != exclude_user_id)
        if db.scalar(q):
            raise ConflictError("An account with this email already exists.", code="EMAIL_TAKEN")


def register_customer(db: Session, data: CustomerRegister) -> User:
    email = str(data.email).lower() if data.email else None
    ensure_unique_contact(db, data.phone, email)
    user = User(
        email=email,
        phone=data.phone,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        role=_role(db, RoleCode.CUSTOMER),
        preferred_locale=data.preferred_locale,
    )
    db.add(user)
    db.flush()
    db.add(Customer(user_id=user.id))
    log.info("auth.customer_registered", extra={"user_id": str(user.id)})
    return user


def register_provider(db: Session, data: ProviderRegister) -> User:
    email = str(data.email).lower()
    ensure_unique_contact(db, data.phone, email)
    user = User(
        email=email,
        phone=data.phone,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        role=_role(db, RoleCode.PROVIDER),
        preferred_locale=data.preferred_locale,
    )
    db.add(user)
    db.flush()
    is_company = data.provider_type.value == "COMPANY"
    provider = Provider(
        user_id=user.id,
        provider_type=data.provider_type,
        display_name=(data.business_name or data.full_name).strip() if is_company else data.full_name.strip(),
        contact_person=data.full_name.strip() if is_company else None,
        bio=data.bio.strip(),
        years_experience=data.years_experience,
        registration_number=data.registration_number,
        capacity=data.capacity if is_company else 1,
        verification_status=VerificationStatus.PENDING,
    )
    db.add(provider)
    db.flush()
    provider_profile.set_services(db, provider, data.service_ids)
    provider_profile.set_areas(db, provider, data.area_ids)
    provider_profile.set_availability(db, provider, data.availability)
    db.add(
        ProviderVerification(
            provider_id=provider.id,
            decision=VerificationDecision.SUBMITTED,
            notes="Application submitted",
            created_at=utcnow(),
        )
    )
    notify_admins(db, "ADMIN_PROVIDER_PENDING", provider=provider.display_name)
    log.info("auth.provider_registered", extra={"user_id": str(user.id), "type": data.provider_type})
    return user


def _lookup(db: Session, identifier: str) -> User | None:
    identifier = identifier.strip()
    conditions = [User.email == identifier.lower()]
    try:
        conditions.append(User.phone == normalise_tz_phone(identifier))
    except ValueError:
        pass
    return db.scalar(select(User).where(or_(*conditions)))


def authenticate(db: Session, identifier: str, password: str) -> User:
    user = _lookup(db, identifier)
    if user is None:
        verify_password(password, DUMMY_HASH)
        log.warning("auth.login_failed", extra={"reason": "unknown_user"})
        raise AuthenticationError("Incorrect email/phone or password.", code="INVALID_CREDENTIALS")
    if not verify_password(password, user.password_hash):
        log.warning("auth.login_failed", extra={"reason": "bad_password", "user_id": str(user.id)})
        raise AuthenticationError("Incorrect email/phone or password.", code="INVALID_CREDENTIALS")
    if not user.is_active:
        log.warning("auth.login_failed", extra={"reason": "inactive", "user_id": str(user.id)})
        raise AuthenticationError("This account has been deactivated. Please contact support.", code="ACCOUNT_INACTIVE")
    user.last_login_at = utcnow()
    return user


def issue_tokens(db: Session, user: User) -> TokenPair:
    access, expires_in = create_access_token(user.id, user.role_code.value)
    raw, digest = new_refresh_token()
    now = utcnow()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest,
            created_at=now,
            expires_at=now + timedelta(days=get_settings().refresh_token_days),
        )
    )
    return TokenPair(access_token=access, refresh_token=raw, expires_in=expires_in, user=user_out(user))


def rotate_refresh_token(db: Session, raw: str) -> TokenPair:
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)).with_for_update())
    if token is None or token.revoked_at is not None or token.expires_at <= utcnow():
        if token is not None and token.revoked_at is not None:
            # Re-use of a rotated token: revoke the whole family for safety.
            for t in db.scalars(
                select(RefreshToken).where(RefreshToken.user_id == token.user_id, RefreshToken.revoked_at.is_(None))
            ):
                t.revoked_at = utcnow()
            db.commit()
            log.warning("auth.refresh_reuse_detected", extra={"user_id": str(token.user_id)})
        raise AuthenticationError("Your session has expired. Please sign in again.", code="REFRESH_INVALID")
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("This account is not active.", code="ACCOUNT_INACTIVE")
    token.revoked_at = utcnow()
    return issue_tokens(db, user)


def revoke_refresh_token(db: Session, raw: str) -> None:
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
    if token and token.revoked_at is None:
        token.revoked_at = utcnow()


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise AuthenticationError("Your current password is incorrect.", code="INVALID_CREDENTIALS")
    user.password_hash = hash_password(new)
    for t in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))):
        t.revoked_at = utcnow()

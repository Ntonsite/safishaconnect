"""Central application configuration.

Every brand-, money- and environment-specific value lives here so the product
can be renamed or re-configured without touching business code.
"""

from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # --- Environment ---------------------------------------------------------
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_json: bool = True

    # --- Brand ---------------------------------------------------------------
    app_name: str = "SafishaCon"
    app_tagline: str = "Book. We assign. We clean."
    app_logo_url: str = "/brand/logo.svg"
    support_email: str = "support@safishacon.local"
    support_phone: str = "+255 700 000 000"
    support_whatsapp: str = "+255 700 000 000"
    office_address: str = "Dar es Salaam, Tanzania"

    # --- Locale & money ------------------------------------------------------
    default_currency: str = "TZS"
    default_locale: Literal["en", "sw"] = "en"
    timezone: str = "Africa/Dar_es_Salaam"
    default_commission_percent: Decimal = Decimal("20")

    # --- Database ------------------------------------------------------------
    database_url: str = "postgresql+psycopg://safisha:safisha@localhost:5432/safishacon"

    # --- Security ------------------------------------------------------------
    jwt_secret: str = Field(default="dev-only-change-me-please-32-bytes-minimum", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    cors_origin_regex: str | None = r"http://(localhost|127\.0\.0\.1)(:\d+)?"
    auth_rate_limit_per_minute: int = 20

    # --- Marketplace operations ----------------------------------------------
    assignment_offer_ttl_minutes: int = 30
    min_booking_lead_hours: int = 2
    max_booking_days_ahead: int = 60
    booking_slot_start_hour: int = 7
    booking_slot_end_hour: int = 17
    background_jobs_enabled: bool = True

    # --- Payments ------------------------------------------------------------
    digital_payments_enabled: bool = False
    mobile_money_provider: str | None = None
    mobile_money_api_key: str | None = None

    # --- Notifications -------------------------------------------------------
    sms_provider: str | None = None
    sms_api_key: str | None = None

    # --- Demo ----------------------------------------------------------------
    demo_mode: bool = True
    seed_demo_password: str = "Safisha@2026"

    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, value: str) -> str:
        # Accept plain postgres URLs from hosting platforms and pin the psycopg3 driver.
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://") :]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production:
        if settings.jwt_secret.startswith("dev-only"):
            raise RuntimeError("JWT_SECRET must be replaced in production")
        if settings.demo_mode:
            raise RuntimeError("DEMO_MODE must be disabled in production")
        if settings.cors_origin_regex:
            raise RuntimeError("CORS_ORIGIN_REGEX must be empty in production; list explicit CORS_ORIGINS")
    return settings

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
    # Per-process pool. Total PostgreSQL connections =
    #   (API containers x WEB_CONCURRENCY x (pool_size + max_overflow)) + worker pool + admin headroom.
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=50)
    db_pool_timeout_seconds: float = Field(default=5, gt=0)  # wait for a free connection, then 503
    db_pool_recycle_seconds: int = 1800  # survive NAT/proxy idle cuts and managed-DB failovers
    db_connect_timeout_seconds: int = 5
    db_statement_timeout_ms: int = 15000  # no request may hold a connection on a runaway query
    db_lock_timeout_ms: int = 5000  # row-lock waits fail fast (409) instead of piling up
    db_idle_in_transaction_timeout_ms: int = 30000

    # --- Security ------------------------------------------------------------
    jwt_secret: str = Field(default="dev-only-change-me-please-32-bytes-minimum", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    cors_origin_regex: str | None = r"http://(localhost|127\.0\.0\.1)(:\d+)?"
    auth_rate_limit_per_minute: int = 20
    # Per signed-in user. Catches runaway clients/scripts, never a real customer.
    write_rate_limit_per_minute: int = 30
    # Reverse proxies whose X-Forwarded-For/Proto headers are trusted (comma-separated IPs/CIDRs).
    # Anything else connecting directly cannot spoof its client IP (rate limits, audit IPs).
    forwarded_allow_ips: str = "127.0.0.1"

    # --- Observability -------------------------------------------------------
    metrics_enabled: bool = True
    # When set, GET /metrics requires "Authorization: Bearer <token>".
    metrics_token: str | None = None
    slow_request_ms: int = 1000

    # --- Marketplace operations ----------------------------------------------
    assignment_offer_ttl_minutes: int = 30
    min_booking_lead_hours: int = 2
    max_booking_days_ahead: int = 60
    booking_slot_start_hour: int = 7
    booking_slot_end_hour: int = 17
    # Run the background jobs (offer expiry, notification delivery) inside the API process.
    # Convenient for local development; deployments run ``python -m app.worker`` instead.
    background_jobs_enabled: bool = True
    worker_interval_seconds: int = Field(default=30, ge=5, le=600)

    # --- Payments ------------------------------------------------------------
    digital_payments_enabled: bool = False
    mobile_money_provider: str | None = None
    mobile_money_api_key: str | None = None

    # --- Notifications -------------------------------------------------------
    sms_provider: str | None = None
    sms_api_key: str | None = None
    # Applied by every outbound integration (SMS, payment gateway): never wait indefinitely.
    external_connect_timeout_seconds: float = 3.0
    external_read_timeout_seconds: float = 10.0
    notification_max_attempts: int = 5

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
        if "*" in settings.cors_origin_list:
            raise RuntimeError("CORS_ORIGINS must list explicit origins in production, not '*'")
        if settings.forwarded_allow_ips.strip() == "*":
            raise RuntimeError("FORWARDED_ALLOW_IPS='*' lets any client spoof its IP; list your proxy addresses")
        if "safisha:safisha@" in settings.database_url:
            raise RuntimeError("DATABASE_URL still uses the development credentials")
    return settings

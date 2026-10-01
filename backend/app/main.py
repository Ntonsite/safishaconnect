import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.middleware.request_context import RequestContextMiddleware
from app.services.jobs import offer_expiry_loop

settings = get_settings()
configure_logging(settings.log_level, settings.log_json)
log = get_logger("app")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    stop = asyncio.Event()
    task = asyncio.create_task(offer_expiry_loop(stop)) if settings.background_jobs_enabled else None
    log.info("app.started", extra={"env": settings.environment, "brand": settings.app_name})
    yield
    stop.set()
    if task:
        await task


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        description=f"{settings.app_tagline} — REST API for the {settings.app_name} cleaning marketplace.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept-Language", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "app": settings.app_name, "database": "ok"}

    return app


app = create_app()

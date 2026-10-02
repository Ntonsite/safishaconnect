import asyncio
import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal, engine
from app.middleware.request_context import RequestContextMiddleware
from app.services.jobs import background_loop

settings = get_settings()
configure_logging(settings.log_level, settings.log_json)
log = get_logger("app")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    stop = asyncio.Event()
    task = asyncio.create_task(background_loop(stop)) if settings.background_jobs_enabled else None
    log.info(
        "app.started",
        extra={"env": settings.environment, "brand": settings.app_name, "in_process_jobs": bool(task)},
    )
    yield
    # Graceful shutdown: uvicorn has stopped accepting connections and drained in-flight
    # requests (--timeout-graceful-shutdown). Let the job loop finish its current unit of
    # work — every unit is its own transaction, so nothing is left half-done — then close
    # pooled connections so PostgreSQL sees clean disconnects.
    stop.set()
    if task:
        await task
    engine.dispose()
    log.info("app.stopped")


def _database_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SET LOCAL statement_timeout = 2000"))
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        log.warning("health.database_unavailable")
        return False


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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept-Language", "X-Request-ID", "Idempotency-Key"],
        expose_headers=["X-Request-ID", "Idempotent-Replayed", "Retry-After"],
    )
    # Outermost: request id + access log + metrics cover every response, CORS included.
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health/live", tags=["health"])
    def live() -> dict:
        """Liveness: the process is up and serving. Never touches dependencies (no restart storms)."""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready() -> JSONResponse:
        """Readiness: can this instance serve traffic right now (database reachable)?"""
        ok = _database_ready()
        return JSONResponse({"status": "ok" if ok else "unavailable"}, status_code=200 if ok else 503)

    @app.get("/health", tags=["health"], include_in_schema=False)
    def health() -> JSONResponse:
        """Backwards-compatible alias of /health/ready."""
        return ready()

    if settings.metrics_enabled:
        from app.core import metrics

        @app.get("/metrics", include_in_schema=False)
        def prometheus(request: Request) -> Response:
            if settings.metrics_token:
                supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
                if not hmac.compare_digest(supplied, settings.metrics_token):
                    return Response(status_code=401)
            body, content_type = metrics.render(SessionLocal)
            return Response(body, media_type=content_type)

    return app


app = create_app()

"""Uniform JSON error responses. Stack traces never leave the server."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg_errors
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.core.logging import get_logger

log = get_logger("errors")

_HTTP_CODES = {401: "NOT_AUTHENTICATED", 403: "PERMISSION_DENIED", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def _body(code: str, message: str, details=None, request_id: str | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details, "request_id": request_id}}


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code in (401, 403):
            log.warning("auth.denied", extra={"path": request.url.path, "code": exc.code})
        return JSONResponse(
            status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details, _rid(request))
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
            message = err.get("msg", "Invalid value")
            details.append({"field": ".".join(loc), "message": message.removeprefix("Value error, ")})
        first = details[0]["message"] if details else "Some fields are invalid."
        return JSONResponse(status_code=422, content=_body("VALIDATION_FAILED", first, details, _rid(request)))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail), None, _rid(request)))

    # --- Database failure modes: predictable, retry-friendly responses instead of 500s ---------

    def _busy(request: Request, code: str, message: str, status: int = 503) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content=_body(code, message, None, _rid(request)),
            headers={"Retry-After": "2"} if status == 503 else None,
        )

    @app.exception_handler(StaleDataError)
    async def stale_write(request: Request, exc: StaleDataError) -> JSONResponse:
        # Optimistic version check failed: somebody changed the record since we read it.
        log.warning("db.concurrent_update", extra={"path": request.url.path})
        return _busy(
            request, "CONCURRENT_UPDATE", "This booking was just updated by someone else. Please refresh.", 409
        )

    @app.exception_handler(IntegrityError)
    async def integrity(request: Request, exc: IntegrityError) -> JSONResponse:
        # Constraints are the last line of defence; services normally reject these first.
        log.warning("db.integrity_violation", extra={"path": request.url.path, "constraint": _constraint(exc)})
        return _busy(request, "CONFLICT", "This change conflicts with the current state. Please refresh.", 409)

    @app.exception_handler(PoolTimeoutError)
    async def pool_exhausted(request: Request, exc: PoolTimeoutError) -> JSONResponse:
        log.error("db.pool_exhausted", extra={"path": request.url.path})
        return _busy(request, "SERVICE_BUSY", "We're very busy right now. Please try again in a moment.")

    @app.exception_handler(DBAPIError)
    async def database_error(request: Request, exc: DBAPIError) -> JSONResponse:
        orig = getattr(exc, "orig", None)
        if isinstance(orig, pg_errors.LockNotAvailable | pg_errors.DeadlockDetected | pg_errors.SerializationFailure):
            log.warning("db.lock_contention", extra={"path": request.url.path, "pg": type(orig).__name__})
            return _busy(request, "CONCURRENT_UPDATE", "Someone else is updating this right now. Please retry.", 409)
        if isinstance(orig, pg_errors.QueryCanceled):
            log.error("db.statement_timeout", extra={"path": request.url.path})
            return _busy(request, "SERVICE_BUSY", "This took too long. Please try again.")
        if isinstance(exc, OperationalError):
            log.error("db.unavailable", extra={"path": request.url.path, "pg": type(orig).__name__})
            return _busy(request, "SERVICE_UNAVAILABLE", "The service is temporarily unavailable. Please retry.")
        log.exception("db.error", extra={"path": request.url.path})
        return _busy(request, "INTERNAL_ERROR", "Something went wrong on our side. Please try again.", 500)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", extra={"path": request.url.path, "request_id": _rid(request)})
        return JSONResponse(
            status_code=500,
            content=_body("INTERNAL_ERROR", "Something went wrong on our side. Please try again.", None, _rid(request)),
        )


def _constraint(exc: IntegrityError) -> str | None:
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None)

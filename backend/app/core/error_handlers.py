"""Uniform JSON error responses. Stack traces never leave the server."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", extra={"path": request.url.path, "request_id": _rid(request)})
        return JSONResponse(
            status_code=500,
            content=_body("INTERNAL_ERROR", "Something went wrong on our side. Please try again.", None, _rid(request)),
        )

"""Request ID propagation, security headers, structured access logs and HTTP metrics.

A plain ASGI middleware (not ``BaseHTTPMiddleware``): no extra task per request,
and the request context it creates is visible to every log line the request writes.
"""

import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import context, metrics
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import engine

log = get_logger("http")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
QUIET_PATHS = {"/health", "/health/live", "/health/ready", "/metrics"}


def _route_template(scope: Scope) -> str:
    route = scope.get("route")
    return getattr(route, "path", None) or "unmatched"


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.settings = get_settings()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = None
        for key, value in scope.get("headers", ()):
            if key == b"x-request-id":
                incoming = value.decode("latin-1")
                break
        # scope["client"] is the real peer, or the X-Forwarded-For address when (and only when)
        # the connection came from a trusted proxy (uvicorn --forwarded-allow-ips).
        client = scope.get("client")
        ctx = context.begin(context.new_request_id(incoming), client[0] if client else None)
        scope.setdefault("state", {})["request_id"] = ctx.request_id
        status_code = 500
        started = time.perf_counter()
        metrics.HTTP_IN_PROGRESS.inc()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = ctx.request_id
                for key, value in SECURITY_HEADERS.items():
                    headers.setdefault(key, value)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            metrics.HTTP_IN_PROGRESS.dec()
            elapsed = time.perf_counter() - started
            path = scope["path"]
            route = _route_template(scope)
            if path not in QUIET_PATHS:
                metrics.observe_request(scope["method"], route, status_code, elapsed, ctx.db_queries)
                metrics.observe_pool(engine)
                elapsed_ms = round(elapsed * 1000, 1)
                fields = {
                    "method": scope["method"],
                    "path": path,
                    "route": route,
                    "status": status_code,
                    "ms": elapsed_ms,
                    "db_queries": ctx.db_queries,
                }
                if elapsed_ms >= self.settings.slow_request_ms:
                    log.warning("http.slow_request", extra=fields)
                else:
                    log.info("http.request", extra=fields)

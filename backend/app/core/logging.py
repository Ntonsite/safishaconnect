"""Structured logging. Never pass passwords or tokens into ``extra``."""

import json
import logging
import sys
from datetime import UTC, datetime

from app.core import context

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime", "taskName"}
_REDACT = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "password_hash",
    "jwt",
    "api_key",
    "secret",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        # Correlate every line written while serving a request (services, jobs, errors).
        ctx = context.current()
        if ctx is not None:
            payload["request_id"] = ctx.request_id
            if ctx.user_id:
                payload["user_id"] = ctx.user_id
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = "[redacted]" if key.lower() in _REDACT else value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter() if json_output else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").setLevel("WARNING")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"safisha.{name}")

"""Per-request context shared by middleware, dependencies, services and log records.

A single mutable object is stored in a ContextVar at the start of each request.
Sync endpoints run in a worker thread with a *copy* of the context, so they can
mutate the object (user id, query count) but must never rebind the variable.
"""

import re
import uuid
from contextvars import ContextVar
from dataclasses import dataclass

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{8,64}$")


@dataclass
class RequestContext:
    request_id: str
    user_id: str | None = None
    route: str | None = None
    client_ip: str | None = None
    db_queries: int = 0


_current: ContextVar[RequestContext | None] = ContextVar("safisha_request", default=None)


def new_request_id(incoming: str | None = None) -> str:
    """Accept a caller/proxy supplied ID only if it is safe to echo into logs and headers."""
    if incoming and _SAFE_ID.match(incoming):
        return incoming
    return uuid.uuid4().hex[:16]


def begin(request_id: str, client_ip: str | None = None) -> RequestContext:
    ctx = RequestContext(request_id=request_id, client_ip=client_ip)
    _current.set(ctx)
    return ctx


def current() -> RequestContext | None:
    return _current.get()


def client_ip() -> str | None:
    ctx = _current.get()
    return ctx.client_ip if ctx is not None else None


def set_user(user_id: object) -> None:
    ctx = _current.get()
    if ctx is not None:
        ctx.user_id = str(user_id)


def count_query() -> None:
    ctx = _current.get()
    if ctx is not None:
        ctx.db_queries += 1

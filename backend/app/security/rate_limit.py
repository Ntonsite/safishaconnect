"""Small in-process sliding-window rate limiter for auth endpoints.

Suitable for a single API instance. When scaling horizontally, move this to a
shared store (Redis) or enforce limits at the gateway.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimitedError


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                raise RateLimitedError("Too many attempts. Please wait a minute and try again.")
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def auth_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    limiter.hit(f"auth:{client}:{request.url.path}", get_settings().auth_rate_limit_per_minute)

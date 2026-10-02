"""In-process sliding-window rate limiter.

Deliberately simple (see docs/architecture/ADR-002-redis.md): limits are per API
process. With N processes a client can make up to N x limit attempts, which is still
an effective brake on credential stuffing at pilot scale, and the edge proxy (nginx
``limit_req`` on /api/v1/auth/) applies a shared limit in front of every replica.
Move the buckets to Redis when several API replicas serve real traffic.

The client IP comes from ``request.client``, which uvicorn only rewrites from
``X-Forwarded-For`` when the connection is from FORWARDED_ALLOW_IPS — so clients
cannot spoof their way around the limit.
"""

import threading
import time
from collections import deque

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimitedError

_SWEEP_EVERY = 1000  # hits between purges of idle buckets (keeps memory bounded)


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._since_sweep = 0

    def hit(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        now = time.monotonic()
        with self._lock:
            self._since_sweep += 1
            if self._since_sweep >= _SWEEP_EVERY:
                self._sweep(now, window_seconds)
            bucket = self._hits.setdefault(key, deque())
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                raise RateLimitedError("Too many attempts. Please wait a minute and try again.")
            bucket.append(now)

    def _sweep(self, now: float, window_seconds: float) -> None:
        self._since_sweep = 0
        for key in [k for k, b in self._hits.items() if not b or now - b[-1] > window_seconds]:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def __len__(self) -> int:
        return len(self._hits)


limiter = SlidingWindowLimiter()


def auth_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    limiter.hit(f"auth:{client}:{request.url.path}", get_settings().auth_rate_limit_per_minute)


def write_rate_limit(user_id: object, action: str) -> None:
    """Per-account brake on expensive writes (booking creation, reviews, complaints)."""
    limiter.hit(f"write:{action}:{user_id}", get_settings().write_rate_limit_per_minute)

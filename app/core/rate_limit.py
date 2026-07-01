"""Simple in-process rate limiting utilities."""

from __future__ import annotations

import logging
from collections import deque
from threading import Lock
from time import time

from fastapi import HTTPException, Request, status

_LOGGER = logging.getLogger(__name__)

# After this many check() calls, sweep stale buckets from the _requests dict
# to prevent unbounded memory growth from many distinct client IPs.
_EVICTION_INTERVAL = 500


class InMemoryRateLimiter:
    """Simple sliding-window in-memory rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        """Store limiter configuration and initialize state."""
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = Lock()
        self._check_count = 0

    def check(self, key: str) -> None:
        """Raise if the key exceeds the configured request budget."""
        now = time()
        with self._lock:
            bucket = self._requests.setdefault(key, deque())
            # Evict timestamps that have fallen outside the window.
            while bucket and now - bucket[0] > self._window_seconds:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded.",
                )
            bucket.append(now)

            # Periodically evict stale buckets — both empty ones (dead IPs) and
            # idle ones whose newest timestamp is older than 2× the window.
            self._check_count += 1
            if self._check_count >= _EVICTION_INTERVAL:
                self._check_count = 0
                cutoff = now - self._window_seconds * 2
                stale_keys = [
                    k for k, v in self._requests.items()
                    if not v or v[-1] < cutoff
                ]
                for k in stale_keys:
                    del self._requests[k]
                if stale_keys:
                    _LOGGER.debug("Evicted %d stale rate-limit buckets", len(stale_keys))


admin_rate_limiter = InMemoryRateLimiter(max_requests=60, window_seconds=60)
chat_rate_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=60)


async def rate_limit_admin_requests(request: Request) -> None:
    """Apply rate limiting to admin endpoints based on client IP."""
    client_host = request.client.host if request.client else "unknown"
    admin_rate_limiter.check(client_host)


async def rate_limit_chat_requests(request: Request) -> None:
    """Apply rate limiting to chat endpoints based on client IP."""
    client_host = request.client.host if request.client else "unknown"
    chat_rate_limiter.check(client_host)

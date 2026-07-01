"""Simple in-process rate limiting utilities."""

from __future__ import annotations

from collections import deque
from threading import Lock
from time import time

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Simple sliding-window in-memory rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        """Store limiter configuration and initialize state."""
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        """Raise if the key exceeds the configured request budget."""
        now = time()
        with self._lock:
            bucket = self._requests.setdefault(key, deque())
            while bucket and now - bucket[0] > self._window_seconds:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded.",
                )
            bucket.append(now)


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

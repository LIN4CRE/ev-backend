"""Tests for in-process rate limiting."""

import pytest
from fastapi import HTTPException

from app.core.rate_limit import InMemoryRateLimiter


def test_in_memory_rate_limiter_blocks_after_budget() -> None:
    """Verify the limiter raises after the allowed request count is exceeded."""
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    limiter.check("client-1")
    limiter.check("client-1")
    with pytest.raises(HTTPException):
        limiter.check("client-1")

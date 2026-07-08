"""Pytest configuration and environment initialization."""

import os

# Set ENVIRONMENT to test before any other imports or settings are loaded
os.environ["ENVIRONMENT"] = "test"
os.environ["REQUIRE_ALEXA_SIGNATURE_HEADERS"] = "false"
os.environ["AI_PROVIDER"] = "stub"
# Explicit admin key for tests. Must satisfy the min_length=24 constraint on
# Settings.admin_api_key. Tests that hit admin endpoints reference this value.
TEST_ADMIN_API_KEY = "test-admin-key-not-for-production"
os.environ["ADMIN_API_KEY"] = TEST_ADMIN_API_KEY


import pytest  # noqa: E402

from app.core.rate_limit import admin_rate_limiter, chat_rate_limiter  # noqa: E402


@pytest.fixture(autouse=True)
def reset_rate_limiters() -> None:
    """Ensure rate limiter state is reset between tests."""
    admin_rate_limiter.reset()
    chat_rate_limiter.reset()

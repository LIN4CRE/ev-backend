"""Tests for admin authentication abstraction."""

import pytest
from fastapi import HTTPException

from app.core.auth import ApiKeyAdminAuthenticator
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_api_key_admin_authenticator_rejects_missing_key() -> None:
    """Verify missing admin keys are rejected."""
    authenticator = ApiKeyAdminAuthenticator(get_settings())
    with pytest.raises(HTTPException) as exc_info:
        await authenticator.authenticate(None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_api_key_admin_authenticator_accepts_valid_key() -> None:
    """Verify the configured admin API key is accepted."""
    authenticator = ApiKeyAdminAuthenticator(get_settings())
    await authenticator.authenticate("change-me-in-production!!!")

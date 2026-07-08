"""Tests for Settings validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_rejects_default_admin_key_in_production() -> None:
    """Verify that using the default admin key in production raises a ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            admin_api_key="change-me-in-production!!!",
        )
    assert "ADMIN_API_KEY cannot contain default 'change-me' placeholders" in str(exc_info.value)


def test_settings_accepts_custom_admin_key_in_production() -> None:
    """Verify that settings allow a custom secure key in production."""
    settings = Settings(
        environment="production",
        admin_api_key="a-very-long-and-secure-custom-key-1234",
    )
    assert settings.admin_api_key == "a-very-long-and-secure-custom-key-1234"

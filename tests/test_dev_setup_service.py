"""Tests for development-only Alexa setup automation."""

from app.core.config import Settings
from app.services.dev_setup_service import DevSetupService


def test_dev_setup_service_blocks_in_production() -> None:
    """Verify local dev commands are blocked outside development-like environments."""
    settings = Settings(environment="production")
    service = DevSetupService(settings)
    assert service.prepare_alexa_local_dev() == "Local Alexa setup commands are only available in development."

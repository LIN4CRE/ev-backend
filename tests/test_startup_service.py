"""Tests for startup diagnostics behavior."""

from app.core.config import get_settings
from app.services.startup_service import StartupService


def test_startup_service_can_emit_report_without_error() -> None:
    """Verify startup diagnostics can run with the current configuration."""
    service = StartupService(get_settings())
    service.emit_startup_report()

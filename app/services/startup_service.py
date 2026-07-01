"""Startup diagnostics and readiness reporting."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_ADMIN_KEY = "change-me-in-production"


class StartupService:
    """Reports configured integrations and runtime readiness details."""

    def __init__(self, settings: Settings) -> None:
        """Store application settings for startup reporting."""
        self._settings = settings

    def emit_startup_report(self) -> None:
        """Log a summarized integration readiness report."""
        self._warn_default_admin_key()
        self._settings.check_cors_origins()
        logger.info(
            "startup_report",
            environment=self._settings.environment,
            alexa_skill_configured=bool(self._settings.alexa_skill_id),
            alexa_signature_verification_enabled=self._settings.require_alexa_signature_headers,
            openai_configured=bool(self._settings.openai_api_key),
            home_assistant_configured=bool(
                self._settings.home_assistant_url and self._settings.home_assistant_token
            ),
            calendar_provider=self._settings.calendar_provider,
            google_calendar_configured=bool(
                self._settings.google_calendar_api_key and self._settings.google_calendar_id
            ),
            web_search_provider=self._settings.web_search_provider,
            memory_backend=self._settings.memory_backend,
        )

    @staticmethod
    def _warn_default_admin_key() -> None:
        """Emit a loud warning if the admin API key is still the default."""
        settings = get_settings()
        if settings.admin_api_key == DEFAULT_ADMIN_KEY:
            import logging as _logging
            _logging.warning(
                "ADMIN_API_KEY is still set to the default value '%s'. "
                "Set a strong random key in production via the ADMIN_API_KEY environment variable.",
                DEFAULT_ADMIN_KEY,
            )

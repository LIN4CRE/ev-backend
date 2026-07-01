"""System-level service functions used by API routes."""

from app.core.config import Settings


class SystemService:
    """Provides system inspection data for safe operational endpoints."""

    def __init__(self, settings: Settings) -> None:
        """Store application settings for endpoint responses."""
        self._settings = settings

    def get_health(self) -> dict:
        """Return a basic health payload suitable for liveness checks."""
        return {
            "status": "ok",
            "service": self._settings.app_name,
            "environment": self._settings.environment,
        }

    def get_safe_config_summary(self) -> dict:
        """Return a redacted configuration summary for admin diagnostics."""
        return {
            "app_name": self._settings.app_name,
            "environment": self._settings.environment,
            "debug": self._settings.debug,
            "api_v1_prefix": self._settings.api_v1_prefix,
            "log_level": self._settings.log_level,
            "alexa_configured": bool(self._settings.alexa_skill_id),
            "alexa_request_tolerance_seconds": self._settings.alexa_request_tolerance_seconds,
            "require_alexa_signature_headers": self._settings.require_alexa_signature_headers,
            "openai_configured": bool(self._settings.openai_api_key),
            "openai_model": self._settings.openai_model,
            "gemini_configured": bool(self._settings.gemini_api_key),
            "gemini_model": self._settings.gemini_model,
            "home_assistant_configured": bool(
                self._settings.home_assistant_url and self._settings.home_assistant_token
            ),
            "calendar_provider": self._settings.calendar_provider,
            "google_calendar_configured": bool(
                self._settings.google_calendar_api_key and self._settings.google_calendar_id
            ),
            "web_search_provider": self._settings.web_search_provider,
            "memory_backend": self._settings.memory_backend,
            "memory_file_path": self._settings.memory_file_path,
            "memory_sqlite_path": self._settings.memory_sqlite_path,
        }

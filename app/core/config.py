"""Application configuration management.

This module centralizes environment-driven configuration so the rest of the
application can depend on a single validated settings object.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        # Load local .env first, then fall back to the project root .env.
        # This allows the centralised root .env to be the single source of
        # truth while still permitting per-component overrides.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Ev Backend", description="Human-readable app name.")
    environment: str = Field(default="development", description="Runtime environment.")
    debug: bool = Field(default=False, description="Whether debug mode is enabled.")
    api_v1_prefix: str = Field(default="/api/v1", description="Base API prefix.")
    log_level: str = Field(default="INFO", description="Application log level.")

    host: str = Field(default="0.0.0.0", description="Bind host for the API server.")
    port: int = Field(default=8000, ge=1, le=65535, description="Bind port for the API server.")

    admin_api_key: str = Field(
        default="change-me-in-production!!!",
        min_length=24,
        description="Static admin API key used for protected admin endpoints. Must be at least 24 characters.",
    )

    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins. Override with CORS_ORIGINS env var.",
    )

    def check_cors_origins(self) -> None:
        """Log a warning when CORS is wide-open."""
        if self.cors_origins == ["*"]:
            import logging as _logging
            _logging.warning(
                "CORS_ORIGINS is set to ['*'] — wide open. "
                "Restrict it in production (e.g. CORS_ORIGINS=http://localhost:3000,http://localhost:5173)."
            )

    alexa_skill_id: str | None = Field(default=None, description="Expected Alexa skill ID.")
    alexa_request_tolerance_seconds: int = Field(
        default=150,
        ge=1,
        le=3600,
        description="Accepted Alexa request timestamp skew in seconds.",
    )
    require_alexa_signature_headers: bool = Field(
        default=False,
        description="Whether Alexa signature verification is required.",
    )
    ai_provider: str = Field(default="stub", description="AI provider: stub, openai, ollama, or gemini.")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key.")
    openai_model: str = Field(default="gpt-4.1-mini", description="OpenAI model for assistant orchestration.")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server base URL.")
    ollama_model: str = Field(default="deepseek-r1:7b", description="Ollama model for assistant orchestration.")
    gemini_api_key: str | None = Field(default=None, description="Google Gemini API key.")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model for assistant orchestration.")
    home_assistant_url: str | None = Field(default=None, description="Home Assistant base URL.")
    home_assistant_token: str | None = Field(default=None, description="Home Assistant access token.")
    calendar_provider: str | None = Field(default=None, description="Calendar provider name.")
    google_calendar_api_key: str | None = Field(default=None, description="Google Calendar API key.")
    google_calendar_id: str | None = Field(default=None, description="Google Calendar ID.")
    web_search_provider: str | None = Field(default=None, description="Web search provider name.")
    use_vertex_ai: bool = Field(default=False, description="Whether to use Vertex AI (mobile app config).")
    gcp_project_id: str | None = Field(default=None, description="GCP project ID for Vertex AI.")
    gcp_location: str = Field(default="us-central1", description="GCP location for Vertex AI.")
    youtube_enabled: bool = Field(default=False, description="Whether YouTube search and playback is enabled.")
    memory_backend: str = Field(default="sqlite", description="Conversation memory backend type.")
    memory_file_path: str = Field(default="./data/conversations.json", description="Path for file-based memory storage.")
    memory_sqlite_path: str = Field(default="./data/conversations.db", description="Path for SQLite conversation storage.")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Normalize and validate the runtime environment name."""
        normalized = value.strip().lower()
        allowed = {"development", "test", "staging", "production"}
        if normalized not in allowed:
            raise ValueError(f"environment must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate logging levels."""
        normalized = value.strip().upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, value: str) -> str:
        """Normalize and validate AI provider selection."""
        normalized = value.strip().lower()
        allowed = {"stub", "openai", "ollama", "gemini"}
        if normalized not in allowed:
            raise ValueError(f"ai_provider must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("memory_backend")
    @classmethod
    def validate_memory_backend(cls, value: str) -> str:
        """Normalize and validate memory backend selection."""
        normalized = value.strip().lower()
        allowed = {"memory", "file", "sqlite"}
        if normalized not in allowed:
            raise ValueError(f"memory_backend must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        """Accept JSON-array, comma-separated, or list-based CORS origin configuration.

        The .env.example ships with JSON syntax (``["http://...","http://..."]``)
        which pydantic-settings does not automatically deserialise from a plain
        string field.  We handle that case explicitly here.
        """
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            # Try JSON array first (e.g. '["http://localhost:3000"]').
            if stripped.startswith("["):
                import json as _json

                try:
                    parsed = _json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if item]
                except _json.JSONDecodeError:
                    pass
            # Fall back to comma-separated values.
            return [item.strip() for item in stripped.split(",") if item.strip()]
        raise ValueError("cors_origins must be a list or comma-separated string")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached application settings instance."""
    return Settings()

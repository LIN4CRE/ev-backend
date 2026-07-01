"""Admin authentication abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from fastapi import Header, HTTPException, Request, status

from app.core.config import Settings, get_settings


class AdminAuthenticator(ABC):
    """Abstract authenticator for admin-protected endpoints."""

    @abstractmethod
    async def authenticate(self, presented_secret: str | None) -> None:
        """Validate the provided admin credential or raise on failure."""


class ApiKeyAdminAuthenticator(AdminAuthenticator):
    """Static API key authenticator used for early admin protection."""

    def __init__(self, settings: Settings) -> None:
        """Store application settings for credential verification."""
        self._settings = settings

    async def authenticate(self, presented_secret: str | None) -> None:
        """Validate the configured admin API key."""
        if not presented_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing admin API key.",
            )
        if presented_secret != self._settings.admin_api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin API key.",
            )


def get_admin_authenticator() -> AdminAuthenticator:
    """Return the configured admin authenticator implementation."""
    return ApiKeyAdminAuthenticator(get_settings())


async def require_admin_access(
    request: Request,
    x_admin_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Dependency wrapper that authenticates admin requests.

    Accepts the admin API key via either:
      - X-Admin-Api-Key header (primary)
      - Authorization: Bearer <key> header (fallback, for client compatibility)
    """
    presented = x_admin_api_key
    if not presented and authorization:
        if authorization.startswith("Bearer "):
            presented = authorization[7:]
    admin_authenticator = get_admin_authenticator()
    await admin_authenticator.authenticate(presented)

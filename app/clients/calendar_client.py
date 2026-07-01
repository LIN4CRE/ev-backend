"""Calendar client abstraction for provider integration."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.clients.google_calendar_client import GoogleCalendarClient
from app.core.config import Settings, get_settings


class CalendarClient(ABC):
    """Abstract client for calendar operations."""

    @abstractmethod
    async def list_upcoming_events(self, limit: int = 5) -> dict:
        """Return a summary of upcoming calendar events."""


class NullCalendarClient(CalendarClient):
    """Fallback calendar client used when no provider is configured."""

    async def list_upcoming_events(self, limit: int = 5) -> dict:
        """Return a consistent response when calendar integration is unavailable."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        return {
            "configured": False,
            "provider": None,
            "events": [],
            "message": (
                "Calendar integration is not configured."
                " Set CALENDAR_PROVIDER=google with your Google Calendar API key"
                " in your .env file to enable it."
            ),
            "limit": limit,
        }


class PlaceholderCalendarClient(CalendarClient):
    """Named provider placeholder with clear boundaries for later real integrations."""

    def __init__(self, provider_name: str) -> None:
        """Store provider identity for reporting purposes."""
        self._provider_name = provider_name

    async def list_upcoming_events(self, limit: int = 5) -> dict:
        """Return a consistent response until a real provider implementation is added."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        return {
            "configured": True,
            "provider": self._provider_name,
            "events": [],
            "message": f"Calendar provider '{self._provider_name}' is configured but not yet fully implemented.",
            "limit": limit,
        }


class GoogleCalendarAdapter(CalendarClient):
    """Adapter exposing the generic calendar interface over Google Calendar."""

    def __init__(self, api_key: str, calendar_id: str) -> None:
        """Initialize the provider client."""
        self._client = GoogleCalendarClient(api_key=api_key, calendar_id=calendar_id)

    async def list_upcoming_events(self, limit: int = 5) -> dict:
        """Return upcoming events through the provider adapter."""
        return await self._client.list_upcoming_events(limit=limit)


def get_calendar_client() -> CalendarClient:
    """Return the configured calendar client implementation."""
    settings: Settings = get_settings()
    provider = (settings.calendar_provider or "").strip().lower()
    if provider == "google" and settings.google_calendar_api_key and settings.google_calendar_id:
        return GoogleCalendarAdapter(
            api_key=settings.google_calendar_api_key,
            calendar_id=settings.google_calendar_id,
        )
    if provider and settings.calendar_provider:
        return PlaceholderCalendarClient(settings.calendar_provider)
    return NullCalendarClient()

"""Google Calendar read-only client implementation."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.exceptions import ExternalServiceError


class GoogleCalendarClient:
    """Minimal Google Calendar HTTP client using an API key.

    This implementation targets public or otherwise API-key-accessible calendar
    reads, which is a maintainable intermediate step before OAuth user grants.
    """

    def __init__(self, api_key: str, calendar_id: str, timeout_seconds: float = 15.0) -> None:
        """Store provider configuration values."""
        self._api_key = api_key
        self._calendar_id = calendar_id
        self._timeout_seconds = timeout_seconds

    async def list_upcoming_events(self, limit: int = 5) -> dict:
        """Fetch upcoming events from Google Calendar."""
        if limit < 1:
            raise ValueError("limit must be at least 1")

        params: dict[str, str | int] = {
            "key": self._api_key,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": limit,
            "timeMin": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self._calendar_id}/events"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise ExternalServiceError("google_calendar", "Unable to retrieve calendar events.") from exc

        events = []
        for item in payload.get("items", []):
            start_data = item.get("start", {})
            events.append(
                {
                    "summary": item.get("summary", "Untitled event"),
                    "start": start_data.get("dateTime") or start_data.get("date"),
                    "status": item.get("status"),
                }
            )

        return {
            "configured": True,
            "provider": "google",
            "events": events,
            "message": "Calendar events retrieved." if events else "No upcoming calendar events were found.",
            "limit": limit,
        }

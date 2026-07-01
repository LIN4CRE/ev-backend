"""Home Assistant client abstraction and HTTP implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ExternalServiceError


class HomeAssistantClient(ABC):
    """Abstract client for Home Assistant operations."""

    @abstractmethod
    async def get_state(self, entity_id: str) -> dict:
        """Return the current state for a Home Assistant entity."""

    @abstractmethod
    async def call_service(self, domain: str, service: str, service_data: dict | None = None) -> dict:
        """Call a Home Assistant service and return a summarized result."""


class NullHomeAssistantClient(HomeAssistantClient):
    """Fallback Home Assistant client used when integration is not configured."""

    async def get_state(self, entity_id: str) -> dict:
        """Return a consistent response when Home Assistant is unavailable."""
        return {
            "configured": False,
            "entity_id": entity_id,
            "message": (
                "Home Assistant is not configured."
                " Set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN"
                " in your .env file to enable it."
            ),
        }

    async def call_service(self, domain: str, service: str, service_data: dict | None = None) -> dict:
        """Return a consistent response when Home Assistant is unavailable."""
        return {
            "configured": False,
            "domain": domain,
            "service": service,
            "service_data": service_data or {},
            "message": (
                "Home Assistant is not configured."
                " Set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN"
                " in your .env file to enable it."
            ),
        }


class HttpHomeAssistantClient(HomeAssistantClient):
    """HTTP-backed Home Assistant client implementation."""

    def __init__(self, base_url: str, token: str, timeout_seconds: float = 15.0) -> None:
        """Store HTTP client configuration values."""
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_seconds = timeout_seconds

    async def get_state(self, entity_id: str) -> dict:
        """Fetch a Home Assistant entity state over HTTP."""
        if not entity_id.strip():
            raise ValueError("entity_id must not be empty")

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(
                f"{self._base_url}/api/states/{entity_id}",
                headers=self._build_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def call_service(self, domain: str, service: str, service_data: dict | None = None) -> dict:
        """Call a Home Assistant service over HTTP."""
        if not domain.strip():
            raise ValueError("domain must not be empty")
        if not service.strip():
            raise ValueError("service must not be empty")

        payload = service_data or {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/api/services/{domain}/{service}",
                    headers=self._build_headers(),
                    json=payload,
                )
                response.raise_for_status()
                return {
                    "domain": domain,
                    "service": service,
                    "service_data": payload,
                    "result": response.json(),
                    "message": "Home Assistant service executed.",
                }
        except Exception as exc:
            raise ExternalServiceError("home_assistant", "Unable to execute Home Assistant service.") from exc

    async def resolve_entity_id(self, spoken_name: str, domain_hint: str | None = None) -> str | None:
        """Resolve a spoken entity name to a Home Assistant entity ID using current state data."""
        normalized_name = spoken_name.strip().lower().replace(" ", "_")
        if not normalized_name:
            return None

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(
                f"{self._base_url}/api/states",
                headers=self._build_headers(),
            )
            response.raise_for_status()
            states = response.json()

        for state in states:
            entity_id = str(state.get("entity_id") or "")
            friendly_name = str(state.get("attributes", {}).get("friendly_name") or "").strip().lower()
            if domain_hint and not entity_id.startswith(f"{domain_hint}."):
                continue
            if entity_id.endswith(f".{normalized_name}") or friendly_name == spoken_name.strip().lower():
                return entity_id
        return None

    def _build_headers(self) -> dict[str, str]:
        """Build authenticated Home Assistant request headers."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }


def get_home_assistant_client() -> HomeAssistantClient:
    """Return the configured Home Assistant client implementation."""
    settings: Settings = get_settings()
    if settings.home_assistant_url and settings.home_assistant_token:
        return HttpHomeAssistantClient(
            base_url=settings.home_assistant_url,
            token=settings.home_assistant_token,
        )
    return NullHomeAssistantClient()

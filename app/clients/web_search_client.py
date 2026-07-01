"""Web search client abstraction for provider integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.clients.search_provider_client import DuckDuckGoInstantAnswerClient
from app.core.config import Settings, get_settings


class WebSearchClient(ABC):
    """Abstract client for web search operations."""

    @abstractmethod
    async def search(self, query: str, limit: int = 3) -> dict:
        """Execute a search query and return summarized results."""


class NullWebSearchClient(WebSearchClient):
    """Fallback web search client used when no provider is configured."""

    async def search(self, query: str, limit: int = 3) -> dict:
        """Return a consistent response when search integration is unavailable."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        return {
            "configured": False,
            "provider": None,
            "query": query,
            "results": [],
            "message": "Web search is not configured. Set WEB_SEARCH_PROVIDER=duckduckgo in your .env file to enable it.",
            "limit": limit,
        }


class PlaceholderWebSearchClient(WebSearchClient):
    """Named provider placeholder with clear boundaries for later real integrations."""

    def __init__(self, provider_name: str) -> None:
        """Store provider identity for reporting purposes."""
        self._provider_name = provider_name

    async def search(self, query: str, limit: int = 3) -> dict:
        """Return a consistent response until a real provider implementation is added."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        return {
            "configured": True,
            "provider": self._provider_name,
            "query": query,
            "results": [],
            "message": f"Web search provider '{self._provider_name}' is configured but not yet implemented.",
            "limit": limit,
        }


class DuckDuckGoWebSearchClient(WebSearchClient):
    """DuckDuckGo-backed search client implementation."""

    def __init__(self) -> None:
        """Initialize the provider wrapper."""
        self._provider = DuckDuckGoInstantAnswerClient()

    async def search(self, query: str, limit: int = 3) -> dict:
        """Search using DuckDuckGo's Instant Answer API."""
        return await self._provider.search(query=query, limit=limit)


def get_web_search_client() -> WebSearchClient:
    """Return the configured web search client implementation."""
    settings: Settings = get_settings()
    provider = (settings.web_search_provider or "").strip().lower()
    if provider == "duckduckgo":
        return DuckDuckGoWebSearchClient()
    if provider and settings.web_search_provider:
        return PlaceholderWebSearchClient(settings.web_search_provider)
    return NullWebSearchClient()

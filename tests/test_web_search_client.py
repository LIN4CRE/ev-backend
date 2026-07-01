"""Tests for web search client implementations."""

import pytest

from app.clients.web_search_client import NullWebSearchClient


@pytest.mark.asyncio
async def test_null_web_search_client_returns_consistent_response() -> None:
    """Verify the null search client returns a consistent fallback payload."""
    client = NullWebSearchClient()
    result = await client.search("weather in London", limit=2)

    assert result["configured"] is False
    assert result["query"] == "weather in London"
    assert result["limit"] == 2
    assert result["results"] == []

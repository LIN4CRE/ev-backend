"""HTTP-backed web search provider client implementations."""

from __future__ import annotations

import urllib.parse

import httpx

from app.core.exceptions import ExternalServiceError


class DuckDuckGoInstantAnswerClient:
    """Simple DuckDuckGo Instant Answer API wrapper.

    This provider is public and unauthenticated, which makes it a practical
    default integration for local development and early production hardening.
    """

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        """Store timeout configuration."""
        self._timeout_seconds = timeout_seconds

    async def search(self, query: str, limit: int = 3) -> dict:
        """Execute a search query and return normalized summarized results."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if limit < 1:
            raise ValueError("limit must be at least 1")

        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_redirect=1&no_html=1"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise ExternalServiceError("duckduckgo", "Unable to complete web search.") from exc

        results: list[dict] = []
        abstract_text = str(payload.get("AbstractText") or "").strip()
        abstract_url = str(payload.get("AbstractURL") or "").strip()
        heading = str(payload.get("Heading") or "").strip()

        if abstract_text:
            results.append(
                {
                    "title": heading or query,
                    "snippet": abstract_text,
                    "url": abstract_url,
                }
            )

        for topic in payload.get("RelatedTopics", []):
            if len(results) >= limit:
                break
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(
                    {
                        "title": str(topic.get("FirstURL") or query).rsplit("/", 1)[-1].replace("_", " "),
                        "snippet": str(topic.get("Text") or "").strip(),
                        "url": str(topic.get("FirstURL") or "").strip(),
                    }
                )
            elif isinstance(topic, dict) and topic.get("Topics"):
                for nested_topic in topic.get("Topics", []):
                    if len(results) >= limit:
                        break
                    if nested_topic.get("Text"):
                        results.append(
                            {
                                "title": str(nested_topic.get("FirstURL") or query).rsplit("/", 1)[-1].replace("_", " "),
                                "snippet": str(nested_topic.get("Text") or "").strip(),
                                "url": str(nested_topic.get("FirstURL") or "").strip(),
                            }
                        )

        return {
            "configured": True,
            "provider": "duckduckgo",
            "query": query,
            "results": results[:limit],
            "message": "Search completed." if results else "No search results were found.",
            "limit": limit,
        }

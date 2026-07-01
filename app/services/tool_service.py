"""Tool registration and execution service."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from fastapi import Depends

from app.clients.calendar_client import CalendarClient, get_calendar_client
from app.clients.home_assistant_client import (
    HomeAssistantClient,
    HttpHomeAssistantClient,
    get_home_assistant_client,
)
from app.clients.web_search_client import WebSearchClient, get_web_search_client
from app.clients.youtube_client import YouTubeClient, get_youtube_client
from app.models.tooling import ToolCall, ToolResult


class AssistantTool(ABC):
    """Abstract assistant tool interface."""

    name: str
    description: str

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the tool with validated arguments."""


class HomeAssistantStateTool(AssistantTool):
    """Tool for fetching Home Assistant entity state."""

    name = "home_assistant_get_state"
    description = "Get the current state of a Home Assistant entity by entity_id or spoken_name."

    def __init__(self, client: HomeAssistantClient) -> None:
        """Store client dependency."""
        self._client = client

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the entity state lookup."""
        entity_id: str | None = str(arguments.get("entity_id", "")).strip() or None
        spoken_name = str(arguments.get("spoken_name", "")).strip()
        domain_hint = str(arguments.get("domain_hint", "")).strip() or None

        if not entity_id and spoken_name and isinstance(self._client, HttpHomeAssistantClient):
            entity_id = await self._client.resolve_entity_id(spoken_name=spoken_name, domain_hint=domain_hint)

        if not entity_id:
            return ToolResult(tool_name=self.name, success=False, error="entity_id or resolvable spoken_name is required")

        try:
            data = await self._client.get_state(entity_id)
            return ToolResult(tool_name=self.name, success=True, data=data)
        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=str(exc))


class HomeAssistantServiceTool(AssistantTool):
    """Tool for calling Home Assistant services."""

    name = "home_assistant_call_service"
    description = "Call a Home Assistant service with domain, service, and optional service_data."

    def __init__(self, client: HomeAssistantClient) -> None:
        """Store client dependency."""
        self._client = client

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the Home Assistant service call."""
        domain = str(arguments.get("domain", "")).strip()
        service = str(arguments.get("service", "")).strip()
        service_data = dict(arguments.get("service_data", {}) or {})
        spoken_name = str(arguments.get("spoken_name", "")).strip()

        if not domain or not service:
            return ToolResult(tool_name=self.name, success=False, error="domain and service are required")

        if spoken_name and "entity_id" not in service_data and isinstance(self._client, HttpHomeAssistantClient):
            resolved = await self._client.resolve_entity_id(spoken_name=spoken_name, domain_hint=domain)
            if resolved:
                service_data["entity_id"] = resolved

        try:
            data = await self._client.call_service(domain, service, service_data)
            return ToolResult(tool_name=self.name, success=True, data=data)
        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=str(exc))


class CalendarUpcomingEventsTool(AssistantTool):
    """Tool for listing upcoming calendar events."""

    name = "calendar_list_upcoming_events"
    description = "List upcoming calendar events with an optional result limit."

    def __init__(self, client: CalendarClient) -> None:
        """Store client dependency."""
        self._client = client

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the calendar lookup."""
        limit = int(arguments.get("limit", 5))
        try:
            data = await self._client.list_upcoming_events(limit=limit)
            return ToolResult(tool_name=self.name, success=True, data=data)
        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=str(exc))


class WebSearchTool(AssistantTool):
    """Tool for performing a web search."""

    name = "web_search"
    description = "Search the web for a query and return summarized results."

    def __init__(self, client: WebSearchClient) -> None:
        """Store client dependency."""
        self._client = client

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the web search."""
        query = str(arguments.get("query", "")).strip()
        limit = int(arguments.get("limit", 3))
        if not query:
            return ToolResult(tool_name=self.name, success=False, error="query is required")

        try:
            data = await self._client.search(query=query, limit=limit)
            return ToolResult(tool_name=self.name, success=True, data=data)
        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=str(exc))


class YouTubeSearchTool(AssistantTool):
    """Tool for searching YouTube videos."""

    name = "youtube_search"
    description = "Search YouTube for videos matching a query and optionally get a playable URL."

    def __init__(self, client: YouTubeClient) -> None:
        """Store client dependency."""
        self._client = client

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the YouTube search."""
        query = str(arguments.get("query", "")).strip()
        limit = int(arguments.get("limit", 3))
        get_url = str(arguments.get("get_url", "")).strip()
        if not query:
            return ToolResult(tool_name=self.name, success=False, error="query is required")
        try:
            data = await self._client.search(query=query, limit=limit)
            if get_url and data.get("results"):
                video_id = data["results"][0].get("id", "")
                if video_id:
                    direct_url = await self._client.get_video_url(video_id)
                    data["direct_url"] = direct_url
                    data["playable_url"] = direct_url
            return ToolResult(tool_name=self.name, success=True, data=data)
        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=str(exc))


class ToolRegistry:
    """Registry and executor for assistant tools."""

    def __init__(self, tools: list[AssistantTool]) -> None:
        """Index tools by name for fast lookup."""
        self._tools = {tool.name: tool for tool in tools}

    def list_tool_specs(self) -> list[dict[str, str]]:
        """Return simple tool metadata for planner consumption."""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]

    async def execute_tool_calls(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute each requested tool call sequentially and return results."""
        results: list[ToolResult] = []
        for tool_call in tool_calls:
            tool = self._tools.get(tool_call.tool_name)
            if tool is None:
                results.append(
                    ToolResult(
                        tool_name=tool_call.tool_name,
                        success=False,
                        error="Unknown tool requested",
                    )
                )
                continue
            results.append(await tool.execute(tool_call.arguments))
        return results


def get_tool_registry(
    home_assistant_client: HomeAssistantClient = Depends(get_home_assistant_client),
    calendar_client: CalendarClient = Depends(get_calendar_client),
    web_search_client: WebSearchClient = Depends(get_web_search_client),
    youtube_client: YouTubeClient = Depends(get_youtube_client),
) -> ToolRegistry:
    """Return a tool registry built from configured integrations."""
    return ToolRegistry(
        tools=[
            HomeAssistantStateTool(home_assistant_client),
            HomeAssistantServiceTool(home_assistant_client),
            CalendarUpcomingEventsTool(calendar_client),
            WebSearchTool(web_search_client),
            YouTubeSearchTool(youtube_client),
        ]
    )

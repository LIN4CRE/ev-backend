"""Tests for assistant tools and registry execution."""

import pytest

from app.clients.calendar_client import NullCalendarClient
from app.clients.home_assistant_client import NullHomeAssistantClient
from app.clients.web_search_client import NullWebSearchClient
from app.models.tooling import ToolCall
from app.services.tool_service import (
    CalendarUpcomingEventsTool,
    HomeAssistantServiceTool,
    HomeAssistantStateTool,
    ToolRegistry,
    WebSearchTool,
)


@pytest.mark.asyncio
async def test_tool_registry_executes_known_and_unknown_tools() -> None:
    """Verify registry execution returns both success and unknown-tool failures."""
    registry = ToolRegistry(
        tools=[
            WebSearchTool(NullWebSearchClient()),
            CalendarUpcomingEventsTool(NullCalendarClient()),
            HomeAssistantStateTool(NullHomeAssistantClient()),
            HomeAssistantServiceTool(NullHomeAssistantClient()),
        ]
    )

    results = await registry.execute_tool_calls(
        [
            ToolCall(tool_name="web_search", arguments={"query": "who is Ada Lovelace", "limit": 2}),
            ToolCall(tool_name="unknown_tool", arguments={}),
        ]
    )

    assert len(results) == 2
    assert results[0].success is True
    assert results[0].tool_name == "web_search"
    assert results[1].success is False
    assert results[1].error == "Unknown tool requested"

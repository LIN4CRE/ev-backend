"""Tests for assistant planning and fallback behavior."""

import pytest

from app.clients.openai_client import StubAIClient
from app.models.tooling import ToolResult
from app.services.assistant_service import AssistantService


@pytest.mark.asyncio
async def test_assistant_service_falls_back_to_calendar_tool_plan() -> None:
    """Verify keyword planning routes to the calendar tool."""
    service = AssistantService(ai_client=StubAIClient())
    plan = await service.plan_response(
        user_text="What is on my calendar today?",
        messages=[],
        available_tools=[],
    )

    assert plan.mode == "tool_call"
    assert plan.tool_calls[0].tool_name == "calendar_list_upcoming_events"


@pytest.mark.asyncio
async def test_assistant_service_builds_tool_fallback_response() -> None:
    """Verify tool results are summarized deterministically when AI finalization is unavailable."""
    service = AssistantService(ai_client=StubAIClient())
    text = await service.build_final_response(
        user_text="Search for Alan Turing",
        messages=[],
        tool_results=[
            ToolResult(
                tool_name="web_search",
                success=True,
                data={"message": "Web search is not configured."},
            )
        ],
    )

    assert "Set WEB_SEARCH_PROVIDER" in text

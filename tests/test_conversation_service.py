"""Tests for conversation orchestration behavior."""

import pytest

from app.clients.calendar_client import NullCalendarClient
from app.clients.home_assistant_client import NullHomeAssistantClient
from app.clients.openai_client import StubAIClient
from app.clients.web_search_client import NullWebSearchClient
from app.models.alexa import AlexaRequestEnvelope
from app.services.conversation_service import ConversationService
from app.services.memory_service import InMemoryConversationMemory
from app.services.tool_service import (
    CalendarUpcomingEventsTool,
    HomeAssistantServiceTool,
    HomeAssistantStateTool,
    ToolRegistry,
    WebSearchTool,
)


@pytest.mark.asyncio
async def test_conversation_service_handles_help_intent() -> None:
    """Verify help intent returns a helpful non-terminal response."""
    service = ConversationService(
        memory=InMemoryConversationMemory(),
        ai_client=StubAIClient(),
        tool_registry=ToolRegistry(
            tools=[
                WebSearchTool(NullWebSearchClient()),
                CalendarUpcomingEventsTool(NullCalendarClient()),
                HomeAssistantStateTool(NullHomeAssistantClient()),
                HomeAssistantServiceTool(NullHomeAssistantClient()),
            ]
        ),
    )
    envelope = AlexaRequestEnvelope.model_validate(
        {
            "version": "1.0",
            "session": {
                "new": False,
                "sessionId": "session-help",
                "application": {"applicationId": "amzn1.ask.skill.test"},
                "user": {"userId": "user-help"},
                "attributes": {},
            },
            "request": {
                "type": "IntentRequest",
                "requestId": "request-help",
                "timestamp": "2026-06-27T12:00:00Z",
                "locale": "en-GB",
                "intent": {
                    "name": "AMAZON.HelpIntent",
                    "slots": {},
                },
            },
        }
    )

    response = await service.handle_alexa_request(envelope)
    assert response.response.shouldEndSession is False
    assert "calendar" in response.response.outputSpeech.text.lower()

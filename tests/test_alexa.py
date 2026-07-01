"""Tests for Alexa webhook behavior."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)

_TEST_SKILL_ID = get_settings().alexa_skill_id or "amzn1.ask.skill.test"


def _current_timestamp() -> str:
    """Return a current ISO timestamp suitable for Alexa request validation tests."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_launch_request_returns_welcome_message() -> None:
    """Verify launch requests produce a valid welcome response."""
    payload = {
        "version": "1.0",
        "session": {
            "new": True,
            "sessionId": "session-1",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": "user-1"},
            "attributes": {},
        },
        "request": {
            "type": "LaunchRequest",
            "requestId": "request-1",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "welcome" in body["response"]["outputSpeech"]["text"].lower() or "opened" in body["response"]["outputSpeech"]["text"].lower() or "hello" in body["response"]["outputSpeech"]["text"].lower()
    assert body["response"]["shouldEndSession"] is False


def test_intent_request_routes_search_like_requests_through_tooling() -> None:
    """Verify search-like intent requests are routed through the tool layer."""
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "session-2",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": "user-2"},
            "attributes": {},
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "request-2",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
            "intent": {
                "name": "AskEvIntent",
                "slots": {
                    "query": {"name": "query", "value": "what is the weather"}
                },
            },
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    body = response.json()
    text = body["response"]["outputSpeech"]["text"]
    assert len(text) > 20  # Ollama generated a real response
    assert not text.startswith("You said:")


def test_invalid_skill_id_is_rejected_when_configured() -> None:
    """Verify requests with the wrong skill ID are rejected when configured.

    Alexa webhook requests must always receive a 200 with a valid Alexa response
    envelope (see app/core/exceptions.py) so the Alexa service does not surface
    "There was a problem with the requested skill's response" to the user.
    """
    from app.core.config import get_settings

    settings = get_settings()
    original_skill_id = settings.alexa_skill_id
    settings.alexa_skill_id = "amzn1.ask.skill.expected"

    payload = {
        "version": "1.0",
        "session": {
            "new": True,
            "sessionId": "session-3",
            "application": {"applicationId": "amzn1.ask.skill.wrong"},
            "user": {"userId": "user-3"},
            "attributes": {},
        },
        "request": {
            "type": "LaunchRequest",
            "requestId": "request-3",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "skill is not available" in body["response"]["outputSpeech"]["text"].lower()

    settings.alexa_skill_id = original_skill_id

"""Alexa-focused end-to-end style tests for operational reliability."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)

_TEST_SKILL_ID = get_settings().alexa_skill_id or "amzn1.ask.skill.test"


def _current_timestamp() -> str:
    """Return a current ISO timestamp suitable for Alexa request validation tests."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_alexa_help_intent_returns_operational_response() -> None:
    """Verify the Alexa webhook returns a stable help response for built-in help intent."""
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "session-help-e2e",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": "user-help-e2e"},
            "attributes": {},
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "request-help-e2e",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
            "intent": {
                "name": "AMAZON.HelpIntent",
                "slots": {},
            },
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "calendar" in body["response"]["outputSpeech"]["text"].lower()
    assert body["response"]["shouldEndSession"] is False


def test_alexa_stop_intent_ends_session() -> None:
    """Verify stop intent produces a terminal Alexa response."""
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "session-stop-e2e",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": "user-stop-e2e"},
            "attributes": {},
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "request-stop-e2e",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
            "intent": {
                "name": "AMAZON.StopIntent",
                "slots": {},
            },
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["response"]["outputSpeech"]["text"] == "Goodbye."
    assert body["response"]["shouldEndSession"] is True

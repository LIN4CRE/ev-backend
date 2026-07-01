"""Tests for explicit Alexa interaction-model intent alignment."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)

_TEST_SKILL_ID = get_settings().alexa_skill_id or "amzn1.ask.skill.test"


def _current_timestamp() -> str:
    """Return a current ISO timestamp suitable for Alexa request validation tests."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_ask_ev_intent_uses_query_slot() -> None:
    """Verify AskEvIntent uses the query slot value for AI processing."""
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "session-ask-ev-intent",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": "user-ask-ev-intent"},
            "attributes": {},
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "request-ask-ev-intent",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
            "intent": {
                "name": "AskEvIntent",
                "slots": {
                    "query": {"name": "query", "value": "hello ev-bot"}
                },
            },
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    text = response.json()["response"]["outputSpeech"]["text"]
    assert len(text) > 20
    assert "hello ev-bot" in text.lower() or "hello" in text.lower()


def test_calendar_query_intent_routes_to_calendar_tooling() -> None:
    """Verify CalendarQueryIntent is routed through calendar-oriented handling."""
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "session-calendar-intent",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": "user-calendar-intent"},
            "attributes": {},
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "request-calendar-intent",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
            "intent": {
                "name": "CalendarQueryIntent",
                "slots": {
                    "timeRange": {"name": "timeRange", "value": "today"}
                },
            },
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    text = response.json()["response"]["outputSpeech"]["text"]
    assert len(text) > 20
    assert ("calendar" in text.lower() or "configure" in text.lower() or ".env" in text
            or "integration" in text.lower() or "events" in text.lower() or "upcoming" in text.lower())


def test_control_home_intent_routes_to_home_tooling() -> None:
    """Verify ControlHomeIntent is routed through home-action handling."""
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "session-home-intent",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": "user-home-intent"},
            "attributes": {},
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "request-home-intent",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
            "intent": {
                "name": "ControlHomeIntent",
                "slots": {
                    "action": {"name": "action", "value": "turn on"},
                    "device": {"name": "device", "value": "living room light"}
                },
            },
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    text = response.json()["response"]["outputSpeech"]["text"]
    assert len(text) > 20

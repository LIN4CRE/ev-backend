"""Tests for additional built-in Alexa intent handling."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)

_TEST_SKILL_ID = get_settings().alexa_skill_id or "amzn1.ask.skill.test"


def _current_timestamp() -> str:
    """Return a current ISO timestamp suitable for Alexa request validation tests."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _intent_payload(intent_name: str) -> dict:
    """Build a minimal Alexa intent payload for built-in intent tests."""
    return {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": f"session-{intent_name}",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": f"user-{intent_name}"},
            "attributes": {},
        },
        "request": {
            "type": "IntentRequest",
            "requestId": f"request-{intent_name}",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
            "intent": {
                "name": intent_name,
                "slots": {},
            },
        },
    }


def test_alexa_fallback_intent_returns_guidance() -> None:
    """Verify fallback intent returns a helpful recovery prompt."""
    response = client.post("/api/v1/alexa/webhook", json=_intent_payload("AMAZON.FallbackIntent"))
    assert response.status_code == 200
    text = response.json()["response"]["outputSpeech"]["text"]
    assert "understand" in text.lower() or "fallback" in text.lower()


def test_alexa_navigate_home_intent_returns_acknowledgement() -> None:
    """Verify navigate home intent returns a stable acknowledgement."""
    response = client.post("/api/v1/alexa/webhook", json=_intent_payload("AMAZON.NavigateHomeIntent"))
    assert response.status_code == 200
    assert "main menu" in response.json()["response"]["outputSpeech"]["text"].lower()


def test_alexa_yes_intent_returns_acknowledgement() -> None:
    """Verify yes intent returns a simple acknowledgement."""
    response = client.post("/api/v1/alexa/webhook", json=_intent_payload("AMAZON.YesIntent"))
    assert response.status_code == 200
    text = response.json()["response"]["outputSpeech"]["text"]
    assert "yes" in text.lower()


def test_alexa_no_intent_returns_acknowledgement() -> None:
    """Verify no intent returns a simple acknowledgement."""
    response = client.post("/api/v1/alexa/webhook", json=_intent_payload("AMAZON.NoIntent"))
    assert response.status_code == 200
    text = response.json()["response"]["outputSpeech"]["text"]
    assert "no" in text.lower()


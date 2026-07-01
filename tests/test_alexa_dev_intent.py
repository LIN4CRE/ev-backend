"""Tests for development Alexa voice command behavior."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)

_TEST_SKILL_ID = get_settings().alexa_skill_id or "amzn1.ask.skill.test"


def _current_timestamp() -> str:
    """Return a current ISO timestamp suitable for Alexa request validation tests."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_prepare_dev_intent_returns_dev_response() -> None:
    """Verify the short dev voice command intent produces a stable response."""
    payload = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "session-dev-intent",
            "application": {"applicationId": _TEST_SKILL_ID},
            "user": {"userId": "user-dev-intent"},
            "attributes": {},
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "request-dev-intent",
            "timestamp": _current_timestamp(),
            "locale": "en-GB",
            "intent": {
                "name": "PrepIntent",
                "slots": {},
            },
        },
    }

    response = client.post("/api/v1/alexa/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["response"]["shouldEndSession"] is False
    assert response.json()["response"]["outputSpeech"]["text"] in {
        "Alexa local setup is ready.",
        "I could not finish local Alexa setup automatically.",
    }

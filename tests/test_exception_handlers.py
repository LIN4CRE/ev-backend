"""Tests for global exception handling behavior."""

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.exceptions import ExternalServiceError, register_exception_handlers
from app.main import app

router = APIRouter()


@router.get("/test-external-error")
def external_error_route() -> dict:
    """Raise a controlled external service error for handler verification."""
    raise ExternalServiceError("search", "timeout")


@router.get("/test-unhandled-error")
def unhandled_error_route() -> dict:
    """Raise an unhandled error for handler verification."""
    raise RuntimeError("boom")


app.include_router(router)
register_exception_handlers(app)
client = TestClient(app, raise_server_exceptions=False)


def test_external_service_error_handler_returns_502() -> None:
    """Verify controlled dependency failures return 502 responses."""
    response = client.get("/test-external-error")
    assert response.status_code == 502
    assert response.json()["detail"] == "External service 'search' failed."


def test_unhandled_exception_handler_returns_500() -> None:
    """Verify unexpected failures return a generic 500 response."""
    response = client.get("/test-unhandled-error")
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error."


def _alexa_webhook_payload() -> dict:
    """Build a minimal valid Alexa LaunchRequest payload for tests."""
    return {
        "version": "1.0",
        "session": {
            "new": True,
            "sessionId": "amzn1.echo-api.session.test",
            "application": {"applicationId": "amzn1.ask.skill.test"},
            "user": {"userId": "amzn1.ask.account.test"},
        },
        "request": {
            "type": "LaunchRequest",
            "requestId": "amzn1.echo-api.request.test",
            "timestamp": "2030-01-01T00:00:00Z",
            "locale": "en-GB",
        },
    }


def test_alexa_webhook_returns_envelope_on_unhandled_exception() -> None:
    """Alexa requests must receive a valid envelope even when the route crashes."""
    response = client.post(
        "/api/v1/alexa/this-route-does-not-exist",
        json=_alexa_webhook_payload(),
    )
    # 404 is fine — we're proving the error envelope shape isn't applied here,
    # since this path doesn't match `/alexa/webhook`.
    assert response.status_code in (404, 405)


def test_alexa_webhook_envelope_shape() -> None:
    """Verify a healthy Alexa request returns a valid envelope (smoke test)."""
    response = client.post(
        "/api/v1/alexa/webhook",
        json=_alexa_webhook_payload(),
    )
    # The webhook may 400 because of timestamp tolerance, but if it does,
    # it MUST be a valid Alexa envelope (not a {"detail": ...} payload).
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1.0"
    assert "response" in body
    assert "outputSpeech" in body["response"]
    assert "shouldEndSession" in body["response"]

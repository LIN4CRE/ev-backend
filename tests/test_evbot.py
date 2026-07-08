"""Tests for the unified EV-Bot companion API routes."""

import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.services.sse_service import _sse_clients
from tests.conftest import TEST_ADMIN_API_KEY

client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-Api-Key": TEST_ADMIN_API_KEY}


def test_evbot_routes_require_admin_auth() -> None:
    """Verify evbot endpoints reject requests without an admin API key."""
    response = client.get("/api/v1/evbot/state")
    assert response.status_code == 401


def test_evbot_state_returns_aggregated_payload() -> None:
    """Verify the state endpoint returns the expected shape."""
    response = client.get("/api/v1/evbot/state", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "online"
    assert "pcConnection" in payload


def test_evbot_health_endpoint() -> None:
    """Verify the lightweight companion health check responds."""
    response = client.get("/api/v1/evbot/health", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "ev-backend"}


def _drain_broadcast(queue: asyncio.Queue) -> dict:
    """Synchronously pull a single message pushed onto an SSE queue."""
    return asyncio.run(asyncio.wait_for(queue.get(), timeout=1))


def test_alexa_trigger_broadcasts_sse_event() -> None:
    """Verify triggering an Alexa action pushes a matching SSE event."""
    queue: asyncio.Queue = asyncio.Queue()
    _sse_clients.append(queue)
    try:
        response = client.post(
            "/api/v1/evbot/alexa/trigger",
            json={"phrase": "turn on the lights"},
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        event = response.json()["event"]
        assert event["phrase"] == "turn on the lights"

        message = _drain_broadcast(queue)
        assert message["type"] == "alexa_event"
        assert message["phrase"] == "turn on the lights"
    finally:
        _sse_clients.remove(queue)


def test_create_macro_broadcasts_sse_event() -> None:
    """Verify creating a macro pushes a matching SSE event."""
    queue: asyncio.Queue = asyncio.Queue()
    _sse_clients.append(queue)
    try:
        response = client.post(
            "/api/v1/evbot/macros",
            json={"name": "goodnight"},
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        macro = response.json()["macro"]
        assert macro["name"] == "goodnight"

        message = _drain_broadcast(queue)
        assert message["type"] == "desktop_macro_created"
        assert message["macro"]["id"] == macro["id"]
    finally:
        _sse_clients.remove(queue)


def test_toggle_macro_broadcasts_sse_event() -> None:
    """Verify toggling a macro pushes a matching SSE event."""
    queue: asyncio.Queue = asyncio.Queue()
    _sse_clients.append(queue)
    try:
        response = client.patch(
            "/api/v1/evbot/macros/macro-1",
            json={"isActive": False},
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["macro"]["isActive"] is False

        message = _drain_broadcast(queue)
        assert message["type"] == "desktop_macro_toggled"
        assert message["macro"]["id"] == "macro-1"
    finally:
        _sse_clients.remove(queue)


def test_delete_macro_broadcasts_sse_event() -> None:
    """Verify deleting a macro pushes a matching SSE event."""
    queue: asyncio.Queue = asyncio.Queue()
    _sse_clients.append(queue)
    try:
        response = client.delete("/api/v1/evbot/macros/macro-1", headers=ADMIN_HEADERS)
        assert response.status_code == 200
        assert response.json() == {"deleted": "macro-1", "ok": True}

        message = _drain_broadcast(queue)
        assert message == {"type": "desktop_macro_deleted", "id": "macro-1"}
    finally:
        _sse_clients.remove(queue)


def test_report_connection_broadcasts_sse_event() -> None:
    """Verify reporting a PC connection pushes a matching SSE event."""
    queue: asyncio.Queue = asyncio.Queue()
    _sse_clients.append(queue)
    try:
        response = client.post(
            "/api/v1/evbot/connection",
            json={"ipAddress": "100.64.0.1"},
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["ipAddress"] == "100.64.0.1"

        message = _drain_broadcast(queue)
        assert message["type"] == "pc_connection"
        assert message["ipAddress"] == "100.64.0.1"
    finally:
        _sse_clients.remove(queue)

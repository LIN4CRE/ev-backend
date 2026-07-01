"""Tests for admin diagnostics endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.memory_service import get_memory_provider

client = TestClient(app)


def test_admin_tools_endpoint_returns_registered_tools() -> None:
    """Verify the admin tools endpoint exposes the available tools."""
    response = client.get(
        "/api/v1/admin/tools",
        headers={"X-Admin-Api-Key": "change-me-in-production!!!"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert any(tool["name"] == "web_search" for tool in payload["tools"])


def test_admin_memory_endpoints_return_session_data() -> None:
    """Verify the admin memory endpoints expose stored conversation state."""
    memory = get_memory_provider()
    memory.append_message("session-admin-test", "user", "hello")
    memory.append_message("session-admin-test", "assistant", "hi there")

    list_response = client.get(
        "/api/v1/admin/memory/sessions",
        headers={"X-Admin-Api-Key": "change-me-in-production!!!"},
    )
    assert list_response.status_code == 200
    assert "session-admin-test" in list_response.json()["sessions"]

    detail_response = client.get(
        "/api/v1/admin/memory/session",
        params={"session_id": "session-admin-test"},
        headers={"X-Admin-Api-Key": "change-me-in-production!!!"},
    )
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["session_id"] == "session-admin-test"
    assert len(payload["messages"]) >= 2

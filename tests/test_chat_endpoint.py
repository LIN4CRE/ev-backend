"""Tests for the chat endpoint and its rate limiting."""

from fastapi.testclient import TestClient

from app.core.rate_limit import chat_rate_limiter
from app.main import app

client = TestClient(app)


def test_chat_endpoint_rate_limiting() -> None:
    """Verify the chat endpoint rate limits after too many requests."""
    # Reset the rate limiter state for a clean test
    chat_rate_limiter.reset()
    
    # We will simulate multiple requests from the same client IP
    # Under test client, client host is testclient
    # Let's fire 20 successful requests (or mock/stub client response)
    # The default AI provider is 'stub' under test environment config
    
    payload = {"message": "hello", "session_id": "test-session"}
    
    # Run 20 requests
    for _ in range(20):
        response = client.post("/api/v1/chat", json=payload)
        # Should be successful (or at least not 429)
        assert response.status_code != 429
        
    # The 21st request should be rate-limited (HTTP 429)
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded."
    
    # Clean up rate limiter state after test
    chat_rate_limiter.reset()

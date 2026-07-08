"""Tests for the SSE broadcast service."""

import asyncio

import pytest

from app.services import sse_service


@pytest.mark.asyncio
async def test_broadcast_drops_oldest_when_client_queue_full(monkeypatch) -> None:
    """A stalled client must not grow memory unboundedly or block broadcasts."""
    monkeypatch.setattr(sse_service, "_sse_clients", [])
    stalled: asyncio.Queue = asyncio.Queue(maxsize=2)
    sse_service._sse_clients.append(stalled)

    await sse_service.broadcast_state_change("event", {"n": 1})
    await sse_service.broadcast_state_change("event", {"n": 2})
    await sse_service.broadcast_state_change("event", {"n": 3})

    assert stalled.qsize() == 2
    first = stalled.get_nowait()
    second = stalled.get_nowait()
    assert first["n"] == 2
    assert second["n"] == 3


@pytest.mark.asyncio
async def test_broadcast_reaches_all_clients(monkeypatch) -> None:
    """Every subscribed client receives each broadcast."""
    monkeypatch.setattr(sse_service, "_sse_clients", [])
    a: asyncio.Queue = asyncio.Queue(maxsize=10)
    b: asyncio.Queue = asyncio.Queue(maxsize=10)
    sse_service._sse_clients.extend([a, b])

    await sse_service.broadcast_state_change("ping", {"x": 1})

    assert a.get_nowait() == {"type": "ping", "x": 1}
    assert b.get_nowait() == {"type": "ping", "x": 1}

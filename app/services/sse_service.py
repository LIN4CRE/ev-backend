"""SSE event bus for broadcasting state changes to subscribed clients."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

# Cap per-client queues so a stalled client (connected but not reading) cannot
# grow memory without bound. When full, the oldest event is dropped for that
# client only — broadcasts never block the producer.
_MAX_QUEUED_EVENTS = 100

_sse_clients: list[asyncio.Queue] = []


async def sse_event_publisher() -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events to all connected clients."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUED_EVENTS)
    _sse_clients.append(queue)
    try:
        while True:
            data = await queue.get()
            yield f"data: {json.dumps(data)}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _sse_clients.remove(queue)


async def broadcast_state_change(event_type: str, payload: dict) -> None:
    """Push a state-change event to all subscribed SSE clients."""
    message = {"type": event_type, **payload}
    for queue in list(_sse_clients):
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass

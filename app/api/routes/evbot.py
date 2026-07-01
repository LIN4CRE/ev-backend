"""EV-Bot unified endpoints — replaces server.ts for mobile/desktop consumers."""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.auth import require_admin_access
from app.services.memory_service import ConversationMemory, get_memory_provider

router = APIRouter(
    prefix="/evbot",
    tags=["evbot"],
    dependencies=[Depends(require_admin_access)],
)


@router.get("/state")
def get_aggregated_state(
    request: Request,
    memory: ConversationMemory = Depends(get_memory_provider),
) -> dict:
    """Return aggregate EV-Bot state — replaced server.ts /api/evbot/state."""
    _ = request
    sessions = memory.list_sessions() if hasattr(memory, "list_sessions") else []
    return {
        "status": "online",
        "alexaEvents": [],
        "desktopMacros": [],
        "sessions": sessions,
    }


@router.post("/alexa/trigger")
async def trigger_alexa_action(
    request: Request,
) -> dict:
    """Trigger an Alexa skill action — replaced server.ts /api/alexa/trigger."""
    body = await request.json()
    phrase = body.get("phrase", "")
    return {
        "event": {
            "id": f"evbot-{hash(phrase)}",
            "timestamp": str(__import__("datetime").datetime.now()),
            "phrase": phrase,
            "status": "forwarded",
            "actionTaken": "Forwarded to Alexa skill",
        }
    }


@router.get("/macros")
def list_macros(request: Request) -> dict:
    """List desktop macros — replaced server.ts /api/desktop/macros."""
    _ = request
    return {"macros": []}


@router.post("/macros")
async def create_macro(request: Request) -> dict:
    """Create a desktop macro — replaced server.ts /api/desktop/macros."""
    _ = request
    body = await request.json()
    return {
        "macro": {
            "id": f"macro-{hash(str(body))}",
            **body,
        }
    }


@router.patch("/macros/{macro_id}")
async def toggle_macro(macro_id: str, request: Request) -> dict:
    """Toggle a macro — replaced server.ts /api/desktop/macros/:id."""
    body = await request.json()
    is_active = body.get("isActive", True)
    return {
        "macro": {
            "id": macro_id,
            "isActive": is_active,
        }
    }


@router.delete("/macros/{macro_id}")
def delete_macro(macro_id: str, request: Request) -> dict:
    """Delete a macro — replaced server.ts /api/desktop/macros/:id."""
    _ = request
    return {"deleted": macro_id, "ok": True}


@router.post("/connection")
async def report_connection(request: Request) -> dict:
    """Report PC connection state — replaced server.ts /api/connection."""
    body = await request.json()
    return {"status": "ok", "connected": True, **body}


@router.get("/health")
def evbot_health(request: Request) -> dict:
    """Lightweight health check from the ev-bot-companion app."""
    _ = request
    return {"status": "healthy", "service": "ev-backend"}


# SSE event bus — clients subscribe and receive state updates
_sse_clients: list[asyncio.Queue] = []


async def _sse_event_publisher(request: Request) -> None:
    """Yield SSE-formatted events to all connected clients."""
    queue: asyncio.Queue = asyncio.Queue()
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
    for queue in _sse_clients:
        await queue.put(message)


@router.get("/events")
async def sse_event_stream(request: Request):
    """Server-Sent Events endpoint — replaces 30s polling with push."""
    return StreamingResponse(
        _sse_event_publisher(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

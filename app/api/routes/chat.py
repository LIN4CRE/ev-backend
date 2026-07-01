"""Web chat routes for ev-bot.uk."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.clients.openai_client import AIClient, get_ai_client
from app.core.rate_limit import rate_limit_chat_requests
from app.services.memory_service import ConversationMemory, get_memory_provider
from app.services.web_chat_service import WebChatService

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Incoming web chat message."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message text.")
    session_id: str = Field(..., min_length=1, max_length=128, description="Client-generated session identifier.")


class ChatResponse(BaseModel):
    """Outgoing web chat reply."""

    reply: str = Field(..., description="Assistant reply text.")
    session_id: str = Field(..., description="Echo of the session identifier.")


@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limit_chat_requests)])
async def web_chat(
    body: ChatRequest,
    memory: ConversationMemory = Depends(get_memory_provider),
    ai_client: AIClient = Depends(get_ai_client),
) -> ChatResponse:
    """Accept a user message and return an EV-expert AI reply."""
    service = WebChatService(memory=memory, ai_client=ai_client)
    try:
        reply = await service.chat(message=body.message, session_id=body.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ChatResponse(reply=reply, session_id=body.session_id)

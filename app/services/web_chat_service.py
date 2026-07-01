"""Web chat orchestration service for ev-bot.uk."""

from __future__ import annotations

from app.clients.openai_client import AIClient
from app.core.system_prompt import EV_SYSTEM_PROMPT
from app.services.memory_service import ConversationMemory


class WebChatService:
    """Orchestrates web chat conversations with an EV-expert persona."""

    def __init__(self, memory: ConversationMemory, ai_client: AIClient) -> None:
        """Store collaborators."""
        self._memory = memory
        self._ai_client = ai_client

    async def chat(self, message: str, session_id: str) -> str:
        """Process a web chat message and return a reply."""
        self._memory.append_message(session_id=session_id, role="user", content=message)
        messages = self._memory.get_messages(session_id)
        reply = await self._ai_client.generate_web_reply(
            system_prompt=EV_SYSTEM_PROMPT,
            messages=messages,
        )
        self._memory.append_message(session_id=session_id, role="assistant", content=reply)
        return reply

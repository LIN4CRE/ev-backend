"""OpenAI client abstractions used by the conversation orchestrator."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings, get_settings
from app.models.tooling import AssistantPlan, ToolResult


class AIClient(ABC):
    """Abstract interface for LLM-backed assistant providers."""

    @abstractmethod
    async def generate_assistant_reply(self, messages: list[dict]) -> str:
        """Generate a simple assistant reply from conversation messages."""

    @abstractmethod
    async def plan_response(
        self,
        user_text: str,
        messages: list[dict],
        available_tools: list[dict[str, str]],
    ) -> AssistantPlan | None:
        """Generate a direct response or requested tool plan."""

    @abstractmethod
    async def generate_final_response(
        self,
        user_text: str,
        messages: list[dict],
        tool_results: list[ToolResult],
    ) -> str | None:
        """Generate the final response after tool execution."""

    @abstractmethod
    async def generate_web_reply(self, system_prompt: str, messages: list[dict]) -> str:
        """Generate a reply using full conversation history and a custom system prompt."""


class StubAIClient(AIClient):
    """Deterministic fallback AI client used until provider integration is enabled."""

    async def generate_assistant_reply(self, messages: list[dict]) -> str:
        """Return a simple response based on the latest user message."""
        latest_user_message = next(
            (message["content"] for message in reversed(messages) if message.get("role") == "user"),
            "Hello.",
        )
        return f"You said: {latest_user_message}"

    async def plan_response(
        self,
        user_text: str,
        messages: list[dict],
        available_tools: list[dict[str, str]],
    ) -> AssistantPlan | None:
        """Return None to allow the orchestration layer fallback planner to decide."""
        _ = user_text
        _ = messages
        _ = available_tools
        return None

    async def generate_final_response(
        self,
        user_text: str,
        messages: list[dict],
        tool_results: list[ToolResult],
    ) -> str | None:
        """Return None to allow orchestration fallback response generation."""
        _ = user_text
        _ = messages
        _ = tool_results
        return None

    async def generate_web_reply(self, system_prompt: str, messages: list[dict]) -> str:
        """Return a stub response indicating the AI provider is not configured."""
        _ = system_prompt
        latest = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "Hello.",
        )
        return (
            f"I heard you ask: '{latest}'. "
            "To get real answers, set AI_PROVIDER=openai and add your OPENAI_API_KEY to .env."
        )


class OpenAIClient(AIClient):
    """HTTP-backed OpenAI client wrapper.

    This implementation uses the Responses API over plain HTTP to keep the
    dependency surface small and the integration explicit.
    """

    def __init__(self, settings: Settings, timeout_seconds: float = 30.0) -> None:
        """Store settings required for provider requests."""
        self._settings = settings
        self._timeout_seconds = timeout_seconds
        self._base_url = "https://api.openai.com/v1/responses"
        self._model = settings.openai_model

    async def generate_assistant_reply(self, messages: list[dict]) -> str:
        """Generate a simple assistant reply using the provider."""
        latest_user_message = next(
            (message["content"] for message in reversed(messages) if message.get("role") == "user"),
            "Hello.",
        )
        plan = await self._request_text(
            system_prompt=(
                "You are Ev, a concise, helpful voice assistant. "
                "Respond briefly and naturally for spoken Alexa output."
            ),
            user_prompt=latest_user_message,
        )
        return plan or f"You said: {latest_user_message}"

    async def plan_response(
        self,
        user_text: str,
        messages: list[dict],
        available_tools: list[dict[str, str]],
    ) -> AssistantPlan | None:
        """Ask the model to decide whether tools are required."""
        _ = messages
        tools_json = json.dumps(available_tools)
        prompt = (
            "Decide whether the user request needs a tool. "
            "Return JSON only with keys: mode, response_text, tool_calls. "
            "mode must be either direct_response or tool_call. "
            "tool_calls must be an array of objects with tool_name and arguments. "
            f"Available tools: {tools_json}. "
            f"User request: {user_text}"
        )
        content = await self._request_text(
            system_prompt=(
                "You are an orchestration planner for Ev. "
                "Return strict JSON only and never include markdown fences."
            ),
            user_prompt=prompt,
        )
        if not content:
            return None

        try:
            return AssistantPlan.model_validate_json(content)
        except Exception:
            return None

    async def generate_final_response(
        self,
        user_text: str,
        messages: list[dict],
        tool_results: list[ToolResult],
    ) -> str | None:
        """Ask the model to turn tool results into a concise spoken answer."""
        _ = messages
        prompt = (
            "Using the provided tool results, answer the user in a concise spoken format. "
            "Avoid markdown, lists, and unnecessary detail. "
            f"User request: {user_text}. "
            f"Tool results: {json.dumps([result.model_dump() for result in tool_results])}"
        )
        return await self._request_text(
            system_prompt="You are Ev, a concise and helpful voice assistant.",
            user_prompt=prompt,
        )

    async def generate_web_reply(self, system_prompt: str, messages: list[dict]) -> str:
        """Generate a reply using full conversation history via Chat Completions API."""
        if not self._settings.openai_api_key:
            return "No API key configured. Please set OPENAI_API_KEY in your .env file."

        chat_messages = [{"role": "system", "content": system_prompt}, *messages]

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self._model, "messages": chat_messages},
                )
                response.raise_for_status()
                body = response.json()
            return body["choices"][0]["message"]["content"].strip()
        except Exception:
            return "Sorry, I couldn't reach the AI right now. Please try again in a moment."

    async def _request_text(self, system_prompt: str, user_prompt: str) -> str | None:
        """Issue a Responses API request and extract text content safely."""
        if not self._settings.openai_api_key:
            return None

        payload = {
            "model": self._model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._base_url,
                    headers={
                        "Authorization": f"Bearer {self._settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except Exception:
            return None

        output = body.get("output", [])
        extracted_parts: list[str] = []
        for item in output:
            for content_item in item.get("content", []):
                text = content_item.get("text")
                if text:
                    extracted_parts.append(text)

        combined = " ".join(part.strip() for part in extracted_parts if part and part.strip()).strip()
        return combined or body.get("output_text")


class OllamaClient(AIClient):
    """Ollama-backed AI client using the local Ollama API."""

    def __init__(self, settings: Settings, timeout_seconds: float = 30.0) -> None:
        """Store settings required for Ollama requests."""
        self._settings = settings
        self._timeout_seconds = timeout_seconds
        self._base_url = settings.ollama_base_url.rstrip("/") + "/api/chat"
        self._model = settings.ollama_model

    async def generate_assistant_reply(self, messages: list[dict]) -> str:
        """Generate a simple assistant reply using Ollama."""
        latest_user_message = next(
            (message["content"] for message in reversed(messages) if message.get("role") == "user"),
            "Hello.",
        )
        content = await self._request_chat(
            system_prompt="You are Ev, a concise, helpful voice assistant. Respond briefly and naturally for spoken Alexa output.",
            user_prompt=latest_user_message,
        )
        return content or f"You said: {latest_user_message}"

    async def plan_response(
        self,
        user_text: str,
        messages: list[dict],
        available_tools: list[dict[str, str]],
    ) -> AssistantPlan | None:
        """Ask the model to decide whether tools are required."""
        _ = messages
        tools_json = json.dumps(available_tools)
        prompt = (
            "Decide whether the user request needs a tool. "
            "Return JSON only with keys: mode, response_text, tool_calls. "
            "mode must be either direct_response or tool_call. "
            "tool_calls must be an array of objects with tool_name and arguments. "
            f"Available tools: {tools_json}. "
            f"User request: {user_text}"
        )
        content = await self._request_chat(
            system_prompt="You are an orchestration planner for Ev. Return strict JSON only and never include markdown fences.",
            user_prompt=prompt,
        )
        if not content:
            return None
        try:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                cleaned = cleaned.rsplit("\n", 1)[0] if "```" in cleaned else cleaned
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return AssistantPlan.model_validate_json(cleaned.strip())
        except Exception:
            return None

    async def generate_final_response(
        self,
        user_text: str,
        messages: list[dict],
        tool_results: list[ToolResult],
    ) -> str | None:
        """Ask the model to turn tool results into a concise spoken answer."""
        _ = messages
        prompt = (
            "Using the provided tool results, answer the user in a concise spoken format. "
            "Avoid markdown, lists, and unnecessary detail. "
            f"User request: {user_text}. "
            f"Tool results: {json.dumps([result.model_dump() for result in tool_results])}"
        )
        return await self._request_chat(
            system_prompt="You are Ev, a concise and helpful voice assistant.",
            user_prompt=prompt,
        )

    async def generate_web_reply(self, system_prompt: str, messages: list[dict]) -> str:
        """Generate a reply using full conversation history via the Ollama API."""
        chat_messages = [{"role": "system", "content": system_prompt}, *messages]
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._base_url,
                    json={"model": self._model, "messages": chat_messages, "stream": False},
                )
                response.raise_for_status()
                body = response.json()
            return (body.get("message") or {}).get("content", "").strip()
        except Exception:
            return "Sorry, I couldn't reach the AI right now. Please try again in a moment."

    async def _request_chat(self, system_prompt: str, user_prompt: str) -> str | None:
        """Issue a chat request to the local Ollama API and extract text content."""
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._base_url,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except Exception:
            return None
        return (body.get("message") or {}).get("content", "").strip() or None


class GeminiClient(AIClient):
    """Google Gemini AI client using the Generative Language REST API."""

    def __init__(self, settings: Settings, timeout_seconds: float = 30.0) -> None:
        """Store settings required for Gemini requests."""
        self._settings = settings
        self._timeout_seconds = timeout_seconds
        self._model = settings.gemini_model
        self._base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"

    async def _request(self, system_prompt: str, messages: list[dict]) -> str | None:
        """Issue a Gemini generateContent request and return the text response."""
        if not self._settings.gemini_api_key:
            return None

        contents = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        payload: dict = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._base_url,
                    params={"key": self._settings.gemini_api_key},
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                body = response.json()
        except Exception:
            return None

        try:
            return body["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            return None

    async def generate_assistant_reply(self, messages: list[dict]) -> str:
        """Generate a concise spoken reply for Alexa."""
        from app.core.system_prompt import EV_SYSTEM_PROMPT
        latest = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "Hello.")
        result = await self._request(EV_SYSTEM_PROMPT, [{"role": "user", "content": latest}])
        return result or f"You said: {latest}"

    async def plan_response(
        self,
        user_text: str,
        messages: list[dict],
        available_tools: list[dict[str, str]],
    ) -> AssistantPlan | None:
        """Ask Gemini to decide whether tools are needed."""
        tools_json = json.dumps(available_tools)
        prompt = (
            "Decide whether the user request needs a tool. "
            "Return JSON only with keys: mode, response_text, tool_calls. "
            "mode must be either direct_response or tool_call. "
            "tool_calls must be an array of objects with tool_name and arguments. "
            f"Available tools: {tools_json}. "
            f"User request: {user_text}"
        )
        content = await self._request(
            "You are an orchestration planner. Return strict JSON only, never markdown fences.",
            [{"role": "user", "content": prompt}],
        )
        if not content:
            return None
        try:
            cleaned = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return AssistantPlan.model_validate_json(cleaned)
        except Exception:
            return None

    async def generate_final_response(
        self,
        user_text: str,
        messages: list[dict],
        tool_results: list[ToolResult],
    ) -> str | None:
        """Turn tool results into a concise spoken answer."""
        prompt = (
            "Using the provided tool results, answer the user in a concise spoken format. "
            "Avoid markdown, lists, and unnecessary detail. "
            f"User request: {user_text}. "
            f"Tool results: {json.dumps([result.model_dump() for result in tool_results])}"
        )
        return await self._request(
            "You are Ev, a concise and helpful voice assistant.",
            [{"role": "user", "content": prompt}],
        )

    async def generate_web_reply(self, system_prompt: str, messages: list[dict]) -> str:
        """Generate a full conversational reply with history."""
        if not self._settings.gemini_api_key:
            return "No Gemini API key configured. Please set GEMINI_API_KEY in your .env file."
        result = await self._request(system_prompt, messages)
        return result or "Sorry, I couldn't reach Gemini right now. Please try again."


def get_ai_client() -> AIClient:
    """Return the most appropriate AI client for the current configuration."""
    settings = get_settings()
    provider = settings.ai_provider
    if provider == "gemini" and settings.gemini_api_key:
        return GeminiClient(settings)
    if provider == "ollama":
        return OllamaClient(settings)
    if provider == "openai" and settings.openai_api_key:
        return OpenAIClient(settings)
    return StubAIClient()

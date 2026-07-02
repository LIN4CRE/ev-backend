"""Conversation orchestration service."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

from app.clients.openai_client import AIClient
from app.core.config import get_settings
from app.models.alexa import (
    AlexaAplRenderDocumentDirective,
    AlexaPlainTextOutputSpeech,
    AlexaReprompt,
    AlexaRequestEnvelope,
    AlexaResponseBody,
    AlexaResponseEnvelope,
)
from app.models.tooling import ToolResult
from app.services.assistant_service import AssistantService
from app.services.dev_setup_service import DevSetupService
from app.services.memory_service import ConversationMemory
from app.services.sse_service import broadcast_state_change
from app.services.tool_service import ToolRegistry

# Hostnames (or parent domains) permitted as APL video sources. yt-dlp resolves
# YouTube playback to *.googlevideo.com stream URLs; the canonical YouTube
# domains are allowed as well.
_ALLOWED_VIDEO_DOMAINS = (
    "googlevideo.com",
    "youtube.com",
    "youtu.be",
    "ytimg.com",
)


def _is_safe_video_url(url: str) -> bool:
    """Return True only for HTTPS URLs on a known YouTube/Google video domain.

    Prevents an unexpected or malicious URL (e.g. from yt-dlp output) from being
    injected verbatim into the APL document sent to the Echo Show device.
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return any(host == domain or host.endswith("." + domain) for domain in _ALLOWED_VIDEO_DOMAINS)


_BUILTIN_PROMPTS = {
    "AMAZON.HelpIntent": "The user just asked for help on a voice assistant. Give a friendly, concise list of things they can ask about: questions, web search, calendar, smart home control, timers, reminders, weather, news, music. Keep it under 30 words since this is spoken aloud.",
    "AMAZON.YesIntent": "The user just said 'yes'. Respond briefly and invite them to tell you what they need. Keep it under 15 words.",
    "AMAZON.NoIntent": "The user just said 'no'. Acknowledge politely and let them know you're here if they need anything. Keep it under 15 words.",
    "AMAZON.NavigateHomeIntent": "The user asked to go back to the main menu. Greet them and briefly remind them what you can do. Keep it under 20 words.",
    "AMAZON.FallbackIntent": "The user said something you couldn't understand. Apologize briefly and remind them of the main capabilities. Keep it under 25 words.",
}


class ResponseCache:
    """Simple in-memory TTL cache for LLM responses."""

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self._ttl = ttl_seconds
        self._cache: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> str | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: str) -> None:
        self._cache[key] = (value, time.time() + self._ttl)

    def invalidate(self, key: str) -> None:
        """Remove a single key from the cache if present."""
        self._cache.pop(key, None)


class ConversationService:
    """Coordinates Alexa requests, memory, tools, and AI-generated responses."""

    def __init__(self, memory: ConversationMemory, ai_client: AIClient, tool_registry: ToolRegistry, base_url: str = "https://ev-bot.uk") -> None:
        """Store required collaborators for conversation processing."""
        self._memory = memory
        self._ai_client = ai_client
        self._tool_registry = tool_registry
        self._base_url = base_url
        self._assistant_service = AssistantService(ai_client=ai_client)
        self._dev_setup_service = DevSetupService(get_settings())
        self._response_cache = ResponseCache()

    async def handle_alexa_request(self, envelope: AlexaRequestEnvelope) -> AlexaResponseEnvelope:
        """Route supported Alexa request types to the appropriate handler."""
        request_type = envelope.request.type

        if request_type == "LaunchRequest":
            return await self._launch_request(envelope)

        if request_type == "SessionEndedRequest":
            # Clear the cached launch response so the next session gets a fresh greeting.
            self._response_cache.invalidate("launch")
            return await self._build_response(
                text="Goodbye.",
                should_end_session=True,
            )

        if request_type == "IntentRequest":
            return await self._handle_intent_request(envelope)

        return await self._build_response(
            text="Sorry, I could not process that request.",
            should_end_session=False,
        )

    async def _launch_request(self, envelope: AlexaRequestEnvelope) -> AlexaResponseEnvelope:
        """Generate a dynamic welcome message via LLM."""
        cached = self._response_cache.get("launch")
        if cached:
            return await self._build_response(
                text=cached,
                should_end_session=False,
                reprompt_text="Try asking me a question or checking your calendar.",
                directives=[self._build_visuals_directive(cached, envelope)],
            )
        text = await self._ai_client.generate_assistant_reply(
            [{"role": "user", "content": "A user has just opened the EV-Bot voice assistant. Say a warm, concise welcome mentioning the official platform 'ev-bot.uk', and list your main capabilities in 2 sentences."}]
        )
        self._response_cache.set("launch", text)
        return await self._build_response(
            text=text,
            should_end_session=False,
            reprompt_text="Try asking me a question or checking your calendar.",
            directives=[self._build_visuals_directive(text, envelope)],
        )

    async def _handle_intent_request(self, envelope: AlexaRequestEnvelope) -> AlexaResponseEnvelope:
        """Handle Alexa intent requests through orchestration logic."""
        session_id = envelope.session.sessionId if envelope.session else envelope.request.requestId
        intent = envelope.request.intent
        if intent is None:
            return await self._build_response(
                text="Sorry, I did not understand that request.",
                should_end_session=False,
            )

        if intent.name == "AMAZON.StopIntent":
            return await self._build_response(text="Goodbye.", should_end_session=True)

        if intent.name == "PrepIntent":
            message = self._dev_setup_service.prepare_alexa_local_dev()
            return await self._build_response(
                text=message,
                should_end_session=False,
                reprompt_text="You can say prep again after starting your tunnel.",
            )

        prompt = _BUILTIN_PROMPTS.get(intent.name)
        if prompt:
            return await self._builtin_intent_via_llm(session_id, intent.name, prompt, envelope)

        utterance = self._build_intent_specific_utterance(intent.name, intent.slots)
        self._memory.append_message(session_id=session_id, role="user", content=utterance)
        messages = self._memory.get_messages(session_id)

        cache_key = f"{intent.name}:{utterance}"
        cached = self._response_cache.get(cache_key)
        if cached:
            return await self._build_response(
                text=cached,
                should_end_session=False,
                reprompt_text="What else can I help with?",
            )

        plan = await self._assistant_service.plan_response(
            user_text=utterance,
            messages=messages,
            available_tools=self._tool_registry.list_tool_specs(),
        )

        if plan.mode == "direct_response" and plan.response_text:
            assistant_reply = plan.response_text
            directives = [self._build_visuals_directive(assistant_reply, envelope)]
        elif plan.mode == "tool_call":
            tool_results = await self._tool_registry.execute_tool_calls(plan.tool_calls)
            assistant_reply = await self._assistant_service.build_final_response(
                user_text=utterance,
                messages=messages,
                tool_results=tool_results,
            )
            directives = self._build_youtube_directives(tool_results)
            if not directives:
                directives = [self._build_visuals_directive(assistant_reply, envelope)]
        else:
            assistant_reply = await self._ai_client.generate_assistant_reply(messages)
            directives = [self._build_visuals_directive(assistant_reply, envelope)]

        self._memory.append_message(session_id=session_id, role="assistant", content=assistant_reply)
        self._response_cache.set(cache_key, assistant_reply)

        return await self._build_response(
            text=assistant_reply,
            should_end_session=False,
            reprompt_text="What else can I help with?",
            directives=directives,
        )

    async def _builtin_intent_via_llm(self, session_id: str, intent_name: str, prompt: str, envelope: AlexaRequestEnvelope | None = None) -> AlexaResponseEnvelope:
        """Generate an LLM-powered response for built-in intents instead of hardcoded text."""
        cached = self._response_cache.get(intent_name)
        if cached:
            return await self._build_response(
                text=cached,
                should_end_session=False,
                reprompt_text="What can I do for you?",
                directives=[self._build_visuals_directive(cached, envelope)],
            )
        text = await self._ai_client.generate_assistant_reply(
            [{"role": "user", "content": prompt}]
        )
        self._response_cache.set(intent_name, text)
        return await self._build_response(
            text=text,
            should_end_session=False,
            reprompt_text="What can I do for you?",
            directives=[self._build_visuals_directive(text, envelope)],
        )

    def _build_youtube_directives(self, tool_results: list[ToolResult]) -> list:
        """Build APL directives if tool results contain a playable YouTube video."""

        for result in tool_results:
            if result.tool_name == "youtube_search" and result.success:
                data = result.data
                playable_url = data.get("direct_url") or data.get("playable_url")
                results = data.get("results", [])
                if playable_url and results and _is_safe_video_url(playable_url):
                    title = results[0].get("title", "YouTube Video")
                    return [self._build_apl_video_directive(title, playable_url)]
        return []

    def _build_intent_specific_utterance(self, intent_name: str, slots: dict[str, Any]) -> str:
        """Convert known Alexa intents into backend-friendly user utterances."""
        if intent_name == "AskEvIntent":
            return self._slot_value(slots, "query") or "help me"

        if intent_name == "CalendarQueryIntent":
            time_range = self._slot_value(slots, "timeRange")
            return f"what is on my calendar {time_range}".strip()

        if intent_name == "YouTubeIntent":
            query = self._slot_value(slots, "query") or "help me"
            return f"show me {query} on youtube"

        if intent_name == "ControlHomeIntent":
            action = self._slot_value(slots, "action") or "check"
            device = self._slot_value(slots, "device") or "device"
            return f"{action} the {device}".strip()

        if intent_name == "WeatherIntent":
            location = self._slot_value(slots, "location") or "my location"
            return f"what is the weather in {location}"

        if intent_name == "SetTimerIntent":
            duration = self._slot_value(slots, "duration") or "5 minutes"
            label = self._slot_value(slots, "label") or "timer"
            return f"set a timer for {duration} called {label}"

        if intent_name == "TimerStatusIntent":
            return "how much time is left on my timer"

        if intent_name == "CancelTimerIntent":
            return "cancel my timer"

        if intent_name == "CreateReminderIntent":
            content = self._slot_value(slots, "reminderContent") or "do something"
            time = self._slot_value(slots, "reminderTime") or "later"
            return f"remind me to {content} at {time}"

        if intent_name == "ReadNotificationsIntent":
            return "read my notifications"

        if intent_name == "GetNewsIntent":
            topic = self._slot_value(slots, "topic") or "latest stories"
            return f"get news about {topic}"

        if intent_name == "SetVolumeIntent":
            level = self._slot_value(slots, "level") or "5"
            return f"set volume to {level}"

        if intent_name == "PlayMusicIntent":
            query = self._slot_value(slots, "query") or "some music"
            return f"play {query}"

        if intent_name == "ShoppingListIntent":
            action = self._slot_value(slots, "action") or "check"
            item = self._slot_value(slots, "item") or "my list"
            return f"{action} {item} to my shopping list"

        return self._extract_utterance_from_slots(intent_name, slots)

    def _slot_value(self, slots: dict[str, Any], slot_name: str) -> str:
        """Return a normalized slot value if present."""
        slot = slots.get(slot_name)
        value = getattr(slot, "value", None) if slot is not None else None
        return str(value).strip() if value else ""

    def _extract_utterance_from_slots(self, intent_name: str, slots: dict[str, Any]) -> str:
        """Extract a fallback utterance from slot values for unknown custom intents."""
        slot_values = [getattr(slot, "value", None) for slot in slots.values()]
        normalized_values = [str(value).strip() for value in slot_values if value]
        if normalized_values:
            return " ".join(normalized_values)
        return intent_name

    def _build_apl_video_directive(self, title: str, video_url: str) -> AlexaAplRenderDocumentDirective:
        """Build an APL RenderDocument directive for playing a video on Echo Show."""
        return AlexaAplRenderDocumentDirective(
            token="ev-youtube-video",
            document={
                "type": "APL",
                "version": "1.9",
                "theme": "dark",
                "import": [
                    {"name": "alexa-layouts", "version": "1.6"},
                ],
                "mainTemplate": {
                    "parameters": ["payload"],
                    "items": [
                        {
                            "type": "Container",
                            "width": "100%",
                            "height": "100%",
                            "items": [
                                {
                                    "type": "Video",
                                    "source": video_url,
                                    "width": "100%",
                                    "height": "100%",
                                    "autoplay": True,
                                    "audio": True,
                                    "scale": "best-fit",
                                },
                                {
                                    "type": "Text",
                                    "text": title,
                                    "position": "overlay",
                                    "top": "80%",
                                    "left": "5%",
                                    "fontSize": 24,
                                    "color": "white",
                                    "fontWeight": "bold",
                                },
                            ],
                        }
                    ],
                },
            },
            datasources={
                "payload": {
                    "videoTitle": title,
                    "videoSource": video_url,
                }
            },
        )

    def _build_apl_eve_visuals_directive(self, text: str) -> AlexaAplRenderDocumentDirective:
        """Build an APL RenderDocument directive to display Eve bot visuals on Echo Show."""
        return AlexaAplRenderDocumentDirective(
            token="eve-bot-visuals",
            document={
                "type": "APL",
                "version": "1.9",
                "theme": "dark",
                "import": [
                    {"name": "alexa-layouts", "version": "1.6"},
                ],
                "mainTemplate": {
                    "parameters": ["payload"],
                    "items": [
                        {
                            "type": "Container",
                            "width": "100%",
                            "height": "100%",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "items": [
                                {
                                    "type": "Image",
                                    "source": f"{self._base_url.rstrip('/')}/static/ev_bot_logo.jpg",
                                    "width": "300dp",
                                    "height": "300dp",
                                    "scale": "best-fit",
                                    "align": "center",
                                },
                                {
                                    "type": "Text",
                                    "text": "${payload.responseText}",
                                    "fontSize": "24dp",
                                    "color": "white",
                                    "textAlign": "center",
                                    "width": "90%",
                                    "marginTop": "20dp",
                                }
                            ]
                        }
                    ]
                }
            },
            datasources={
                "payload": {
                    "responseText": text
                }
            }
        )

    def _build_visuals_directive(self, text: str, envelope: AlexaRequestEnvelope | None = None) -> Any:
        """Build APL or HTML Start/HandleMessage directive depending on device capabilities."""
        if envelope:
            context = envelope.context or {}
            system = context.get("System", {})
            device = system.get("device", {})
            supported = device.get("supportedInterfaces", {})
            if "Alexa.Presentation.HTML" in supported:
                from app.models.alexa import (
                    AlexaHtmlHandleMessageDirective,
                    AlexaHtmlStartDirective,
                )
                if envelope.request.type == "LaunchRequest":
                    # Start the HTML5 companion view on the Echo Show screen.
                    return AlexaHtmlStartDirective(
                        request={
                            "uri": f"{self._base_url.rstrip('/')}/?view=echoshow",
                            "method": "GET",
                        }
                    )
                # Update animated character speech & subtitles in real-time.
                return AlexaHtmlHandleMessageDirective(
                    message={
                        "text": text,
                        "expression": "talking",
                    }
                )
        return self._build_apl_eve_visuals_directive(text)

    async def _build_response(
        self,
        text: str,
        should_end_session: bool,
        reprompt_text: str | None = None,
        directives: list | None = None,
    ) -> AlexaResponseEnvelope:
        """Build a valid Alexa response envelope and broadcast to companion app."""
        import datetime
        import logging

        _logger = logging.getLogger(__name__)
        try:
            await broadcast_state_change(
                "alexa_event",
                {
                    "id": f"alexa-{int(time.time() * 1000)}",
                    "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                    "phrase": text,
                    "status": "success",
                    "actionTaken": text,
                },
            )
        except Exception as exc:  # pragma: no cover
            _logger.warning("SSE broadcast failed (non-fatal): %s", exc)

        response = AlexaResponseBody(
            outputSpeech=AlexaPlainTextOutputSpeech(text=text),
            shouldEndSession=should_end_session,
            reprompt=AlexaReprompt(outputSpeech=AlexaPlainTextOutputSpeech(text=reprompt_text))
            if reprompt_text
            else None,
            directives=directives or [],
        )
        return AlexaResponseEnvelope(response=response)

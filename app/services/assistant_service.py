"""Assistant planning service backed by AI and deterministic fallbacks."""

from __future__ import annotations

from app.clients.openai_client import AIClient
from app.models.tooling import AssistantPlan, ToolCall, ToolResult


class AssistantService:
    """Produces assistant plans and final responses."""

    def __init__(self, ai_client: AIClient) -> None:
        """Store AI client dependency."""
        self._ai_client = ai_client

    async def plan_response(self, user_text: str, messages: list[dict], available_tools: list[dict[str, str]]) -> AssistantPlan:
        """Produce a tool plan or direct response for the current user message."""
        planned = await self._ai_client.plan_response(
            user_text=user_text,
            messages=messages,
            available_tools=available_tools,
        )
        if planned is not None:
            return planned
        return self._fallback_plan(user_text)

    async def build_final_response(
        self,
        user_text: str,
        messages: list[dict],
        tool_results: list[ToolResult],
    ) -> str:
        """Build the final assistant response after tool execution."""
        tool_response = await self._ai_client.generate_final_response(
            user_text=user_text,
            messages=messages,
            tool_results=tool_results,
        )
        if tool_response:
            return tool_response
        return self._fallback_tool_response(tool_results)

    def _fallback_plan(self, user_text: str) -> AssistantPlan:
        """Create a deterministic plan when the AI provider cannot plan."""
        text = user_text.lower()

        calendar_words = [
            "calendar", "schedule", "events", "diary", "appointment",
            "plans", "coming up", "busy", "whats on", "what have i got",
        ]
        if any(w in text for w in calendar_words):
            return AssistantPlan(
                mode="tool_call",
                tool_calls=[ToolCall(tool_name="calendar_list_upcoming_events", arguments={"limit": 5})],
            )

        search_words = [
            "search", "look up", "who is", "what is", "where is",
            "when is", "how do", "tell me about", "do you know",
            "explain", "find out",
        ]
        if any(w in text for w in search_words):
            return AssistantPlan(
                mode="tool_call",
                tool_calls=[ToolCall(tool_name="web_search", arguments={"query": user_text, "limit": 3})],
            )

        youtube_words = ["youtube", "video", "watch", "show me", "play"]
        if any(w in text for w in youtube_words):
            clean_query = text
            for phrase in ["show me", "play", "on youtube", "youtube video", "watch", "find"]:
                clean_query = clean_query.replace(phrase, "")
            clean_query = clean_query.strip() or user_text
            return AssistantPlan(
                mode="tool_call",
                tool_calls=[ToolCall(
                    tool_name="youtube_search",
                    arguments={"query": clean_query, "limit": 1, "get_url": "true"},
                )],
            )

        if self._looks_like_home_request(text):
            domain = self._infer_home_domain(text)
            spoken_name = self._infer_device_name(text)
            if self._is_turn_on_action(text):
                return AssistantPlan(
                    mode="tool_call",
                    tool_calls=[
                        ToolCall(
                            tool_name="home_assistant_call_service",
                            arguments={
                                "domain": domain,
                                "service": "turn_on",
                                "spoken_name": spoken_name,
                                "service_data": {},
                            },
                        )
                    ],
                )
            if self._is_turn_off_action(text):
                return AssistantPlan(
                    mode="tool_call",
                    tool_calls=[
                        ToolCall(
                            tool_name="home_assistant_call_service",
                            arguments={
                                "domain": domain,
                                "service": "turn_off",
                                "spoken_name": spoken_name,
                                "service_data": {},
                            },
                        )
                    ],
                )
            return AssistantPlan(
                mode="tool_call",
                tool_calls=[
                    ToolCall(
                        tool_name="home_assistant_get_state",
                        arguments={
                            "spoken_name": spoken_name,
                            "domain_hint": domain,
                        },
                    )
                ],
            )

        return AssistantPlan(
            mode="direct_response",
            response_text=(
                f"I heard: {user_text}. If you need help with"
                " a question, search, calendar, or smart home devices, just let me know."
            ),
        )

    def _looks_like_home_request(self, text: str) -> bool:
        """Determine whether text appears to be a smart-home command or query."""
        keywords = ["light", "lamp", "switch", "fan", "heater", "plug", "device", "tv", "television", "thermostat"]
        return any(keyword in text for keyword in keywords)

    def _infer_home_domain(self, text: str) -> str:
        """Infer the Home Assistant domain from user wording."""
        if any(keyword in text for keyword in ["light", "lamp"]):
            return "light"
        if "fan" in text:
            return "fan"
        if "heater" in text:
            return "climate"
        if any(keyword in text for keyword in ["switch", "plug", "device"]):
            return "switch"
        return "switch"

    def _infer_device_name(self, text: str) -> str:
        """Infer a spoken device name from a smart-home style request."""
        normalized = text
        for phrase in [
            "turn on the ",
            "turn off the ",
            "switch on the ",
            "switch off the ",
            "turn on ",
            "turn off ",
            "switch on ",
            "switch off ",
            "check the ",
            "check ",
            "what is the status of the ",
            "set the ",
            "make the ",
            "i want to ",
            "i need to ",
            "please ",
            "could you ",
            "would you ",
            "can you ",
        ]:
            normalized = normalized.replace(phrase, "")
        return normalized.strip() or "device"

    def _is_turn_on_action(self, text: str) -> bool:
        """Return whether the user requested an activation action."""
        return any(phrase in text for phrase in ["turn on", "switch on", "enable"])

    def _is_turn_off_action(self, text: str) -> bool:
        """Return whether the user requested a deactivation action."""
        return any(phrase in text for phrase in ["turn off", "switch off", "disable"])

    def _fallback_tool_response(self, tool_results: list[ToolResult]) -> str:
        """Create a deterministic response summary from tool results."""
        if not tool_results:
            return "I could not complete that request."

        first = tool_results[0]
        if not first.success:
            return f"I could not complete the tool request: {first.error}"

        if first.tool_name == "web_search":
            results = first.data.get("results", [])
            if results:
                top = results[0]
                title = top.get("title", "")
                snippet = top.get("snippet", "")
                if snippet:
                    return f"I found this about your search: {snippet}"
                return f"I found a result titled '{title}'."
            message = first.data.get("message", "")
            if "not configured" in message.lower():
                return (
                    "I can search the web for you."
                    " Set WEB_SEARCH_PROVIDER=duckduckgo in your .env file"
                    " and restart me, then I can look things up."
                )
            return "I searched but did not find any results for that."

        if first.tool_name == "calendar_list_upcoming_events":
            events = first.data.get("events", [])
            if events:
                event_list = []
                for ev in events:
                    summary = ev.get("summary", "Untitled")
                    start = ev.get("start", "")
                    event_list.append(f"{summary} at {start}" if start else summary)
                if len(event_list) == 1:
                    return f"You have one event: {event_list[0]}."
                return f"You have {len(event_list)} events: " + ". ".join(event_list) + "."
            message = first.data.get("message", "")
            if "not configured" in message.lower():
                return (
                    "I can check your calendar."
                    " Set CALENDAR_PROVIDER=google with your Google Calendar API key"
                    " in .env, then I can look up your events."
                )
            return "You have no upcoming events on your calendar."

        if first.tool_name == "youtube_search":
            results = first.data.get("results", [])
            if results:
                top = results[0]
                title = top.get("title", "Untitled")
                channel = top.get("channel", "")
                duration = top.get("duration", 0)
                minutes = duration // 60 if duration else 0
                time_info = f" ({minutes} minutes)" if minutes else ""
                direct_url = first.data.get("direct_url") or first.data.get("playable_url")
                part = f" I have also prepared a video demonstration on your screen.{'  ' + direct_url if direct_url else ''}"
                return f"I found a video titled '{title}' by {channel}{time_info}.{part}"
            message = first.data.get("message", "")
            if "not enabled" in message.lower():
                return "YouTube integration is not enabled. Set YOUTUBE_ENABLED=true in your .env file to enable video searches."
            return "I could not find any YouTube videos for that."

        if first.tool_name.startswith("home_assistant"):
            message = first.data.get("message", "")
            if "not configured" in message.lower():
                return (
                    "I can control your smart home if you connect Home Assistant."
                    " Set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN in your .env file."
                )
            domain = first.data.get("domain", "")
            service = first.data.get("service", "")
            entity_id = first.data.get("entity_id", "")
            if domain and service:
                return f"I have turned {service.replace('_', ' ')} for your {domain} device."
            if entity_id:
                state = first.data.get("state", "")
                if state:
                    return f"Your {entity_id} is currently {state}."
                return f"I checked your {entity_id} device."
            return f"Smart home action completed: {message}"

        return "Your request was processed."

"""Models used for assistant tool planning and execution."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Represents a requested tool invocation from the assistant layer."""

    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Represents the result of a tool invocation."""

    tool_name: str = Field(..., min_length=1)
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class AssistantPlan(BaseModel):
    """Represents either a direct response or a response requiring tools."""

    mode: Literal["direct_response", "tool_call"]
    response_text: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)

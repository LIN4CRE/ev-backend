"""Pydantic models for Alexa request and response payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AlexaApplication(BaseModel):
    """Alexa application metadata."""

    applicationId: str = Field(..., min_length=1)


class AlexaSessionUser(BaseModel):
    """Alexa session user metadata."""

    userId: str = Field(..., min_length=1)


class AlexaSession(BaseModel):
    """Alexa session envelope details."""

    new: bool
    sessionId: str = Field(..., min_length=1)
    application: AlexaApplication
    user: AlexaSessionUser
    attributes: dict[str, Any] = Field(default_factory=dict)


class AlexaIntentSlot(BaseModel):
    """Alexa intent slot payload."""

    name: str = Field(..., min_length=1)
    value: str | None = None


class AlexaIntent(BaseModel):
    """Alexa intent payload."""

    name: str = Field(..., min_length=1)
    slots: dict[str, AlexaIntentSlot] = Field(default_factory=dict)


class AlexaRequestBody(BaseModel):
    """Alexa request body representing supported request types for this stage."""

    type: Literal["LaunchRequest", "IntentRequest", "SessionEndedRequest"]
    requestId: str = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1)
    locale: str = Field(..., min_length=1)
    intent: AlexaIntent | None = None

    @field_validator("intent")
    @classmethod
    def validate_intent_for_intent_request(cls, value: AlexaIntent | None, info):
        """Ensure intents are only required for IntentRequest payloads."""
        request_type = info.data.get("type")
        if request_type == "IntentRequest" and value is None:
            raise ValueError("intent is required when type is IntentRequest")
        return value


class AlexaRequestEnvelope(BaseModel):
    """Top-level Alexa request envelope."""

    version: str = Field(..., min_length=1)
    session: AlexaSession | None = None
    request: AlexaRequestBody
    context: dict[str, Any] = Field(default_factory=dict)


class AlexaPlainTextOutputSpeech(BaseModel):
    """Alexa plain text speech payload."""

    type: Literal["PlainText"] = "PlainText"
    text: str = Field(..., min_length=1)


class AlexaReprompt(BaseModel):
    """Alexa reprompt payload."""

    outputSpeech: AlexaPlainTextOutputSpeech


class AlexaDirective(BaseModel):
    """Base model for Alexa response directives (APL, VideoApp, etc.)."""

    type: str


class AlexaAplRenderDocumentDirective(AlexaDirective):
    """Directive to render an APL document on screen-enabled devices."""

    type: str = "Alexa.Presentation.APL.RenderDocument"
    token: str = "ev-video-token"
    document: dict[str, Any]
    datasources: dict[str, Any] = Field(default_factory=dict)


class AlexaHtmlStartDirective(AlexaDirective):
    """Directive to start an HTML5 web app on screen-enabled devices using Web API for Games."""

    type: str = "Alexa.Presentation.HTML.Start"
    request: dict[str, Any]
    configuration: dict[str, Any] = Field(default_factory=lambda: {"timeoutInSeconds": 300})


class AlexaHtmlHandleMessageDirective(AlexaDirective):
    """Directive to send a message to a running HTML5 web app on screen-enabled devices."""

    type: str = "Alexa.Presentation.HTML.HandleMessage"
    message: dict[str, Any] = Field(default_factory=dict)


class AlexaResponseBody(BaseModel):
    """Alexa response body."""

    outputSpeech: AlexaPlainTextOutputSpeech
    reprompt: AlexaReprompt | None = None
    shouldEndSession: bool = False
    directives: list[AlexaDirective] = Field(default_factory=list)


class AlexaResponseEnvelope(BaseModel):
    """Top-level Alexa response envelope."""

    version: str = "1.0"
    sessionAttributes: dict[str, Any] = Field(default_factory=dict)
    response: AlexaResponseBody

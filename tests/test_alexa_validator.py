"""Tests for Alexa request validation."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import get_settings
from app.models.alexa import AlexaRequestEnvelope
from app.services.alexa_signature_service import get_alexa_signature_verifier
from app.validators.alexa import SettingsBasedAlexaRequestValidator


def _build_request() -> Request:
    """Build a minimal Starlette request for validator tests."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/alexa/webhook",
        "headers": [],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_validator_rejects_mismatched_skill_id() -> None:
    """Verify the validator rejects a request with the wrong application ID."""
    settings = get_settings()
    original_skill_id = settings.alexa_skill_id
    settings.alexa_skill_id = "amzn1.ask.skill.expected"

    validator = SettingsBasedAlexaRequestValidator(settings, get_alexa_signature_verifier())
    envelope = AlexaRequestEnvelope.model_validate(
        {
            "version": "1.0",
            "session": {
                "new": True,
                "sessionId": "session-validator",
                "application": {"applicationId": "amzn1.ask.skill.wrong"},
                "user": {"userId": "user-validator"},
                "attributes": {},
            },
            "request": {
                "type": "LaunchRequest",
                "requestId": "request-validator",
                "timestamp": "2026-06-27T12:00:00Z",
                "locale": "en-GB",
            },
        }
    )

    with pytest.raises(HTTPException):
        await validator.validate(_build_request(), envelope)

    settings.alexa_skill_id = original_skill_id

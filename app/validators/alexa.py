"""Alexa request validation abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.models.alexa import AlexaRequestEnvelope
from app.services.alexa_signature_service import (
    AlexaSignatureVerifier,
    get_alexa_signature_verifier,
)


class AlexaRequestValidator(ABC):
    """Abstract validator for Alexa webhook requests."""

    @abstractmethod
    async def validate(self, request: Request, envelope: AlexaRequestEnvelope) -> None:
        """Validate an Alexa request and raise if invalid."""


class SettingsBasedAlexaRequestValidator(AlexaRequestValidator):
    """Pragmatic validator using configuration and cryptographic verification boundaries."""

    def __init__(self, settings: Settings, signature_verifier: AlexaSignatureVerifier) -> None:
        """Store settings and signature verifier dependencies."""
        self._settings = settings
        self._signature_verifier = signature_verifier

    async def validate(self, request: Request, envelope: AlexaRequestEnvelope) -> None:
        """Validate skill identity, request freshness, and signature verification when enabled."""
        self._validate_timestamp(envelope.request.timestamp)
        self._validate_skill_id(envelope)

        if envelope.request.type == "IntentRequest" and envelope.request.intent is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="IntentRequest payload must include an intent.",
            )

        if self._settings.require_alexa_signature_headers:
            signature = request.headers.get("Signature")
            cert_chain_url = request.headers.get("SignatureCertChainUrl")
            if not signature or not cert_chain_url:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Alexa signature headers.",
                )
            raw_body = await request.body()
            await self._signature_verifier.verify(signature, cert_chain_url, raw_body)

    def _validate_timestamp(self, timestamp_value: str) -> None:
        """Reject stale requests outside the accepted skew window."""
        try:
            request_time = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Alexa request timestamp.",
            ) from exc

        current_time = datetime.now(UTC)
        allowed_skew = timedelta(seconds=self._settings.alexa_request_tolerance_seconds)
        if abs(current_time - request_time) > allowed_skew:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alexa request timestamp is outside the allowed tolerance.",
            )

    def _validate_skill_id(self, envelope: AlexaRequestEnvelope) -> None:
        """Reject requests for unexpected Alexa skill IDs."""
        if envelope.session and self._settings.alexa_skill_id:
            application_id = envelope.session.application.applicationId
            if application_id != self._settings.alexa_skill_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid Alexa skill application ID.",
                )


def get_alexa_request_validator() -> AlexaRequestValidator:
    """Return the configured Alexa request validator implementation."""
    return SettingsBasedAlexaRequestValidator(get_settings(), get_alexa_signature_verifier())

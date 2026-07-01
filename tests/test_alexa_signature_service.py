"""Tests for Alexa signature verification helpers."""

import pytest
from fastapi import HTTPException

from app.services.alexa_signature_service import AlexaSignatureVerifier


def test_alexa_signature_verifier_rejects_invalid_cert_url_scheme() -> None:
    """Verify non-HTTPS Alexa certificate URLs are rejected."""
    verifier = AlexaSignatureVerifier()
    with pytest.raises(HTTPException):
        verifier._validate_cert_url("http://s3.amazonaws.com/echo.api/echo-api-cert.pem")


def test_alexa_signature_verifier_rejects_invalid_cert_url_host() -> None:
    """Verify invalid Alexa certificate URL hosts are rejected."""
    verifier = AlexaSignatureVerifier()
    with pytest.raises(HTTPException):
        verifier._validate_cert_url("https://example.com/echo.api/echo-api-cert.pem")

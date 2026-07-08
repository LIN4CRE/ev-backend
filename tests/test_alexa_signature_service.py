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


def test_alexa_signature_verifier_rejects_invalid_cert_url_path() -> None:
    """Verify Alexa certificate URLs outside the /echo.api/ path are rejected."""
    verifier = AlexaSignatureVerifier()
    with pytest.raises(HTTPException):
        verifier._validate_cert_url("https://s3.amazonaws.com/not-echo-api/echo-api-cert.pem")


def test_alexa_signature_verifier_rejects_invalid_cert_url_port() -> None:
    """Verify Alexa certificate URLs on a non-standard port are rejected."""
    verifier = AlexaSignatureVerifier()
    with pytest.raises(HTTPException):
        verifier._validate_cert_url("https://s3.amazonaws.com:8443/echo.api/echo-api-cert.pem")


def test_alexa_signature_verifier_accepts_valid_cert_url_with_explicit_port() -> None:
    """Verify Alexa certificate URLs are accepted with an explicit default HTTPS port."""
    verifier = AlexaSignatureVerifier()
    verifier._validate_cert_url("https://s3.amazonaws.com:443/echo.api/echo-api-cert.pem")

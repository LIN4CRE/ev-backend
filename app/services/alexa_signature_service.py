"""Alexa signature and certificate verification boundary."""

from __future__ import annotations

import base64
import time
from urllib.parse import urlparse

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from fastapi import HTTPException, status


class CertificateCache:
    """Thread-safe in-memory cache for Alexa signing certificates.

    Once fetched, a certificate is re-used for its remaining validity period
    (typically 30+ days) instead of being re-downloaded on every request.
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[bytes, float]] = {}

    def get(self, url: str) -> bytes | None:
        entry = self._cache.get(url)
        if entry is None:
            return None
        data, expires_at = entry
        if time.time() > expires_at:
            del self._cache[url]
            return None
        return data

    def set(self, url: str, data: bytes, ttl_seconds: float) -> None:
        self._cache[url] = (data, time.time() + ttl_seconds)


class AlexaSignatureVerifier:
    """Performs certificate and signature verification for Alexa requests."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        """Store network timeout configuration."""
        self._timeout_seconds = timeout_seconds
        self._cert_cache = CertificateCache()

    async def verify(self, signature_b64: str, cert_chain_url: str, raw_body: bytes) -> None:
        """Verify Alexa request signature against the remote signing certificate."""
        if not signature_b64.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Alexa signature.",
            )
        if not cert_chain_url.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Alexa certificate chain URL.",
            )

        self._validate_cert_url(cert_chain_url)
        certificate_pem = await self._download_certificate(cert_chain_url)
        certificate = x509.load_pem_x509_certificate(certificate_pem)
        expires_ttl = (certificate.not_valid_after_utc - certificate.not_valid_before_utc).total_seconds()
        self._cert_cache.set(cert_chain_url, certificate_pem, expires_ttl)
        self._validate_certificate(certificate)

        signature = base64.b64decode(signature_b64)
        public_key = certificate.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Alexa certificate public key type is invalid.",
            )

        try:
            public_key.verify(signature, raw_body, padding.PKCS1v15(), hashes.SHA1())
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Alexa request signature verification failed.",
            ) from exc

    def _validate_cert_url(self, cert_chain_url: str) -> None:
        """Validate Alexa certificate chain URL rules."""
        parsed = urlparse(cert_chain_url)
        if parsed.scheme != "https":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Alexa certificate URL must use HTTPS.",
            )
        if parsed.hostname != "s3.amazonaws.com":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Alexa certificate URL host is invalid.",
            )
        if not parsed.path.startswith("/echo.api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Alexa certificate URL path is invalid.",
            )

    async def _download_certificate(self, cert_chain_url: str) -> bytes:
        """Download the Alexa signing certificate chain.

        Returns a cached copy if available and still valid (typically 30+ day TTL).
        """
        cached = self._cert_cache.get(cert_chain_url)
        if cached is not None:
            return cached
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(cert_chain_url)
            response.raise_for_status()
            return response.content

    def _validate_certificate(self, certificate: x509.Certificate) -> None:
        """Validate certificate subject and expiration boundaries."""
        try:
            common_name = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except IndexError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Alexa certificate is missing a common name.",
            ) from exc

        if common_name != "echo-api.amazon.com":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Alexa certificate common name is invalid.",
            )

        now = datetime_now_utc()
        if certificate.not_valid_before_utc > now or certificate.not_valid_after_utc < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Alexa certificate is expired or not yet valid.",
            )


def datetime_now_utc():
    """Return the current UTC datetime via a helper for easier testing."""
    from datetime import UTC, datetime

    return datetime.now(UTC)


signature_verifier = AlexaSignatureVerifier()


def get_alexa_signature_verifier() -> AlexaSignatureVerifier:
    """Return the shared Alexa signature verifier instance."""
    return signature_verifier

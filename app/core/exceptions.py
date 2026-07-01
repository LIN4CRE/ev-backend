"""Application exception types and handlers."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExternalServiceError(Exception):
    """Raised when an external provider fails in a controlled way."""

    def __init__(self, service_name: str, message: str) -> None:
        """Store service context and an operator-friendly error message."""
        self.service_name = service_name
        self.message = message
        super().__init__(message)


def _is_alexa_webhook(request: Request) -> bool:
    """Return True if the incoming request targets the Alexa webhook route."""
    path = request.url.path if request.url else ""
    return "/alexa/webhook" in path


def _alexa_error_envelope(message: str, should_end_session: bool = True) -> dict:
    """Build a valid Alexa response envelope for an error condition."""
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": message,
            },
            "shouldEndSession": should_end_session,
        },
    }


async def external_service_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert controlled external dependency failures into safe API responses."""
    assert isinstance(exc, ExternalServiceError)
    logger.warning("external_service_error", service=exc.service_name, message=exc.message)
    if _is_alexa_webhook(request):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=_alexa_error_envelope(
                "Sorry, a backend service is unavailable right now. Please try again in a moment."
            ),
        )
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"External service '{exc.service_name}' failed.",
            "message": exc.message,
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic response for unexpected exceptions while logging details."""
    logger.exception("unhandled_exception", error=str(exc))
    if _is_alexa_webhook(request):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=_alexa_error_envelope(
                "Sorry, something went wrong on my end. Please try again."
            ),
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log HTTP exceptions consistently before returning them.

    For Alexa webhook requests, always return HTTP 200 with a valid Alexa response
    envelope. Amazon's Alexa service requires a 200 status with a well-formed
    envelope even when validation fails — anything else triggers
    "There was a problem with the requested skill's response."
    """
    assert isinstance(exc, HTTPException)
    logger.warning(
        "http_exception",
        path=request.url.path if request.url else "",
        status_code=exc.status_code,
        detail=exc.detail,
    )
    if _is_alexa_webhook(request):
        detail_text = str(exc.detail) if exc.detail else "Request could not be processed."
        detail_lower = detail_text.lower()
        if "timestamp" in detail_lower:
            spoken = "Sorry, your request took too long. Please try again."
        elif "skill" in detail_lower or "application" in detail_lower:
            spoken = "Sorry, this skill is not available right now."
        elif "signature" in detail_lower:
            spoken = "Sorry, I could not verify that request."
        else:
            spoken = "Sorry, I could not process that request."
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=_alexa_error_envelope(spoken, should_end_session=True),
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert Pydantic validation errors into safe API responses.

    For Alexa webhook requests, always return HTTP 200 with a valid Alexa response
    envelope. Amazon's Alexa service requires a 200 status with a well-formed
    envelope even when the request body fails validation - anything else triggers
    "There was a problem with the requested skill's response."
    """
    assert isinstance(exc, RequestValidationError)
    errors_summary = "; ".join(
        f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg', '')}"
        for err in exc.errors()
    )
    logger.warning(
        "validation_exception",
        path=request.url.path if request.url else "",
        errors=errors_summary,
    )
    if _is_alexa_webhook(request):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=_alexa_error_envelope(
                "Sorry, I received an unexpected request. Please try again."
            ),
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI application."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ExternalServiceError, external_service_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

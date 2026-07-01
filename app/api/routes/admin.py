"""Admin diagnostics routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.auth import require_admin_access
from app.core.config import get_settings
from app.core.rate_limit import rate_limit_admin_requests
from app.services.audit_service import AuditService, get_audit_service
from app.services.memory_service import ConversationMemory, get_memory_provider
from app.services.tool_service import ToolRegistry, get_tool_registry

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_access), Depends(rate_limit_admin_requests)],
)


@router.get("/memory/sessions")
def list_memory_sessions(
    request: Request,
    memory: ConversationMemory = Depends(get_memory_provider),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict:
    """Return known session IDs and message counts for diagnostics."""
    _ = request
    audit_service.log_admin_event("list_memory_sessions")
    if not hasattr(memory, "list_sessions"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="The configured memory provider does not support session listing.",
        )
    return {"sessions": memory.list_sessions()}


@router.get("/memory/session")
def get_memory_session(
    request: Request,
    session_id: str = Query(..., min_length=1),
    memory: ConversationMemory = Depends(get_memory_provider),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict:
    """Return the full transcript for a single conversation session."""
    _ = request
    audit_service.log_admin_event("get_memory_session", {"session_id": session_id})
    if not hasattr(memory, "get_full_session"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="The configured memory provider does not support session inspection.",
        )
    return {"session_id": session_id, "messages": memory.get_full_session(session_id)}


@router.get("/tools")
def list_tools(
    request: Request,
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict:
    """Return registered assistant tools for diagnostics."""
    _ = request
    audit_service.log_admin_event("list_tools")
    return {"tools": tool_registry.list_tool_specs()}


@router.get("/settings")
def get_public_settings() -> dict:
    """Return non-secret settings so mobile/desktop consumers can self-configure."""
    s = get_settings()
    return {
        "environment": s.environment,
        "cors_origins": s.cors_origins,
        "ai_provider": s.ai_provider,
        "gemini_model": s.gemini_model,
        "openai_model": s.openai_model,
        "ollama_model": s.ollama_model,
        "use_vertex_ai": s.use_vertex_ai,
        "gcp_project_id": s.gcp_project_id,
        "gcp_location": s.gcp_location,
        "home_assistant_url": s.home_assistant_url,
        "calendar_provider": s.calendar_provider,
        "google_calendar_id": s.google_calendar_id,
        "web_search_provider": s.web_search_provider,
        "youtube_enabled": s.youtube_enabled,
        "alexa_skill_id": s.alexa_skill_id,
        "memory_backend": s.memory_backend,
        "api_v1_prefix": s.api_v1_prefix,
    }

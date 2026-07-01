"""Administrative audit logging helpers."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Writes structured audit events for sensitive admin actions."""

    def log_admin_event(self, action: str, metadata: dict | None = None) -> None:
        """Emit a structured admin audit log entry."""
        logger.info("admin_event", action=action, metadata=metadata or {})


audit_service = AuditService()


def get_audit_service() -> AuditService:
    """Return the shared audit service instance."""
    return audit_service

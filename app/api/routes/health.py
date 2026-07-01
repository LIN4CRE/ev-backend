"""Health and diagnostics routes."""

from fastapi import APIRouter, Depends

from app.core.auth import require_admin_access
from app.core.config import Settings, get_settings
from app.services.system_service import SystemService

router = APIRouter(tags=["system"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    """Return a public health response."""
    service = SystemService(settings)
    return service.get_health()


@router.get("/admin/config", dependencies=[Depends(require_admin_access)])
def admin_config(settings: Settings = Depends(get_settings)) -> dict:
    """Return a redacted configuration summary for administrators."""
    service = SystemService(settings)
    return service.get_safe_config_summary()

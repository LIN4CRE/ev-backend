"""Compatibility wrappers for protected endpoints."""

from app.core.auth import require_admin_access

__all__ = ["require_admin_access"]

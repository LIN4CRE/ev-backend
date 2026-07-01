"""Development-only local Alexa setup automation service."""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]


class DevSetupService:
    """Runs safe development-only Alexa local setup automation."""

    def __init__(self, settings: Settings) -> None:
        """Store settings used to gate local automation."""
        self._settings = settings

    def prepare_alexa_local_dev(self) -> str:
        """Run the Alexa local development preparation flow if enabled."""
        if self._settings.environment not in {"development", "test"}:
            return "Local Alexa setup commands are only available in development."

        try:
            subprocess.run(["python", "scripts/alexa_local_dev.py"], cwd=ROOT, check=True)
        except Exception:
            return "I could not finish local Alexa setup automatically."

        return "Alexa local setup is ready."

"""Shared path constants for local automation scripts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_JSON_PATH = ROOT / "alexa" / "skill-package" / "skill.json"
MODEL_PATH = ROOT / "alexa" / "skill-package" / "interactionModels" / "custom" / "en-GB.json"
HELPER_ENV_PATH = ROOT / ".env.alexa.local"

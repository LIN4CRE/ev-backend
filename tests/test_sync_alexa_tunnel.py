"""Tests for Alexa tunnel synchronization automation."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "sync_alexa_tunnel.py"
SKILL_JSON_PATH = ROOT / "alexa" / "skill-package" / "skill.json"
HELPER_ENV_PATH = ROOT / ".env.alexa.local"


def test_sync_alexa_tunnel_updates_manifest_and_helper_env() -> None:
    """Verify Alexa tunnel sync updates both manifest and local helper env file."""
    original_skill_content = SKILL_JSON_PATH.read_text(encoding="utf-8")
    original_helper_content = HELPER_ENV_PATH.read_text(encoding="utf-8") if HELPER_ENV_PATH.exists() else None
    try:
        env = os.environ.copy()
        env["ALEXA_PUBLIC_ENDPOINT"] = "https://example.sync.test/api/v1/alexa/webhook"
        subprocess.run(["python", str(SCRIPT_PATH)], check=True, cwd=ROOT, env=env)

        with SKILL_JSON_PATH.open("r", encoding="utf-8") as file_handle:
            skill = json.load(file_handle)
        endpoint = skill["manifest"]["apis"]["custom"]["endpoint"]["uri"]
        assert endpoint == "https://example.sync.test/api/v1/alexa/webhook"

        helper_content = HELPER_ENV_PATH.read_text(encoding="utf-8")
        assert "ALEXA_PUBLIC_ENDPOINT=https://example.sync.test/api/v1/alexa/webhook" in helper_content
    finally:
        SKILL_JSON_PATH.write_text(original_skill_content, encoding="utf-8")
        if original_helper_content is None:
            if HELPER_ENV_PATH.exists():
                HELPER_ENV_PATH.unlink()
        else:
            HELPER_ENV_PATH.write_text(original_helper_content, encoding="utf-8")

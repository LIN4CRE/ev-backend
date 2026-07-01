"""Tests for Alexa manifest endpoint automation."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "update_alexa_endpoint.py"
SKILL_JSON_PATH = ROOT / "alexa" / "skill-package" / "skill.json"


def test_alexa_manifest_endpoint_update_script_changes_endpoint(tmp_path) -> None:
    """Verify the endpoint update script rewrites the Alexa manifest URI."""
    original_content = SKILL_JSON_PATH.read_text(encoding="utf-8")
    try:
        env = os.environ.copy()
        env["ALEXA_PUBLIC_ENDPOINT"] = "https://example.test/api/v1/alexa/webhook"
        subprocess.run(["python", str(SCRIPT_PATH)], check=True, cwd=ROOT, env=env)

        with SKILL_JSON_PATH.open("r", encoding="utf-8") as file_handle:
            skill = json.load(file_handle)
        endpoint = skill["manifest"]["apis"]["custom"]["endpoint"]["uri"]
        assert endpoint == "https://example.test/api/v1/alexa/webhook"
    finally:
        SKILL_JSON_PATH.write_text(original_content, encoding="utf-8")

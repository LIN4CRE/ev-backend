"""Tests for local Alexa development workflow automation."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "alexa_local_dev.py"


def test_alexa_local_dev_script_runs_with_manual_endpoint_env() -> None:
    """Verify local Alexa prep script succeeds when a public endpoint is supplied."""
    env = {
        "PATH": subprocess.run(["python", "-c", "import os; print(os.environ['PATH'])"], capture_output=True, text=True).stdout.strip(),
        "ALEXA_PUBLIC_ENDPOINT": "https://example.local.dev/api/v1/alexa/webhook",
        "ALEXA_LOCAL_PORT": "8000",
    }
    result = subprocess.run(["python", str(SCRIPT_PATH)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Alexa setup summary" in result.stdout

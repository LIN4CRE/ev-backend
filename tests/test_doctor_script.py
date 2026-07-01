"""Tests for local environment doctor diagnostics."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "doctor.py"


def test_doctor_script_runs_and_reports_repo_root() -> None:
    """Verify the doctor script runs and prints basic diagnostics."""
    result = subprocess.run(["python", str(SCRIPT_PATH)], cwd=ROOT, capture_output=True, text=True)
    assert "Repo root" in result.stdout

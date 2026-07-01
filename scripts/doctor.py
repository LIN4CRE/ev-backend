"""Environment doctor for local Alexa development readiness."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = [
    ROOT / "alexa" / "skill-package" / "skill.json",
    ROOT / "alexa" / "skill-package" / "interactionModels" / "custom" / "en-GB.json",
    ROOT / "docker-compose.yml",
    ROOT / "requirements.txt",
]


def _check(condition: bool, label: str, ok: str, fail: str) -> tuple[bool, str]:
    """Format a doctor check result."""
    return condition, f"[{ 'OK' if condition else 'FAIL' }] {label}: {ok if condition else fail}"


def main() -> None:
    """Run local environment checks and print actionable diagnostics."""
    results: list[tuple[bool, str]] = []

    results.append(_check(ROOT.exists(), "Repo root", str(ROOT), "Repository root not found"))
    results.append(
        _check(
            sys.executable != "",
            "Python executable",
            sys.executable,
            "Python executable not available",
        )
    )
    results.append(
        _check(shutil.which("docker") is not None, "Docker CLI", shutil.which("docker") or "", "Docker not found in PATH")
    )
    results.append(
        _check(
            shutil.which("ngrok") is not None,
            "ngrok CLI",
            shutil.which("ngrok") or "",
            "ngrok not found in PATH (optional, but recommended)",
        )
    )

    for required_path in REQUIRED_PATHS:
        results.append(
            _check(
                required_path.exists(),
                f"Required path {required_path.relative_to(ROOT)}",
                "present",
                "missing",
            )
        )

    endpoint = os.getenv("ALEXA_PUBLIC_ENDPOINT", "").strip()
    results.append(
        _check(
            endpoint == "" or endpoint.startswith("https://"),
            "ALEXA_PUBLIC_ENDPOINT",
            endpoint or "not set",
            "must be empty or start with https://",
        )
    )

    is_windows = os.name == "nt"
    results.append(
        _check(
            True,
            "Operating system",
            "Windows" if is_windows else os.name,
            "Unknown OS",
        )
    )

    for _, line in results:
        print(line)

    if not all(ok for ok, _ in results if "ngrok CLI" not in _):
        raise SystemExit(1)

    print("Environment doctor checks completed.")


if __name__ == "__main__":
    main()

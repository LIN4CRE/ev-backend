"""Prepare local Alexa development workflow with tunnel sync and readiness output."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

from common_paths import ROOT

NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
DEFAULT_PORT = os.getenv("ALEXA_LOCAL_PORT", "8000")
DEFAULT_WEBHOOK_PATH = "/api/v1/alexa/webhook"


def _run_python_script(script_name: str, env: dict[str, str] | None = None) -> None:
    """Run a repository Python helper script."""
    command = [sys.executable, f"scripts/{script_name}"]
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def _detect_ngrok_https_url() -> str | None:
    """Return the first detected HTTPS ngrok public URL if available."""
    try:
        with urlopen(NGROK_API_URL, timeout=2) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    for tunnel in payload.get("tunnels", []):
        public_url = str(tunnel.get("public_url") or "").strip()
        if public_url.startswith("https://"):
            return public_url
    return None


def _start_ngrok_if_possible(port: str) -> bool:
    """Attempt to start ngrok in the background if it is installed locally."""
    if _detect_ngrok_https_url():
        return True

    ngrok_path = shutil.which("ngrok")
    if not ngrok_path:
        return False

    subprocess.Popen(  # noqa: S603
        [ngrok_path, "http", port],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(10):
        time.sleep(1)
        if _detect_ngrok_https_url():
            return True
    return False


def main() -> None:
    """Run the Alexa local-development preparation flow."""
    port = DEFAULT_PORT
    ngrok_ready = _start_ngrok_if_possible(port)
    detected_url = _detect_ngrok_https_url()

    env = os.environ.copy()
    if detected_url:
        env["ALEXA_PUBLIC_ENDPOINT"] = f"{detected_url}{DEFAULT_WEBHOOK_PATH}"

    _run_python_script("generate_alexa_skill_package.py")
    if env.get("ALEXA_PUBLIC_ENDPOINT"):
        _run_python_script("sync_alexa_tunnel.py", env=env)
    else:
        _run_python_script("update_alexa_endpoint.py", env=env)
    _run_python_script("validate_alexa_skill_package.py")
    _run_python_script("print_alexa_ready_summary.py")

    print(f"Python executable: {sys.executable}")
    print(f"Repo root: {ROOT}")
    if ngrok_ready:
        print("ngrok tunnel detected and synchronized.")
    else:
        print("No ngrok tunnel detected or started automatically. Provide ALEXA_PUBLIC_ENDPOINT if needed.")


if __name__ == "__main__":
    main()

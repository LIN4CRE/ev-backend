"""Synchronize a public tunnel URL into Alexa skill and local helper files."""

from __future__ import annotations

import json
import os
from urllib.request import urlopen

from common_paths import HELPER_ENV_PATH, SKILL_JSON_PATH

TUNNEL_ENV_KEY = "ALEXA_PUBLIC_ENDPOINT"
NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
DEFAULT_WEBHOOK_PATH = "/api/v1/alexa/webhook"


def _detect_public_base_url() -> str | None:
    """Detect a public HTTPS base URL from a local ngrok agent if available."""
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


def _resolve_endpoint() -> str:
    """Resolve the public Alexa webhook endpoint from env or local tunnel detection."""
    configured = os.getenv(TUNNEL_ENV_KEY, "").strip()
    if configured:
        return configured

    detected_base = _detect_public_base_url()
    if detected_base:
        return f"{detected_base}{DEFAULT_WEBHOOK_PATH}"

    raise ValueError(
        "Could not determine Alexa public endpoint. Set ALEXA_PUBLIC_ENDPOINT or run a local ngrok tunnel."
    )


def _update_skill_manifest(endpoint: str) -> None:
    """Write the resolved endpoint into the Alexa skill manifest."""
    with SKILL_JSON_PATH.open("r", encoding="utf-8") as file_handle:
        skill = json.load(file_handle)

    skill["manifest"]["apis"]["custom"]["endpoint"]["uri"] = endpoint

    with SKILL_JSON_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(skill, file_handle, indent=2)
        file_handle.write("\n")


def _update_helper_env(endpoint: str) -> None:
    """Write a helper env file for local Alexa workflow reuse."""
    HELPER_ENV_PATH.write_text(f"ALEXA_PUBLIC_ENDPOINT={endpoint}\n", encoding="utf-8")


def main() -> None:
    """Resolve, persist, and display Alexa tunnel endpoint information."""
    endpoint = _resolve_endpoint()
    if not endpoint.startswith("https://"):
        raise ValueError("Resolved Alexa endpoint must use HTTPS.")

    _update_skill_manifest(endpoint)
    _update_helper_env(endpoint)

    print("Alexa tunnel sync complete.")
    print(f"Resolved endpoint: {endpoint}")
    print(f"Updated skill manifest: {SKILL_JSON_PATH}")
    print(f"Updated helper env file: {HELPER_ENV_PATH}")


if __name__ == "__main__":
    main()

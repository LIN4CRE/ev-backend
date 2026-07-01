"""Validate the Alexa skill package structure and core conventions."""

from __future__ import annotations

import json
from pathlib import Path

from common_paths import MODEL_PATH, SKILL_JSON_PATH


def _load_json(path: Path) -> dict:
    """Load JSON content from a file path."""
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def main() -> None:
    """Validate that the Alexa skill package contains the expected structures."""
    skill = _load_json(SKILL_JSON_PATH)
    model = _load_json(MODEL_PATH)

    manifest = skill.get("manifest", {})
    custom_api = manifest.get("apis", {}).get("custom", {})
    endpoint_uri = custom_api.get("endpoint", {}).get("uri", "")
    if not endpoint_uri.startswith("https://"):
        raise ValueError("Alexa custom skill endpoint must use HTTPS.")

    language_model = model.get("interactionModel", {}).get("languageModel", {})
    invocation_name = language_model.get("invocationName", "")
    if not invocation_name or invocation_name != invocation_name.lower():
        raise ValueError("Alexa invocation name must be present and lowercase.")

    intent_names = {intent.get("name") for intent in language_model.get("intents", [])}
    required_intents = {
        "AskEvIntent",
        "ControlHomeIntent",
        "CalendarQueryIntent",
        "AMAZON.HelpIntent",
        "AMAZON.StopIntent",
    }
    missing = required_intents - intent_names
    if missing:
        raise ValueError(f"Missing required intents: {sorted(missing)}")

    print("Alexa skill package validation passed.")


if __name__ == "__main__":
    main()

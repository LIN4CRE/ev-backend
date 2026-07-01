"""Tests for the Alexa skill package artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_JSON_PATH = ROOT / "alexa" / "skill-package" / "skill.json"
MODEL_PATH = ROOT / "alexa" / "skill-package" / "interactionModels" / "custom" / "en-GB.json"


def test_alexa_skill_package_files_are_valid_json() -> None:
    """Verify the Alexa skill package files parse as valid JSON."""
    with SKILL_JSON_PATH.open("r", encoding="utf-8") as file_handle:
        skill = json.load(file_handle)
    with MODEL_PATH.open("r", encoding="utf-8") as file_handle:
        model = json.load(file_handle)

    assert "manifest" in skill
    assert "interactionModel" in model


def test_alexa_skill_package_contains_expected_intents() -> None:
    """Verify the interaction model contains core intents required by the backend."""
    with MODEL_PATH.open("r", encoding="utf-8") as file_handle:
        model = json.load(file_handle)

    intents = model["interactionModel"]["languageModel"]["intents"]
    intent_names = {intent["name"] for intent in intents}
    assert "AskEvIntent" in intent_names
    assert "ControlHomeIntent" in intent_names
    assert "CalendarQueryIntent" in intent_names
    assert "AMAZON.HelpIntent" in intent_names
    assert "AMAZON.StopIntent" in intent_names

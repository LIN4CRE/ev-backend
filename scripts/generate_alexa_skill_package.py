"""Generate or update the Alexa skill package from project defaults."""

from __future__ import annotations

import json

from common_paths import MODEL_PATH, SKILL_JSON_PATH


def main() -> None:
    """Verify skill package files exist and are valid JSON."""
    for path in [SKILL_JSON_PATH, MODEL_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"Required Alexa skill package file is missing: {path}")
        with path.open("r", encoding="utf-8") as file_handle:
            json.load(file_handle)
    print("Alexa skill package files are present and valid JSON.")


if __name__ == "__main__":
    main()

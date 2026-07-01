"""Update the Alexa skill manifest endpoint URI automatically."""

from __future__ import annotations

import json
import os

from common_paths import SKILL_JSON_PATH

DEFAULT_ENDPOINT_ENV = "ALEXA_PUBLIC_ENDPOINT"


def main() -> None:
    """Inject the configured public Alexa webhook endpoint into the skill manifest."""
    endpoint = os.getenv(DEFAULT_ENDPOINT_ENV, "").strip()
    if not endpoint:
        print(f"No {DEFAULT_ENDPOINT_ENV} provided; leaving Alexa skill endpoint unchanged.")
        return
    if not endpoint.startswith("https://"):
        raise ValueError("ALEXA_PUBLIC_ENDPOINT must start with https://")

    with SKILL_JSON_PATH.open("r", encoding="utf-8") as file_handle:
        skill = json.load(file_handle)

    skill["manifest"]["apis"]["custom"]["endpoint"]["uri"] = endpoint

    with SKILL_JSON_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(skill, file_handle, indent=2)
        file_handle.write("\n")

    print(f"Updated Alexa skill endpoint to: {endpoint}")


if __name__ == "__main__":
    main()

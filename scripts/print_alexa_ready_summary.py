"""Print a concise Alexa local-setup summary after tunnel sync."""

from __future__ import annotations

import json

from common_paths import MODEL_PATH, SKILL_JSON_PATH


def main() -> None:
    """Display the Alexa endpoint and next setup steps."""
    with SKILL_JSON_PATH.open("r", encoding="utf-8") as file_handle:
        skill = json.load(file_handle)

    endpoint = skill["manifest"]["apis"]["custom"]["endpoint"]["uri"]
    print("Alexa setup summary")
    print("-------------------")
    print(f"Skill endpoint: {endpoint}")
    print(f"Interaction model: {MODEL_PATH}")
    print("Import or copy the interaction model above into the Alexa Developer Console.")
    print("Build the skill in the Alexa Developer Console and test against the endpoint above.")


if __name__ == "__main__":
    main()

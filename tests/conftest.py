"""Pytest configuration and environment initialization."""

import os

# Set ENVIRONMENT to test before any other imports or settings are loaded
os.environ["ENVIRONMENT"] = "test"
os.environ["REQUIRE_ALEXA_SIGNATURE_HEADERS"] = "false"
os.environ["AI_PROVIDER"] = "stub"



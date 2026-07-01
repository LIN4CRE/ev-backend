"""Persistent storage for conversation memory."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock


class JsonFileConversationStore:
    """Thread-safe JSON-file-backed conversation store.

    This storage mechanism is intentionally simple and suitable for local
    development or low-throughput deployments. It preserves the conversation
    memory contract while providing persistence across restarts.
    """

    def __init__(self, file_path: str) -> None:
        """Initialize the storage file and synchronization primitives."""
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self._path.exists():
            self._write_data({})

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Persist a single message for a session."""
        if not session_id.strip():
            raise ValueError("session_id must not be empty")
        if not role.strip():
            raise ValueError("role must not be empty")
        if not content.strip():
            raise ValueError("content must not be empty")

        with self._lock:
            data = self._read_data()
            data.setdefault(session_id, []).append({"role": role, "content": content})
            self._write_data(data)

    def get_messages(self, session_id: str) -> list[dict]:
        """Return a copy of stored messages for a session."""
        if not session_id.strip():
            raise ValueError("session_id must not be empty")
        with self._lock:
            data = self._read_data()
            return list(data.get(session_id, []))

    def list_sessions(self) -> dict[str, int]:
        """Return all session IDs with message counts."""
        with self._lock:
            data = self._read_data()
            return {session_id: len(messages) for session_id, messages in data.items()}

    def get_full_session(self, session_id: str) -> list[dict]:
        """Return the full stored transcript for a session."""
        return self.get_messages(session_id)

    def _read_data(self) -> dict[str, list[dict]]:
        """Read JSON data from disk."""
        with self._path.open("r", encoding="utf-8") as file_handle:
            loaded = json.load(file_handle)
            if not isinstance(loaded, dict):
                raise ValueError("Conversation storage file must contain a JSON object")
            return loaded

    def _write_data(self, data: dict[str, list[dict]]) -> None:
        """Write JSON data to disk atomically enough for this stage."""
        with self._path.open("w", encoding="utf-8") as file_handle:
            json.dump(data, file_handle, indent=2)

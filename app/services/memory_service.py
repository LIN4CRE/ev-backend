"""Conversation memory abstractions and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Lock

from app.core.config import get_settings
from app.services.persistence_service import JsonFileConversationStore
from app.services.sqlite_persistence_service import SQLiteConversationStore


class ConversationMemory(ABC):
    """Abstract interface for conversation memory providers."""

    @abstractmethod
    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Persist a single message for the provided session."""

    @abstractmethod
    def get_messages(self, session_id: str) -> list[dict]:
        """Return all messages stored for the provided session."""


class InMemoryConversationMemory(ConversationMemory):
    """Thread-safe in-memory conversation storage for early-stage development."""

    def __init__(self) -> None:
        """Initialize backing storage and synchronization primitives."""
        self._store: dict[str, list[dict]] = {}
        self._lock = Lock()

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Store a message for a session after validating required values."""
        if not session_id.strip():
            raise ValueError("session_id must not be empty")
        if not role.strip():
            raise ValueError("role must not be empty")
        if not content.strip():
            raise ValueError("content must not be empty")

        with self._lock:
            self._store.setdefault(session_id, []).append({"role": role, "content": content})

    def get_messages(self, session_id: str) -> list[dict]:
        """Return a copy of stored messages for a session."""
        if not session_id.strip():
            raise ValueError("session_id must not be empty")

        with self._lock:
            return list(self._store.get(session_id, []))

    def list_sessions(self) -> dict[str, int]:
        """Return all session IDs with message counts."""
        with self._lock:
            return {session_id: len(messages) for session_id, messages in self._store.items()}

    def get_full_session(self, session_id: str) -> list[dict]:
        """Return the full stored transcript for a session."""
        return self.get_messages(session_id)


class PersistentConversationMemory(ConversationMemory):
    """Conversation memory implementation backed by JSON-file persistence."""

    def __init__(self, file_path: str) -> None:
        """Initialize the persistent storage backend."""
        self._store = JsonFileConversationStore(file_path)

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Persist a message for a session."""
        self._store.append_message(session_id, role, content)

    def get_messages(self, session_id: str) -> list[dict]:
        """Return persisted messages for a session."""
        return self._store.get_messages(session_id)

    def list_sessions(self) -> dict[str, int]:
        """Return all session IDs with message counts."""
        return self._store.list_sessions()

    def get_full_session(self, session_id: str) -> list[dict]:
        """Return the full stored transcript for a session."""
        return self._store.get_full_session(session_id)


class SQLiteConversationMemory(ConversationMemory):
    """Conversation memory implementation backed by SQLite persistence."""

    def __init__(self, database_path: str) -> None:
        """Initialize the SQLite storage backend."""
        self._store = SQLiteConversationStore(database_path)

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Persist a message for a session."""
        self._store.append_message(session_id, role, content)

    def get_messages(self, session_id: str) -> list[dict]:
        """Return persisted messages for a session."""
        return self._store.get_messages(session_id)

    def list_sessions(self) -> dict[str, int]:
        """Return all session IDs with message counts."""
        return self._store.list_sessions()

    def get_full_session(self, session_id: str) -> list[dict]:
        """Return the full stored transcript for a session."""
        return self._store.get_full_session(session_id)


memory_provider: ConversationMemory | None = None


def get_memory_provider() -> ConversationMemory:
    """Return the configured conversation memory provider instance."""
    global memory_provider
    if memory_provider is None:
        settings = get_settings()
        if settings.environment == "test":
            memory_provider = InMemoryConversationMemory()
        elif settings.memory_backend == "sqlite":
            memory_provider = SQLiteConversationMemory(settings.memory_sqlite_path)
        elif settings.memory_backend == "file":
            memory_provider = PersistentConversationMemory(settings.memory_file_path)
        else:
            memory_provider = InMemoryConversationMemory()
    return memory_provider


def close_memory_provider() -> None:
    """Close the memory provider, releasing any underlying resources."""
    global memory_provider
    if memory_provider is not None and hasattr(memory_provider, '_store'):
        store = getattr(memory_provider, '_store', None)
        if store is not None and hasattr(store, 'close'):
            store.close()
    memory_provider = None

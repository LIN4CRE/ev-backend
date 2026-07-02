"""SQLite-backed persistent storage for conversation memory."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from sqlite3 import Connection
from threading import RLock

DEFAULT_MAX_MESSAGES_PER_SESSION = 100


class SQLiteConversationStore:
    """Thread-safe SQLite-backed conversation store with connection reuse."""

    def __init__(self, database_path: str, max_messages: int = DEFAULT_MAX_MESSAGES_PER_SESSION) -> None:
        """Initialize the database file and schema."""
        self._database_path = database_path
        self._max_messages = max_messages
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection: Connection | None = None
        self._initialize_schema()

    def close(self) -> None:
        """Close the SQLite connection."""
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def _get_connection(self) -> Connection:
        """Return the shared connection, creating it if needed."""
        if self._connection is None:
            self._connection = sqlite3.connect(self._database_path, check_same_thread=False)
        return self._connection

    def _enforce_message_limit(self, session_id: str) -> None:
        """Remove oldest messages beyond the per-session limit."""
        with self._lock:
            conn = self._get_connection()
            count = conn.execute(
                "SELECT COUNT(*) FROM conversation_messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
            if count > self._max_messages:
                excess = count - self._max_messages
                conn.execute(
                    """DELETE FROM conversation_messages WHERE id IN (
                        SELECT id FROM conversation_messages WHERE session_id = ?
                        ORDER BY id ASC LIMIT ?
                    )""",
                    (session_id, excess),
                )
                conn.commit()

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Persist a message row to SQLite."""
        if not session_id.strip():
            raise ValueError("session_id must not be empty")
        if not role.strip():
            raise ValueError("role must not be empty")
        if not content.strip():
            raise ValueError("content must not be empty")

        with self._lock:
            self._get_connection().execute(
                "INSERT INTO conversation_messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            self._get_connection().commit()
            self._enforce_message_limit(session_id)

    def get_messages(self, session_id: str) -> list[dict]:
        """Return all messages for a session in insertion order."""
        if not session_id.strip():
            raise ValueError("session_id must not be empty")

        with self._lock:
            cursor = self._get_connection().execute(
                "SELECT role, content FROM conversation_messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            )
            return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

    def list_sessions(self) -> dict[str, int]:
        """Return all session IDs with message counts."""
        with self._lock:
            cursor = self._get_connection().execute(
                "SELECT session_id, COUNT(*) FROM conversation_messages GROUP BY session_id ORDER BY session_id ASC"
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_full_session(self, session_id: str) -> list[dict]:
        """Return the full stored transcript for a session."""
        return self.get_messages(session_id)

    def _initialize_schema(self) -> None:
        """Create required tables if they do not already exist."""
        with self._lock:
            conn = self._get_connection()
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON conversation_messages(session_id)"
            )
            conn.commit()

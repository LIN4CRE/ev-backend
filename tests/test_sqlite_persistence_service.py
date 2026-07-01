"""Tests for SQLite-backed conversation storage."""

from app.services.sqlite_persistence_service import SQLiteConversationStore


def test_sqlite_conversation_store_persists_messages(tmp_path) -> None:
    """Verify SQLite persistence stores and returns session messages."""
    store = SQLiteConversationStore(str(tmp_path / "conversations.db"))
    store.append_message("session-sqlite", "user", "hello")
    store.append_message("session-sqlite", "assistant", "hi")

    assert store.get_messages("session-sqlite") == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert store.list_sessions()["session-sqlite"] == 2

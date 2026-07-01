"""Tests for persistent conversation storage."""

from app.services.persistence_service import JsonFileConversationStore


def test_json_file_conversation_store_persists_messages(tmp_path) -> None:
    """Verify messages are persisted and can be read back from disk."""
    store = JsonFileConversationStore(str(tmp_path / "conversations.json"))
    store.append_message("session-1", "user", "hello")
    store.append_message("session-1", "assistant", "hi")

    assert store.get_messages("session-1") == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert store.list_sessions()["session-1"] == 2

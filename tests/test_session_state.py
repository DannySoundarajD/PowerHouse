"""
Unit tests for SessionState.
"""

import pytest
import tempfile
from pathlib import Path

from src.utils.session_state import SessionState


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


def test_create_session(temp_db):
    """Test session creation."""
    state = SessionState(db_path=temp_db)
    
    session_id = state.create_session(router_model="qwen3.5:2b")
    
    assert session_id is not None
    assert state.session_exists(session_id)
    
    state.close()


def test_add_message(temp_db):
    """Test adding messages to session."""
    state = SessionState(db_path=temp_db)
    
    session_id = state.create_session()
    
    # Add user message
    msg_id_1 = state.add_message(
        session_id=session_id,
        role="user",
        content="Hello, how are you?",
        model_used="qwen3.5:2b",
    )
    
    # Add assistant message
    msg_id_2 = state.add_message(
        session_id=session_id,
        role="assistant",
        content="I'm doing well, thank you!",
        model_used="qwen3.5:2b",
    )
    
    assert msg_id_1 > 0
    assert msg_id_2 > msg_id_1
    
    # Retrieve messages
    messages = state.get_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    
    state.close()


def test_context_window(temp_db):
    """Test context window retrieval."""
    state = SessionState(db_path=temp_db)
    
    session_id = state.create_session()
    
    # Add 10 messages
    for i in range(10):
        role = "user" if i % 2 == 0 else "assistant"
        state.add_message(
            session_id=session_id,
            role=role,
            content=f"Message {i}",
        )
    
    # Get context window (should preserve first 3 and last 6)
    context = state.get_context_window(session_id, protect_first=3, protect_last=6)
    
    # For 10 messages with protect_first=3, protect_last=6:
    # Total needed: 3 + 6 = 9, have 10, so should return all 10
    assert len(context) == 10
    
    state.close()


def test_fts_search(temp_db):
    """Test full-text search."""
    state = SessionState(db_path=temp_db)
    
    session_id = state.create_session()
    
    # Add messages with specific content
    state.add_message(session_id, "user", "How do I calculate pressure drop?")
    state.add_message(session_id, "assistant", "Pressure drop can be calculated using...")
    state.add_message(session_id, "user", "What about temperature?")
    state.add_message(session_id, "assistant", "Temperature affects pressure...")
    
    # Search for "pressure"
    results = state.search_messages(session_id, "pressure", top_k=5)
    
    # Should find 2 messages with "pressure"
    assert len(results) >= 2
    assert any("pressure" in r["content"].lower() for r in results)
    
    state.close()


def test_session_stats(temp_db):
    """Test session statistics."""
    state = SessionState(db_path=temp_db)
    
    session_id = state.create_session(router_model="qwen3.5:2b")
    
    # Add some messages
    state.add_message(session_id, "user", "Hello")
    state.add_message(session_id, "assistant", "Hi there!")
    state.add_message(session_id, "user", "How are you?")
    
    stats = state.get_session_stats(session_id)
    
    assert stats["message_count"] == 3
    assert stats["user_messages"] == 2
    assert stats["assistant_messages"] == 1
    assert stats["router_model"] == "qwen3.5:2b"
    
    state.close()


def test_list_sessions(temp_db):
    """Test listing sessions."""
    state = SessionState(db_path=temp_db)
    
    # Create multiple sessions
    session_ids = []
    for i in range(3):
        sid = state.create_session(router_model=f"model-{i}")
        state.add_message(sid, "user", f"Message in session {i}")
        session_ids.append(sid)
    
    # List sessions
    sessions = state.list_sessions(limit=10)
    
    assert len(sessions) == 3
    assert all(s["session_id"] in session_ids for s in sessions)
    
    state.close()

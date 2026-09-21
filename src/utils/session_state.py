"""
SQLite-backed session state management for Sentinel AI Workbench.
Follows Sentinel's sentinel_state.py architecture with WAL mode and FTS5 search.
"""

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import DB_PATH, DB_WAL_MODE, PROTECT_FIRST_N, PROTECT_LAST_N
from .logger import get_logger

logger = get_logger(__name__)


class SessionState:
    """
    SQLite-backed session state with FTS5 full-text search.
    Stores conversation history, model usage, and metadata.
    """
    
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize session state manager."""
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # SQLite connection (check_same_thread=False for multi-threaded access)
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode
        )
        
        # Enable WAL mode for concurrent readers + one writer
        if DB_WAL_MODE:
            self.conn.execute("PRAGMA journal_mode=WAL")
        
        # Other pragmas for performance
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        self.conn.execute("PRAGMA temp_store=MEMORY")
        
        self._init_schema()
        logger.info(f"SessionState initialized: {self.db_path}")
    
    def _init_schema(self):
        """Initialize database schema."""
        # Sessions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                last_active REAL NOT NULL,
                router_model TEXT,
                metadata TEXT,
                compression_count INTEGER DEFAULT 0
            )
        """)
        
        # Messages table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                token_count INTEGER,
                model_used TEXT,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Create index on session_id for fast lookups
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, id)
        """)
        
        # FTS5 virtual table for full-text search
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
            USING fts5(
                content,
                session_id UNINDEXED,
                content=messages,
                content_rowid=id
            )
        """)
        
        # Triggers to keep FTS index in sync
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_fts_insert
            AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content, session_id)
                VALUES (new.id, new.content, new.session_id);
            END
        """)
        
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_fts_delete
            AFTER DELETE ON messages BEGIN
                DELETE FROM messages_fts WHERE rowid = old.id;
            END
        """)
        
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_fts_update
            AFTER UPDATE ON messages BEGIN
                UPDATE messages_fts
                SET content = new.content, session_id = new.session_id
                WHERE rowid = new.id;
            END
        """)
        
        # Schema version tracking
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Check/set schema version
        result = self.conn.execute(
            "SELECT value FROM schema_metadata WHERE key = 'version'"
        ).fetchone()
        
        if not result:
            self.conn.execute(
                "INSERT INTO schema_metadata (key, value) VALUES ('version', ?)",
                (str(self.SCHEMA_VERSION),)
            )
    
    def create_session(
        self,
        session_id: Optional[str] = None,
        router_model: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Create a new session."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        now = time.time()
        metadata_json = json.dumps(metadata) if metadata else None
        
        self.conn.execute("""
            INSERT INTO sessions (session_id, created_at, last_active, router_model, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, now, now, router_model, metadata_json))
        
        logger.info(f"Created session: {session_id}")
        return session_id
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        result = self.conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        return result is not None
    
    def update_session_activity(self, session_id: str):
        """Update last_active timestamp for session."""
        self.conn.execute("""
            UPDATE sessions SET last_active = ? WHERE session_id = ?
        """, (time.time(), session_id))
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        token_count: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> int:
        """Add a message to the session."""
        if not self.session_exists(session_id):
            self.create_session(session_id)
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor = self.conn.execute("""
            INSERT INTO messages (session_id, role, content, timestamp, token_count, model_used, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, role, content, time.time(), token_count, model_used, metadata_json))
        
        msg_id = cursor.lastrowid
        
        # Update session activity
        self.update_session_activity(session_id)
        
        logger.debug(f"Added message {msg_id} to session {session_id}: role={role}, model={model_used}")
        return msg_id
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict]:
        """Get messages for a session."""
        query = """
            SELECT id, role, content, timestamp, token_count, model_used, metadata
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
        """
        
        params = [session_id]
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        rows = self.conn.execute(query, params).fetchall()
        
        messages = []
        for row in rows:
            msg = {
                "id": row[0],
                "role": row[1],
                "content": row[2],
                "timestamp": row[3],
                "token_count": row[4],
                "model_used": row[5],
            }
            if row[6]:  # metadata
                msg["metadata"] = json.loads(row[6])
            messages.append(msg)
        
        return messages
    
    def get_context_window(
        self,
        session_id: str,
        protect_first: int = PROTECT_FIRST_N,
        protect_last: int = PROTECT_LAST_N,
    ) -> List[Dict]:
        """
        Get context window with Sentinel-style compression.
        Preserves first N and last M messages, compresses middle if needed.
        """
        messages = self.get_messages(session_id)
        
        if len(messages) <= protect_first + protect_last:
            # No compression needed
            return messages
        
        # Split into head, middle, tail
        head = messages[:protect_first]
        tail = messages[-protect_last:]
        middle = messages[protect_first:-protect_last]
        
        # For now, return all (compression will be implemented in context_compressor)
        # This is the hook point for future compression logic
        return head + middle + tail
    
    def search_messages(
        self,
        session_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        FTS5 full-text search across session messages.
        Returns ranked results with snippets.
        """
        results = self.conn.execute("""
            SELECT
                m.id,
                m.role,
                m.content,
                m.timestamp,
                m.model_used,
                snippet(messages_fts, 0, '<mark>', '</mark>', '...', 64) as snippet,
                rank
            FROM messages_fts
            JOIN messages m ON m.id = messages_fts.rowid
            WHERE messages_fts MATCH ? AND session_id = ?
            ORDER BY rank
            LIMIT ?
        """, (query, session_id, top_k)).fetchall()
        
        return [
            {
                "id": row[0],
                "role": row[1],
                "content": row[2],
                "timestamp": row[3],
                "model_used": row[4],
                "snippet": row[5],
                "rank": row[6],
            }
            for row in results
        ]
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session."""
        stats = self.conn.execute("""
            SELECT
                COUNT(*) as message_count,
                SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                SUM(COALESCE(token_count, 0)) as total_tokens,
                MIN(timestamp) as first_message_time,
                MAX(timestamp) as last_message_time
            FROM messages
            WHERE session_id = ?
        """, (session_id,)).fetchone()
        
        session_info = self.conn.execute("""
            SELECT created_at, router_model, compression_count
            FROM sessions
            WHERE session_id = ?
        """, (session_id,)).fetchone()
        
        if stats and session_info:
            return {
                "message_count": stats[0],
                "user_messages": stats[1],
                "assistant_messages": stats[2],
                "total_tokens": stats[3],
                "first_message_time": stats[4],
                "last_message_time": stats[5],
                "session_created": session_info[0],
                "router_model": session_info[1],
                "compression_count": session_info[2],
            }
        
        return {}
    
    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """List recent sessions."""
        rows = self.conn.execute("""
            SELECT
                s.session_id,
                s.created_at,
                s.last_active,
                s.router_model,
                COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.session_id = m.session_id
            GROUP BY s.session_id
            ORDER BY s.last_active DESC
            LIMIT ?
        """, (limit,)).fetchall()
        
        return [
            {
                "session_id": row[0],
                "created_at": row[1],
                "last_active": row[2],
                "router_model": row[3],
                "message_count": row[4],
            }
            for row in rows
        ]
    
    def delete_session(self, session_id: str):
        """Delete a session and all its messages."""
        self.conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self.conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        logger.info(f"Deleted session: {session_id}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("SessionState closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global session state instance
_session_state: Optional[SessionState] = None


def get_session_state() -> SessionState:
    """Get or create global session state instance."""
    global _session_state
    if _session_state is None:
        _session_state = SessionState()
    return _session_state

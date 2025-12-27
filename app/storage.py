import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Tuple
from contextlib import contextmanager

DB_PATH = "/data/app.db"


def get_db_path():
    """Get database path, create directory if needed"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return DB_PATH


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema"""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                raw_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_source ON messages(source)
        """)


def check_db_ready() -> bool:
    """Check if database is ready"""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def insert_message(message_id: str, timestamp: str, source: str, raw_data: dict) -> bool:
    """
    Insert message with idempotency check.
    Returns True if inserted, False if already exists.
    """
    try:
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO messages (message_id, timestamp, source, raw_data, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                message_id,
                timestamp,
                source,
                json.dumps(raw_data),
                datetime.utcnow().isoformat()
            ))
        return True
    except sqlite3.IntegrityError:
        # Message ID already exists (idempotency)
        return False


def get_messages(
    page: int = 1,
    page_size: int = 10,
    source: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[List[dict], int]:
    """
    Get paginated messages with optional filtering.
    Returns (messages, total_count)
    """
    offset = (page - 1) * page_size
    
    # Build WHERE clause
    conditions = []
    params = []
    
    if source:
        conditions.append("source = ?")
        params.append(source)
    
    if start_date:
        conditions.append("timestamp >= ?")
        params.append(start_date)
    
    if end_date:
        conditions.append("timestamp <= ?")
        params.append(end_date)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Get total count
    with get_db_connection() as conn:
        count_result = conn.execute(
            f"SELECT COUNT(*) as count FROM messages WHERE {where_clause}",
            params
        ).fetchone()
        total = count_result["count"] if count_result else 0
        
        # Get paginated results
        query = f"""
            SELECT message_id, timestamp, source, raw_data, created_at
            FROM messages
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params_with_pagination = params + [page_size, offset]
        
        rows = conn.execute(query, params_with_pagination).fetchall()
        
        messages = []
        for row in rows:
            messages.append({
                "message_id": row["message_id"],
                "timestamp": row["timestamp"],
                "source": row["source"],
                "raw_data": json.loads(row["raw_data"]),
                "created_at": row["created_at"]
            })
    
    return messages, total


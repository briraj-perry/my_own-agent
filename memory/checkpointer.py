"""SQLite chat memory persistence and LangGraph SQLite Checkpointer implementation."""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple
from contextlib import contextmanager

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
    SerializerProtocol,
)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from config import settings

logger = logging.getLogger(__name__)


class SQLiteChatMemory:
    """Helper for persisting user/assistant chat history in SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or settings.chat_history_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema for chat messages."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_thread_id ON chat_messages(thread_id)"
            )

    def save_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Save a single chat message to history."""
        meta_json = json.dumps(metadata) if metadata else None
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO chat_messages (thread_id, role, content, metadata) VALUES (?, ?, ?, ?)",
                (thread_id, role, content, meta_json),
            )
            return cursor.lastrowid

    def get_messages(
        self, thread_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve recent chat history for a thread ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT role, content, metadata, created_at FROM chat_messages WHERE thread_id = ? ORDER BY id ASC LIMIT ?",
                (thread_id, limit),
            )
            rows = cursor.fetchall()
            result = []
            for r in rows:
                result.append(
                    {
                        "role": r["role"],
                        "content": r["content"],
                        "metadata": json.loads(r["metadata"])
                        if r["metadata"]
                        else {},
                        "created_at": r["created_at"],
                    }
                )
            return result

    def clear_history(self, thread_id: str) -> None:
        """Clear chat history for a specific thread."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM chat_messages WHERE thread_id = ?", (thread_id,)
            )

    def list_threads(self) -> List[str]:
        """List all thread IDs stored in database."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT thread_id FROM chat_messages"
            )
            return [row["thread_id"] for row in cursor.fetchall()]


class SQLiteCheckpointer(BaseCheckpointSaver):
    """LangGraph Checkpointer implementation using SQLite for state persistence across runs."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        serde: Optional[SerializerProtocol] = None,
    ):
        super().__init__(serde=serde or JsonPlusSerializer())
        self.db_path = Path(db_path or settings.checkpoint_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create checkpoints table if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    type TEXT,
                    checkpoint BLOB NOT NULL,
                    metadata BLOB NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoint_writes (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    type TEXT,
                    value BLOB NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                )
            """
            )

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Get checkpoint tuple for given runnable config."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")

        with self._get_connection() as conn:
            if checkpoint_id:
                query = """
                    SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, checkpoint, metadata
                    FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                """
                cursor = conn.execute(query, (thread_id, checkpoint_ns, checkpoint_id))
            else:
                query = """
                    SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, checkpoint, metadata
                    FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ?
                    ORDER BY checkpoint_id DESC
                    LIMIT 1
                """
                cursor = conn.execute(query, (thread_id, checkpoint_ns))

            row = cursor.fetchone()
            if not row:
                return None

            checkpoint = self.serde.loads(row["checkpoint"])
            metadata = self.serde.loads(row["metadata"])

            # Load writes
            writes_query = """
                SELECT task_id, channel, value
                FROM checkpoint_writes
                WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
            """
            writes_cursor = conn.execute(
                writes_query, (thread_id, checkpoint_ns, row["checkpoint_id"])
            )
            pending_writes = [
                (w_row["task_id"], w_row["channel"], self.serde.loads(w_row["value"]))
                for w_row in writes_cursor.fetchall()
            ]

            parent_config = (
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["parent_checkpoint_id"],
                    }
                }
                if row["parent_checkpoint_id"]
                else None
            )

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["checkpoint_id"],
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=pending_writes,
            )

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints matching the filter criteria."""
        thread_id = config["configurable"]["thread_id"] if config else None
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "") if config else ""

        query = "SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, checkpoint, metadata FROM checkpoints WHERE 1=1"
        params: List[Any] = []

        if thread_id:
            query += " AND thread_id = ?"
            params.append(thread_id)
        if checkpoint_ns:
            query += " AND checkpoint_ns = ?"
            params.append(checkpoint_ns)
        if before and "checkpoint_id" in before.get("configurable", {}):
            query += " AND checkpoint_id < ?"
            params.append(before["configurable"]["checkpoint_id"])

        query += " ORDER BY checkpoint_id DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                checkpoint = self.serde.loads(row["checkpoint"])
                metadata = self.serde.loads(row["metadata"])
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": row["thread_id"],
                            "checkpoint_ns": row["checkpoint_ns"],
                            "checkpoint_id": row["checkpoint_id"],
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config={
                        "configurable": {
                            "thread_id": row["thread_id"],
                            "checkpoint_ns": row["checkpoint_ns"],
                            "checkpoint_id": row["parent_checkpoint_id"],
                        }
                    }
                    if row["parent_checkpoint_id"]
                    else None,
                )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Store a checkpoint for a thread."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        checkpoint_bytes = self.serde.dumps(checkpoint)
        metadata_bytes = self.serde.dumps(metadata)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, checkpoint, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    thread_id,
                    checkpoint_ns,
                    checkpoint["id"],
                    parent_checkpoint_id,
                    checkpoint_bytes,
                    metadata_bytes,
                ),
            )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Store pending writes for a task."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        with self._get_connection() as conn:
            for idx, (channel, value) in enumerate(writes):
                val_bytes = self.serde.dumps(value)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO checkpoint_writes (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, value)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        thread_id,
                        checkpoint_ns,
                        checkpoint_id,
                        task_id,
                        idx,
                        channel,
                        val_bytes,
                    ),
                )


def get_sqlite_checkpointer(
    db_path: Optional[Path] = None,
) -> BaseCheckpointSaver:
    """Factory to return an initialized SQLiteCheckpointer."""
    try:
        return SQLiteCheckpointer(db_path=db_path)
    except Exception as e:
        logger.warning(
            f"Failed to initialize SQLiteCheckpointer ({e}), falling back to MemorySaver."
        )
        return MemorySaver()


def get_memory_checkpointer() -> MemorySaver:
    """Factory to return an in-memory checkpointer."""
    return MemorySaver()

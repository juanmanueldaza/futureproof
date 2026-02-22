"""LangGraph checkpointer factory for persistent conversation state.

Provides SqliteSaver instances for persisting conversation state across sessions.
The checkpointer stores:
- Message history for each thread
- Agent state (current analysis, pending actions)
- Checkpoint metadata for time-travel debugging

Usage:
    from futureproof.memory import get_checkpointer

    checkpointer = get_checkpointer()
    agent = create_agent(..., checkpointer=checkpointer)

    # Conversations persist automatically with thread_id
    config = {"configurable": {"thread_id": "main"}}
    agent.invoke({"messages": [...]}, config)
"""

from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

# Cached singleton to avoid creating new connections on every call
_checkpointer: SqliteSaver | None = None


def get_data_dir() -> Path:
    """Get or create the FutureProof data directory."""
    data_dir = Path.home() / ".futureproof"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_checkpointer() -> SqliteSaver:
    """Get a synchronous SqliteSaver checkpointer (cached singleton).

    Returns:
        SqliteSaver instance connected to ~/.futureproof/memory.db

    Note:
        The SqliteSaver handles thread-safety internally with locks.
        Safe to use from multiple threads (check_same_thread=False).
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    import sqlite3

    db_path = get_data_dir() / "memory.db"
    # Create connection with check_same_thread=False for multi-threaded use
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    _checkpointer = SqliteSaver(conn)
    return _checkpointer


def clear_thread_history(thread_id: str) -> None:
    """Clear conversation history for a specific thread.

    Args:
        thread_id: The thread identifier to clear

    Note:
        This is a destructive operation. Use with caution.
    """
    import sqlite3

    db_path = get_data_dir() / "memory.db"
    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        # LangGraph stores data across both tables with thread_id
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        conn.commit()
    finally:
        conn.close()


def list_threads() -> list[str]:
    """List all conversation thread IDs.

    Returns:
        List of thread IDs that have stored conversations.
    """
    import sqlite3

    db_path = get_data_dir() / "memory.db"
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT thread_id FROM checkpoints "
            "UNION SELECT DISTINCT thread_id FROM writes"
        )
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return []
    finally:
        conn.close()

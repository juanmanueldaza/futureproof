"""Episodic memory tools for the career agent."""

import logging
from collections.abc import Callable
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _store_to_episodic(
    action_fn: Callable[[], Any],
    success_msg: str,
    error_noun: str,
) -> str:
    """Store a memory to the episodic store with shared error handling.

    Args:
        action_fn: Callable that creates the memory object when called
        success_msg: Message to return on success
        error_noun: Noun describing what failed (for error message)

    Returns:
        Success message or error string
    """
    try:
        from fu7ur3pr00f.memory.episodic import get_episodic_store

        get_episodic_store().remember(action_fn())
    except Exception as e:
        logger.exception("Error storing %s to ChromaDB", error_noun)
        return f"Could not store {error_noun}: {e}"

    return success_msg


@tool
def remember_decision(
    decision: str,
    context: str,
    outcome: str = "",
) -> str:
    """Store a career decision in long-term memory.

    Args:
        decision: The decision that was made
        context: Context and reasoning behind the decision
        outcome: Optional outcome if known

    Use this when the user makes an important career decision that should be
    remembered across sessions, such as rejecting a job offer, choosing a
    technology stack, or setting a career direction.
    """
    from fu7ur3pr00f.memory.episodic import remember_decision as create_decision

    return _store_to_episodic(
        lambda: create_decision(decision, context, outcome),
        (
            f"Remembered: {decision!r}. "
            "I'll be able to recall this in future conversations."
        ),
        "decision",
    )


@tool
def remember_job_application(
    company: str,
    role: str,
    status: str,
    notes: str = "",
) -> str:
    """Record a job application in long-term memory.

    Args:
        company: Company name
        role: Role applied for
        status: Status (applied, interviewing, rejected, offer, accepted, declined)
        notes: Additional notes about the application

    Use this to track job applications across sessions.
    """
    from fu7ur3pr00f.memory.episodic import remember_application

    return _store_to_episodic(
        lambda: remember_application(company, role, status, notes),
        f"Recorded application to {company} for {role} (status: {status}).",
        "application",
    )


@tool
def recall_memories(
    query: str,
    limit: int = 5,
) -> str:
    """Search long-term memory for relevant past experiences.

    Args:
        query: What to search for (semantic search)
        limit: Maximum number of memories to return

    Use this to recall past decisions, job applications, or conversations
    that are relevant to the current discussion.
    """
    try:
        from fu7ur3pr00f.memory.episodic import get_episodic_store

        store = get_episodic_store()
        memories = store.recall(query, limit=limit)

        if not memories:
            return "No relevant memories found."

        result_parts = [f"Found {len(memories)} relevant memories:"]
        for mem in memories:
            date_str = mem.timestamp.strftime("%Y-%m-%d")
            result_parts.append(f"\n**[{mem.memory_type.value}] {date_str}**")
            result_parts.append(f"  {mem.content}")
            if mem.context:
                result_parts.append(f"  Context: {mem.context}")

        return "\n".join(result_parts)

    except Exception:
        logger.exception("Error recalling from ChromaDB")
        return "No relevant memories found."


@tool
def get_memory_stats() -> str:
    """Get statistics about what's stored in long-term memory.

    Use this to see an overview of stored memories, including counts
    by type (decisions, applications, conversations, etc.).
    """
    from fu7ur3pr00f.memory.episodic import get_episodic_store

    store = get_episodic_store()
    stats = store.stats()

    result_parts = ["Long-term memory statistics:"]
    result_parts.append(f"\nTotal memories: {stats['total_memories']}")
    result_parts.append("\nBy type:")
    for mem_type, count in stats["by_type"].items():
        if count > 0:
            result_parts.append(f"  - {mem_type}: {count}")

    return "\n".join(result_parts)

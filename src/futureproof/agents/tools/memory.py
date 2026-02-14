"""Episodic memory tools for the career agent."""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


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
    try:
        from futureproof.memory.episodic import (
            get_episodic_store,
        )
        from futureproof.memory.episodic import (
            remember_decision as create_decision,
        )

        memory = create_decision(decision, context, outcome)
        get_episodic_store().remember(memory)
    except Exception as e:
        logger.exception("Error storing decision to ChromaDB")
        return f"Could not store decision: {e}"

    return f"Remembered: '{decision}'. I'll be able to recall this in future conversations."


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
    try:
        from futureproof.memory.episodic import get_episodic_store, remember_application

        memory = remember_application(company, role, status, notes)
        get_episodic_store().remember(memory)
    except Exception as e:
        logger.exception("Error storing application to ChromaDB")
        return f"Could not store application: {e}"

    return f"Recorded application to {company} for {role} (status: {status})."


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
        from futureproof.memory.episodic import get_episodic_store

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
    from futureproof.memory.episodic import get_episodic_store

    store = get_episodic_store()
    stats = store.stats()

    result_parts = ["Long-term memory statistics:"]
    result_parts.append(f"\nTotal memories: {stats['total_memories']}")
    result_parts.append("\nBy type:")
    for mem_type, count in stats["by_type"].items():
        if count > 0:
            result_parts.append(f"  - {mem_type}: {count}")

    return "\n".join(result_parts)

"""Episodic memory tools for the career agent."""

import logging
import uuid
from collections.abc import Callable
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _dual_write_memory(
    runtime: ToolRuntime | None,
    namespace: tuple[str, ...],
    key: str,
    store_data: dict[str, Any],
    episodic_fn: Callable[..., Any],
    episodic_args: tuple,
) -> None:
    """Write to both InMemoryStore (runtime) and ChromaDB (persistent).

    Args:
        runtime: LangGraph ToolRuntime with optional store access
        namespace: InMemoryStore namespace tuple (e.g., ("default", "decisions"))
        key: Unique key for the memory entry
        store_data: Data dict to write to InMemoryStore
        episodic_fn: Function that creates an EpisodicMemory instance
        episodic_args: Arguments to pass to episodic_fn
    """
    # Write to LangGraph InMemoryStore (cross-thread runtime access)
    if runtime and runtime.store:
        try:
            runtime.store.put(namespace, key, store_data)
        except Exception:
            logger.debug("InMemoryStore write failed (non-critical)", exc_info=True)

    # Write to ChromaDB (persistent storage)
    from futureproof.memory.episodic import get_episodic_store

    store = get_episodic_store()
    memory = episodic_fn(*episodic_args)
    store.remember(memory)


@tool
def remember_decision(
    decision: str,
    context: str,
    outcome: str = "",
    runtime: ToolRuntime = None,  # type: ignore[assignment]
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
    memory_id = str(uuid.uuid4())
    text = f"{decision}. Context: {context}"
    if outcome:
        text += f". Outcome: {outcome}"

    try:
        from futureproof.memory.episodic import remember_decision as create_decision

        _dual_write_memory(
            runtime=runtime,
            namespace=("default", "decisions"),
            key=memory_id,
            store_data={"text": text, "type": "decision", "outcome": outcome},
            episodic_fn=create_decision,
            episodic_args=(decision, context, outcome),
        )
    except ImportError:
        logger.warning("ChromaDB not available - episodic memory disabled")
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
    runtime: ToolRuntime = None,  # type: ignore[assignment]
) -> str:
    """Record a job application in long-term memory.

    Args:
        company: Company name
        role: Role applied for
        status: Status (applied, interviewing, rejected, offer, accepted, declined)
        notes: Additional notes about the application

    Use this to track job applications across sessions.
    """
    memory_id = str(uuid.uuid4())
    text = f"Applied to {company} for {role}. Status: {status}"
    if notes:
        text += f". {notes}"

    try:
        from futureproof.memory.episodic import remember_application

        _dual_write_memory(
            runtime=runtime,
            namespace=("default", "applications"),
            key=memory_id,
            store_data={
                "text": text,
                "type": "application",
                "company": company,
                "role": role,
                "status": status,
            },
            episodic_fn=remember_application,
            episodic_args=(company, role, status, notes),
        )
    except ImportError:
        logger.warning("ChromaDB not available")
    except Exception as e:
        logger.exception("Error storing application to ChromaDB")
        return f"Could not store application: {e}"

    return f"Recorded application to {company} for {role} (status: {status})."


@tool
def recall_memories(
    query: str,
    limit: int = 5,
    runtime: ToolRuntime = None,  # type: ignore[assignment]
) -> str:
    """Search long-term memory for relevant past experiences.

    Args:
        query: What to search for (semantic search)
        limit: Maximum number of memories to return

    Use this to recall past decisions, job applications, or conversations
    that are relevant to the current discussion.
    """
    result_parts: list[str] = []

    # Search ChromaDB (persistent, primary source)
    try:
        from futureproof.memory.episodic import get_episodic_store

        store = get_episodic_store()
        memories = store.recall(query, limit=limit)

        if memories:
            result_parts.append(f"Found {len(memories)} relevant memories:")
            for mem in memories:
                date_str = mem.timestamp.strftime("%Y-%m-%d")
                result_parts.append(f"\n**[{mem.memory_type.value}] {date_str}**")
                result_parts.append(f"  {mem.content}")
                if mem.context:
                    result_parts.append(f"  Context: {mem.context}")

    except ImportError:
        logger.debug("ChromaDB not available")
    except Exception:
        logger.exception("Error recalling from ChromaDB")

    # Also search InMemoryStore for recent session memories
    if runtime and runtime.store:
        try:
            for namespace in [("default", "decisions"), ("default", "applications")]:
                items = runtime.store.search(namespace, query=query, limit=limit)
                for item in items:
                    text = item.value.get("text", "")
                    mem_type = item.value.get("type", "memory")
                    if text and text not in "\n".join(result_parts):
                        result_parts.append(f"\n**[{mem_type}]** {text}")
        except Exception:
            logger.debug("InMemoryStore search failed (non-critical)", exc_info=True)

    if not result_parts:
        return "No relevant memories found."

    return "\n".join(result_parts)


@tool
def get_memory_stats() -> str:
    """Get statistics about what's stored in long-term memory.

    Use this to see an overview of stored memories, including counts
    by type (decisions, applications, conversations, etc.).
    """
    try:
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

    except ImportError:
        return "Note: Long-term memory is not available (ChromaDB not installed)."
    except Exception as e:
        logger.exception("Error getting memory stats")
        return f"Could not get memory stats: {e}"

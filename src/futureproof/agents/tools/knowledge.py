"""Knowledge base (RAG) tools for the career agent."""

from langchain_core.tools import tool
from langgraph.types import interrupt


def _parse_source(source: str):
    """Parse and validate a KnowledgeSource string."""
    from futureproof.memory.knowledge import KnowledgeSource

    try:
        return KnowledgeSource(source)
    except ValueError:
        valid = ", ".join(s.value for s in KnowledgeSource)
        raise ValueError(f"Invalid source '{source}'. Valid sources: {valid}")


@tool
def search_career_knowledge(
    query: str,
    sources: list[str] | None = None,
    limit: int = 5,
) -> str:
    """Search the career knowledge base for relevant information.

    Args:
        query: What to search for (e.g., "Python projects", "leadership experience")
        sources: Optional filter by source (linkedin, portfolio, assessment)
        limit: Maximum results to return

    Use this to find specific information from the user's career history
    instead of relying on general context. More efficient than loading
    all career data. Examples:
    - "Python projects" to find Python-related work
    - "leadership" to find management or leadership experience
    - "recent contributions" for recent activity
    """
    from futureproof.services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    results = service.search(query, limit=limit, sources=sources)

    if not results:
        return (
            f"No results found for '{query}'. "
            "Try a different query or check if career data has been indexed."
        )

    result_parts = [f"Found {len(results)} relevant results for '{query}':"]
    for i, result in enumerate(results, 1):
        source = result.get("source", "unknown")
        section = result.get("section", "")
        content = result.get("content", "")[:500]
        result_parts.append(f"\n**{i}. [{source}] {section}**")
        result_parts.append(content)

    return "\n".join(result_parts)


@tool
def get_knowledge_stats() -> str:
    """Get statistics about the career knowledge base.

    Shows what career data is indexed and available for search.
    Use this to see if the knowledge base has been populated.
    """
    from futureproof.services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    stats = service.get_stats()

    total = stats.get("total_chunks", 0)
    if total == 0:
        return "Career knowledge base is empty. Ask me to index your career data."

    result_parts = ["Career Knowledge Base Statistics:"]
    result_parts.append(f"\nTotal chunks indexed: {total}")
    result_parts.append("\nBy source:")
    for source, count in stats.get("by_source", {}).items():
        if count > 0:
            result_parts.append(f"  - {source}: {count} chunks")

    return "\n".join(result_parts)


@tool
def index_career_knowledge(source: str = "") -> str:
    """Check indexed career data in the knowledge base.

    Args:
        source: Specific source to check (linkedin, portfolio, assessment).
                Leave empty to check all available sources.

    All sources are auto-indexed when gathered. Use this to verify indexing status.
    """
    from futureproof.services.knowledge_service import KnowledgeService

    service = KnowledgeService()

    results = service.index_all(verbose=False)

    if source:
        ks = _parse_source(source)
        count = results.get(ks.value, 0)
        if count > 0:
            return f"'{source}' has {count} chunks indexed in the knowledge base."
        return f"No data indexed for '{source}'. Gather the data first."
    else:
        total = sum(results.values())
        indexed = sum(1 for c in results.values() if c > 0)
        result_parts = [f"{total} chunks from {indexed} sources:"]
        for src, count in results.items():
            if count > 0:
                result_parts.append(f"  - {src}: {count} chunks")
        return "\n".join(result_parts)


@tool
def clear_career_knowledge(source: str = "") -> str:
    """Clear indexed data from the career knowledge base.

    Args:
        source: Specific source to clear (linkedin, portfolio, assessment).
                Leave empty to clear all indexed data.

    Use this to remove outdated indexed data before re-indexing.
    """
    target = f"'{source}'" if source else "all"
    approved = interrupt(
        {
            "question": f"Clear {target} indexed career data?",
            "details": "This will permanently remove the data from the knowledge base. "
            "You will need to re-gather to restore it.",
        }
    )
    if not approved:
        return "Knowledge base clear cancelled."

    from futureproof.memory.knowledge import KnowledgeSource, get_knowledge_store

    store = get_knowledge_store()

    if source:
        ks = _parse_source(source)
        deleted = store.clear_source(ks)
        return f"Cleared {deleted} chunks for '{source}' from the knowledge base."
    else:
        total_deleted = 0
        for ks in KnowledgeSource:
            total_deleted += store.clear_source(ks)
        return f"Cleared {total_deleted} chunks from the knowledge base."

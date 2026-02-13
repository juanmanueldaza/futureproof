"""Knowledge base (RAG) tools for the career agent."""

import logging

from langchain_core.tools import tool
from langgraph.types import interrupt

logger = logging.getLogger(__name__)


@tool
def search_career_knowledge(
    query: str,
    sources: list[str] | None = None,
    limit: int = 5,
) -> str:
    """Search the career knowledge base for relevant information.

    Args:
        query: What to search for (e.g., "Python projects", "leadership experience")
        sources: Optional filter by source (github, gitlab, linkedin, portfolio, assessment)
        limit: Maximum results to return

    Use this to find specific information from the user's career history
    instead of relying on general context. More efficient than loading
    all career data. Examples:
    - "Python projects" to find Python-related work
    - "leadership" to find management or leadership experience
    - "recent contributions" for recent activity
    """
    try:
        from futureproof.services.knowledge_service import KnowledgeService

        service = KnowledgeService()
        results = service.search(query, limit=limit, sources=sources)

        if not results:
            return (
                f"No results found for '{query}'. "
                "Try a different query or check if career data has been indexed."
            )

        parts = [f"Found {len(results)} relevant results for '{query}':"]
        for i, result in enumerate(results, 1):
            source = result.get("source", "unknown")
            section = result.get("section", "")
            content = result.get("content", "")[:500]  # Truncate for display
            parts.append(f"\n**{i}. [{source}] {section}**")
            parts.append(content)

        return "\n".join(parts)

    except ImportError:
        return "Knowledge base not available (ChromaDB not installed)."
    except Exception as e:
        logger.exception("Error searching knowledge base")
        return f"Error searching knowledge base: {e}"


@tool
def get_knowledge_stats() -> str:
    """Get statistics about the career knowledge base.

    Shows what career data is indexed and available for search.
    Use this to see if the knowledge base has been populated.
    """
    try:
        from futureproof.services.knowledge_service import KnowledgeService

        service = KnowledgeService()
        stats = service.get_stats()

        total = stats.get("total_chunks", 0)
        if total == 0:
            return (
                "Career knowledge base is empty. "
                "Ask me to index your career data, or run `futureproof index` from the CLI."
            )

        parts = ["Career Knowledge Base Statistics:"]
        parts.append(f"\nTotal chunks indexed: {total}")
        parts.append("\nBy source:")
        for source, count in stats.get("by_source", {}).items():
            if count > 0:
                parts.append(f"  - {source}: {count} chunks")

        return "\n".join(parts)

    except ImportError:
        return "Knowledge base not available (ChromaDB not installed)."
    except Exception as e:
        logger.exception("Error getting knowledge stats")
        return f"Error getting stats: {e}"


@tool
def index_career_knowledge(source: str = "") -> str:
    """Index gathered career data into the knowledge base for semantic search.

    Args:
        source: Specific source to index (github, gitlab, linkedin, portfolio,
                assessment). Leave empty to index all available sources.

    This creates embeddings from gathered career data so it can be searched
    semantically. Run this after gathering new data to make it searchable.
    """
    try:
        from futureproof.memory.knowledge import KnowledgeSource
        from futureproof.services.knowledge_service import KnowledgeService

        service = KnowledgeService()

        if source:
            ks = KnowledgeSource(source)
            chunks = service.index_source(ks, verbose=False)
            return f"Indexed {chunks} chunks from '{source}' into the knowledge base."
        else:
            results = service.index_all(verbose=False)
            total = sum(results.values())
            indexed = sum(1 for c in results.values() if c > 0)
            parts = [f"Indexed {total} chunks from {indexed} sources:"]
            for src, count in results.items():
                if count > 0:
                    parts.append(f"  - {src}: {count} chunks")
            return "\n".join(parts)

    except ValueError:
        from futureproof.memory.knowledge import KnowledgeSource

        valid = ", ".join(s.value for s in KnowledgeSource)
        return f"Invalid source '{source}'. Valid sources: {valid}"
    except ImportError:
        return "Knowledge base not available (ChromaDB not installed)."
    except Exception as e:
        logger.exception("Error indexing knowledge base")
        return f"Error indexing knowledge base: {e}"


@tool
def clear_career_knowledge(source: str = "") -> str:
    """Clear indexed data from the career knowledge base.

    Args:
        source: Specific source to clear (github, gitlab, linkedin, portfolio,
                assessment). Leave empty to clear all indexed data.

    Use this to remove outdated indexed data before re-indexing.
    """
    target = f"'{source}'" if source else "all"
    approved = interrupt(
        {
            "question": f"Clear {target} indexed career data?",
            "details": "This will remove the data from the knowledge base. "
            "The original gathered files are not affected.",
        }
    )
    if not approved:
        return "Knowledge base clear cancelled."

    try:
        from futureproof.memory.knowledge import KnowledgeSource, get_knowledge_store

        store = get_knowledge_store()

        if source:
            ks = KnowledgeSource(source)
            deleted = store.clear_source(ks)
            return f"Cleared {deleted} chunks for '{source}' from the knowledge base."
        else:
            total_deleted = 0
            for ks in KnowledgeSource:
                total_deleted += store.clear_source(ks)
            return f"Cleared {total_deleted} chunks from the knowledge base."

    except ValueError:
        from futureproof.memory.knowledge import KnowledgeSource as KS

        valid = ", ".join(s.value for s in KS)
        return f"Invalid source '{source}'. Valid sources: {valid}"
    except ImportError:
        return "Knowledge base not available (ChromaDB not installed)."
    except Exception as e:
        logger.exception("Error clearing knowledge base")
        return f"Error clearing knowledge base: {e}"

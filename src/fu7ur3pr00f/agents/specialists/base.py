"""Base class for specialist agents.

All specialist agents inherit from this base class to ensure:
- Consistent interface (can_handle, process)
- Shared memory access (ChromaDB)
- Common tool registry
- Unified error handling

Example:
    >>> class CoachAgent(BaseAgent):
    ...     name = "coach"
    ...     description = "Leadership and career growth coach"
    ...     
    ...     def can_handle(self, intent: str) -> bool:
    ...         return "leadership" in intent or "promotion" in intent
    ...     
    ...     async def process(self, context: dict[str, Any]) -> str:
    ...         return "Leadership advice..."
"""

import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fu7ur3pr00f.memory.chromadb_store import get_chroma_client


@dataclass
class KnowledgeResult:
    """A single result from knowledge base search.
    
    Attributes:
        content: The text content of the chunk
        metadata: Associated metadata (source, section, etc.)
        score: Similarity score (if available)
    
    Example:
        >>> result = KnowledgeResult(
        ...     content="Python developer with 5 years experience",
        ...     metadata={"source": "linkedin", "section": "experience"},
        ...     score=0.92
        ... )
        >>> print(result.content)
        'Python developer with 5 years experience'
    """
    content: str
    metadata: dict[str, Any]
    score: float | None = None


@dataclass
class MemoryResult:
    """A single episodic memory result.
    
    Attributes:
        content: The memory content
        event_type: Type of event (decision, application, etc.)
        timestamp: When the memory was stored
        score: Similarity score (if available)
    
    Example:
        >>> memory = MemoryResult(
        ...     content="Accepted Senior Engineer offer at TechCorp",
        ...     event_type="decision",
        ...     timestamp=1711234567.0,
        ...     score=0.88
        ... )
    """
    content: str
    event_type: str
    timestamp: float | None = None
    score: float | None = None


class BaseAgent(ABC):
    """Abstract base class for all specialist agents.
    
    Subclasses must implement:
    - name: Agent identifier
    - description: Human-readable description
    - can_handle(): Intent matching logic
    - process(): Request processing logic
    
    Example:
        >>> class CoachAgent(BaseAgent):
        ...     name = "coach"
        ...     description = "Career growth and leadership coach"
        ...     tools = [analyze_career_alignment, get_career_advice]
        ...     
        ...     def can_handle(self, intent: str) -> bool:
        ...         return any(k in intent.lower() for k in ["leadership", "promotion"])
        ...     
        ...     async def process(self, context: dict[str, Any]) -> str:
        ...         return "Based on your CliftonStrengths..."
    """
    
    # Class-level attributes (override in subclasses)
    tools: list[Callable] = []
    
    # Class-level ChromaDB client and lock for thread-safe lazy loading
    _chroma: Any = None
    _lock: threading.Lock = threading.Lock()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier (e.g., 'coach', 'founder', 'learning').
        
        Returns:
            Lowercase agent name without spaces
            
        Example:
            >>> agent = CoachAgent()
            >>> agent.name
            'coach'
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of agent's purpose.
        
        Returns:
            Brief description (1-2 sentences)
            
        Example:
            >>> agent = FounderAgent()
            >>> agent.description
            'Helps developers launch startups and build companies'
        """
        pass
    
    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle the request.
        
        Args:
            intent: User query or intent string
            
        Returns:
            True if this agent should handle the request
            
        Example:
            >>> agent = CoachAgent()
            >>> agent.can_handle("I want to get promoted to Staff Engineer")
            True
            >>> agent.can_handle("Find me remote Python jobs")
            False
        """
        pass
    
    @abstractmethod
    async def process(self, context: dict[str, Any]) -> str:
        """Process the request and return response.
        
        Args:
            context: Request context including:
                - query: User's question/request
                - user_profile: Current user profile
                - conversation_history: Previous turns
                - tool_results: Results from tool execution
        
        Returns:
            Agent response string
            
        Example:
            >>> agent = CoachAgent()
            >>> context = {
            ...     "query": "How can I improve my leadership?",
            ...     "user_profile": {...},
            ...     "conversation_history": []
            ... }
            >>> response = await agent.process(context)
            >>> print(response)
            'Based on your CliftonStrengths...'
        """
        pass
    
    def get_tools(self) -> list[Callable]:
        """Get tools available to this agent.
        
        Returns:
            List of tool functions
            
        Example:
            >>> agent = CoachAgent()
            >>> tools = agent.get_tools()
            >>> len(tools)
            5
        """
        return list(self.tools)
    
    @property
    def chroma(self) -> Any:
        """Lazy-loaded, thread-safe ChromaDB client.
        
        Uses double-check locking to ensure only one client is created
        even when multiple threads access it simultaneously.
        
        Returns:
            ChromaDB client instance
            
        Example:
            >>> agent = CoachAgent()
            >>> client = agent.chroma  # Creates client on first access
            >>> collection = client.get_collection("career_knowledge")
        """
        if self._chroma is None:
            with self._lock:
                if self._chroma is None:  # Double-check
                    self._chroma = get_chroma_client()
        return self._chroma
    
    def search_knowledge(
        self, 
        query: str, 
        limit: int = 5,
        section: str | None = None,
        sources: list[str] | None = None,
    ) -> list[KnowledgeResult]:
        """Search knowledge base with optional filters.
        
        Args:
            query: Search query (will be embedded)
            limit: Number of results to return (default: 5)
            section: Optional filter by section (e.g., "experience", "skills")
            sources: Optional filter by sources (e.g., ["linkedin", "github"])
        
        Returns:
            List of KnowledgeResult objects with content and metadata
            
        Example:
            >>> agent = CoachAgent()
            >>> results = agent.search_knowledge(
            ...     query="Python development experience",
            ...     limit=5,
            ...     section="experience"
            ... )
            >>> for result in results:
            ...     print(f"{result.content[:50]}... (score: {result.score})")
        """
        collection = self.chroma.get_collection("career_knowledge")
        
        # Build where filter
        where: dict[str, Any] = {}
        if section:
            where["section"] = section
        if sources:
            where["$or"] = [{"source": s} for s in sources]
        
        results = collection.query(
            query_texts=[query],
            n_results=limit,
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )
        
        # Convert to KnowledgeResult list
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results.get('distances', [None] * len(documents))[0]
        
        return [
            KnowledgeResult(
                content=doc,
                metadata=meta,
                score=1.0 - dist if dist is not None else None,  # Convert distance to similarity
            )
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]
    
    def index_knowledge(
        self, 
        documents: list[str], 
        metadatas: list[dict[str, Any]],
    ) -> list[str]:
        """Index documents to knowledge base.
        
        Args:
            documents: Text documents to index
            metadatas: Metadata for each document (must include 'source' and 'section')
        
        Returns:
            List of generated document IDs
            
        Example:
            >>> agent = CoachAgent()
            >>> ids = agent.index_knowledge(
            ...     documents=["Senior Engineer at TechCorp"],
            ...     metadatas=[{"source": "linkedin", "section": "experience"}]
            ... )
            >>> len(ids)
            1
        """
        if len(documents) != len(metadatas):
            raise ValueError(
                f"documents and metadatas must have same length "
                f"({len(documents)} != {len(metadatas)})"
            )
        
        collection = self.chroma.get_collection("career_knowledge")
        
        # Generate unique IDs
        ids = [f"doc_{uuid.uuid4().hex[:12]}" for _ in range(len(documents))]
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        
        return ids
    
    def remember(
        self, 
        event_type: str, 
        data: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store episodic memory.
        
        Args:
            event_type: Type of event (e.g., "decision", "application", "goal")
            data: Event data to store
            metadata: Optional additional metadata (timestamp added automatically)
        
        Returns:
            Generated memory ID
            
        Example:
            >>> agent = CoachAgent()
            >>> memory_id = agent.remember(
            ...     event_type="decision",
            ...     data="Accepted promotion to Staff Engineer",
            ...     metadata={"company": "TechCorp", "salary": 200000}
            ... )
            >>> print(memory_id)
            'episodic_decision_a1b2c3d4'
        """
        collection = self.chroma.get_collection("episodic_memory")
        
        # Build metadata with timestamp
        full_metadata: dict[str, Any] = {
            "type": event_type,
            "timestamp": time.time(),
            **(metadata or {}),
        }
        
        # Generate unique ID
        memory_id = f"episodic_{event_type}_{uuid.uuid4().hex[:8]}"
        
        collection.add(
            documents=[data],
            metadatas=[full_metadata],
            ids=[memory_id],
        )
        
        return memory_id
    
    def recall_memories(
        self, 
        query: str, 
        event_type: str | None = None,
        limit: int = 5,
    ) -> list[MemoryResult]:
        """Recall episodic memories with optional filtering.
        
        Args:
            query: Search query
            event_type: Optional filter by event type
            limit: Number of results to return
        
        Returns:
            List of MemoryResult objects
            
        Example:
            >>> agent = CoachAgent()
            >>> memories = agent.recall_memories(
            ...     query="career decisions",
            ...     event_type="decision",
            ...     limit=5
            ... )
            >>> for memory in memories:
            ...     print(f"{memory.content} (type: {memory.event_type})")
        """
        collection = self.chroma.get_collection("episodic_memory")
        
        # Build where filter
        where: dict[str, Any] = {}
        if event_type:
            where["type"] = event_type
        
        results = collection.query(
            query_texts=[query],
            n_results=limit,
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )
        
        # Convert to MemoryResult list
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results.get('distances', [None] * len(documents))[0]
        
        return [
            MemoryResult(
                content=doc,
                event_type=meta.get("type", "unknown"),
                timestamp=meta.get("timestamp"),
                score=1.0 - dist if dist is not None else None,
            )
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]
    
    def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about episodic memory.
        
        Returns:
            Dict with memory counts by type
            
        Example:
            >>> agent = CoachAgent()
            >>> stats = agent.get_memory_stats()
            >>> print(stats)
            {'total': 42, 'by_type': {'decision': 10, 'application': 25, 'goal': 7}}
        """
        collection = self.chroma.get_collection("episodic_memory")
        all_data = collection.get(include=["metadatas"])
        
        # Count by type
        by_type: dict[str, int] = {}
        for metadata in all_data['metadatas']:
            event_type = metadata.get("type", "unknown")
            by_type[event_type] = by_type.get(event_type, 0) + 1
        
        return {
            "total": len(all_data['ids']),
            "by_type": by_type,
        }

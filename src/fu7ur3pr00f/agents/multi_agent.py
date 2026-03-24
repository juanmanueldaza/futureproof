"""Multi-agent wrapper for FutureProof career intelligence system.

This module provides a multi-agent alternative to the single career_agent.py.
It uses an orchestrator to route requests to specialist agents (Coach, Learning,
Jobs, Code, Founder) instead of a single monolithic agent.

Usage:
    from fu7ur3pr00f.agents.multi_agent import MultiAgentSystem
    
    system = MultiAgentSystem()
    await system.initialize()
    
    # Handle queries
    response = await system.handle("How can I get promoted?")
    print(response)
"""

import asyncio
import logging
from typing import Any

from fu7ur3pr00f.agents.specialists import OrchestratorAgent

logger = logging.getLogger(__name__)


class MultiAgentSystem:
    """Multi-agent system for career intelligence.
    
    Uses OrchestratorAgent to route requests to specialist agents:
    - CoachAgent: Career growth, leadership, promotions
    - LearningAgent: Skill development, expertise building
    - JobsAgent: Job search, market fit, salary insights
    - CodeAgent: GitHub, GitLab, open source strategy
    - FounderAgent: Startups, entrepreneurship, launch planning
    
    Example:
        >>> system = MultiAgentSystem()
        >>> await system.initialize()
        >>> response = await system.handle("How do I get promoted?")
        >>> print(response)
    """
    
    def __init__(self):
        """Initialize multi-agent system."""
        self.orchestrator: OrchestratorAgent | None = None
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize all specialist agents.
        
        Call this once before handling any requests.
        
        Example:
            >>> system = MultiAgentSystem()
            >>> await system.initialize()
            >>> # Now ready to handle requests
        """
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing multi-agent system...")
            
            # Create and initialize orchestrator
            self.orchestrator = OrchestratorAgent()
            await self.orchestrator.initialize()
            
            # Log available agents
            agents = self.orchestrator.get_available_agents()
            agent_names = [a["name"] for a in agents]
            logger.info(f"Initialized agents: {', '.join(agent_names)}")
            
            self._initialized = True
    
    async def handle(self, query: str, context: dict[str, Any] | None = None) -> str:
        """Handle a user query using the multi-agent system.
        
        Args:
            query: User's question or request
            context: Optional context dict (user_profile, conversation_history, etc.)
        
        Returns:
            Agent response string
        
        Example:
            >>> system = MultiAgentSystem()
            >>> await system.initialize()
            >>> response = await system.handle("How can I get promoted?")
        """
        if not self._initialized:
            await self.initialize()
        
        if context is None:
            context = {}
        
        context["query"] = query
        
        # Route through orchestrator
        response = await self.orchestrator.process(context)
        
        logger.debug(f"Query: {query[:50]}... → Response: {len(response)} chars")
        
        return response
    
    async def stream(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ):
        """Stream a response token-by-token.
        
        Currently yields the full response as a single chunk.
        Future: Stream token-by-token from specialist agents.
        
        Args:
            query: User's question
            context: Optional context dict
        
        Yields:
            Response chunks (currently single chunk)
        """
        response = await self.handle(query, context)
        yield {"content": response}
    
    async def stream_parallel(
        self,
        query: str,
        agent_names: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Stream responses from multiple agents in parallel.
        
        Yields responses as they become available from each agent.
        
        Args:
            query: User's question
            agent_names: List of agents to query (default: all)
            context: Optional context dict
        
        Yields:
            Dict with agent name and response
        
        Example:
            >>> async for response in system.stream_parallel(
            ...     "Career advice",
            ...     ["coach", "learning"]
            ... ):
            ...     print(f"{response['agent']}: {response['content'][:100]}")
        """
        if not self._initialized:
            await self.initialize()
        
        if context is None:
            context = {}
        context["query"] = query
        
        if agent_names is None:
            agent_names = list(self.orchestrator.specialists.keys())
        
        async def stream_agent(name):
            agent = self.orchestrator.specialists.get(name)
            if agent:
                response = await agent.process(context)
                return {"agent": name, "content": response}
            return {"agent": name, "content": ""}
        
        # Run agents in parallel and yield as they complete
        tasks = [asyncio.create_task(stream_agent(name)) for name in agent_names]
        for task in asyncio.as_completed(tasks):
            result = await task
            yield result
    
    def get_available_agents(self) -> list[dict[str, str]]:
        """Get list of available specialist agents.
        
        Returns:
            List of agent info dicts with name and description
        
        Example:
            >>> agents = system.get_available_agents()
            >>> for agent in agents:
            ...     print(f"{agent['name']}: {agent['description']}")
        """
        if not self._initialized:
            return []
        
        return self.orchestrator.get_available_agents()
    
    async def get_agent_info(self, agent_name: str) -> dict[str, Any] | None:
        """Get info about a specific agent.
        
        Args:
            agent_name: Agent name (e.g., "coach", "learning")
        
        Returns:
            Agent info dict or None if not found
        """
        if not self._initialized:
            return None
        
        agents = self.get_available_agents()
        for agent in agents:
            if agent["name"] == agent_name:
                return agent
        
        return None


# =============================================================================
# Convenience Functions
# =============================================================================

# Global multi-agent system instance
_multi_agent_system: MultiAgentSystem | None = None
_init_lock = asyncio.Lock()


async def get_multi_agent_system() -> MultiAgentSystem:
    """Get or create the global multi-agent system instance.
    
    Returns:
        Initialized MultiAgentSystem instance
    
    Example:
        >>> system = await get_multi_agent_system()
        >>> response = await system.handle("How can I get promoted?")
    """
    global _multi_agent_system
    
    async with _init_lock:
        if _multi_agent_system is None:
            _multi_agent_system = MultiAgentSystem()
            await _multi_agent_system.initialize()
        
        return _multi_agent_system


async def handle_query(query: str, context: dict[str, Any] | None = None) -> str:
    """Handle a query using the multi-agent system.
    
    Convenience function that gets/creates the global system and handles the query.
    
    Args:
        query: User's question
        context: Optional context dict
    
    Returns:
        Agent response
    
    Example:
        >>> response = await handle_query("How do I get promoted?")
        >>> print(response)
    """
    system = await get_multi_agent_system()
    return await system.handle(query, context)


async def list_agents() -> list[dict[str, str]]:
    """List all available specialist agents.
    
    Returns:
        List of agent info dicts
    
    Example:
        >>> agents = await list_agents()
        >>> len(agents)
        5
    """
    system = await get_multi_agent_system()
    return system.get_available_agents()

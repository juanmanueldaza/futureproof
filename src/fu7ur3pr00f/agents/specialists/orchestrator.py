"""Orchestrator Agent — Routes requests and synthesizes responses.

The main entry point for the multi-agent system. Receives all user queries,
routes to appropriate specialist agents, and synthesizes coherent responses.

Example:
    >>> orchestrator = OrchestratorAgent()
    >>> response = await orchestrator.handle("How can I get promoted?")
    >>> print(response)
    'Based on your CliftonStrengths...'
"""

import asyncio

from fu7ur3pr00f.agents.specialists.base import BaseAgent
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent
from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter


class OrchestratorAgent(BaseAgent):
    """Main orchestrator for multi-agent system.
    
    Responsibilities:
    - Receive all user queries
    - Classify intent and route to specialist
    - Execute specialist agents (parallel when possible)
    - Synthesize responses into coherent answer
    - Ensure values alignment
    
    Example:
        >>> orchestrator = OrchestratorAgent()
        >>> await orchestrator.initialize()
        >>> response = await orchestrator.handle("Should I start a company?")
    """
    
    @property
    def name(self) -> str:
        """Agent identifier."""
        return "orchestrator"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Routes requests and synthesizes multi-agent responses"
    
    # All specialist agents
    specialists: dict[str, BaseAgent] = {}
    
    # Intent routing keywords
    ROUTING_KEYWORDS = {
        "coach": {
            "promotion", "promoted", "leadership", "lead", "manager",
            "staff", "principal", "senior", "career growth", "career path",
            "influence", "office politics", "cliftonstrengths", "strengths",
            "coaching", "mentor", "mentoring",
        },
        "learning": {
            "learning", "study", "learn", "skills", "courses", "certification",
            "expert", "authority", "teaching", "mentoring", "conference",
            "talk", "blog", "write", "publish",
        },
        "jobs": {
            "jobs", "job", "hiring", "interview", "salary", "compensation", "benefits",
            "remote", "work from home", "job search", "apply", "resume", "cv",
        },
        "code": {
            "github", "gitlab", "repos", "repositories", "code", "commits",
            "open source", "oss", "contributions", "projects", "portfolio",
        },
        "founder": {
            "startup", "founder", "cofounder", "co-founder", "launch",
            "product", "entrepreneur", "mvp", "side project", "business idea",
            "company", "build", "launch",
        },
    }
    
    def can_handle(self, intent: str) -> bool:
        """Orchestrator can handle all intents (routes to specialists).
        
        Args:
            intent: User query string
        
        Returns:
            Always True (orchestrator handles everything)
        """
        return True
    
    async def process(self, context: dict) -> str:
        """Process request by routing to specialist and synthesizing.
        
        Args:
            context: Request context with query, user_profile, etc.
        
        Returns:
            Synthesized response from specialist agent(s)
        """
        query = context.get("query", "")
        
        # Route to appropriate specialist
        specialist_name = self._route_query(query)
        specialist = self.specialists.get(specialist_name)
        
        if not specialist:
            return self._handle_no_specialist(query)
        
        # Process with specialist
        response = await specialist.process(context)
        
        # Synthesize and apply values
        synthesized = self._synthesize_response(response, specialist_name, query)
        
        return synthesized
    
    async def process_parallel(
        self,
        context: dict,
        agent_names: list[str] | None = None,
    ) -> dict[str, str]:
        """Process request with multiple agents in parallel.
        
        Args:
            context: Request context
            agent_names: List of agent names to query (default: all)
        
        Returns:
            Dict mapping agent names to their responses
        
        Example:
            >>> results = await orchestrator.process_parallel(
            ...     {"query": "Career advice"},
            ...     ["coach", "learning"]
            ... )
            >>> print(results["coach"])
        """
        if agent_names is None:
            agent_names = list(self.specialists.keys())
        
        async def process_agent(name):
            agent = self.specialists.get(name)
            if agent:
                response = await agent.process(context)
                return name, response
            return name, ""
        
        # Run agents in parallel
        results = await asyncio.gather(*[
            process_agent(name) for name in agent_names
        ])
        
        return dict(results)
    
    async def initialize(self) -> None:
        """Initialize all specialist agents.
        
        Call this before handling any requests.
        
        Example:
            >>> orchestrator = OrchestratorAgent()
            >>> await orchestrator.initialize()
            >>> # Now ready to handle requests
        """
        # Initialize all specialist agents
        self.specialists["coach"] = CoachAgent()
        self.specialists["learning"] = LearningAgent()
        self.specialists["jobs"] = JobsAgent()
        self.specialists["code"] = CodeAgent()
        self.specialists["founder"] = FounderAgent()
    
    def _route_query(self, query: str) -> str:
        """Route query to appropriate specialist based on keywords.
        
        Args:
            query: User query string
        
        Returns:
            Specialist agent name
        
        Example:
            >>> orchestrator = OrchestratorAgent()
            >>> orchestrator._route_query("How do I get promoted?")
            'coach'
            >>> orchestrator._route_query("Find me a job")
            'jobs'
        """
        query_lower = query.lower()
        
        # Score each specialist
        scores: dict[str, int] = {}
        for specialist, keywords in self.ROUTING_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[specialist] = score
        
        # Return highest scoring specialist
        max_score = max(scores.values())
        if max_score == 0:
            return "coach"  # Default to coach for ambiguous queries

        # Find specialist with highest score
        best_score = 0
        best_specialist = "coach"
        for specialist, score in scores.items():
            if score > best_score:
                best_score = score
                best_specialist = specialist
        return best_specialist
    
    def _handle_no_specialist(self, query: str) -> str:
        """Handle query when no specialist is available.
        
        Args:
            query: User query
        
        Returns:
            Fallback response
        """
        return (
            "I'm still learning about that topic. Currently, I can help you with:\n\n"
            "- **Career growth** (promotions, leadership, CliftonStrengths)\n"
            "- **Learning** (skill development, becoming an expert)\n"
            "- **Job search** (finding opportunities, salary insights)\n"
            "- **Code/projects** (GitHub, GitLab, open source)\n"
            "- **Startups** (launching products, finding co-founders)\n\n"
            "Which would you like help with?"
        )
    
    def _synthesize_response(
        self,
        response: str,
        specialist_name: str,
        query: str,
    ) -> str:
        """Synthesize specialist response with orchestrator context.
        
        Args:
            response: Specialist agent's response
            specialist_name: Name of specialist that generated response
            query: Original user query
        
        Returns:
            Synthesized response
        """
        # For now, just apply values filter
        # In future, could combine multiple specialist responses
        
        filtered = apply_values_filter(
            response,
            context=ValuesContext(),
            include_values_reminder=False,
        )
        
        return filtered
    
    async def handle(self, query: str, context: dict | None = None) -> str:
        """Convenience method to handle a query.
        
        Args:
            query: User query string
            context: Optional context dict
        
        Returns:
            Agent response
        
        Example:
            >>> orchestrator = OrchestratorAgent()
            >>> await orchestrator.initialize()
            >>> response = await orchestrator.handle("How can I get promoted?")
        """
        if context is None:
            context = {}
        
        context["query"] = query
        
        return await self.process(context)
    
    def get_available_agents(self) -> list[dict[str, str]]:
        """Get list of available specialist agents.
        
        Returns:
            List of agent info dicts with name and description
        
        Example:
            >>> orchestrator = OrchestratorAgent()
            >>> await orchestrator.initialize()
            >>> agents = orchestrator.get_available_agents()
            >>> len(agents)
            1  # Coach agent in Phase 0
        """
        return [
            {"name": agent.name, "description": agent.description}
            for agent in self.specialists.values()
        ]


# Export for agent registry
__all__ = ["OrchestratorAgent"]

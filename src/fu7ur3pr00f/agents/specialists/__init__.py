"""Specialist agents for multi-agent FutureProof architecture.

This package contains all specialist agents that handle specific domains:
- Coach Agent: Career growth and leadership
- Learning Agent: Skill development and expertise
- Jobs Agent: Employment opportunities
- Code Agent: GitHub, GitLab, open source
- Founder Agent: Startups and entrepreneurship
- Orchestrator Agent: Routes requests and synthesizes responses

Example:
    >>> from fu7ur3pr00f.agents.specialists import OrchestratorAgent
    >>> orchestrator = OrchestratorAgent()
    >>> await orchestrator.initialize()
    >>> response = await orchestrator.handle("How can I get promoted?")
"""

from fu7ur3pr00f.agents.specialists.base import (
    BaseAgent,
    KnowledgeResult,
    MemoryResult,
)
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent
from fu7ur3pr00f.agents.specialists.orchestrator import OrchestratorAgent

__all__ = [
    # Base classes
    "BaseAgent",
    "KnowledgeResult",
    "MemoryResult",
    # Specialist agents
    "CoachAgent",
    "LearningAgent",
    "JobsAgent",
    "CodeAgent",
    "FounderAgent",
    "OrchestratorAgent",
]


def get_agent(name: str) -> BaseAgent:
    """Get a specialist agent by name.
    
    Args:
        name: Agent name (e.g., "coach", "orchestrator")
    
    Returns:
        Agent instance
    
    Raises:
        ValueError: If agent name is unknown
    
    Example:
        >>> agent = get_agent("coach")
        >>> isinstance(agent, CoachAgent)
        True
    """
    agents = {
        "coach": CoachAgent,
        "learning": LearningAgent,
        "jobs": JobsAgent,
        "code": CodeAgent,
        "founder": FounderAgent,
        "orchestrator": OrchestratorAgent,
    }
    
    if name not in agents:
        raise ValueError(
            f"Unknown agent: {name}. Available: {list(agents.keys())}"
        )
    
    return agents[name]()


def list_agents() -> list[dict[str, str]]:
    """List all available specialist agents.
    
    Returns:
        List of agent info dicts with name and description
    
    Example:
        >>> agents = list_agents()
        >>> len(agents)
        6
    """
    coach = CoachAgent()
    learning = LearningAgent()
    jobs = JobsAgent()
    code = CodeAgent()
    founder = FounderAgent()
    orchestrator = OrchestratorAgent()
    
    return [
        {"name": coach.name, "description": coach.description},
        {"name": learning.name, "description": learning.description},
        {"name": jobs.name, "description": jobs.description},
        {"name": code.name, "description": code.description},
        {"name": founder.name, "description": founder.description},
        {"name": orchestrator.name, "description": orchestrator.description},
    ]

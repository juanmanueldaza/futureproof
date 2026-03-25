"""Specialist agents for multi-agent FutureProof architecture.

Each specialist has a focused system prompt and calls the LLM directly.
The OrchestratorAgent routes queries by keyword matching.

Usage:
    >>> from fu7ur3pr00f.agents.specialists import OrchestratorAgent
    >>> orchestrator = OrchestratorAgent()
    >>> await orchestrator.initialize()
    >>> response = await orchestrator.handle("How can I get promoted?")
"""

from fu7ur3pr00f.agents.specialists.base import BaseAgent, KnowledgeResult, MemoryResult
from fu7ur3pr00f.agents.specialists.coach import CoachAgent
from fu7ur3pr00f.agents.specialists.code import CodeAgent
from fu7ur3pr00f.agents.specialists.founder import FounderAgent
from fu7ur3pr00f.agents.specialists.jobs import JobsAgent
from fu7ur3pr00f.agents.specialists.learning import LearningAgent
from fu7ur3pr00f.agents.specialists.orchestrator import OrchestratorAgent

__all__ = [
    "BaseAgent",
    "KnowledgeResult",
    "MemoryResult",
    "CoachAgent",
    "LearningAgent",
    "JobsAgent",
    "CodeAgent",
    "FounderAgent",
    "OrchestratorAgent",
]

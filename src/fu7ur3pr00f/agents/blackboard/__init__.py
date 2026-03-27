"""Blackboard pattern implementation for multi-specialist collaboration.

The blackboard is a shared data structure that specialists read from and write to.
It enables collaborative analysis where each specialist:
1. Reads findings from previous specialists
2. Analyzes the user's query in context of those findings
3. Writes its own findings to the blackboard
4. Passes to the next specialist

This eliminates redundancy and creates integrated advice through iterative refinement.

Key components:
- CareerBlackboard: Typed dict defining the shared state
- BlackboardScheduler: Decides which specialist runs next
- BlackboardExecutor: Orchestrates specialist contributions
- Specialist.contribute(): New method that takes blackboard instead of streaming
"""

from fu7ur3pr00f.agents.blackboard.blackboard import (
    CareerBlackboard,
    make_initial_blackboard,
)
from fu7ur3pr00f.agents.blackboard.conversation_graph import build_conversation_graph
from fu7ur3pr00f.agents.blackboard.engine import (
    ConversationEngine,
    TurnResult,
    get_conversation_engine,
)
from fu7ur3pr00f.agents.blackboard.executor import BlackboardExecutor
from fu7ur3pr00f.agents.blackboard.findings_schema import SpecialistFindingsModel
from fu7ur3pr00f.agents.blackboard.graph import build_blackboard_graph
from fu7ur3pr00f.agents.blackboard.scheduler import BlackboardScheduler
from fu7ur3pr00f.agents.blackboard.session import (
    ActiveGoal,
    ConversationTurn,
    SessionState,
    make_initial_session,
)
from fu7ur3pr00f.agents.blackboard.turn_classifier import classify

__all__ = [
    "CareerBlackboard",
    "BlackboardScheduler",
    "BlackboardExecutor",
    "SpecialistFindingsModel",
    "build_blackboard_graph",
    "make_initial_blackboard",
    "SessionState",
    "ConversationTurn",
    "ActiveGoal",
    "make_initial_session",
    "classify",
    "build_conversation_graph",
    "ConversationEngine",
    "TurnResult",
    "get_conversation_engine",
]

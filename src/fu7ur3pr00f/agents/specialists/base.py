"""Base class for specialist agents.

Each specialist contributes to the shared CareerBlackboard using its curated
tool subset. All queries run through the blackboard pattern — there is no
separate single-agent mode.

The base class handles:
- Multi-turn tool-calling loop during blackboard contribution
- Structured findings extraction via Pydantic
- Keyword-based intent routing
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from langgraph.errors import GraphInterrupt as _GraphInterrupt

from fu7ur3pr00f.agents.blackboard.blackboard import CareerBlackboard, SpecialistFinding
from fu7ur3pr00f.prompts import load_prompt
from fu7ur3pr00f.utils.security import sanitize_for_prompt

logger = logging.getLogger(__name__)

_CONTRIBUTE_INSTRUCTION = "\n\n" + load_prompt("specialist_contribute")


@dataclass
class KnowledgeResult:
    """A search result from the career knowledge base."""

    content: str
    metadata: dict[str, Any]
    score: float | None = None


@dataclass
class MemoryResult:
    """A recalled episodic memory."""

    content: str
    event_type: str
    timestamp: float | None = None
    score: float | None = None


class BaseAgent(ABC):
    """Abstract base for specialist agents.

    Subclasses must implement:
    - name           : str — agent identifier
    - description    : str — human-readable description
    - system_prompt  : str — specialist persona and instructions
    - tools          : list — curated subset of the career tools
    - KEYWORDS       : frozenset[str] — keywords for intent matching

    Subclasses inherit can_handle() which uses KEYWORDS.
    """

    # Subclasses override this with their own frozenset of keywords
    KEYWORDS: frozenset[str] = frozenset()

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier (e.g., 'coach')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Specialist persona and focused instructions."""
        ...

    @property
    @abstractmethod
    def tools(self) -> list:
        """Curated tool subset for this specialist."""
        ...

    def can_handle(self, intent: str) -> bool:
        """Keyword-based intent matching for routing."""
        return any(kw in intent.lower() for kw in self.KEYWORDS)

    # ── Blackboard pattern ───────────────────────────────────────────────

    def contribute(
        self,
        blackboard: CareerBlackboard,
        stream_writer: Any = None,
    ) -> SpecialistFinding:
        """Contribute analysis to the shared blackboard using real tools.

        Runs a multi-turn tool-calling loop:
        1. Reads query, user profile, and previous findings from blackboard
        2. Calls model with bound tools; executes tool calls iteratively
        3. Extracts structured findings from the final response

        Args:
            blackboard: Shared state with user profile, query, and previous findings
            stream_writer: Optional LangGraph stream writer for real-time events

        Returns:
            Dict of structured findings to record on the blackboard.
        """
        return self._contribute_via_agent(blackboard, stream_writer)

    def _contribute_via_agent(
        self,
        blackboard: CareerBlackboard,
        stream_writer: Any = None,
    ) -> SpecialistFinding:
        """Multi-turn tool-calling contribution loop.

        Binds tools to the model and iterates until the model produces a
        final text response (no more tool calls), up to MAX_TOOL_ROUNDS.
        """
        from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

        from fu7ur3pr00f.llm.fallback import get_model_with_fallback

        query = blackboard.get("query", "")

        system_content = self.system_prompt + _CONTRIBUTE_INSTRUCTION
        human_content = self._build_context(blackboard)

        messages: list[Any] = [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content),
        ]

        # Build tool name → tool function lookup
        tool_map = {t.name: t for t in self.tools}

        try:
            model, _ = get_model_with_fallback(purpose="agent")
            model_with_tools = model.bind_tools(self.tools)
        except Exception as e:
            logger.error("%s: failed to bind tools: %s", self.name, e)
            return {"reasoning": f"Setup error: {e}", "confidence": 0.0}

        MAX_TOOL_ROUNDS = 10
        MAX_TOTAL_TOOL_CALLS = 25

        tool_call_count = 0
        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                response = model_with_tools.invoke(messages)
            except Exception as e:
                logger.error(
                    "%s: LLM call failed (round %d): %s", self.name, round_num, e
                )
                break

            messages.append(response)

            # No tool calls → final text response
            if not getattr(response, "tool_calls", None):
                break

            # Check if adding more tool calls would exceed the cap
            if tool_call_count + len(response.tool_calls) > MAX_TOTAL_TOOL_CALLS:
                logger.warning(
                    "%s: tool call cap reached (%d/%d), stopping early",
                    self.name,
                    tool_call_count,
                    MAX_TOTAL_TOOL_CALLS,
                )
                break

            # Execute each tool call
            tool_call_count += len(response.tool_calls)
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("args", {})
                tool_id = tc["id"]

                if stream_writer:
                    stream_writer(
                        {
                            "type": "tool_start",
                            "specialist": self.name,
                            "tool": tool_name,
                            "args": tool_args,
                        }
                    )

                tool_fn = tool_map.get(tool_name)
                if tool_fn is None:
                    result_str = (
                        f"Tool {tool_name!r} not available to {self.name} specialist."
                    )
                    logger.warning("%s: tool not found: %s", self.name, tool_name)
                else:
                    try:
                        result = tool_fn.invoke(tool_args)
                        result_str = str(result)[:3000]
                    except _GraphInterrupt:
                        raise
                    except Exception as e:
                        result_str = f"Error running {tool_name}: {e}"
                        logger.warning(
                            "%s: tool error (%s): %s", self.name, tool_name, e
                        )

                if stream_writer:
                    stream_writer(
                        {
                            "type": "tool_result",
                            "specialist": self.name,
                            "tool": tool_name,
                            "result": result_str[:500],
                        }
                    )

                messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))

        return self._extract_findings({"messages": messages}, query)

    def _build_context(self, blackboard: CareerBlackboard) -> str:
        """Build the human message context from blackboard state."""
        query = blackboard.get("query", "")
        user_profile = blackboard.get("user_profile", {})
        previous_findings = blackboard.get("findings", {})

        # User profile section
        profile_parts = []
        if user_profile:
            for key, label in [
                ("name", "Name"),
                ("current_role", "Current role"),
                ("role", "Current role"),
                ("years_experience", "Years of experience"),
                ("technical_skills", "Technical skills"),
                ("goals", "Goals"),
                ("target_roles", "Target roles"),
            ]:
                val = user_profile.get(key)
                if val:
                    if isinstance(val, list):
                        val = ", ".join(sanitize_for_prompt(str(v)) for v in val[:10])
                    else:
                        val = sanitize_for_prompt(str(val))
                    profile_parts.append(f"{label}: {val}")

        profile_context = (
            "\n".join(profile_parts) if profile_parts else "No profile data available"
        )

        # Previous findings section
        context_msg = self._format_previous_findings(previous_findings)

        full_prompt = f"USER QUERY: {query}\n\nUser Profile:\n{profile_context}"

        # Append specialist guidance — fill placeholders with actual values
        from fu7ur3pr00f.prompts import load_prompt
        guidance = (
            load_prompt("specialist_guidance")
            .replace("{specialist_name}", self.name)
            .replace("{user_query}", sanitize_for_prompt(query))
        )
        full_prompt += f"\n\n{guidance}"
        if context_msg:
            full_prompt += f"\n\nContext from other specialists:\n{context_msg}"

        # Cross-turn context (from prior conversation turns)
        constraints = blackboard.get("constraints", [])
        prior_turns = [c for c in constraints if c.startswith("PRIOR_TURNS:")]
        if prior_turns:
            cross_turn_ctx = prior_turns[0][11:]  # Strip "PRIOR_TURNS:"
            full_prompt += f"\n\nContext from previous conversation:\n{cross_turn_ctx}"

        return full_prompt

    def _format_previous_findings(
        self, previous_findings: dict[str, SpecialistFinding]
    ) -> str:
        """Format findings from previous specialists for context (with truncation)."""
        context_parts = []

        if previous_findings:
            context_parts.append("Other specialists have found:")
            for specialist, finding in previous_findings.items():
                context_parts.append(f"\n{specialist.upper()}:")
                for key, value in finding.items():
                    if key not in ("confidence", "iteration_contributed"):
                        safe_value = sanitize_for_prompt(str(value))
                        context_parts.append(f"  - {key}: {safe_value}")

        context_msg = "\n".join(context_parts) if context_parts else ""
        return context_msg[:4000]

    def _extract_findings(
        self,
        agent_result: dict[str, Any],
        query: str,
    ) -> SpecialistFinding:
        """Extract structured findings from the tool-calling loop result.

        Finds the last AI message with text content, then uses structured
        output to extract typed findings from it.
        """
        from langchain_core.messages import AIMessage, HumanMessage

        from fu7ur3pr00f.agents.blackboard.findings_schema import (
            SpecialistFindingsModel,
        )
        from fu7ur3pr00f.llm.fallback import get_model_with_fallback

        messages = agent_result.get("messages", [])
        if not messages:
            return {"reasoning": "No output from agent", "confidence": 0.50}

        # Find last AI message with text content (skip tool-call-only messages)
        agent_text = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = getattr(msg, "content", "")
                if content and isinstance(content, str) and content.strip():
                    agent_text = content[:4000]
                    break

        if not agent_text:
            # Fall back to last message of any type
            last_msg = messages[-1]
            agent_text = str(getattr(last_msg, "content", str(last_msg)))[:4000]

        try:
            model, _ = get_model_with_fallback(purpose="analysis")
            extractor = model.with_structured_output(SpecialistFindingsModel)

            extraction_prompt = (
                f"Extract career findings from this specialist analysis.\n\n"
                f"Query: {query}\n\n"
                f"Specialist output:\n{agent_text}\n\n"
                f"IMPORTANT: Write the 'reasoning' field as a direct response to the user "
                f"in first person (e.g. 'Your current title is Senior Analyst'). "
                f"For factual questions: one direct sentence. "
                f"For analysis/strategy: comprehensive narrative. "
                f"Never write in third person (e.g. do NOT write "
                f"'The specialist identified...' or 'Based on the query...')."
            )

            result: SpecialistFindingsModel = extractor.invoke(  # type: ignore
                [HumanMessage(content=extraction_prompt)]
            )
            return result.model_dump(exclude_none=True)  # type: ignore

        except Exception as e:
            logger.warning(
                "%s._extract_findings structured extraction failed: %s",
                self.name,
                e,
            )
            return {
                "reasoning": sanitize_for_prompt(agent_text[:2000]),
                "confidence": 0.60,
            }

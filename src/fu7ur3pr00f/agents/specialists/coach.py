"""Coach Agent — Career growth and leadership coaching specialist.

Helps developers get promoted, develop leadership skills, and grow their careers
within organizations using CliftonStrengths-based coaching.

Example:
    >>> agent = CoachAgent()
    >>> context = {"query": "How can I get promoted to Staff Engineer?"}
    >>> response = await agent.process(context)
    >>> print(response)
    'Based on your CliftonStrengths (Activator #2, Ideation #5)...'
"""

from collections.abc import Callable

from fu7ur3pr00f.agents.specialists.base import BaseAgent, KnowledgeResult
from fu7ur3pr00f.agents.values import (
    ValuesContext,
    apply_values_filter,
)


class CoachAgent(BaseAgent):
    """Career growth and leadership coaching specialist.
    
    Focus areas:
    - Promotions (Senior → Staff → Principal)
    - Leadership development
    - Navigating office politics
    - Building influence
    - CliftonStrengths-based growth
    
    Example:
        >>> agent = CoachAgent()
        >>> agent.name
        'coach'
        >>> agent.description
        'Career growth and leadership coach'
        >>> agent.can_handle("I want to get promoted")
        True
    """
    
    # Tools available to this agent
    tools: list[Callable] = []  # Populated from existing tools
    
    @property
    def name(self) -> str:
        """Agent identifier."""
        return "coach"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Career growth and leadership coach"
    
    # Keywords for intent matching
    KEYWORDS = {
        "promotion",
        "promoted",
        "leadership",
        "lead",
        "manager",
        "staff",
        "principal",
        "senior",
        "career growth",
        "career path",
        "influence",
        "office politics",
        "cliftonstrengths",
        "strengths",
        "coaching",
        "mentor",
        "mentoring",
    }
    
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle career growth/leadership requests.
        
        Args:
            intent: User query string
        
        Returns:
            True if query relates to career growth, promotions, or leadership
            
        Example:
            >>> agent = CoachAgent()
            >>> agent.can_handle("How do I get promoted to Staff Engineer?")
            True
            >>> agent.can_handle("Find me remote Python jobs")
            False
            >>> agent.can_handle("I want to develop my leadership skills")
            True
        """
        intent_lower = intent.lower()
        return any(keyword in intent_lower for keyword in self.KEYWORDS)
    
    async def process(self, context: dict[str, str]) -> str:
        """Process career growth/leadership request.
        
        Args:
            context: Request context with:
                - query: User's question
                - user_profile: Current user profile data
                - conversation_history: Previous turns
        
        Returns:
            Career coaching response with actionable advice
            
        Example:
            >>> agent = CoachAgent()
            >>> context = {
            ...     "query": "How can I get promoted to Staff Engineer?",
            ...     "user_profile": {"current_role": "Senior Engineer"},
            ... }
            >>> response = await agent.process(context)
        """
        query = context.get("query", "")
        user_profile = context.get("user_profile", {})
        
        # Gather relevant context from knowledge base
        experience = self._get_experience(user_profile)
        strengths = self._get_strengths(user_profile)
        goals = self._get_goals(user_profile)
        
        # Analyze promotion readiness
        readiness = self._assess_promotion_readiness(experience, strengths, goals)
        
        # Create development plan
        plan = self._create_development_plan(readiness, goals)
        
        # Build response
        response = self._build_response(query, experience, strengths, readiness, plan)
        
        # Apply values filter
        filtered_response = apply_values_filter(
            response,
            context=ValuesContext(
                has_work_life_balance=True,  # We promote work-life harmony
                fair_compensation=True,  # We advocate for fair pay
            ),
            include_values_reminder=False,
        )
        
        return filtered_response
    
    def _get_experience(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's work experience from knowledge base.
        
        Args:
            user_profile: User profile data
        
        Returns:
            List of experience entries
        """
        results = self.search_knowledge(
            query="work experience positions roles",
            limit=10,
            section="Experience",
        )
        return results
    
    def _get_strengths(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's CliftonStrengths from knowledge base.
        
        Args:
            user_profile: User profile data
        
        Returns:
            List of strengths entries
        """
        results = self.search_knowledge(
            query="CliftonStrengths strengths themes talents",
            limit=10,
            section="CliftonStrengths",
        )
        
        # Also check assessment section
        if not results:
            results = self.search_knowledge(
                query="strengths top 5 top 10 all 34",
                limit=10,
                sources=["assessment"],
            )
        
        return results
    
    def _get_goals(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's career goals from knowledge base.
        
        Args:
            user_profile: User profile data
        
        Returns:
            List of goal entries
        """
        results = self.search_knowledge(
            query="career goals target role aspirations",
            limit=5,
        )
        
        # Also check episodic memory for goals
        if not results:
            memories = self.recall_memories(
                query="career goals",
                event_type="goal",
                limit=5,
            )
            results = [
                KnowledgeResult(content=m.content, metadata={"type": m.event_type})
                for m in memories
            ]
        
        return results
    
    def _assess_promotion_readiness(
        self,
        experience: list[KnowledgeResult],
        strengths: list[KnowledgeResult],
        goals: list[KnowledgeResult],
    ) -> dict:
        """Assess user's readiness for promotion.
        
        Args:
            experience: User's work experience
            strengths: User's CliftonStrengths
            goals: User's career goals
        
        Returns:
            Readiness assessment with scores and gaps
        """
        # Calculate years of experience
        years = self._calculate_years_experience(experience)
        
        # Identify leadership themes in strengths
        leadership_themes = self._identify_leadership_themes(strengths)
        
        # Assess against typical promotion criteria
        readiness = {
            "years_experience": years,
            "years_ready": years >= 5,  # Typical for Senior → Staff
            "leadership_themes": leadership_themes,
            "themes_ready": len(leadership_themes) >= 3,
            "impact_examples": self._count_impact_examples(experience),
            "impact_ready": self._count_impact_examples(experience) >= 3,
            "goals_aligned": self._goals_aligned_with_promotion(goals),
        }
        
        # Overall readiness score
        readiness["score"] = sum([
            readiness["years_ready"],
            readiness["themes_ready"],
            readiness["impact_ready"],
            readiness["goals_aligned"],
        ]) / 4 * 100
        
        return readiness
    
    def _calculate_years_experience(self, experience: list[KnowledgeResult]) -> int:
        """Calculate total years of experience.
        
        Args:
            experience: List of experience entries
        
        Returns:
            Total years of experience
        """
        # Simple heuristic: count experience entries * 2 years average
        # In production, would parse actual dates
        return max(len(experience) * 2, 0)
    
    def _identify_leadership_themes(self, strengths: list[KnowledgeResult]) -> list[str]:
        """Identify leadership-related CliftonStrengths themes.
        
        Args:
            strengths: List of strength entries
        
        Returns:
            List of leadership themes present in user's strengths
        
        Leadership themes include:
        - Influencing: Activator, Command, Communication, Competition, Maximizer,
          Self-Assurance, Significance, Woo
        - Relationship Building: Developer, Empathy, Harmony, Includer, Positivity, Relator
        - Strategic Thinking: Ideation, Input, Intellection, Strategic
        """
        leadership_themes = {
            "activator", "command", "communication", "competition",
            "maximizer", "self-assurance", "significance", "woo",
            "developer", "empathy", "harmony", "includer", "positivity", "relator",
            "ideation", "input", "intellection", "strategic",
        }
        
        found_themes = []
        for strength in strengths:
            content_lower = strength.content.lower()
            for theme in leadership_themes:
                if theme in content_lower:
                    found_themes.append(theme.title())
        
        return found_themes
    
    def _count_impact_examples(self, experience: list[KnowledgeResult]) -> int:
        """Count impact/metric examples in experience.
        
        Args:
            experience: List of experience entries
        
        Returns:
            Number of impact examples (metrics, percentages, etc.)
        """
        impact_keywords = {
            "improved", "increased", "decreased", "reduced",
            "%", "percent", "x", "led", "architected", "designed",
            "mentored", "coached", "managed", "directed",
        }
        
        count = 0
        for exp in experience:
            content_lower = exp.content.lower()
            if any(kw in content_lower for kw in impact_keywords):
                count += 1
        
        return count
    
    def _goals_aligned_with_promotion(self, goals: list[KnowledgeResult]) -> bool:
        """Check if user's goals align with promotion.
        
        Args:
            goals: List of goal entries
        
        Returns:
            True if goals mention promotion, leadership, or growth
        """
        promotion_keywords = {
            "staff", "principal", "lead", "manager", "director",
            "promot", "growth", "leadership", "senior",
        }
        
        for goal in goals:
            content_lower = goal.content.lower()
            if any(kw in content_lower for kw in promotion_keywords):
                return True
        
        return False
    
    def _create_development_plan(
        self,
        readiness: dict,
        goals: list[KnowledgeResult],
    ) -> dict:
        """Create personalized development plan.
        
        Args:
            readiness: Readiness assessment
            goals: User's career goals
        
        Returns:
            Development plan with actions and timeline
        """
        plan = {
            "actions": [],
            "timeline_months": 6,
            "focus_areas": [],
        }
        
        # Identify gaps
        if not readiness["years_ready"]:
            plan["focus_areas"].append("Gain more experience")
            plan["actions"].append({
                "action": "Document impact and achievements",
                "timeline": "Ongoing",
                "priority": "High",
            })
        
        if not readiness["themes_ready"]:
            plan["focus_areas"].append("Develop leadership strengths")
            plan["actions"].append({
                "action": "Take on mentorship responsibilities",
                "timeline": "1-3 months",
                "priority": "High",
            })
            plan["actions"].append({
                "action": "Lead a cross-team initiative",
                "timeline": "3-6 months",
                "priority": "Medium",
            })
        
        if not readiness["impact_ready"]:
            plan["focus_areas"].append("Increase visible impact")
            plan["actions"].append({
                "action": "Quantify your achievements with metrics",
                "timeline": "1 month",
                "priority": "High",
            })
            plan["actions"].append({
                "action": "Share work through talks, blogs, or documentation",
                "timeline": "2-4 months",
                "priority": "Medium",
            })
        
        if not readiness["goals_aligned"]:
            plan["focus_areas"].append("Clarify career goals")
            plan["actions"].append({
                "action": "Discuss career path with manager",
                "timeline": "1 month",
                "priority": "High",
            })
        
        return plan
    
    def _build_response(
        self,
        query: str,
        experience: list[KnowledgeResult],
        strengths: list[KnowledgeResult],
        readiness: dict,
        plan: dict,
    ) -> str:
        """Build coaching response.
        
        Args:
            query: Original user query
            experience: User's experience
            strengths: User's strengths
            readiness: Readiness assessment
            plan: Development plan
        
        Returns:
            Formatted coaching response
        """
        lines = []
        
        # Opening
        lines.append("## Career Growth Analysis\n")
        
        # Strengths summary
        if strengths:
            lines.append("### Your Strengths")
            count = len(strengths)
            lines.append(f"Based on your CliftonStrengths, you have {count} themes.\n")
            
            leadership = self._identify_leadership_themes(strengths)
            if leadership:
                lines.append(f"**Leadership themes:** {', '.join(leadership)}\n")
        
        # Readiness assessment
        lines.append("### Promotion Readiness")
        lines.append(f"Overall readiness score: **{readiness['score']:.0f}%**\n")
        
        lines.append("**Strengths:**")
        if readiness["years_ready"]:
            lines.append("✅ Years of experience")
        else:
            lines.append("⏳ More time needed (typical timeline: 5+ years)")
        
        if readiness["themes_ready"]:
            lines.append("✅ Leadership strengths identified")
        else:
            lines.append("⏳ Develop more leadership themes")
        
        if readiness["impact_ready"]:
            lines.append("✅ Strong impact examples")
        else:
            lines.append("⏳ Document more measurable impact")
        
        if readiness["goals_aligned"]:
            lines.append("✅ Goals aligned with promotion\n")
        else:
            lines.append("⏳ Clarify promotion goals\n")
        
        # Development plan
        lines.append("### Development Plan\n")
        
        if plan["focus_areas"]:
            lines.append(f"**Focus areas:** {', '.join(plan['focus_areas'])}\n")
        
        lines.append("**Actions:**")
        for action in plan["actions"]:
            action_text = f"- {action['action']} ({action['timeline']}"
            lines.append(f"{action_text}, {action['priority']} priority)")
        
        # Closing encouragement
        lines.append("\n### Next Steps")
        lines.append("1. Review this plan with your manager")
        lines.append("2. Pick 1-2 high-priority actions to start")
        lines.append("3. Track your progress and celebrate wins")
        lines.append("\nRemember: Leadership is service. Use strengths to help others succeed.")
        
        return "\n".join(lines)


# Export for agent registry
__all__ = ["CoachAgent"]

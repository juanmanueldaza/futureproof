"""Learning Agent — Technical skill development and expertise building.

Helps developers become recognized experts through skill gap analysis,
learning roadmaps, tech trends, and authority building strategies.

Example:
    >>> agent = LearningAgent()
    >>> response = await agent.process({"query": "How do I become an expert in Python?"})
"""

from collections.abc import Callable

from fu7ur3pr00f.agents.specialists.base import BaseAgent, KnowledgeResult
from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter


class LearningAgent(BaseAgent):
    """Technical skill development and expertise building specialist.
    
    Focus areas:
    - Skill gap analysis
    - Learning roadmaps
    - Tech trends analysis
    - Building authority (talks, blogs, courses)
    - Becoming "the go-to person" for X
    
    Example:
        >>> agent = LearningAgent()
        >>> agent.name
        'learning'
    """
    
    @property
    def name(self) -> str:
        """Agent identifier."""
        return "learning"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Technical skill development and expertise building"
    
    # Tools available to this agent
    tools: list[Callable] = []
    
    # Keywords for intent matching
    KEYWORDS = {
        "learning", "study", "learn", "skills", "courses", "certification",
        "expert", "authority", "teaching", "mentoring", "conference",
        "talk", "blog", "write", "publish", "roadmap", "curriculum",
        "training", "workshop", "bootcamp", "degree", "master", "phd",
    }
    
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle learning/skill development requests."""
        intent_lower = intent.lower()
        return any(keyword in intent_lower for keyword in self.KEYWORDS)
    
    async def process(self, context: dict) -> str:
        """Process learning/skill development request."""
        query = context.get("query", "")
        user_profile = context.get("user_profile", {})
        
        # Gather context
        current_skills = self._get_current_skills(user_profile)
        target_role = self._get_target_role(user_profile)
        
        # Analyze skill gaps
        gaps = self._analyze_skill_gaps(current_skills, target_role)
        
        # Get tech trends
        trends = self._get_tech_trends(target_role)
        
        # Create learning roadmap
        roadmap = self._create_learning_roadmap(gaps, trends)
        
        # Build response
        response = self._build_response(query, current_skills, gaps, trends, roadmap)
        
        # Apply values filter
        filtered = apply_values_filter(
            response,
            context=ValuesContext(
                company_contributes_to_oss=True,  # We promote OSS learning
                has_work_life_balance=True,  # Sustainable learning pace
            ),
            include_values_reminder=False,
        )
        
        return filtered
    
    def _get_current_skills(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's current skills from knowledge base."""
        results = self.search_knowledge(
            query="skills technical skills programming languages",
            limit=10,
            section="Skills",
        )
        
        if not results:
            # Try GitHub languages
            results = self.search_knowledge(
                query="GitHub languages repositories",
                limit=10,
                sources=["github"],
            )
        
        return results
    
    def _get_target_role(self, user_profile: dict) -> str:
        """Get user's target role from profile."""
        # Check profile first
        if "target_role" in user_profile:
            return user_profile["target_role"]
        
        # Search knowledge base
        results = self.search_knowledge(
            query="target role career goal aspiration",
            limit=1,
        )
        
        if results:
            return results[0].content[:100]  # First 100 chars
        
        return "Senior Engineer"  # Default
    
    def _analyze_skill_gaps(
        self,
        current_skills: list[KnowledgeResult],
        target_role: str,
    ) -> dict:
        """Analyze gaps between current skills and target role."""
        # Define typical skills for target roles
        role_skills = {
            "staff engineer": {
                "technical": ["system design", "architecture", "scalability"],
                "leadership": ["mentoring", "technical strategy", "cross-team collaboration"],
                "impact": ["technical vision", "organizational impact"],
            },
            "principal engineer": {
                "technical": ["distributed systems", "architecture", "performance"],
                "leadership": ["technical leadership", "mentorship", "strategy"],
                "impact": ["company-wide impact", "industry recognition"],
            },
            "senior engineer": {
                "technical": ["advanced programming", "system design", "debugging"],
                "leadership": ["mentoring juniors", "code review"],
                "impact": ["team impact", "project ownership"],
            },
        }
        
        # Get required skills for target role
        target_lower = target_role.lower()
        required = role_skills.get("staff engineer", role_skills["senior engineer"])
        for role, skills in role_skills.items():
            if role in target_lower:
                required = skills
                break
        
        # Get current skill names
        current_skill_names = set()
        for skill in current_skills:
            current_skill_names.add(skill.content.lower())
        
        # Find gaps
        gaps = {
            "technical": [],
            "leadership": [],
            "impact": [],
        }
        
        for category, skills in required.items():
            for skill in skills:
                if not any(skill in current for current in current_skill_names):
                    gaps[category].append(skill)
        
        return gaps
    
    def _get_tech_trends(self, target_role: str) -> list[str]:
        """Get current tech trends for target role."""
        # Search knowledge base for trends
        results = self.search_knowledge(
            query="tech trends technology trends emerging",
            limit=5,
        )
        
        trends = []
        for result in results:
            trends.append(result.content[:100])
        
        # Default trends if none found
        if not trends:
            trends = [
                "AI/ML integration",
                "Cloud-native architectures",
                "Platform engineering",
                "Developer experience tools",
            ]
        
        return trends
    
    def _create_learning_roadmap(self, gaps: dict, trends: list[str]) -> dict:
        """Create personalized learning roadmap."""
        roadmap = {
            "immediate": [],  # 0-3 months
            "short_term": [],  # 3-6 months
            "medium_term": [],  # 6-12 months
            "long_term": [],  # 12+ months
        }
        
        # Immediate: Pick 1-2 high-impact technical gaps
        if gaps["technical"]:
            roadmap["immediate"] = [
                {"skill": gaps["technical"][0], "action": "Build project", "months": 2},
            ]
            if len(gaps["technical"]) > 1:
                roadmap["short_term"].append(
                    {"skill": gaps["technical"][1], "action": "Take a course", "months": 4}
                )
        
        # Short-term: Leadership skills
        if gaps["leadership"]:
            roadmap["short_term"].append(
                {"skill": gaps["leadership"][0], "action": "Mentor a junior developer", "months": 5}
            )
        
        # Medium-term: Impact skills
        if gaps["impact"]:
            roadmap["medium_term"].append(
                {"skill": gaps["impact"][0], "action": "Lead a cross-team initiative", "months": 9}
            )
        
        # Long-term: Authority building
        roadmap["long_term"] = [
            {"skill": "Industry recognition", "action": "Speak at a conference", "months": 12},
            {"skill": "Thought leadership", "action": "Write technical blog posts", "months": 15},
        ]
        
        return roadmap
    
    def _build_response(
        self,
        query: str,
        current_skills: list[KnowledgeResult],
        gaps: dict,
        trends: list[str],
        roadmap: dict,
    ) -> str:
        """Build learning response."""
        lines = []
        
        lines.append("## Learning & Expertise Development\n")
        
        # Current skills summary
        lines.append("### Your Current Skills")
        if current_skills:
            lines.append(f"Identified {len(current_skills)} skill areas.\n")
        else:
            lines.append("No skills data found. Consider gathering from GitHub/LinkedIn.\n")
        
        # Skill gaps
        lines.append("### Skill Gaps Analysis\n")
        
        if gaps["technical"]:
            lines.append("**Technical gaps:**")
            for skill in gaps["technical"]:
                lines.append(f"- {skill}")
        
        if gaps["leadership"]:
            lines.append("\n**Leadership gaps:**")
            for skill in gaps["leadership"]:
                lines.append(f"- {skill}")
        
        if gaps["impact"]:
            lines.append("\n**Impact gaps:**")
            for skill in gaps["impact"]:
                lines.append(f"- {skill}")
        
        if not any(gaps.values()):
            lines.append("Great! Your skills align well with your target role.\n")
        
        # Tech trends
        lines.append("\n### Current Tech Trends")
        for trend in trends:
            lines.append(f"- {trend}")
        
        # Learning roadmap
        lines.append("\n### Learning Roadmap\n")
        
        lines.append("**Immediate (0-3 months):**")
        for item in roadmap["immediate"]:
            lines.append(f"- Learn {item['skill']}: {item['action']}")
        
        lines.append("\n**Short-term (3-6 months):**")
        for item in roadmap["short_term"]:
            lines.append(f"- Learn {item['skill']}: {item['action']}")
        
        lines.append("\n**Medium-term (6-12 months):**")
        for item in roadmap["medium_term"]:
            lines.append(f"- Learn {item['skill']}: {item['action']}")
        
        lines.append("\n**Long-term (12+ months):**")
        for item in roadmap["long_term"]:
            lines.append(f"- {item['skill']}: {item['action']}")
        
        # Closing
        lines.append("\n### Tips for Effective Learning")
        lines.append("1. **Build projects** — Learning by doing is most effective")
        lines.append("2. **Teach others** — Writing/speaking reinforces your knowledge")
        lines.append("3. **Contribute to OSS** — Real-world experience + visibility")
        lines.append("4. **Find mentors** — Learn from those ahead of you")
        lines.append("\nRemember: Knowledge should be free. Share what you learn!")
        
        return "\n".join(lines)


__all__ = ["LearningAgent"]

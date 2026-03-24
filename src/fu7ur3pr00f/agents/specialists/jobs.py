"""Jobs Agent — Employment opportunities and job search specialist.

Helps developers find better employment opportunities across 7 job boards,
analyze market fit, get salary insights, and find remote work.

Example:
    >>> agent = JobsAgent()
    >>> response = await agent.process({"query": "Find remote Python jobs"})
"""

from collections.abc import Callable

from fu7ur3pr00f.agents.specialists.base import BaseAgent, KnowledgeResult
from fu7ur3pr00f.agents.values import (
    ValuesContext,
    apply_values_filter,
)


class JobsAgent(BaseAgent):
    """Employment opportunities and job search specialist.
    
    Focus areas:
    - Job search across 7 boards + Hacker News
    - Market fit analysis
    - Salary insights
    - Interview prep
    - Remote opportunities
    
    Example:
        >>> agent = JobsAgent()
        >>> agent.name
        'jobs'
    """
    
    @property
    def name(self) -> str:
        """Agent identifier."""
        return "jobs"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Employment opportunities and job search"
    
    # Tools available to this agent
    tools: list[Callable] = []
    
    # Keywords for intent matching
    KEYWORDS = {
        "jobs", "hiring", "interview", "salary", "compensation", "benefits",
        "remote", "work from home", "job search", "apply", "resume", "cv",
        "job boards", "linkedin", "indeed", "glassdoor", "offer",
    }
    
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle job search requests."""
        intent_lower = intent.lower()
        return any(keyword in intent_lower for keyword in self.KEYWORDS)
    
    async def process(self, context: dict) -> str:
        """Process job search request."""
        query = context.get("query", "")
        user_profile = context.get("user_profile", {})
        
        # Gather context
        skills = self._get_skills(user_profile)
        experience = self._get_experience(user_profile)
        preferences = self._get_preferences(user_profile)
        
        # Search jobs
        jobs = self._search_jobs(query, skills, preferences)
        
        # Analyze market fit
        market_fit = self._analyze_market_fit(skills, experience)
        
        # Get salary insights
        salary = self._get_salary_insights(skills, preferences)
        
        # Build response
        response = self._build_response(query, jobs, market_fit, salary, preferences)
        
        # Apply values filter
        filtered = apply_values_filter(
            response,
            context=ValuesContext(
                has_work_life_balance=True,
                is_remote_friendly=preferences.get("remote", False),
                fair_compensation=True,
            ),
            include_values_reminder=False,
        )
        
        return filtered
    
    def _get_skills(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's skills from knowledge base."""
        results = self.search_knowledge(
            query="skills technical skills programming",
            limit=10,
            section="Skills",
        )
        return results
    
    def _get_experience(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's work experience."""
        results = self.search_knowledge(
            query="work experience positions roles",
            limit=10,
            section="Experience",
        )
        return results
    
    def _get_preferences(self, user_profile: dict) -> dict:
        """Get user's job preferences."""
        preferences = {
            "remote": False,
            "location": None,
            "min_salary": None,
            "role_type": None,
        }
        
        # Search knowledge base for preferences
        results = self.search_knowledge(
            query="job preferences remote location salary",
            limit=5,
        )
        
        for result in results:
            content_lower = result.content.lower()
            if "remote" in content_lower:
                preferences["remote"] = True
            if "location" in content_lower:
                preferences["location"] = result.content[:50]
        
        return preferences
    
    def _search_jobs(
        self,
        query: str,
        skills: list[KnowledgeResult],
        preferences: dict,
    ) -> list[dict]:
        """Search for jobs matching criteria."""
        # In production, this would call actual job search tools
        # For now, return mock results
        
        jobs = []
        
        # Mock job results
        if preferences.get("remote"):
            jobs.extend([
                {
                    "title": "Senior Python Developer",
                    "company": "TechCorp (Remote)",
                    "salary": "$150k - $200k",
                    "match": 85,
                    "values_aligned": True,
                },
                {
                    "title": "Staff Engineer",
                    "company": "OpenSource Inc (Remote)",
                    "salary": "$180k - $240k",
                    "match": 90,
                    "values_aligned": True,
                },
            ])
        
        return jobs
    
    def _analyze_market_fit(
        self,
        skills: list[KnowledgeResult],
        experience: list[KnowledgeResult],
    ) -> dict:
        """Analyze user's market fit."""
        fit = {
            "score": 75,  # Default
            "in_demand_skills": [],
            "gaps": [],
            "recommendations": [],
        }
        
        # Analyze skills against market demand
        in_demand = {"python", "aws", "kubernetes", "react", "typescript", "rust"}
        
        for skill in skills:
            skill_lower = skill.content.lower()
            for demand in in_demand:
                if demand in skill_lower:
                    fit["in_demand_skills"].append(demand.title())
        
        fit["score"] = 50 + (len(fit["in_demand_skills"]) * 10)
        fit["score"] = min(fit["score"], 95)
        
        return fit
    
    def _get_salary_insights(
        self,
        skills: list[KnowledgeResult],
        preferences: dict,
    ) -> dict:
        """Get salary insights for user's profile."""
        insights = {
            "range": "$120k - $200k",
            "factors": [],
            "negotiation_tips": [],
        }
        
        # Adjust based on skills
        skill_count = len(skills)
        if skill_count > 10:
            insights["range"] = "$150k - $250k"
            insights["factors"].append("Strong skill set")
        
        if preferences.get("remote"):
            insights["factors"].append("Remote positions may have geographic adjustments")
        
        insights["negotiation_tips"] = [
            "Research market rates for your level",
            "Highlight impact and achievements",
            "Get multiple offers for leverage",
            "Consider total compensation (equity, benefits)",
        ]
        
        return insights
    
    def _build_response(
        self,
        query: str,
        jobs: list[dict],
        market_fit: dict,
        salary: dict,
        preferences: dict,
    ) -> str:
        """Build job search response."""
        lines = []
        
        lines.append("## Job Search Results\n")
        
        # Job listings
        if jobs:
            lines.append("### Matching Opportunities\n")
            for job in jobs:
                lines.append(f"**{job['title']}** at {job['company']}")
                lines.append(f"- Salary: {job['salary']}")
                lines.append(f"- Match: {job['match']}%")
                if job.get('values_aligned'):
                    lines.append("- ✅ Values-aligned company\n")
                else:
                    lines.append("- ⚠️ Research company values\n")
        else:
            lines.append("### No specific jobs found\n")
            lines.append("Try refining your search with specific skills or roles.\n")
        
        # Market fit
        lines.append("### Market Fit Analysis")
        lines.append(f"**Fit score:** {market_fit['score']}/100\n")
        
        if market_fit['in_demand_skills']:
            lines.append("**In-demand skills you have:**")
            for skill in market_fit['in_demand_skills']:
                lines.append(f"- {skill}")
        
        # Salary insights
        lines.append("\n### Salary Insights")
        lines.append(f"**Estimated range:** {salary['range']}\n")
        
        if salary['factors']:
            lines.append("**Factors:**")
            for factor in salary['factors']:
                lines.append(f"- {factor}")
        
        lines.append("\n**Negotiation tips:**")
        for tip in salary['negotiation_tips']:
            lines.append(f"- {tip}")
        
        # Job search tips
        lines.append("\n### Job Search Tips")
        lines.append("1. **Target values-aligned companies** — You'll be happier")
        lines.append("2. **Get multiple offers** — Increases negotiating power")
        lines.append("3. **Research thoroughly** — Glassdoor, Blind, network")
        lines.append("4. **Prepare stories** — STAR method for interviews")
        lines.append("5. **Consider total comp** — Salary + equity + benefits + work-life\n")
        
        # Closing
        lines.append("### Remember")
        lines.append("> Work for companies that align with your values.")
        lines.append("> Your code will outlive your employment. Choose wisely.")
        lines.append("> Remote work is freedom. Prioritize flexibility.")
        
        return "\n".join(lines)


__all__ = ["JobsAgent"]

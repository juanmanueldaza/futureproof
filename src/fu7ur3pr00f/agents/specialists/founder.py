"""Founder Agent — Entrepreneurial opportunities and startup guidance.

Helps developers identify entrepreneurial opportunities, assess founder fit,
find co-founders, and create launch roadmaps for products and companies.

Example:
    >>> agent = FounderAgent()
    >>> response = await agent.process({"query": "Should I start a company?"})
"""

from collections.abc import Callable

from fu7ur3pr00f.agents.specialists.base import BaseAgent, KnowledgeResult
from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter


class FounderAgent(BaseAgent):
    """Entrepreneurial opportunities and startup guidance specialist.
    
    Focus areas:
    - Opportunity identification
    - Founder fit analysis
    - Partnership/co-founder matching
    - Launch planning
    - Go/no-go recommendations
    
    Example:
        >>> agent = FounderAgent()
        >>> agent.name
        'founder'
    """
    
    @property
    def name(self) -> str:
        """Agent identifier."""
        return "founder"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Entrepreneurial opportunities and startup guidance"
    
    # Tools available to this agent
    tools: list[Callable] = []
    
    # Keywords for intent matching
    KEYWORDS = {
        "startup", "founder", "cofounder", "co-founder", "launch",
        "product", "entrepreneur", "mvp", "side project", "business idea",
        "company", "build", "launch", "venture", "seed", "funding",
    }
    
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle entrepreneurial requests."""
        intent_lower = intent.lower()
        return any(keyword in intent_lower for keyword in self.KEYWORDS)
    
    async def process(self, context: dict) -> str:
        """Process entrepreneurial/startup request."""
        query = context.get("query", "")
        user_profile = context.get("user_profile", {})
        
        # Gather context
        projects = self._get_projects(user_profile)
        strengths = self._get_strengths(user_profile)
        network = self._get_network(user_profile)
        
        # Identify opportunities
        opportunities = self._identify_opportunities(projects, strengths)
        
        # Assess founder fit
        founder_fit = self._assess_founder_fit(strengths, projects)
        
        # Find potential co-founders
        cofounders = self._find_potential_cofounders(network, strengths)
        
        # Create launch roadmap
        roadmap = self._create_launch_roadmap(opportunities, founder_fit)
        
        # Build response
        response = self._build_response(
            query, opportunities, founder_fit, cofounders, roadmap
        )
        
        # Apply values filter
        filtered = apply_values_filter(
            response,
            context=ValuesContext(
                product_respects_freedom=True,  # Promote ethical products
                work_is_ethical=True,
            ),
            include_values_reminder=False,
        )
        
        return filtered
    
    def _get_projects(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's projects from knowledge base."""
        results = self.search_knowledge(
            query="projects side projects portfolio github gitlab",
            limit=10,
        )
        
        # Also search GitHub/GitLab sources
        github = self.search_knowledge(
            query="repositories projects",
            limit=5,
            sources=["github"],
        )
        
        gitlab = self.search_knowledge(
            query="projects repositories",
            limit=5,
            sources=["gitlab"],
        )
        
        return results + github + gitlab
    
    def _get_strengths(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's CliftonStrengths."""
        results = self.search_knowledge(
            query="CliftonStrengths strengths themes",
            limit=10,
            sources=["assessment"],
        )
        return results
    
    def _get_network(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's network connections."""
        results = self.search_knowledge(
            query="connections network colleagues collaborators",
            limit=10,
            section="Connections",
            include_social=True,
        )
        return results
    
    def _identify_opportunities(
        self,
        projects: list[KnowledgeResult],
        strengths: list[KnowledgeResult],
    ) -> list[dict]:
        """Identify product opportunities based on projects and strengths."""
        opportunities = []
        
        # Analyze projects for traction signals
        for project in projects:
            content_lower = project.content.lower()
            
            # Look for traction signals
            has_users = "users" in content_lower or "using" in content_lower
            has_growth = "growth" in content_lower or "growing" in content_lower
            has_problem = "problem" in content_lower or "solve" in content_lower
            
            if has_problem:
                opportunities.append({
                    "type": "Existing project",
                    "description": project.content[:150],
                    "signals": {
                        "solves_problem": has_problem,
                        "has_users": has_users,
                        "growing": has_growth,
                    },
                    "recommendation": "Consider launching" if has_users else "Validate first",
                })
        
        # If no projects, suggest idea validation
        if not opportunities:
            opportunities.append({
                "type": "New opportunity",
                "description": "Look for problems in your daily work",
                "signals": {"solves_problem": True},
                "recommendation": "Start by identifying problems you face",
            })
        
        return opportunities
    
    def _assess_founder_fit(
        self,
        strengths: list[KnowledgeResult],
        projects: list[KnowledgeResult],
    ) -> dict:
        """Assess user's founder fit based on strengths and experience."""
        fit = {
            "score": 50,  # Default
            "entrepreneurial_themes": [],
            "strengths": [],
            "gaps": [],
            "recommendations": [],
        }
        
        # Entrepreneurial CliftonStrengths themes
        entrepreneurial_themes = {
            "activator": "Takes action, starts projects",
            "ideation": "Generates ideas, sees patterns",
            "self-assurance": "Confident in decisions",
            "achiever": "Works hard, finishes projects",
            "maximizer": "Optimizes, improves",
            "futuristic": "Sees future possibilities",
        }
        
        # Check for entrepreneurial themes
        for strength in strengths:
            content_lower = strength.content.lower()
            for theme, description in entrepreneurial_themes.items():
                if theme in content_lower:
                    fit["entrepreneurial_themes"].append({
                        "theme": theme.title(),
                        "description": description,
                    })
        
        # Calculate founder fit score
        theme_count = len(fit["entrepreneurial_themes"])
        fit["score"] = min(50 + (theme_count * 10), 95)
        
        # Add recommendations
        if theme_count < 2:
            fit["gaps"].append("Consider finding co-founder with complementary strengths")
            fit["recommendations"].append("Partner with someone who has Activator or Ideation")
        
        if len(projects) < 2:
            fit["gaps"].append("Build more projects to test ideas quickly")
            fit["recommendations"].append("Start small — launch MVPs to validate ideas")
        
        return fit
    
    def _find_potential_cofounders(
        self,
        network: list[KnowledgeResult],
        strengths: list[KnowledgeResult],
    ) -> list[dict]:
        """Find potential co-founders from user's network."""
        candidates = []
        
        # Look for complementary skills in network
        for connection in network[:5]:  # Top 5 connections
            candidates.append({
                "name": "Connection from network",
                "why": "Past collaborator with complementary skills",
                "approach": "Reach out about specific project idea",
            })
        
        # If no network data, provide general advice
        if not candidates:
            candidates.append({
                "name": "Look in your network",
                "why": "Past colleagues who left to start companies",
                "approach": "Attend startup events, reach out to alumni",
            })
        
        return candidates
    
    def _create_launch_roadmap(
        self,
        opportunities: list[dict],
        founder_fit: dict,
    ) -> dict:
        """Create launch roadmap for opportunities."""
        roadmap = {
            "phase_1": {
                "name": "Validate (Weeks 1-4)",
                "actions": [
                    "Talk to 10 potential users",
                    "Define the problem clearly",
                    "Build landing page",
                    "Get 50 email signups",
                ],
            },
            "phase_2": {
                "name": "Build MVP (Weeks 5-12)",
                "actions": [
                    "Build minimum viable product",
                    "Get 10 paying users",
                    "Iterate based on feedback",
                    "Document everything",
                ],
            },
            "phase_3": {
                "name": "Launch (Weeks 13-16)",
                "actions": [
                    "Public launch",
                    "Reach out to press/blogs",
                    "Post on Product Hunt",
                    "Gather testimonials",
                ],
            },
            "phase_4": {
                "name": "Grow (Months 5-12)",
                "actions": [
                    "Focus on retention",
                    "Build features users request",
                    "Consider funding options",
                    "Hire if needed",
                ],
            },
        }
        
        return roadmap
    
    def _build_response(
        self,
        query: str,
        opportunities: list[dict],
        founder_fit: dict,
        cofounders: list[dict],
        roadmap: dict,
    ) -> str:
        """Build entrepreneurial guidance response."""
        lines = []
        
        lines.append("## Entrepreneurial Analysis\n")
        
        # Opportunities
        lines.append("### Opportunities Identified\n")
        for opp in opportunities:
            lines.append(f"**{opp['type']}**")
            lines.append(f"{opp['description']}")
            lines.append(f"Recommendation: {opp['recommendation']}\n")
        
        # Founder fit
        lines.append("### Founder Fit Analysis")
        lines.append(f"**Fit score:** {founder_fit['score']}/100\n")
        
        if founder_fit['entrepreneurial_themes']:
            lines.append("**Your entrepreneurial strengths:**")
            for theme in founder_fit['entrepreneurial_themes']:
                lines.append(f"- {theme['theme']}: {theme['description']}")
        
        if founder_fit['gaps']:
            lines.append("\n**Areas to address:**")
            for gap in founder_fit['gaps']:
                lines.append(f"- {gap}")
        
        # Co-founders
        lines.append("\n### Potential Co-founders\n")
        for candidate in cofounders:
            lines.append(f"**{candidate['name']}**")
            lines.append(f"- Why: {candidate['why']}")
            lines.append(f"- Approach: {candidate['approach']}\n")
        
        # Launch roadmap
        lines.append("### Launch Roadmap\n")
        
        for phase, details in roadmap.items():
            lines.append(f"**{details['name']}**")
            for action in details['actions']:
                lines.append(f"- {action}")
            lines.append("")
        
        # Go/No-Go framework
        lines.append("### Go/No-Go Decision Framework\n")
        lines.append("**Green lights (proceed):**")
        lines.append("- Users actively asking for solution")
        lines.append("- You have unique insight/advantage")
        lines.append("- Market is growing")
        lines.append("- You can build MVP in <3 months\n")
        
        lines.append("**Red lights (reconsider):**")
        lines.append("- No one willing to pay")
        lines.append("- Crowded market with no differentiation")
        lines.append("- Requires significant upfront capital")
        lines.append("- Misaligned with your values\n")
        
        # Closing
        lines.append("### Remember")
        lines.append("> Build products that liberate users, not trap them.")
        lines.append("> Sustainable businesses > growth-at-all-costs.")
        lines.append("> Open source business models are viable.")
        lines.append("> Success = impact + freedom, not just exit.\n")
        
        lines.append("**The best time to start was yesterday. The second best time is now.**")
        
        return "\n".join(lines)


__all__ = ["FounderAgent"]

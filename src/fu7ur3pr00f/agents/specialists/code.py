"""Code Agent — GitHub, GitLab, and open source contributions specialist.

Helps developers build impactful code projects, optimize their GitHub/GitLab
presence, and develop effective open source strategies.

Example:
    >>> agent = CodeAgent()
    >>> response = await agent.process({"query": "How can I improve my GitHub?"})
"""

from collections.abc import Callable

from fu7ur3pr00f.agents.specialists.base import BaseAgent, KnowledgeResult
from fu7ur3pr00f.agents.values import ValuesContext, apply_values_filter


class CodeAgent(BaseAgent):
    """GitHub, GitLab, and open source contributions specialist.
    
    Focus areas:
    - GitHub/GitLab profile optimization
    - Open source strategy
    - Building widely-used projects
    - Contribution visibility
    - Code quality & documentation
    
    Example:
        >>> agent = CodeAgent()
        >>> agent.name
        'code'
    """
    
    @property
    def name(self) -> str:
        """Agent identifier."""
        return "code"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "GitHub, GitLab, and open source contributions"
    
    # Tools available to this agent
    tools: list[Callable] = []
    
    # Keywords for intent matching (GitHub + GitLab)
    KEYWORDS = {
        "github", "gitlab", "repos", "repositories", "code", "commits",
        "open source", "oss", "contributions", "projects", "portfolio",
        "pull request", "merge request", "git", "commit history",
    }
    
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle code/project requests."""
        intent_lower = intent.lower()
        return any(keyword in intent_lower for keyword in self.KEYWORDS)
    
    async def process(self, context: dict) -> str:
        """Process code/project request."""
        query = context.get("query", "")
        user_profile = context.get("user_profile", {})
        
        # Gather data from both platforms
        github_data = self._get_github_data(user_profile)
        gitlab_data = self._get_gitlab_data(user_profile)
        
        # Analyze code presence
        analysis = self._analyze_code_presence(github_data, gitlab_data)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(analysis)
        
        # Build response
        response = self._build_response(query, analysis, recommendations)
        
        # Apply values filter (promote OSS)
        filtered = apply_values_filter(
            response,
            context=ValuesContext(
                company_contributes_to_oss=True,
                product_respects_freedom=True,
            ),
            include_values_reminder=False,
        )
        
        return filtered
    
    def _get_github_data(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's GitHub data from knowledge base."""
        results = self.search_knowledge(
            query="GitHub repositories contributions commits",
            limit=10,
            sources=["github"],
        )
        return results
    
    def _get_gitlab_data(self, user_profile: dict) -> list[KnowledgeResult]:
        """Get user's GitLab data from knowledge base."""
        results = self.search_knowledge(
            query="GitLab repositories projects merge requests",
            limit=10,
            sources=["gitlab"],
        )
        return results
    
    def _analyze_code_presence(
        self,
        github_data: list[KnowledgeResult],
        gitlab_data: list[KnowledgeResult],
    ) -> dict:
        """Analyze user's code presence across platforms."""
        all_data = github_data + gitlab_data
        
        analysis = {
            "total_repos": len(all_data),
            "github_repos": len(github_data),
            "gitlab_repos": len(gitlab_data),
            "has_readme": 0,
            "has_tests": 0,
            "has_documentation": 0,
            "active_contributions": 0,
            "popular_projects": 0,
            "languages": set(),
            "quality_score": 0,
        }
        
        # Analyze each repo/project
        for item in all_data:
            content_lower = item.content.lower()
            
            if "readme" in content_lower:
                analysis["has_readme"] += 1
            if "test" in content_lower or "spec" in content_lower:
                analysis["has_tests"] += 1
            if "document" in content_lower or "wiki" in content_lower:
                analysis["has_documentation"] += 1
            if "commit" in content_lower or "contribute" in content_lower:
                analysis["active_contributions"] += 1
            if "star" in content_lower or "popular" in content_lower:
                analysis["popular_projects"] += 1
            
            # Extract languages (simple heuristic)
            common_languages = {"python", "javascript", "typescript", "rust", "go", "java", "ruby"}
            for lang in common_languages:
                if lang in content_lower:
                    analysis["languages"].add(lang.title())
        
        # Calculate quality score (0-100)
        if analysis["total_repos"] > 0:
            readme_score = (analysis["has_readme"] / analysis["total_repos"]) * 25
            test_score = (analysis["has_tests"] / analysis["total_repos"]) * 25
            doc_score = (analysis["has_documentation"] / analysis["total_repos"]) * 25
            activity = analysis["active_contributions"] / analysis["total_repos"]
            activity_score = min(activity * 25, 25)
            
            total = readme_score + test_score + doc_score + activity_score
            analysis["quality_score"] = round(total)
        
        analysis["languages"] = list(analysis["languages"])
        
        return analysis
    
    def _generate_recommendations(self, analysis: dict) -> list[dict]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # README recommendation
        if analysis["total_repos"] > 0 and analysis["has_readme"] < analysis["total_repos"]:
            recommendations.append({
                "priority": "High",
                "area": "Documentation",
                "action": "Add README to all projects",
                "impact": "Makes projects accessible and shows professionalism",
            })
        
        # Tests recommendation
        if analysis["total_repos"] > 0 and analysis["has_tests"] < analysis["total_repos"]:
            recommendations.append({
                "priority": "High",
                "area": "Testing",
                "action": "Add tests to your projects",
                "impact": "Shows code quality and makes projects production-ready",
            })
        
        # Activity recommendation
        if analysis["active_contributions"] < 3:
            recommendations.append({
                "priority": "Medium",
                "area": "Activity",
                "action": "Increase contribution frequency",
                "impact": "Shows consistent engagement with code",
            })
        
        # Open source recommendation
        if analysis["total_repos"] < 5:
            recommendations.append({
                "priority": "Medium",
                "area": "Portfolio",
                "action": "Build more public projects",
                "impact": "Demonstrates skills to potential employers/collaborators",
            })
        
        # OSS contribution recommendation
        recommendations.append({
            "priority": "High",
            "area": "Open Source",
            "action": "Contribute to existing open source projects",
            "impact": "Learn from others, build network, gain visibility",
        })
        
        return recommendations
    
    def _build_response(
        self,
        query: str,
        analysis: dict,
        recommendations: list[dict],
    ) -> str:
        """Build code presence response."""
        lines = []
        
        lines.append("## Code Presence Analysis\n")
        
        # Overview
        lines.append("### Overview")
        lines.append(f"**Total projects:** {analysis['total_repos']}")
        lines.append(f"- GitHub: {analysis['github_repos']}")
        lines.append(f"- GitLab: {analysis['gitlab_repos']}")
        langs = analysis['languages']
        lang_str = ', '.join(langs) if langs else 'Not detected'
        lines.append(f"**Languages:** {lang_str}")
        lines.append(f"**Quality score:** {analysis['quality_score']}/100\n")
        
        # Quality breakdown
        lines.append("### Quality Breakdown")
        if analysis['total_repos'] > 0:
            readme = f"{analysis['has_readme']}/{analysis['total_repos']}"
            tests = f"{analysis['has_tests']}/{analysis['total_repos']}"
            docs = f"{analysis['has_documentation']}/{analysis['total_repos']}"
            lines.append(f"- Projects with README: {readme}")
            lines.append(f"- Projects with tests: {tests}")
            lines.append(f"- Projects with docs: {docs}")
            lines.append(f"- Active contributions: {analysis['active_contributions']}")
        else:
            lines.append("No projects found. Time to start building!\n")
        
        # Recommendations
        lines.append("\n### Recommendations\n")
        
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"**{i}. {rec['action']}** ({rec['priority']} priority)")
            lines.append(f"   - *Impact:* {rec['impact']}")
            lines.append(f"   - *Area:* {rec['area']}\n")
        
        # Open source strategy
        lines.append("### Open Source Strategy\n")
        lines.append("1. **Start small** — Fix typos, improve documentation")
        lines.append("2. **Find projects you use** — You understand the pain points")
        lines.append("3. **Look for 'good first issue' labels** — Beginner-friendly")
        lines.append("4. **Be consistent** — Regular contributions > one-time")
        lines.append("5. **Build your own OSS** — Solve problems you face\n")
        
        # Closing
        lines.append("### Remember")
        lines.append("> Your code is your legacy. Build things that help others.")
        lines.append("> Open source is the default for important software.")
        lines.append("> Share your work. Stand on the shoulders of giants.")
        
        return "\n".join(lines)


__all__ = ["CodeAgent"]

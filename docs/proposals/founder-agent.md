---
status: Draft
version: 0.1.0
created: 2025-03-23
author: @juanmanueldaza
revisions:
  - 2025-03-23: Founder Agent design (entrepreneurial focus)
---

# Founder Agent Design

**Status:** Proposal  
**Agent Type:** Specialist (Entrepreneurial Focus)  
**Priority:** Phase 2 (after Coach Agent proves multi-agent works)

---

## Mission

Help developers identify entrepreneurial opportunities, assess founder fit, and launch products — not just join companies.

---

## Why This Agent Exists

**Problem:** Developers with great projects and entrepreneurial strengths don't realize their potential. They:
- Build side projects but never launch
- Have founder strengths (Activator, Ideation) but pursue traditional careers
- Don't see market opportunities in their work
- Lack guidance on co-founder matching, launch strategy

**Current Gap:** Jobs Agent helps find jobs. Coach Agent helps with leadership. **No agent helps with building companies.**

**Founder Agent fills this gap.**

---

## Core Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Opportunity Identification** | Find product opportunities in user's projects, skills, market gaps |
| **Founder Fit Analysis** | Assess if user has strengths/experience for specific opportunities |
| **Partnership Matching** | Identify potential co-founders, advisors from network |
| **Launch Planning** | Create roadmaps for MVP, launch, early traction |
| **Go/No-Go Recommendations** | Provide data-backed advice on pursuing ideas |

---

## Data Sources

### Internal (FutureProof)
| Source | What It Provides |
|--------|------------------|
| CliftonStrengths | Entrepreneurial themes (Activator, Ideation, Self-Assurance, Achiever) |
| LinkedIn | Network, past collaborations, industry connections |
| GitHub/GitLab | Projects, code quality, technical depth |
| Portfolio | Launched products, MVPs, prototypes |
| Knowledge Base | Past entrepreneurial attempts, lessons learned |

### External (Market Intelligence)
| Source | What It Provides |
|--------|------------------|
| Job boards | Market demand, skill gaps → product opportunities |
| Tech trends (HN, Dev.to) | Emerging needs, underserved markets |
| Tavily search | Competitive landscape, TAM analysis |
| Hacker News "Who's Hiring" | Who's building what, potential competitors/partners |

---

## Tools

### Existing Tools (Reuse)
```python
# Knowledge search
search_career_knowledge(query="side projects")
search_career_knowledge(query="portfolio")

# Market analysis
analyze_market_fit(target_role="founder")  # Adapt for product-market fit
get_tech_trends()  # Find emerging opportunities
analyze_market_skills()  # Skill gaps → product opportunities

# Network
search_career_knowledge(section="Connections", include_social=True)  # Find potential co-founders
```

### New Tools (Build)

#### 1. `identify_product_opportunities`
```python
def identify_product_opportunities(user_context: dict) -> list[Opportunity]:
    """
    Identify product opportunities based on:
    - User's projects (what they've built)
    - Market gaps (what's missing)
    - User's strengths (what they're good at)
    
    Returns:
    - List of opportunities with:
      - Problem statement
      - Target market
      - Competitive landscape
      - Founder fit score
      - Recommended next steps
    """
```

#### 2. `analyze_founder_fit`
```python
def analyze_founder_fit(
    strengths: list[str],
    projects: list[Project],
    opportunity: Opportunity
) -> FounderFitAnalysis:
    """
    Assess if user is good fit for specific opportunity.
    
    Analyzes:
    - Strengths alignment (Activator, Ideation, etc.)
    - Technical feasibility (can they build it?)
    - Domain expertise (do they understand the market?)
    - Network (do they know potential customers/partners?)
    
    Returns:
    - Fit score (0-100)
    - Strengths that help
    - Gaps to address
    - Recommendation (proceed/pivot/shelve)
    """
```

#### 3. `find_potential_cofounders`
```python
def find_potential_cofounders(
    user_network: list[Connection],
    required_skills: list[str],
    complementary_strengths: list[str]
) -> list[CofounderCandidate]:
    """
    Find potential co-founders from user's network.
    
    Looks for:
    - Complementary skills (technical vs. business)
    - Complementary strengths (Ideator + Executor)
    - Past collaboration history
    - Shared values/interests
    
    Returns:
    - Ranked list of candidates
    - Why they're a good fit
    - Suggested outreach approach
    """
```

#### 4. `create_launch_roadmap`
```python
def create_launch_roadmap(
    opportunity: Opportunity,
    user_context: dict,
    timeline_months: int = 6
) -> LaunchRoadmap:
    """
    Create step-by-step launch plan.
    
    Includes:
    - MVP scope (minimum viable product)
    - Milestones (build, test, launch, iterate)
    - Resource requirements (time, money, skills)
    - Risk mitigation
    - Success metrics
    
    Returns:
    - Week-by-week roadmap
    - Key decisions and deadlines
    - Go/no-go checkpoints
    """
```

#### 5. `assess_market_timing`
```python
def assess_market_timing(
    opportunity: Opportunity,
    market_trends: list[Trend],
    competitive_landscape: list[Competitor]
) -> MarketTiming:
    """
    Assess if now is the right time to pursue opportunity.
    
    Analyzes:
    - Market readiness (too early? too late?)
    - Competitive window (first mover vs. fast follower)
    - Technology maturity
    - Economic conditions
    
    Returns:
    - Timing score (0-100)
    - Why now / why not now
    - Recommended launch window
    """
```

---

## Example Workflows

### Workflow 1: "Should I launch my side project?"

```
User: "I built a developer tool for API testing. Should I try to launch it?"

Founder Agent:
1. Fetch project from GitHub/GitLab
   → Analyze code quality, uniqueness, completeness
   
2. Research competitive landscape
   → Find existing API testing tools
   → Identify differentiation opportunities
   
3. Assess founder-market fit
   → Check strengths (Activator? Self-Assurance?)
   → Check domain expertise (API development experience)
   → Check network (knows potential early users?)
   
4. Analyze market timing
   → Is demand growing?
   → Is market saturated?
   
5. Create recommendation
   → If strong fit: Launch roadmap with MVP scope
   → If weak fit: Suggest finding co-founder or shelve idea
```

### Workflow 2: "I have a startup idea. What do you think?"

```
User: "I want to build a better CI/CD platform for small teams."

Founder Agent:
1. Research existing solutions
   → CircleCI, GitHub Actions, GitLab CI
   → Identify gaps (pricing? complexity? specific use cases?)
   
2. Assess user's qualifications
   → Check projects (built CI/CD tools before?)
   → Check strengths (Executor? Problem-solver?)
   → Check network (knows potential customers?)
   
3. Analyze market opportunity
   → TAM for CI/CD platforms
   → Underserved segments (small teams specifically)
   
4. Provide recommendation
   → "Yes, if you focus on [specific niche]"
   → "No, market is saturated unless you have unique angle"
   → "Maybe, but find co-founder with [specific skills]"
```

### Workflow 3: "Find me a co-founder"

```
User: "I have an idea but need a technical co-founder."

Founder Agent:
1. Understand what user brings
   → Strengths (business? design? domain expertise?)
   → Network (who do they already know?)
   → Idea stage (just idea? MVP? paying customers?)
   
2. Search network for candidates
   → LinkedIn connections with technical roles
   → GitHub collaborators with strong projects
   → Past colleagues who might be interested
   
3. Rank candidates
   → Skill complementarity
   → Strength complementarity
   → Shared interests/values
   → Likelihood to say yes (past interactions)
   
4. Provide outreach strategy
   → "Reach out to Alice first — she's built similar tools"
   → "Mention [specific project] to pique interest"
   → "Suggest coffee chat, not immediate commitment"
```

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Opportunities identified | 3-5 per user | Count from `identify_product_opportunities` |
| Founder fit accuracy | 80%+ user agreement | User feedback on recommendations |
| Launches completed | Track over time | Follow-up: "Did you launch?" |
| Co-founder matches | Track over time | "Did you find a co-founder?" |
| User satisfaction | 4/5 stars | Post-session rating |

---

## Integration Points

### With Coach Agent
```
Founder Agent needs: User's strengths for founder fit analysis
Coach Agent provides: CliftonStrengths analysis, leadership assessment

Example:
Founder: "Does user have entrepreneurial strengths?"
Coach: "Yes — Activator (#2), Ideation (#5), Self-Assurance (#7)"
Founder: "Strong founder profile — recommend pursuing"
```

### With Code Agent
```
Founder Agent needs: Project quality assessment
Code Agent provides: Repo analysis, code quality scores

Example:
Founder: "How good is their side project?"
Code: "Well-documented, 80% test coverage, 50 GitHub stars"
Founder: "Strong technical foundation — viable for launch"
```

### With Learning Agent
```
Founder Agent needs: Skill gap analysis for building product
Learning Agent provides: Learning roadmap, skill recommendations

Example:
Founder: "What skills does user need to build this?"
Learning: "Needs: deployment, scaling, security"
Founder: "Add 'learn deployment' to launch roadmap"
```

### With Jobs Agent
```
Founder Agent provides: Alternative to job search (build vs. join)
Jobs Agent provides: Backup options if startup fails

Example:
Founder: "User could build startup in this space"
Jobs: "Or join these 5 companies working on similar problems"
Orchestrator: "Present both options — user decides"
```

---

## Implementation Priority

**Phase 0:** Coach Agent only (prove multi-agent works)

**Phase 1:** Learning Agent, Code Agent, Jobs Agent

**Phase 2:** Founder Agent (after other agents proven)

**Why wait:**
- Founder Agent is complex (requires data from multiple sources)
- Need working multi-agent infrastructure first
- Should prove simpler agents before building complex ones

**But it's high-value:**
- Differentiates FutureProof from job-search tools
- Serves underserved market (entrepreneurial devs)
- High user engagement (startup dreams are passionate)

---

## Risks

| Risk | Mitigation |
|------|------------|
| Giving bad startup advice | Clear disclaimers: "Not financial/legal advice" |
| Users quitting jobs prematurely | Balanced recommendations (build vs. join vs. stay) |
| Over-promising success | Realistic success rates, risk factors |
| Co-founder matching fails | Frame as "potential introductions" not guarantees |

---

## Naming Discussion

| Name | Pros | Cons |
|------|------|------|
| **Founder Agent** | ✅ Action-oriented, builder mindset | — |
| Entrepreneur Agent | Broad, recognizable | Includes investors, not just builders |
| Startup Agent | Clear focus | Sounds early-stage only |
| Product Agent | Product-focused | Too narrow (PM vs. company building) |
| Business Agent | Generic | Sounds corporate, not entrepreneurial |

**Decision:** **Founder Agent** — clearest, most action-oriented

---

## See Also

- [Multi-Agent Design](multi-agent-design.md) — Overall architecture
- [Coach Agent](multi-agent-design.md#2-coach-agent-soft-skills--leadership) — Strengths analysis
- [Code Agent](multi-agent-design.md#5-code-agent-github--gitlab--open-source) — Project analysis

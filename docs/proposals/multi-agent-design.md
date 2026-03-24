---
status: Draft
version: 0.1.0
created: 2025-03-23
author: @juanmanueldaza
revisions:
  - 2025-03-23: Initial technical design
  - 2025-03-23: Added values-driven design principles
---

# Multi-Agent Architecture Design Document

**Status:** Draft — For Discussion  
**Branch:** `feature/multi-agent-architecture`  
**Date:** March 2025  
**Author:** FutureProof Team

---

## Vision: Developer Success, Not Just Employment

**FutureProof is NOT a job search tool.**

FutureProof helps developers **succeed on their own terms** — whether that's:
- Getting promoted to Staff Engineer (Coach Agent)
- Launching a startup (Founder Agent)
- Becoming a recognized expert (Learning + Code Agent)
- Finding remote work for time freedom (Jobs Agent)
- Building open source for impact (Code Agent)

**Jobs are ONE path. Success is the destination.**

See: [Vision Statement](vision-developer-success.md)

---

## Executive Summary

**TL;DR:** We're building a multi-agent architecture that helps developers **succeed**, not just find jobs.

**Critical Question:** Are we solving a real problem or adding complexity for sophistication?

**Answer:** The real problem is that most career tools assume success = employment. We're building agents for ALL success paths: career growth, entrepreneurship, technical mastery, time freedom, and impact.

---

## Problem Statement

### Current Single-Agent Limitations

1. **Context dilution** — 40 tools in one agent can lead to tool selection confusion
2. **No specialization** — Same agent handles CliftonStrengths coaching and job search
3. **Prompt bloat** — System prompt grows with each new capability
4. **Testing complexity** — Hard to test specific domains in isolation
5. **Job-centric bias** — Current agent assumes user wants employment, not other success paths

### Real User Needs (Success-Oriented)

| User Goal | Current Solution | Gap |
|-----------|------------------|-----|
| "Get promoted to Staff" | `analyze_career_alignment` | Generic, not leadership-focused |
| "Launch my startup" | None | ❌ No entrepreneurial support |
| "Become recognized expert" | `analyze_skill_gaps` | No authority-building strategy |
| "Find remote work" | `search_jobs` | ✅ Works well |
| "Build impactful OSS" | `get_github_profile` | Surface-level, no strategy |
| "Start consulting" | None | ❌ No freelance/consulting support |

**Verdict:** We're missing entire success paths (entrepreneurship, consulting, open source). Multi-agent enables specialized support for each path.

---

## A2A Protocol Evaluation

### What is A2A?

**Agent2Agent (A2A)** is an open protocol by Google (announced April 2025) for agent-to-agent communication across different vendors/platforms.

**Key features:**
- Agent capability discovery (Agent Cards)
- Task lifecycle management
- Secure authentication (OpenAPI-compatible)
- Long-running task support
- Modality agnostic (text, audio, video)

### Should FutureProof Use A2A?

**Verdict: NO — Not for our use case.**

### Why Not A2A

| A2A Use Case | FutureProof Reality | Fit |
|--------------|---------------------|-----|
| Cross-vendor agent communication | Single codebase, all agents ours | ❌ Overkill |
| Enterprise interoperability | Self-contained application | ❌ Not needed |
| External agent discovery | Agents are internal, known at compile time | ❌ Unnecessary |
| Complex task orchestration | Simple request/response | ❌ Over-engineering |

### What We Should Use Instead

**Direct function calls with shared state:**

```python
# Simple, KISS-compliant
class OrchestratorAgent:
    def __init__(self):
        self.coach = CoachAgent()
        self.learning = LearningAgent()
        self.jobs = JobsAgent()
        self.github = GitHubAgent()
    
    async def handle(self, query: str) -> str:
        # Route based on intent
        agent = self._route(query)
        return await agent.process(query)
```

**Why this is better for us:**
- **Zero protocol overhead** — Direct calls, no HTTP/JSON-RPC
- **Shared memory** — All agents access same ChromaDB instance
- **Type safety** — Compile-time checking, not runtime discovery
- **Testability** — Mock agents easily
- **Performance** — No network latency

### When A2A Would Make Sense

FutureProof should consider A2A **only if**:

1. We integrate with external enterprise agents (Salesforce, SAP)
2. We deploy agents as separate services (microservices)
3. We need cross-platform agent discovery
4. We support long-running tasks (hours/days)

**None of these apply today.**

---

## Proposed Architecture (KISS-Compliant)

### Design Principles

| Principle | Application |
|-----------|-------------|
| **KISS** | Direct function calls, no protocol overhead |
| **DRY** | Shared base class, shared tools, shared memory |
| **SOLID** | Single responsibility per agent, open for extension |
| **YAGNI** | Only 4 specialist agents initially, add more only if proven necessary |
| **Free Software** | All agents promote software freedom, OSS contributions |
| **Hacker Ethic** | Meritocratic, anti-gatekeeping, build beautiful code |
| **Developer Sovereignty** | Local data, no lock-in, user owns everything |

**See:** [Values & Ethics](values.md) — Complete statement of FutureProof values

### Agent Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                           │
│  - Routes requests                                              │
│  - Manages conversation context                                 │
│  - Synthesizes multi-agent responses                            │
│  - Falls back to single-agent for simple queries                │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│  Coach Agent  │   │  Learning Agent │   │  Jobs Agent   │
│  - Strengths  │   │  - Skill gaps   │   │  - Job search │
│  - Leadership │   │  - Learning paths│  │  - Market fit │
│  - Career plan│   │  - Tech trends  │   │  - Salary     │
└───────────────┘   └─────────────────┘   └───────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Code Agent    │
                    │  - GitHub+GitLab│
                    │  - Contributions│
                    │  - OSS strategy │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Founder Agent  │
                    │  - Opportunity  │
                    │  - Partnerships │
                    │  - Launch plan  │
                    └─────────────────┘
```

### Agent Responsibilities

#### 1. Orchestrator Agent (FutureProof Main)

**Responsibility:** Route requests, manage context, synthesize responses

**First Question:** "What does success look like for you?"

**Success Paths:**
| User Says | Routes To |
|-----------|-----------|
| "Get promoted" | Coach Agent |
| "Launch startup" | Founder Agent |
| "Become expert" | Learning + Code Agent |
| "Find remote work" | Jobs Agent |
| "Build OSS" | Code Agent |
| "Start consulting" | Founder + Jobs Agent |

**When it handles:**
- Simple queries ("What's my current role?")
- Multi-step workflows (gather → analyze → generate)
- Cross-agent synthesis ("Plan my career transition")
- Clarifying success definition ("What do you want?")

**When it delegates:**
- Strengths/coaching → Coach Agent
- Learning/skills → Learning Agent
- Job search → Jobs Agent
- Code/repos → Code Agent
- Entrepreneurship → Founder Agent

**Example flow:**
```
User: "Help me transition to Staff Engineer"

Orchestrator:
1. Route to Coach Agent → Leadership development plan
2. Route to Learning Agent → Skill gaps + learning roadmap
3. Route to Jobs Agent → Market opportunities
4. Route to Code Agent → OSS contribution strategy
5. Synthesize all → Coherent career transition plan
```

**Example flow (entrepreneurial):**
```
User: "Should I quit my job and build my startup?"

Orchestrator:
1. Route to Founder Agent → Opportunity analysis, launch roadmap
2. Route to Coach Agent → Strengths for founder fit
3. Route to Code Agent → Project quality assessment
4. Route to Jobs Agent → Alternative: job opportunities as backup
5. Synthesize all → Balanced recommendation (build vs. join vs. stay)
```

---

#### 2. Coach Agent (Soft Skills & Leadership)

**Responsibility:** CliftonStrengths-based coaching, leadership development

**Data Sources:**
- CliftonStrengths assessment (Top 5/10/34)
- LinkedIn profile (roles, trajectory)
- User goals and career alignment

**Tools:**
- Existing: `analyze_career_alignment`, `get_career_advice`
- New: `analyze_strengths_for_leadership`, `create_development_plan`

**Example:**
```
User: "How can I leverage my strengths for leadership?"

Coach Agent:
1. Load CliftonStrengths from knowledge base
2. Analyze strengths vs leadership competencies
3. Generate development plan with specific actions
```

**Why separate agent:**
- Deep strengths expertise (not generic advice)
- Long-term coaching relationship tracking
- Specialized prompts for CliftonStrengths interpretation

---

#### 3. Learning Agent (Technical Skills)

**Responsibility:** Skill gap analysis, learning paths, tech trends

**Data Sources:**
- LinkedIn Skills
- GitHub languages/repos
- Market skill demands (job postings)
- Tech trends (HN, Dev.to, Stack Overflow)

**Tools:**
- Existing: `analyze_skill_gaps`, `get_tech_trends`, `analyze_market_skills`
- New: `generate_learning_path`, `recommend_resources`

**Example:**
```
User: "What should I learn to become Staff Engineer?"

Learning Agent:
1. Analyze current skills vs Staff Engineer requirements
2. Check market trends for in-demand skills
3. Generate prioritized learning roadmap
4. Recommend specific resources (courses, books, projects)
```

**Why separate agent:**
- Focused on learning (not career coaching)
- Tracks learning progress over time
- Specialized in pedagogical sequencing

---

#### 4. Jobs Agent (Job Search)

**Responsibility:** Job search, market fit, salary insights

**Data Sources:**
- 7 job boards (JobSpy, MCP)
- Hacker News hiring threads
- Salary data (Tavily, market research)

**Tools:**
- Existing: `search_jobs`, `analyze_market_fit`, `get_salary_insights`, `compare_salary_ppp`

**Example:**
```
User: "Find me remote Python jobs paying $150k+"

Jobs Agent:
1. Search all job boards with filters
2. Analyze market fit for each position
3. Get salary insights
4. Return curated list with fit scores
```

**Why separate agent:**
- Already works well (minimal changes needed)
- High-volume searches benefit from isolation
- Can optimize for speed independently

---

#### 5. Code Agent (GitHub + GitLab + Open Source)

**Responsibility:** Code repository analysis, contributions, OSS strategy across ALL platforms

**Data Sources:**
- GitHub API (via MCP)
- GitLab API (via `glab` CLI)
- Repo analysis (code quality, README, issues)
- Contribution history from both platforms

**Tools:**
- Existing: `get_github_profile`, `get_github_repo`, `search_github_repos`
- Existing: `get_gitlab_project`, `get_gitlab_file`, `search_gitlab_projects`
- New: `analyze_repo_quality`, `recommend_oss_projects`, `contribution_strategy`, `merge_contributions`

**Example:**
```
User: "How can I improve my code presence for Staff Engineer roles?"

Code Agent:
1. Fetch repos from BOTH GitHub and GitLab
2. Analyze all repos for code quality, documentation, impact
3. Merge contribution history from both platforms
4. Compare to Staff Engineer profiles
5. Provide specific improvement recommendations
```

**Why "Code Agent" not "GitHub Agent":**
- Users have code on multiple platforms
- Single view of all contributions (DRY)
- Platform-agnostic analysis (SOLID)
- Avoids confusion when user asks about GitLab

**Why separate agent:**
- Deep code analysis (not surface-level)
- OSS-specific expertise
- Can run complex repo analysis without blocking other agents
- Unified view across GitHub + GitLab

---

#### 6. Founder Agent (Entrepreneurial & Product Focus)

**Responsibility:** Identify entrepreneurial opportunities, product potential, partnerships, and launch strategies

**Data Sources:**
- User's built projects (GitHub, GitLab, portfolio)
- CliftonStrengths (entrepreneurial themes: Activator, Ideation, Self-Assurance, etc.)
- Market gaps and trends
- Network connections (LinkedIn, past collaborations)
- Side projects, MVPs, prototypes

**Tools:**
- Existing: `search_career_knowledge` (projects, portfolio)
- Existing: `analyze_market_fit`, `get_tech_trends`
- New: `identify_product_opportunities`, `analyze_founder_fit`, `find_potential_cofounders`, `create_launch_roadmap`, `assess_market_timing`

**Example:**
```
User: "Should I turn my side project into a startup?"

Founder Agent:
1. Analyze side project (code quality, uniqueness, traction)
2. Assess founder-market fit (strengths, experience, network)
3. Research market opportunity (competitors, TAM, trends)
4. Identify potential co-founders/partners from network
5. Create launch roadmap with milestones
6. Provide go/no-go recommendation with reasoning
```

**Example 2:**
```
User: "I have an idea for a developer tool. Should I pursue it?"

Founder Agent:
1. Analyze user's strengths for founder fit (Activator? Ideation?)
2. Research existing solutions (competitive landscape)
3. Identify market gap and differentiation
4. Assess technical feasibility (user's skills, projects)
5. Recommend: build MVP, find co-founder, or shelve idea
```

**Why "Founder Agent" not "Entrepreneur Agent":**
- ✅ **Founder** — Action-oriented, builder mindset
- ❌ ~~Entrepreneur~~ — Too broad, includes investors, business-only folks
- ❌ ~~Product Agent~~ — Too narrow (product management vs. building company)
- ❌ ~~Business Agent~~ — Too generic, sounds corporate

**Why separate agent:**
- Entrepreneurial thinking is fundamentally different from job-seeking
- Requires synthesizing: strengths + projects + market + network
- Long-term opportunity tracking (ideas, MVPs, launches)
- Connects users with potential co-founders, advisors
- Focus on **building** vs. **joining** companies

**Founder vs. Coach Agent:**
| Founder Agent | Coach Agent |
|---------------|-------------|
| Build companies | Grow in career |
| Launch products | Get promoted |
| Find co-founders | Find mentors |
| Market opportunities | Leadership opportunities |
| Equity, ownership | Salary, benefits |

**Founder vs. Jobs Agent:**
| Founder Agent | Jobs Agent |
|---------------|------------|
| Create jobs | Find jobs |
| Build product | Join company |
| Risk-taking | Stability |
| Equity-focused | Salary-focused |

---

## Implementation Strategy

### Phase 0: Foundation (Week 1)

**Goal:** Prove multi-agent works for ONE workflow before expanding.

**Scope:**
1. Create `BaseAgent` abstract class
2. Implement `CoachAgent` only (CliftonStrengths focus)
3. Simple router in orchestrator
4. Test: "Analyze my leadership strengths"

**Success Criteria:**
- Response quality ≥ current single-agent
- Latency < 2x single-agent
- No context loss

**Code Structure:**
```
src/fu7ur3pr00f/agents/
├── career_agent.py          # Existing (unchanged)
├── orchestrator.py          # New (routing logic)
└── specialists/
    ├── base.py              # BaseAgent class
    ├── coach.py             # CoachAgent
    ├── learning.py          # (later)
    ├── jobs.py              # (later)
    └── github.py            # (later)
```

### Phase 1: Core Agents (Week 2-3)

**Goal:** Implement all 4 specialist agents.

**Scope:**
1. Learning Agent
2. Jobs Agent (minimal changes)
3. GitHub Agent
4. Router with intent classification

**Success Criteria:**
- All agents work independently
- Router correctly routes 90%+ of queries
- Fallback to single-agent works

### Phase 2: Integration (Week 4)

**Goal:** Full multi-agent workflows.

**Scope:**
1. Orchestrator synthesis
2. Parallel agent execution
3. End-to-end testing
4. Performance benchmarking

**Success Criteria:**
- Multi-agent completes full workflows
- Latency acceptable (<5s for most queries)
- Users prefer multi-agent responses

### Phase 3: Migration (Week 5+)

**Goal:** Gradual migration from single-agent.

**Approach:**
```python
# Hybrid approach — safest migration
async def handle_request(query: str) -> str:
    if is_complex_request(query):
        return await multi_agent_pipeline(query)
    else:
        return await single_agent(query)
```

**Decision Point:** After 2 weeks of usage:
- If multi-agent performs better → migrate more workflows
- If no clear benefit → keep hybrid or revert

---

## Technical Design

### Base Agent Class

```python
# src/fu7ur3pr00f/agents/specialists/base.py

from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Base class for all specialist agents."""
    
    name: str
    description: str
    tools: list[Callable] = []
    
    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle the request."""
        pass
    
    @abstractmethod
    async def process(self, context: dict) -> str:
        """Process request and return response."""
        pass
    
    # Shared memory access
    def search_knowledge(self, query: str, limit: int = 5) -> list[dict]:
        """Search knowledge base."""
        ...
    
    def index_knowledge(self, documents: list[str]) -> None:
        """Index documents."""
        ...
    
    def remember(self, event_type: str, data: str) -> None:
        """Store episodic memory."""
        ...
```

### Router Implementation

```python
# src/fu7ur3pr00f/agents/orchestrator.py

INTENT_MAP = {
    # Coach Agent
    "leadership": "coach",
    "strengths": "coach",
    "clifton": "coach",
    "coaching": "coach",
    
    # Learning Agent
    "learning": "learning",
    "skills": "learning",
    "study": "learning",
    "courses": "learning",
    
    # Jobs Agent
    "jobs": "jobs",
    "hiring": "jobs",
    "salary": "jobs",
    "interview": "jobs",
    
    # Code Agent (GitHub + GitLab)
    "github": "code",
    "gitlab": "code",
    "repos": "code",
    "repositories": "code",
    "open source": "code",
    "contributions": "code",
    "commits": "code",
    
    # Founder Agent
    "founder": "founder",
    "startup": "founder",
    "cofounder": "founder",
    "co-founder": "founder",
    "launch": "founder",
    "product": "founder",
    "entrepreneur": "founder",
    "mv": "founder",  # MVP
    "side project": "founder",
    "business idea": "founder",
}

def route_request(query: str) -> str:
    """Route query to appropriate agent."""
    query_lower = query.lower()
    
    # Simple keyword matching (KISS)
    for keyword, agent in INTENT_MAP.items():
        if keyword in query_lower:
            return agent
    
    # Fallback to orchestrator
    return "orchestrator"
```

### Shared Memory

```python
# All agents share same ChromaDB instance

from fu7ur3pr00f.memory.chromadb_store import get_chroma_client

class BaseAgent:
    _chroma = None  # Shared across all agents
    
    @property
    def chroma(self):
        if self._chroma is None:
            self._chroma = get_chroma_client()
        return self._chroma
```

**Why shared:**
- No data duplication (DRY)
- All agents see full context
- Simpler than syncing isolated stores

### Tool Registry

```python
# src/fu7ur3pr00f/agents/tools/registry.py

# Shared tools (all agents can use)
SHARED_TOOLS = {
    "profile": [
        get_user_profile,
        update_user_name,
        ...
    ],
    "knowledge": [
        search_career_knowledge,
        index_career_knowledge,
        ...
    ],
}

# Agent-specific tools
COACH_TOOLS = SHARED_TOOLS["profile"] + [
    analyze_career_alignment,
    get_career_advice,
    analyze_strengths_for_leadership,  # New
]

LEARNING_TOOLS = SHARED_TOOLS["knowledge"] + [
    analyze_skill_gaps,
    get_tech_trends,
    generate_learning_path,  # New
]
```

---

## Testing Strategy

### Unit Tests (Per Agent)

```python
# tests/agents/specialists/test_coach_agent.py

def test_coach_agent_strengths_analysis():
    agent = CoachAgent()
    context = {
        "user_id": "test",
        "query": "leadership strengths",
        "user_profile": {...},
    }
    response = agent.process(context)
    assert "strengths" in response.lower()
    assert "leadership" in response.lower()
```

### Integration Tests (Agent Team)

```python
# tests/agents/test_orchestrator.py

async def test_multi_agent_career_plan():
    orchestrator = OrchestratorAgent()
    query = "Plan my transition to Staff Engineer"
    response = await orchestrator.handle(query)
    
    # Should include insights from multiple agents
    assert "learning" in response.lower()
    assert "leadership" in response.lower()
```

### Performance Benchmarks

```python
# tests/benchmarks/test_multi_agent.py

def benchmark_single_vs_multi():
    test_queries = [
        "Analyze my leadership strengths",
        "What should I learn for Staff Engineer?",
        "Find remote Python jobs",
    ]
    
    single_times = []
    multi_times = []
    
    for query in test_queries:
        single_times.append(time(single_agent, query))
        multi_times.append(time(multi_agent_pipeline, query))
    
    # Multi-agent should be <2x slower (acceptable tradeoff)
    assert median(multi_times) < median(single_times) * 2
```

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Context loss between agents | High | Medium | Shared memory, context passing |
| Increased latency | Medium | High | Parallel execution, caching |
| Routing errors | Medium | Medium | Fallback to orchestrator |
| Code duplication | Medium | Low | Shared base class, tool registry |
| Testing complexity | Low | Medium | Per-agent tests, integration tests |
| YAGNI violation | Medium | High | Start with one agent, prove value |

---

## Decision Framework

### Before Implementing Each Agent

1. **What specific problem does this solve?**
   - Current limitation: _______
   - Multi-agent improvement: _______

2. **How will we measure success?**
   - Metric: Response quality, latency, user satisfaction
   - Baseline: Single-agent performance
   - Target: ≥ quality, <2x latency

3. **What's the rollback plan?**
   - If agent fails: Disable routing, use single-agent

4. **Is this YAGNI?**
   - Do we have user requests? Yes/No
   - Building for hypothetical future? Yes/No

---

## Comparison: Single vs. Multi-Agent

| Aspect | Single-Agent | Multi-Agent |
|--------|--------------|-------------|
| **Simplicity** | ✅ Simple | ❌ More complex |
| **Specialization** | ❌ Generic | ✅ Specialized |
| **Testing** | ❌ Hard to isolate | ✅ Per-agent tests |
| **Latency** | ✅ Fast | ⚠️ Slower (routing overhead) |
| **Context** | ✅ Full context | ⚠️ Must pass explicitly |
| **Extensibility** | ⚠️ Prompt bloat | ✅ Add agents easily |
| **Debugging** | ❌ Hard | ✅ Easier per-agent |
| **Maintenance** | ✅ One codebase | ⚠️ Multiple agents |

**Verdict:** Multi-agent adds complexity but enables specialization. Only proceed if specialization benefit outweighs complexity cost.

---

## Recommendation

### Proceed with Caution

1. **Start small** — Coach Agent only (Week 1)
2. **Prove value** — Benchmark vs single-agent
3. **Iterate** — Add agents only if Coach succeeds
4. **Keep fallback** — Hybrid approach (single + multi)

### Don't Use A2A

- Overkill for single-codebase multi-agent
- Direct function calls are simpler (KISS)
- Consider A2A only if we need external agent integration

### Success Looks Like

- Users get better coaching/learning/GitHub insights
- Latency increase is acceptable (<2x)
- Code is more maintainable (not less)
- Testing is easier (not harder)

---

## Next Steps

1. **Review this document** — Team feedback
2. **Implement Phase 0** — Coach Agent prototype
3. **Benchmark** — Compare to single-agent
4. **Decide** — Proceed, iterate, or abandon

---

## See Also

- [Architecture Proposal](docs/proposals/multi-agent-architecture.md)
- [Current Architecture](docs/architecture.md)
- [A2A Protocol Spec](https://github.com/a2aproject/A2A)
- [A2A Python SDK](https://github.com/a2aproject/a2a-python)

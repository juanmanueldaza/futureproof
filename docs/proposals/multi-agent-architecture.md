# Multi-Agent Architecture Proposal

## Critical Assessment (Linus Torvalds Style)

**Don't multi-agent for the sake of it.** The current single-agent works because:
- Multi-agent handoffs **failed** with GPT-4.1 (over-delegation, lost context)
- One agent with 40 tools is **simpler** and **more reliable**
- Context switching between agents adds **latency** and **complexity**

**Before we proceed, ask:**
1. What problems does multi-agent solve that single-agent can't?
2. Are we adding complexity for perceived sophistication?
3. Will this actually work better, or just look fancier?

---

## Proposed Architecture (If We Proceed)

### Design Principles

| Principle | Application |
|-----------|-------------|
| **KISS** | Minimal agents, clear boundaries, no orchestration overhead |
| **DRY** | Shared tools, shared memory, no duplication |
| **SOLID** | Each agent has single responsibility, open for extension |
| **YAGNI** | Only add agents when proven necessary |

### Agent Team Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                           │
│  (routes requests, manages context, synthesizes responses)      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│  Coach Agent  │   │  Learning Agent │   │  Jobs Agent   │
│  (soft skills)│   │  (tech skills)  │   │  (search)     │
└───────────────┘   └─────────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  GitHub Agent   │
                    │  (code/projects)│
                    └─────────────────┘
```

---

## Agent Responsibilities

### 1. Orchestrator Agent (FutureProof Main)

**Responsibility:** Route requests, manage conversation context, synthesize responses

**Tools:**
- All profile management tools
- All settings tools
- Routing logic to specialist agents

**When to use:**
- User asks general career questions
- Multi-step workflows (gather → analyze → generate)
- Cross-agent synthesis needed

**Example:**
```
User: "Help me plan my career transition to Staff Engineer"
Orchestrator → routes to Coach + Learning + Jobs agents
Orchestrator → synthesizes all responses into coherent plan
```

---

### 2. Coach Agent (Soft Skills & Leadership)

**Responsibility:** CliftonStrengths, leadership, soft skills, career coaching

**Data Sources:**
- CliftonStrengths assessment
- LinkedIn profile (roles, trajectory)
- User goals and career alignment

**Tools:**
- `analyze_career_alignment`
- `get_career_advice`
- CliftonStrengths analysis (new tool)
- Leadership assessment (new tool)

**Example:**
```
User: "How can I leverage my strengths for leadership?"
Coach Agent → analyzes strengths + career data
Coach Agent → provides leadership development plan
```

---

### 3. Learning Agent (Technical Skills)

**Responsibility:** Skill gaps, learning paths, tech trends

**Data Sources:**
- LinkedIn Skills
- GitHub languages/repos
- Market skill demands
- Tech trends (HN, Dev.to, Stack Overflow)

**Tools:**
- `analyze_skill_gaps`
- `get_tech_trends`
- `analyze_market_skills`
- Learning path generator (new tool)

**Example:**
```
User: "What should I learn to become Staff Engineer?"
Learning Agent → analyzes gaps + market trends
Learning Agent → generates learning roadmap
```

---

### 4. Jobs Agent (Job Search)

**Responsibility:** Job search, market fit, salary insights

**Data Sources:**
- 7 job boards (JobSpy, MCP)
- Hacker News hiring threads
- Salary data (Tavily, market research)

**Tools:**
- `search_jobs`
- `analyze_market_fit`
- `get_salary_insights`
- `compare_salary_ppp`

**Example:**
```
User: "Find me remote Python jobs paying $150k+"
Jobs Agent → searches all job boards
Jobs Agent → filters by salary, location
Jobs Agent → returns curated list
```

---

### 5. GitHub Agent (Code & Open Source)

**Responsibility:** GitHub profile, repos, contributions, open source strategy

**Data Sources:**
- GitHub API (via MCP)
- Repo analysis
- Contribution history

**Tools:**
- `get_github_profile`
- `get_github_repo`
- `search_github_repos`
- Contribution analyzer (new tool)
- Open source recommender (new tool)

**Example:**
```
User: "How can I improve my GitHub for Staff Engineer roles?"
GitHub Agent → analyzes repos, contributions
GitHub Agent → provides improvement recommendations
```

---

## Implementation Strategy

### Phase 1: Foundation (Week 1)

1. **Create agent base class** — Shared interface, common tools
2. **Shared memory layer** — All agents read/write to same ChromaDB
3. **Router mechanism** — Simple intent-based routing

```python
# src/fu7ur3pr00f/agents/base.py
class BaseAgent(ABC):
    """Base class for all specialist agents."""
    
    name: str
    description: str
    tools: list[Callable]
    
    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Check if this agent can handle the request."""
        ...
    
    @abstractmethod
    async def process(self, context: dict) -> str:
        """Process the request and return response."""
        ...
```

### Phase 2: Specialist Agents (Week 2-3)

1. **Extract from monolith** — Move tools to appropriate agents
2. **Add routing logic** — Intent classification
3. **Test each agent independently** — Unit tests per agent

### Phase 3: Integration (Week 4)

1. **Orchestrator synthesis** — Combine agent responses
2. **End-to-end testing** — Full workflows
3. **Performance benchmarking** — Compare to single-agent

---

## Critical Design Decisions

### 1. Shared vs. Isolated Memory

**Recommendation:** Shared ChromaDB collections

```python
# All agents use same ChromaDB instance
chroma = get_chroma_client()
knowledge_collection = chroma["career_knowledge"]
episodic_collection = chroma["episodic_memory"]
```

**Why:**
- No data duplication (DRY)
- Agents see full context
- Simpler than syncing between isolated stores

### 2. Tool Sharing

**Recommendation:** Shared tool registry

```python
# src/fu7ur3pr00f/agents/tools/__init__.py
SHARED_TOOLS = {
    "profile": [...],
    "gathering": [...],
    "knowledge": [...],
}

# Agent-specific tools
COACH_TOOLS = SHARED_TOOLS["profile"] + [analyze_career_alignment, ...]
LEARNING_TOOLS = SHARED_TOOLS["gathering"] + [analyze_skill_gaps, ...]
```

**Why:**
- No code duplication (DRY)
- Consistent behavior across agents
- Easier maintenance

### 3. Routing Strategy

**Recommendation:** Intent classification with fallback

```python
INTENT_MAP = {
    "leadership": "coach",
    "strengths": "coach",
    "learning": "learning",
    "skills": "learning",
    "jobs": "jobs",
    "salary": "jobs",
    "github": "github",
    "repos": "github",
}

def route_request(query: str) -> str:
    # Simple keyword matching first
    for keyword, agent in INTENT_MAP.items():
        if keyword in query.lower():
            return agent
    
    # Fallback to orchestrator
    return "orchestrator"
```

**Why:**
- Simple and predictable (KISS)
- No ML overhead
- Easy to extend

### 4. Response Synthesis

**Recommendation:** Orchestrator synthesizes all agent responses

```python
async def synthesize(agent_responses: dict[str, str]) -> str:
    """Combine agent responses into coherent answer."""
    
    synthesis_prompt = f"""
    Synthesize responses from multiple agents:
    
    Coach: {agent_responses.get('coach', 'N/A')}
    Learning: {agent_responses.get('learning', 'N/A')}
    Jobs: {agent_responses.get('jobs', 'N/A')}
    GitHub: {agent_responses.get('github', 'N/A')}
    
    Provide a unified, actionable response.
    """
    
    return await call_llm(synthesis_prompt)
```

**Why:**
- Single point of synthesis (DRY)
- Consistent voice
- User sees one answer, not fragmented responses

---

## When NOT to Use Multi-Agent

**Stick with single-agent if:**

1. **Simple queries** — "What's my current role?" doesn't need routing
2. **Cross-cutting concerns** — CV generation uses data from all sources
3. **Context-heavy tasks** — Long conversations lose context between agents
4. **Performance critical** — Each hop adds latency

**Hybrid approach:**
- Single agent for simple tasks
- Multi-agent for complex, multi-domain requests

---

## Migration Path

### Option A: Gradual Migration (Recommended)

1. Keep single-agent as default
2. Add multi-agent for specific workflows
3. Compare performance
4. Migrate more workflows if proven better

```python
# Orchestrator decides per-request
if is_complex_request(query):
    response = await multi_agent_pipeline(query)
else:
    response = await single_agent(query)
```

### Option B: Full Replacement (Risky)

1. Build complete multi-agent system
2. Test thoroughly
3. Switch all traffic at once
4. Rollback if issues

**Not recommended** — Too much risk, no fallback

---

## Testing Strategy

### Unit Tests (Per Agent)

```python
def test_coach_agent_strengths_analysis():
    agent = CoachAgent()
    context = {"user_id": "test", "query": "leadership strengths"}
    response = agent.process(context)
    assert "strengths" in response.lower()
```

### Integration Tests (Agent Team)

```python
async def test_multi_agent_career_plan():
    orchestrator = OrchestratorAgent()
    query = "Plan my transition to Staff Engineer"
    response = await orchestrator.handle(query)
    assert "learning" in response
    assert "leadership" in response
```

### Performance Benchmarks

```python
def benchmark_single_vs_multi():
    single_times = []
    multi_times = []
    
    for query in test_queries:
        single_times.append(time(single_agent, query))
        multi_times.append(time(multi_agent, query))
    
    assert median(multi_times) < median(single_times) * 1.5  # <50% slower
```

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context loss between agents | High | Shared memory, context passing |
| Increased latency | Medium | Parallel agent execution |
| Routing errors | Medium | Fallback to orchestrator |
| Code duplication | Medium | Shared base classes, tool registry |
| Testing complexity | Low | Per-agent unit tests, integration tests |

---

## Decision Framework

**Before implementing, answer:**

1. **What specific problem does this solve?**
   - Current single-agent limitation: _______
   - Multi-agent improvement: _______

2. **How will we measure success?**
   - Metric: _______
   - Baseline: _______
   - Target: _______

3. **What's the rollback plan?**
   - If multi-agent fails: _______

4. **Is this YAGNI?**
   - Do we have user requests for this? Yes/No
   - Are we building for hypothetical future? Yes/No

---

## Next Steps

1. **Build prototype** — Minimal multi-agent for one workflow
2. **Benchmark** — Compare to single-agent
3. **Decide** — Proceed, iterate, or abandon

**Prototype scope:**
- Coach Agent only (CliftonStrengths + LinkedIn)
- Simple routing (keyword-based)
- One workflow: "Analyze my leadership strengths"

**Success criteria:**
- Response quality ≥ single-agent
- Latency < 2x single-agent
- No context loss

---

## See Also

- [Architecture](docs/architecture.md) — Current single-agent design
- [Tools Reference](docs/tools.md) — Available tools
- [Memory System](docs/memory_system.md) — Shared memory design

---
status: Draft
version: 0.1.0
created: 2025-03-23
author: @juanmanueldaza
revisions:
  - 2025-03-23: Initial multi-agent architecture proposal
---

# Multi-Agent Architecture Summary

**TL;DR:** FutureProof is building a multi-agent system to help developers **succeed on their own terms** — not just find jobs.

---

## Vision

**FutureProof is NOT a job search tool.**

We help developers succeed whether they want to:
| Success Path | Agent |
|--------------|-------|
| Get promoted to Staff Engineer | Coach Agent |
| Launch a startup | Founder Agent |
| Become recognized expert | Learning + Code Agent |
| Find remote work | Jobs Agent |
| Build impactful open source | Code Agent |
| Start consulting | Founder + Jobs Agent |

**Read:** [Vision Statement](vision-developer-success.md) | [Values](values.md) | [Diagrams](diagrams.md)

---

## Agent Team

```
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Agent (Main)                      │
│  "What does success look like for you?"                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│  Coach Agent  │   │  Learning Agent │   │  Jobs Agent   │
│  Leadership   │   │  Skill mastery  │   │  Employment   │
│  Promotion    │   │  Expert status  │   │  Remote work  │
└───────────────┘   └─────────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Code Agent    │
                    │  GitHub+GitLab  │
                    │  OSS strategy   │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Founder Agent  │
                    │  Startups       │
                    │  Co-founders    │
                    │  Launch plan    │
                    └─────────────────┘
```

---

## Agent Responsibilities

| Agent | For Developers Who Want To... | Key Features |
|-------|-------------------------------|--------------|
| **Coach** | Get promoted, lead teams | CliftonStrengths, leadership plan |
| **Learning** | Become technical expert | Skill gaps, learning roadmap |
| **Jobs** | Find better employment | 7 job boards, salary insights |
| **Code** | Build impactful projects | GitHub+GitLab, OSS strategy |
| **Founder** | Launch companies | Opportunity ID, co-founder matching |

---

## Key Design Decisions

### 1. No A2A Protocol

**Decision:** Direct function calls, not A2A protocol

**Why:**
- A2A is for cross-vendor communication (Salesforce ↔ SAP)
- We're single codebase, internal agents
- Direct calls are simpler (KISS), faster, type-safe

### 2. Shared Memory

**Decision:** All agents share same ChromaDB

**Why:**
- No data duplication (DRY)
- All agents see full context
- Simpler than syncing isolated stores

### 3. Simple Router

**Decision:** Keyword-based intent routing

**Why:**
- Simple and predictable (KISS)
- No ML overhead
- Easy to extend

### 4. Fallback to Single-Agent

**Decision:** Hybrid approach during migration

**Why:**
- Safe migration path
- Can revert if multi-agent fails
- Simple queries don't need routing

---

## Implementation Plan

### Phase 0: Prove It Works (Week 1)
- ✅ Create `BaseAgent` class
- ⏳ Implement `CoachAgent` only
- ⏳ Test: "Analyze my leadership strengths"
- ⏳ Benchmark vs single-agent

### Phase 1: Core Agents (Week 2-3)
- ⏳ Learning Agent
- ⏳ Code Agent (GitHub + GitLab)
- ⏳ Jobs Agent (minimal changes)
- ⏳ Router with intent classification

### Phase 2: Differentiator (Week 4)
- ⏳ Founder Agent (entrepreneurial focus)
- ⏳ Orchestrator synthesis
- ⏳ Parallel agent execution

### Phase 3: Migration (Week 5+)
- ⏳ Gradual migration from single-agent
- ⏳ Performance benchmarking
- ⏳ User feedback

---

## Files to Read

| File | Purpose |
|------|---------|
| [README](README.md) | **Start here** — Quick summary |
| [vision-developer-success.md](vision-developer-success.md) | **Vision** — Why we're doing this |
| [values.md](values.md) | **Core Values** — Free software, hacker ethic, OSS |
| [multi-agent-design.md](multi-agent-design.md) | Full technical design |
| [founder-agent.md](founder-agent.md) | Founder Agent deep dive |
| [diagrams.md](diagrams.md) | Mermaid architecture diagrams |
| [multi-agent-architecture.md](multi-agent-architecture.md) | Initial proposal |

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Response quality | ≥ single-agent | User ratings |
| Latency | < 2x single-agent | Benchmarks |
| User satisfaction | 4/5 stars | Post-session survey |
| Path diversity | 40% non-job paths | Analytics |
| Goal achievement | 60%+ reach goals | Follow-up surveys |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Context loss | Shared memory, explicit passing |
| Increased latency | Parallel execution, caching |
| Routing errors | Fallback to orchestrator |
| YAGNI violation | Start with one agent, prove value |

---

## Next Steps

1. **Read vision statement** — Understand the "why"
2. **Review technical design** — Understand the "how"
3. **Implement Phase 0** — Coach Agent prototype
4. **Benchmark** — Compare to single-agent
5. **Decide** — Proceed, iterate, or abandon

---

**Bottom Line:**

We're not building a job search tool.

We're building a **developer success tool**.

Jobs are one path. Success is the destination.

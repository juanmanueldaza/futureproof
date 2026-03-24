---
status: Draft
version: 0.1.0
created: 2025-03-23
author: @juanmanueldaza
revisions:
  - 2025-03-23: Multi-agent pattern comparison (7 patterns evaluated)
---

# Multi-Agent Pattern Options

**Complete guide to multi-agent design patterns** and why we chose Orchestrator-Specialist for FutureProof.

---

## Overview: 7 Multi-Agent Patterns

| Pattern | Complexity | Best For | FutureProof Fit |
|---------|------------|----------|-----------------|
| **1. Orchestrator-Specialist** | Medium | Domain specialization | ✅ **CHOSEN** |
| 2. Hierarchical | High | Complex task decomposition | ⚠️ Overkill |
| 3. Peer-to-Peer | Low | Simple, equal agents | ❌ No coordination |
| 4. Blackboard | High | Collaborative problem-solving | ❌ Too complex |
| 5. Pipeline | Medium | Sequential workflows | ❌ Too rigid |
| 6. Swarm | High | Parallel exploration | ❌ Unpredictable |
| 7. Marketplace | High | Competitive task assignment | ❌ Too complex |

---

## 1. Orchestrator-Specialist ✅ (CHOSEN)

```
                    ┌─────────────────┐
                    │  Orchestrator   │
                    │  (coordinator)  │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ Specialist│    │ Specialist│    │ Specialist│
    │  Agent A  │    │  Agent B  │    │  Agent C  │
    └──────────┘     └──────────┘     └──────────┘
```

**How it works:**
- Central orchestrator receives all requests
- Routes to specialist based on intent
- Specialists process independently
- Orchestrator synthesizes final response

**Pros:**
- ✅ Clear separation of concerns
- ✅ Easy to add new specialists
- ✅ Centralized control and values
- ✅ Specialists can be tested independently
- ✅ Shared memory easy to implement

**Cons:**
- ❌ Orchestrator is single point of failure
- ❌ Can become bottleneck
- ❌ Routing logic can get complex

**Used by:**
- FutureProof (obviously)
- Many enterprise AI systems
- Customer service bots with domain routing

**Why we chose it:**
> Perfect for our use case: different success paths (career, startup, mastery) need different expertise, but all share values and memory.

---

## 2. Hierarchical (Multi-Level Orchestrator)

```
                    ┌─────────────────┐
                    │  Master Agent   │
                    │  (top level)    │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Sub-Orchestrator│ │ Sub-Orchestrator│ │ Sub-Orchestrator│
    │   (Career)   │ │   (Startup)  │ │   (Learning) │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                 │                 │
    ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐
    ▼             ▼   ▼             ▼   ▼             ▼
┌──────┐    ┌──────┐ ┌──────┐   ┌──────┐ ┌──────┐  ┌──────┐
│Coach │    │Jobs  │ │Founder│  │Code  │ │Learn │  │Docs  │
└──────┘    └──────┘ └──────┘   └──────┘ └──────┘  └──────┘
```

**How it works:**
- Multiple levels of orchestration
- Master agent delegates to sub-orchestrators
- Sub-orchestrators manage leaf agents
- Results bubble up through hierarchy

**Pros:**
- ✅ Scales to many agents (100+)
- ✅ Clear organizational structure
- ✅ Can model complex domains

**Cons:**
- ❌ High latency (multiple hops)
- ❌ Complex to implement
- ❌ Hard to debug
- ❌ Over-engineered for our needs

**Used by:**
- Large enterprise systems
- Government/military AI
- Complex simulation systems

**Why we rejected it:**
> We have 5 agents, not 50. Hierarchy adds latency and complexity without benefit. KISS principle says: start simple, add levels only if needed.

---

## 3. Peer-to-Peer (Mesh)

```
    ┌──────┐         ┌──────┐
    │Agent │◄───────►│Agent │
    │  A   │         │  B   │
    └──┬───┘         └──┬───┘
       │                │
       │    ┌──────┐    │
       └───►│Agent │◄───┘
            │  C   │
       ┌───►│      │◄───┐
       │    └──────┘    │
       │                │
    ┌──┴───┐         ┌──┴───┐
    │Agent │◄───────►│Agent │
    │  D   │         │  E   │
    └──────┘         └──────┘
```

**How it works:**
- All agents are equal (no orchestrator)
- Agents communicate directly
- Each agent can route to others
- Emergent coordination

**Pros:**
- ✅ No single point of failure
- ✅ Flexible, adaptive
- ✅ Low latency (direct communication)

**Cons:**
- ❌ No central coordination
- ❌ Hard to enforce values consistently
- ❌ Can lead to circular conversations
- ❌ Difficult to debug

**Used by:**
- Distributed sensor networks
- Swarm robotics
- Decentralized AI research

**Why we rejected it:**
> We need central coordination for values enforcement and success-path routing. P2P is too anarchic for our opinionated stance.

---

## 4. Blackboard (Shared Workspace)

```
    ┌─────────────────────────────────────────┐
    │           BLACKBOARD                    │
    │  (Shared problem-solving workspace)     │
    │                                         │
    │  Problem: "Should I quit my job?"       │
    │  ─────────────────────────────────      │
    │  [Coach]: Analyzing strengths...        │
    │  [Founder]: Market opportunity: HIGH    │
    │  [Jobs]: Backup options: 50 roles       │
    │  [Code]: Project quality: 85/100        │
    │  ─────────────────────────────────      │
    │  Solution: Build MVP while employed     │
    └─────────────────────────────────────────┘
           ▲                ▲                ▲
           │                │                │
    ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
    │   Agent A   │  │   Agent B   │  │   Agent C   │
    │ (specialist)│  │ (specialist)│  │ (specialist)│
    └─────────────┘  └─────────────┘  └─────────────┘
```

**How it works:**
- Shared workspace (blackboard) holds problem state
- Agents read from and write to blackboard
- Agents contribute when they have relevant expertise
- Solution emerges from collaboration

**Pros:**
- ✅ True collaboration (agents build on each other's insights)
- ✅ Flexible problem-solving
- ✅ Good for complex, multi-faceted problems

**Cons:**
- ❌ Complex to implement
- ❌ Requires conflict resolution
- ❌ Can have race conditions
- ❌ Overkill for our use case

**Used by:**
- Medical diagnosis systems
- Scientific research AI
- Complex planning systems

**Why we rejected it:**
> We don't need true collaboration — each query has a clear primary agent. Blackboard is for problems where multiple agents must genuinely collaborate on the same subproblem.

---

## 5. Pipeline (Sequential)

```
┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐
│Agent │───►│Agent │───►│Agent │───►│Agent │───►│Agent │
│  A   │    │  B   │    │  C   │    │  D   │    │  E   │
└──────┘    └──────┘    └──────┘    └──────┘    └──────┘
  Input      Enrich      Analyze     Plan       Output
```

**How it works:**
- Agents arranged in sequence
- Each agent processes and passes to next
- Output of one is input to next
- Linear workflow

**Pros:**
- ✅ Simple to understand
- ✅ Easy to debug (clear flow)
- ✅ Good for well-defined workflows

**Cons:**
- ❌ Inflexible (can't skip steps)
- ❌ High latency (sequential)
- ❌ Can't handle branching logic
- ❌ Not suitable for varied queries

**Used by:**
- Document processing pipelines
- Data transformation workflows
- Content moderation systems

**Why we rejected it:**
> User queries are too varied. Sometimes we need Coach only, sometimes Founder + Code + Jobs. Pipeline is too rigid.

---

## 6. Swarm (Parallel Exploration)

```
              ┌──────────┐
              │  Query   │
              └────┬─────┘
                   │
         ┌─────────┼─────────┐
         │         │         │
         ▼         ▼         ▼
    ┌────────┐ ┌────────┐ ┌────────┐
    │ Agent  │ │ Agent  │ │ Agent  │
    │   A    │ │   B    │ │   C    │
    └───┬────┘ └───┬────┘ └───┬────┘
        │         │         │
        └─────────┼─────────┘
                  │
                  ▼
         ┌────────────────┐
         │  Aggregator    │
         │ (best answer)  │
         └────────────────┘
```

**How it works:**
- Query sent to ALL agents in parallel
- Each agent provides independent answer
- Aggregator selects best answer
- Like parallel brainstorming

**Pros:**
- ✅ Maximum exploration
- ✅ No agent biases the others
- ✅ Can discover unexpected insights

**Cons:**
- ❌ Expensive (all agents run every time)
- ❌ Wasteful (most agents irrelevant)
- ❌ Hard to aggregate conflicting answers
- ❌ Unpredictable which agent "wins"

**Used by:**
- Research exploration systems
- Creative brainstorming AI
- Competitive evaluation systems

**Why we rejected it:**
> Too wasteful. If user asks about startups, we don't need Jobs Agent running. We want targeted expertise, not parallel exploration.

---

## 7. Marketplace (Competitive Bidding)

```
              ┌──────────┐
              │  Query   │
              └────┬─────┘
                   │
                   ▼
         ┌───────────────────┐
         │    AUCTIONEER     │
         │  (posts task)     │
         └─────────┬─────────┘
                   │
         ┌─────────┼─────────┐
         │         │         │
         ▼         ▼         ▼
    ┌────────┐ ┌────────┐ ┌────────┐
    │ Agent  │ │ Agent  │ │ Agent  │
    │   A    │ │   B    │ │   C    │
    │ "I can │ │ "I can │ │ "I can │
    │ do it!"│ │ do it!"│ │ do it!"│
    └───┬────┘ └───┬────┘ └───┬────┘
        │         │         │
        └─────────┼─────────┘
                  │
                  ▼
         ┌────────────────┐
         │  Auctioneer    │
         │ (selects bid)  │
         └────────────────┘
```

**How it works:**
- Auctioneer posts task
- Agents bid (claim they can do it)
- Auctioneer selects best bid
- Selected agent executes task

**Pros:**
- ✅ Dynamic task assignment
- ✅ Agents self-select based on capability
- ✅ Can handle agent failures gracefully

**Cons:**
- ❌ Complex bidding logic
- ❌ Overhead of auction process
- ❌ Can lead to gaming the system
- ❌ Unpredictable which agent wins

**Used by:**
- Task allocation in robotics
- Distributed computing
- Gig economy platforms

**Why we rejected it:**
> We know which agent should handle each query (keyword routing). No need for bidding overhead. KISS principle.

---

## Comparison Matrix

| Pattern | Complexity | Latency | Flexibility | Debugging | Our Fit |
|---------|------------|---------|-------------|-----------|---------|
| **Orchestrator-Specialist** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Perfect |
| Hierarchical | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ❌ Overkill |
| Peer-to-Peer | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ❌ No coordination |
| Blackboard | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ❌ Too complex |
| Pipeline | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ❌ Too rigid |
| Swarm | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ❌ Wasteful |
| Marketplace | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ❌ Unnecessary |

---

## Why Orchestrator-Specialist Wins for FutureProof

### Technical Reasons

1. **Clear separation of concerns** — Each agent has one job
2. **Easy to test** — Can test each specialist independently
3. **Shared memory** — Easy to implement with ChromaDB
4. **Values enforcement** — Orchestrator ensures all agents uphold values
5. **Scalable** — Can add new specialists without changing others

### Philosophical Reasons

1. **KISS** — Simple enough to understand, complex enough to work
2. **DRY** — Shared tools and memory, no duplication
3. **SOLID** — Single Responsibility Principle per agent
4. **YAGNI** — Start with 5 agents, add more only if needed

### User Experience Reasons

1. **Consistent voice** — Orchestrator synthesizes into coherent response
2. **Values-aligned** — All responses filtered through shared values
3. **Fast enough** — Parallel execution where possible
4. **Predictable** — Users know what to expect

---

## When We Might Evolve

### To Hierarchical (if...)
- We have 20+ agents
- Need sub-orchestrators for domains
- Single orchestrator becomes bottleneck

### To Blackboard (if...)
- Agents need true collaboration on same problem
- Problems are genuinely multi-faceted
- Insights build on each other

### To P2P (if...)
- We want emergent behavior
- Decentralization is a goal (not just technical choice)
- Can tolerate less predictability

**For now: Orchestrator-Specialist is the right choice.**

---

## See Also

- [Multi-Agent Design](multi-agent-design.md) — Our implementation
- [Values](values.md) — What all agents believe
- [Diagrams](diagrams.md) — Visual representations

---

**Bottom line:** We chose Orchestrator-Specialist because it's the simplest pattern that solves our actual problem. Not too simple (Pipeline), not too complex (Hierarchical, Blackboard). Just right.

---
status: Draft
version: 0.1.0
created: 2025-03-23
author: @juanmanueldaza
revisions:
  - 2025-03-23: 11 Mermaid diagrams for multi-agent architecture
---

# Multi-Agent Architecture Diagrams

Visual representations of the FutureProof multi-agent system.

---

## Reading Order

**Start here:**
1. [Overall Architecture](#1-overall-agent-architecture) — Big picture view
2. [Success Paths Flow](#2-success-paths-flow) — How routing works
3. [Request Flow](#3-request-flow-detailed) — Detailed sequence diagram

**Deep dive:**
4. [Agent Collaboration](#4-agent-collaboration-example) — How agents work together
5. [Single vs. Multi-Agent](#5-single-agent-vs-multi-agent-comparison) — Architecture comparison
6. [Data Flow](#6-data-flow-shared-memory-pattern) — Shared memory design

**Reference:**
7. [Intent Routing](#7-intent-based-routing) — Keyword matching flow
8. [Implementation Timeline](#8-phase-based-implementation) — Gantt chart
9. [Success Metrics](#9-success-metrics-dashboard) — How we measure success
10. [Decision Tree](#10-agent-decision-tree) — Routing logic
11. [Communication Pattern](#11-multi-agent-communication-pattern) — Full system view

---

## 1. Overall Agent Architecture

```mermaid
graph TB
    subgraph User
        U[Developer]
    end

    subgraph Orchestrator["Orchestrator Agent (Main)"]
        O1["First Question:<br/>What does success look like?"]
        O2["Route Request"]
        O3["Synthesize Response"]
    end

    subgraph Specialists["Specialist Agents"]
        C[Coach Agent<br/>Leadership & Promotion]
        L[Learning Agent<br/>Skill Mastery]
        J[Jobs Agent<br/>Employment]
        CD[Code Agent<br/>GitHub + GitLab]
        F[Founder Agent<br/>Startups & Launches]
    end

    subgraph Memory["Shared Memory"]
        ChromaDB[(ChromaDB<br/>Knowledge + Episodic)]
        Tools[Shared Tool Registry]
    end

    U -->|"Career question"| O1
    O1 --> O2
    O2 -->|"Leadership"| C
    O2 -->|"Skills"| L
    O2 -->|"Jobs"| J
    O2 -->|"Code/Repos"| CD
    O2 -->|"Startup"| F
    
    C --> O3
    L --> O3
    J --> O3
    CD --> O3
    F --> O3
    
    O3 --> U
    
    C <--> ChromaDB
    L <--> ChromaDB
    J <--> ChromaDB
    CD <--> ChromaDB
    F <--> ChromaDB
    
    C <--> Tools
    L <--> Tools
    J <--> Tools
    CD <--> Tools
    F <--> Tools
```

---

## 2. Success Paths Flow

```mermaid
flowchart LR
    Start[Developer Question] --> Router{Orchestrator<br/>Routes Request}
    
    Router -->|"Get promoted"| Coach
    Router -->|"Launch startup"| Founder
    Router -->|"Become expert"| Learning
    Router -->|"Find job"| Jobs
    Router -->|"Build OSS"| Code
    
    Coach --> Success1["Career Growth<br/>Promotion, Leadership"]
    Founder --> Success2["Entrepreneurship<br/>Product Launch, Equity"]
    Learning --> Success3["Technical Mastery<br/>Expert Status"]
    Jobs --> Success4["Employment<br/>Better Job, Remote"]
    Code --> Success5["Open Source Impact<br/>Community Respect"]
    
    Success1 --> Goal["Developer Success<br/>On Their Own Terms"]
    Success2 --> Goal
    Success3 --> Goal
    Success4 --> Goal
    Success5 --> Goal
    
    style Goal fill:#90EE90,stroke:#333,stroke-width:3px
```

---

## 3. Request Flow (Detailed)

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant C as Coach Agent
    participant L as Learning Agent
    participant F as Founder Agent
    participant M as Shared Memory
    
    U->>O: "Should I quit my job and build my startup?"
    
    O->>O: Analyze intent
    O->>M: Get user profile
    M-->>O: CliftonStrengths, projects, goals
    
    par Parallel Agent Execution
        O->>F: Route to Founder Agent
        F->>M: Get projects from Code Agent
        F->>M: Assess founder-market fit
        F-->>O: Opportunity analysis
        
        O->>C: Route to Coach Agent
        C->>M: Get strengths
        C-->>O: Leadership potential
        
        O->>J: Route to Jobs Agent
        J->>M: Get market data
        J-->>O: Backup job options
    end
    
    O->>O: Synthesize all responses
    O-->>U: "Based on your strengths (Activator #2),<br/>market opportunity, and project quality:<br/>Consider building MVP while employed.<br/>Here's your 6-month roadmap..."
```

---

## 4. Agent Collaboration Example

```mermaid
graph LR
    subgraph UserGoal["User Goal: Launch Startup"]
        G["I have a side project<br/>with traction. Should I<br/>quit my job?"]
    end
    
    subgraph Agents["Agent Team"]
        F[Founder Agent<br/>• Opportunity analysis<br/>• Launch roadmap<br/>• Co-founder matching]
        C[Coach Agent<br/>• Strengths for founder fit<br/>• Leadership potential]
        CD[Code Agent<br/>• Project quality<br/>• GitHub+GitLab analysis]
        J[Jobs Agent<br/>• Backup options<br/>• Market demand]
    end
    
    subgraph Synthesis["Orchestrator Synthesis"]
        S["Balanced Recommendation:<br/>✓ Strong founder fit<br/>✓ Project shows traction<br/>⚠ Find co-founder first<br/>⚠ Keep job until MVP<br/>📋 6-month roadmap"]
    end
    
    G --> F
    G --> C
    G --> CD
    G --> J
    
    F --> S
    C --> S
    CD --> S
    J --> S
    
    S --> G
```

---

## 5. Single-Agent vs. Multi-Agent Comparison

```mermaid
graph TB
    subgraph Single["Single-Agent Architecture (Current)"]
        U1[User] --> SA[Single Agent<br/>40 Tools]
        SA --> Chroma1[(ChromaDB)]
        SA --> Tools1[All Tools<br/>Profile, Gathering,<br/>Analysis, Market,<br/>Generation, Memory]
        
        style SA fill:#FFB6C1,stroke:#333
    end
    
    subgraph Multi["Multi-Agent Architecture (Proposed)"]
        U2[User] --> OA[Orchestrator Agent<br/>Routes + Synthesizes]
        OA --> C2[Coach Agent]
        OA --> L2[Learning Agent]
        OA --> J2[Jobs Agent]
        OA --> CD2[Code Agent]
        OA --> F2[Founder Agent]
        
        C2 --> Chroma2[(Shared<br/>ChromaDB)]
        L2 --> Chroma2
        J2 --> Chroma2
        CD2 --> Chroma2
        F2 --> Chroma2
        
        style OA fill:#98FB98,stroke:#333
        style C2 fill:#87CEEB,stroke:#333
        style L2 fill:#87CEEB,stroke:#333
        style J2 fill:#87CEEB,stroke:#333
        style CD2 fill:#87CEEB,stroke:#333
        style F2 fill:#87CEEB,stroke:#333
    end
    
    Single -.->|"Limited specialization<br/>Job-centric bias"| Multi
```

---

## 6. Data Flow: Shared Memory Pattern

```mermaid
graph TB
    subgraph Agents["All Agents"]
        A1[Coach]
        A2[Learning]
        A3[Jobs]
        A4[Code]
        A5[Founder]
    end
    
    subgraph Memory["Shared Memory Layer"]
        KB[(Knowledge Base<br/>Career Data)]
        EM[(Episodic Memory<br/>Decisions, Apps)]
        TR[Tool Registry<br/>40 Shared Tools]
    end
    
    subgraph Data["Data Sources"]
        LI[LinkedIn]
        GH[GitHub]
        GL[GitLab]
        CS[CliftonStrengths]
        PF[Portfolio]
        JB[Job Boards]
    end
    
    A1 <--> KB
    A2 <--> KB
    A3 <--> KB
    A4 <--> KB
    A5 <--> KB
    
    A1 <--> EM
    A2 <--> EM
    A3 <--> EM
    A4 <--> EM
    A5 <--> EM
    
    A1 <--> TR
    A2 <--> TR
    A3 <--> TR
    A4 <--> TR
    A5 <--> TR
    
    LI --> KB
    GH --> KB
    GL --> KB
    CS --> KB
    PF --> KB
    JB --> KB
```

---

## 7. Intent-Based Routing

```mermaid
flowchart TD
    Query[User Query] --> Keywords{Keyword Matching}
    
    Keywords -->|"leadership, strengths,<br/>promotion, coaching"| Coach[Coach Agent]
    Keywords -->|"learning, skills,<br/>study, courses"| Learning[Learning Agent]
    Keywords -->|"jobs, hiring,<br/>salary, interview"| Jobs[Jobs Agent]
    Keywords -->|"github, gitlab,<br/>repos, code, oss"| Code[Code Agent]
    Keywords -->|"startup, founder,<br/>launch, product,<br/>cofounder"| Founder[Founder Agent]
    
    Keywords -->|"No match"| Fallback[Orchestrator Fallback<br/>Ask clarifying question]
    
    Coach --> Response[Synthesize & Respond]
    Learning --> Response
    Jobs --> Response
    Code --> Response
    Founder --> Response
    Fallback --> Response
    
    style Coach fill:#FFB6C1
    style Learning fill:#87CEEB
    style Jobs fill:#98FB98
    style Code fill:#DDA0DD
    style Founder fill:#FFD700
```

---

## 8. Phase-Based Implementation

```mermaid
gantt
    title Multi-Agent Implementation Timeline
    dateFormat  YYYY-MM-DD
    section Phase 0
    BaseAgent Class       :done,    base, 2025-03-01, 3d
    Coach Agent           :active,  coach, after base, 4d
    Simple Router         :         router, after base, 2d
    Benchmark             :         bench, after coach, 2d
    
    section Phase 1
    Learning Agent        :         learn, after bench, 4d
    Code Agent            :         code, after bench, 4d
    Jobs Agent            :         jobs, after bench, 2d
    Integration Tests     :         tests, after learn, 3d
    
    section Phase 2
    Founder Agent         :         founder, after tests, 5d
    Parallel Execution    :         parallel, after tests, 3d
    Synthesis Logic       :         synth, after founder, 3d
    
    section Phase 3
    Hybrid Migration      :         migrate, after synth, 5d
    Performance Bench     :         perf, after migrate, 3d
    User Feedback         :         feedback, after migrate, 7d
```

---

## 9. Success Metrics Dashboard

```mermaid
graph LR
    subgraph Metrics["Success Metrics"]
        Quality[Response Quality<br/>≥ Single-Agent]
        Latency[Latency<br/>< 2x Single-Agent]
        Satisfaction[User Satisfaction<br/>4/5 Stars]
        Diversity[Path Diversity<br/>40% Non-Job]
        Achievement[Goal Achievement<br/>60%+ Reach Goals]
    end
    
    subgraph Collection["Data Collection"]
        PR[Post-Session Ratings]
        FU[Follow-Up Surveys<br/>6-month, 1-year]
        AN[Analytics<br/>Path Chosen]
        BN[Benchmarks<br/>Latency, Quality]
    end
    
    PR --> Quality
    PR --> Satisfaction
    FU --> Achievement
    AN --> Diversity
    BN --> Latency
    
    style Quality fill:#90EE90
    style Latency fill:#90EE90
    style Satisfaction fill:#90EE90
    style Diversity fill:#FFD700
    style Achievement fill:#FFD700
```

---

## 10. Agent Decision Tree

```mermaid
graph TD
    Start[User Question] --> Q1{"What does<br/>success look like?"}
    
    Q1 -->|"Grow at company"| Q2{"What kind of growth?"}
    Q2 -->|"Leadership"| Coach
    Q2 -->|"Technical Expert"| Learning
    
    Q1 -->|"Build something"| Q3{"Build what?"}
    Q3 -->|"Company/Startup"| Founder
    Q3 -->|"Open Source"| Code
    
    Q1 -->|"Find job"| Q4{"What kind?"}
    Q4 -->|"Remote/Flexible"| Jobs
    Q4 -->|"Higher Salary"| Jobs
    
    Q1 -->|"Time Freedom"| Freedom[Freedom Agent<br/>Future]
    Q1 -->|"Financial Independence"| Wealth[Wealth Agent<br/>Future]
    
    Coach --> Action[Action Plan]
    Learning --> Action
    Founder --> Action
    Code --> Action
    Jobs --> Action
    Freedom --> Action
    Wealth --> Action
    
    style Coach fill:#FFB6C1
    style Learning fill:#87CEEB
    style Founder fill:#FFD700
    style Code fill:#DDA0DD
    style Jobs fill:#98FB98
```

---

## 11. Multi-Agent Communication Pattern

```mermaid
graph TB
    subgraph Orchestrator["Orchestrator Agent"]
        O1[Intent Classifier]
        O2[Context Manager]
        O3[Response Synthesizer]
    end
    
    subgraph Agents["Specialist Agents"]
        C[Coach Agent]
        L[Learning Agent]
        J[Jobs Agent]
        CD[Code Agent]
        F[Founder Agent]
    end
    
    subgraph Shared["Shared Resources"]
        ChromaDB[(ChromaDB<br/>Shared Memory)]
        Tools[Tool Registry]
        LLM[LLM Fallback Chain]
    end
    
    O1 --> C
    O1 --> L
    O1 --> J
    O1 --> CD
    O1 --> F
    
    C <--> ChromaDB
    L <--> ChromaDB
    J <--> ChromaDB
    CD <--> ChromaDB
    F <--> ChromaDB
    
    C <--> Tools
    L <--> Tools
    J <--> Tools
    CD <--> Tools
    F <--> Tools
    
    C <--> LLM
    L <--> LLM
    J <--> LLM
    CD <--> LLM
    F <--> LLM
    
    C --> O3
    L --> O3
    J --> O3
    CD --> O3
    F --> O3
```

---

## See Also

- [Multi-Agent Design](multi-agent-design.md) — Technical specification
- [Vision Statement](vision-developer-success.md) — Why we're doing this
- [Founder Agent](founder-agent.md) — Entrepreneurial focus

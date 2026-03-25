# Architecture

## Overview

FutureProof is a career intelligence agent with two modes:

- **Single Agent (default):** One `career_agent.py` with 41 tools — used for every typed message in the chat loop
- **Multi-Agent (opt-in):** Orchestrator routes to specialist agents (Coach, Learning, Jobs, Code, Founder) — accessed via `/multi` in chat

## Design Decisions

### Single Agent

**Why**: Original multi-agent handoffs failed with GPT-4.1 due to over-delegation and lost context.

**Implementation**: One agent (`career_agent.py`) with all tools registered. Tools are organized by domain:
- Profile management
- Data gathering
- GitHub / GitLab access
- Career analysis
- CV generation
- Knowledge base search
- Market intelligence
- Financial calculations
- Episodic memory
- Settings

### Multi-Agent (opt-in via `/multi`)

Specialist agents for focused domains, routed by an `OrchestratorAgent`:

| Agent | Focus |
|-------|-------|
| `CoachAgent` | Career growth, leadership, promotions |
| `LearningAgent` | Skill development, expertise building |
| `JobsAgent` | Job search, market fit, salary |
| `CodeAgent` | GitHub, GitLab, open source |
| `FounderAgent` | Startups, entrepreneurship |

### Database-First Pipeline

**Why**: Intermediate files add complexity and slow down the pipeline.

**Implementation**: Gatherers return `Section` NamedTuples and index directly to ChromaDB. No markdown header roundtrip.

```
Gatherer → Section NamedTuple → ChromaDB → RAG search
```

### Two-Pass Synthesis

**Why**: GPT-4o genericizes analysis responses regardless of prompt engineering.

**Implementation**: `AnalysisSynthesisMiddleware` masks analysis tool results from the agent model, then replaces the generic final response with focused synthesis from a reasoning model.

```
Agent → Tool execution → Masked results for agent model
                       → Reasoning model synthesis → Final response
```

Analysis tool results (skill gaps, alignment, advice) are displayed directly to the user in Rich panels during streaming. The agent only sees a short marker so it cannot rewrite them.

### Summarization Middleware

**Why**: Long conversations exceed model context windows.

**Implementation**: `SummarizationMiddleware` compresses message history when it exceeds 16,000 tokens, keeping the most recent 20 messages intact.

```
Long history → SummarizationMiddleware → Compressed summary + recent messages
```

### Multi-Provider LLM Fallback

**Why**: Reliability. If one provider fails, fall back to another.

**Implementation**: `FallbackLLMManager` routes requests based on purpose:
- `AGENT_MODEL` — Tool calling
- `ANALYSIS_MODEL` — Analysis / CV generation
- `SUMMARY_MODEL` — Summarization
- `SYNTHESIS_MODEL` — Synthesis (reasoning)
- `EMBEDDING_MODEL` — Embeddings

### HITL Confirmation

**Why**: Destructive or expensive operations should require user approval.

**Implementation**: LangGraph `interrupt()` pauses execution for:
- Full data gathering (`gather_all_career_data`)
- CV generation
- Knowledge clearing

## Memory Storage

Two separate stores:

| Store | Backend | Path | Purpose |
|-------|---------|------|---------|
| Conversation checkpoints | SQLite (`SqliteSaver`) | `~/.fu7ur3pr00f/memory.db` | Per-thread message history, agent state, time-travel |
| Episodic + knowledge | ChromaDB | `~/.fu7ur3pr00f/episodic/` | RAG over career data, episodic memories |

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User (Rich UI)                          │
│              prompt-toolkit input + Rich streaming output       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Chat Client (chat/client.py)                 │
│  - Slash command handler (/gather, /profile, /multi, etc.)     │
│  - HITL interrupt loop                                          │
│  - Summary echo detection                                       │
│  - Automatic model fallback on error                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Single Agent (41 tools) — career_agent.py          │
│  Middleware stack:                                              │
│  1. build_dynamic_prompt — injects live profile + KB stats     │
│  2. ToolCallRepairMiddleware — repairs orphaned tool_calls      │
│  3. AnalysisSynthesisMiddleware — two-pass synthesis            │
│  4. SummarizationMiddleware — context window management        │
│                                                                 │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐  │
│  │ Profile  │ Gathering│   MCP    │ Analysis │  Generation  │  │
│  │ Goals    │ LinkedIn │  GitHub  │ Skill gap│  CV (MD+PDF) │  │
│  │ Skills   │ Portfolio│  Jobs    │  Market  │              │  │
│  │ Salary   │ Strengths│  Tavily  │  Advice  │              │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │                     │                    │
           ▼                     ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐
│  ChromaDB        │  │  FallbackLLM     │  │  SQLite        │
│  (episodic/)     │  │  OpenAI/Anthropic│  │  (memory.db)   │
│  - Career KB     │  │  Google/Azure    │  │  Conversation  │
│  - Episodic mem  │  │  Ollama/Proxy    │  │  checkpoints   │
└──────────────────┘  └──────────────────┘  └────────────────┘
```

## Data Flow

### Gathering

1. User runs `/gather` (slash command) or tells the agent to gather data
2. `GathererService` (or individual gatherers) parse files from `~/.fu7ur3pr00f/data/raw/`
3. Each gatherer returns `Section` NamedTuples
4. Sections are chunked and indexed to ChromaDB with embeddings
5. User notified of completion

### Analysis

1. User asks a question in natural language (e.g., "what are my skill gaps for Staff Engineer?")
2. Agent queries ChromaDB for relevant context
3. Agent calls analysis tools (`analyze_skill_gaps`, `analyze_career_alignment`, `get_career_advice`)
4. Results displayed directly to user in Rich panels (streaming)
5. `AnalysisSynthesisMiddleware` replaces agent's generic final text with focused synthesis
6. Synthesized response returned to user

### CV Generation

1. User asks agent to generate CV (natural language)
2. HITL interrupt prompts for confirmation
3. Agent gathers relevant profile data from ChromaDB
4. CV generator creates Markdown
5. WeasyPrint converts to PDF
6. Both formats saved to `~/.fu7ur3pr00f/data/output/`

### Orchestrator (LangGraph Functional API)

The `orchestrator.py` module uses LangGraph's `@entrypoint` / `@task` Functional API for structured workflows. It is used by the analysis/advice tools internally:

- `analyze_task` — career analysis via LLM
- `analyze_market_task` — market-aware analysis
- `advise_task` — strategic career advice

These dispatch via a table (`_EXACT_HANDLERS`) to avoid long if-chains.

## Key Files

| File | Purpose |
|------|---------|
| `src/fu7ur3pr00f/agents/career_agent.py` | Single agent, middleware stack, singleton cache |
| `src/fu7ur3pr00f/agents/middleware.py` | Dynamic prompt, synthesis, tool repair middleware |
| `src/fu7ur3pr00f/agents/orchestrator.py` | LangGraph Functional API for analysis workflows |
| `src/fu7ur3pr00f/agents/multi_agent.py` | Multi-agent system (`/multi` command) |
| `src/fu7ur3pr00f/agents/specialists/` | Specialist agents (Coach, Learning, Jobs, Code, Founder) |
| `src/fu7ur3pr00f/llm/fallback.py` | Multi-provider fallback routing |
| `src/fu7ur3pr00f/memory/chromadb_store.py` | ChromaDB base store (episodic/ directory) |
| `src/fu7ur3pr00f/memory/checkpointer.py` | SQLite checkpointer (memory.db) |
| `src/fu7ur3pr00f/agents/tools/` | **41 tools** organized by domain |
| `src/fu7ur3pr00f/mcp/` | **12 MCP clients** for real-time data |
| `src/fu7ur3pr00f/gatherers/` | Data gathering (LinkedIn, CV, portfolio, assessments) |
| `src/fu7ur3pr00f/generators/` | CV generation (Markdown + PDF via WeasyPrint) |
| `src/fu7ur3pr00f/chat/client.py` | Chat loop, slash commands, HITL, streaming |

See [Tools Reference](tools.md) for the complete list of all 41 tools.  
See [MCP Clients](mcp_clients.md) for the complete list of all 12 MCP clients.

## See Also

- [Configuration](configuration.md)
- [Memory System](memory_system.md)
- [QWEN.md](../QWEN.md)

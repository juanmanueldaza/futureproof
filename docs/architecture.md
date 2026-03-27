# Architecture

## Overview

FutureProof is a career intelligence agent with two modes:

- **Single Agent (default):** One `career_agent.py` with 41 tools — used for every typed message in the chat loop
- **Multi-Agent (opt-in):** Orchestrator routes to specialist agents (Coach, Learning, Jobs, Code, Founder) — accessed via `/multi` in chat

## Design Decisions

### Single Agent (Default)

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

### Multi-Agent (LLM-Routed, opt-in via `/multi`)

Specialist agents for focused domains, routed by LLM-based semantic routing:

| Agent | Focus | Keywords |
|-------|-------|----------|
| `CoachAgent` | Career growth, leadership, promotions, mentoring | promotion, leadership, mentor, coach, career |
| `LearningAgent` | Skill development, expertise building, trending skills | learn, skill, course, certification, trending, tech |
| `JobsAgent` | Job search, market fit, salary, compensation | job, remote, salary, compensation, market fit |
| `CodeAgent` | GitHub, GitLab, open source contributions | github, gitlab, code, repository, open source |
| `FounderAgent` | Startups, entrepreneurship, product-market fit | startup, founder, bootstrap, raise, saas, business |

**Routing Architecture**:
- **Primary**: LLM-based semantic routing (`_route_with_llm`) using `purpose="summary"` model
- **Fallback**: Keyword matching (`_route_with_keywords`) if LLM unavailable
- **Input**: `route(query, conversation_history, turn_type)`
- **Output**: `list[str]` of 1-4 specialist names ordered by relevance
- **Fast paths**: Factual queries → coach only; follow-ups → reuse previous specialists
- **Schema**: `RoutingDecision` Pydantic model with structured output guarantee

**Specialist Guidance**:
All instructions load from `prompts/md/specialist_guidance.md`. Specialists MUST search knowledge base specific to user's query intent (not generic profiles). No fallback code — system errors if guidance missing.

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

### Session-Level Persistence (Multi-Agent)

**Why**: Career decisions evolve across multiple conversation turns. Specialists need cumulative context.

**Implementation**: Two-layer LangGraph StateGraph:
1. **Outer graph** (`conversation_graph.py`): Session-scoped, persistent per `thread_id`
   - Classifies turn type (factual, follow_up, steer, new_query, workflow_step)
   - Routes query to 1-4 specialists via LLM
   - Executes inner blackboard for this turn
   - Accumulates findings across turns
   - Synthesizes response with cross-turn context
   - Suggests proactive next steps

2. **Inner graph** (`graph.py`): Per-turn blackboard execution
   - Specialists share `CareerBlackboard` (TypedDict)
   - Each specialist reads user profile + query + previous findings
   - Specialists contribute structured findings
   - Optional iteration (up to 5 rounds) via scheduler strategies
   - Single synthesis pass via LLM

**Callback Threading**:
Five callbacks flow through the system:
- `on_specialist_start(name)` — Display specialist working status
- `on_specialist_complete(name, finding)` — Display specialist results
- `on_tool_start(specialist, tool_name, args)` — Display tool invocation
- `on_tool_result(specialist, tool_name, result)` — Display tool result
- `confirm_fn(question, details)` → bool — HITL approval gate

Callbacks are wired from `engine.invoke_turn()` → `build_conversation_graph()` → `execute_inner_node()` → `executor.execute()` → specialist nodes.

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

### Single Agent
| File | Purpose |
|------|---------|
| `src/fu7ur3pr00f/agents/career_agent.py` | Single agent, middleware stack, singleton cache |
| `src/fu7ur3pr00f/agents/middleware.py` | Dynamic prompt, synthesis, tool repair middleware |

### Multi-Agent & Routing
| File | Purpose |
|------|---------|
| `src/fu7ur3pr00f/agents/specialists/orchestrator.py` | LLM routing + keyword fallback, specialist registry |
| `src/fu7ur3pr00f/agents/specialists/routing_schema.py` | `RoutingDecision` Pydantic model with name validator |
| `src/fu7ur3pr00f/agents/specialists/base.py` | `BaseAgent` abstract class, tool-calling loop, context building |
| `src/fu7ur3pr00f/agents/specialists/coach.py` | CoachAgent (career growth, leadership) |
| `src/fu7ur3pr00f/agents/specialists/learning.py` | LearningAgent (skill development, trending) |
| `src/fu7ur3pr00f/agents/specialists/jobs.py` | JobsAgent (job search, salary, market fit) |
| `src/fu7ur3pr00f/agents/specialists/code.py` | CodeAgent (GitHub, GitLab, open source) |
| `src/fu7ur3pr00f/agents/specialists/founder.py` | FounderAgent (startups, entrepreneurship) |

### Session & Blackboard
| File | Purpose |
|------|---------|
| `src/fu7ur3pr00f/agents/blackboard/engine.py` | Session-level entry point, thread management |
| `src/fu7ur3pr00f/agents/blackboard/conversation_graph.py` | Outer graph (session-scoped), turn classification & routing |
| `src/fu7ur3pr00f/agents/blackboard/graph.py` | Inner graph (per-turn), blackboard execution, specialist dispatch |
| `src/fu7ur3pr00f/agents/blackboard/blackboard.py` | `CareerBlackboard` TypedDict, `SpecialistFinding` schema |
| `src/fu7ur3pr00f/agents/blackboard/turn_classifier.py` | Turn type classification (factual, follow_up, etc.) |
| `src/fu7ur3pr00f/agents/blackboard/session.py` | Session state helpers, context formatting |
| `src/fu7ur3pr00f/agents/blackboard/findings_schema.py` | `SpecialistFindingsModel` structured output schema |

### Prompts (Prompt-Driven Behavior)
| File | Purpose |
|------|---------|
| `src/fu7ur3pr00f/prompts/md/route_specialists.md` | Routing prompt (specialist domain descriptions) |
| `src/fu7ur3pr00f/prompts/md/specialist_guidance.md` | **CRITICAL**: Knowledge search + intent matching instructions |
| `src/fu7ur3pr00f/prompts/md/specialist_contribute.md` | Multi-turn tool-calling loop instructions |
| `src/fu7ur3pr00f/prompts/md/synthesis.md` | Synthesis prompt for final response |

### Core Systems
| File | Purpose |
|------|---------|
| `src/fu7ur3pr00f/llm/fallback.py` | Multi-provider fallback routing (`get_model_with_fallback`) |
| `src/fu7ur3pr00f/memory/chromadb_store.py` | ChromaDB base store (episodic/ directory) |
| `src/fu7ur3pr00f/memory/checkpointer.py` | SQLite checkpointer (memory.db) |
| `src/fu7ur3pr00f/agents/tools/` | **40 tools** organized by domain |
| `src/fu7ur3pr00f/mcp/` | **12 MCP clients** for real-time data |
| `src/fu7ur3pr00f/gatherers/` | Data gathering (LinkedIn, CV, portfolio, assessments) |
| `src/fu7ur3pr00f/generators/` | CV generation (Markdown + PDF via WeasyPrint) |
| `src/fu7ur3pr00f/chat/client.py` | Chat loop, slash commands, HITL, streaming, callbacks |

See [Tools Reference](tools.md) for the complete list of all 40 tools.
See [MCP Clients](mcp_clients.md) for the complete list of all 12 MCP clients.

## See Also

- [Configuration](configuration.md)
- [Memory System](memory_system.md)
- [QWEN.md](../QWEN.md)

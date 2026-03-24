# Architecture

## Overview

FutureProof is a career intelligence agent built on a single-agent architecture with 40+ tools and 12 MCP clients.

## Design Decisions

### Single Agent

**Why**: Multi-agent handoffs failed with GPT-4.1 due to over-delegation and lost context.

**Implementation**: One agent (`career_agent.py`) with all tools registered. Tools are organized by domain:
- Profile management
- Data gathering
- Career analysis
- CV generation
- Knowledge base search
- Market intelligence
- Episodic memory
- Settings

### Database-First Pipeline

**Why**: Intermediate files add complexity and slow down the pipeline.

**Implementation**: Gatherers return `Section` NamedTuples and index directly to ChromaDB. No markdown header roundtrip.

```
Gatherer → Section NamedTuple → ChromaDB → RAG search
```

### Two-Pass Synthesis

**Why**: GPT-4o genericizes analysis responses regardless of prompt engineering.

**Implementation**: `AnalysisSynthesisMiddleware` intercepts tool results, then replaces the generic LLM response with focused synthesis from a reasoning model.

```
Agent → Tool execution → Generic response → Middleware → Reasoning model synthesis → Final response
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
- CV generation
- Full data gathering
- Knowledge clearing

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User (Rich UI)                          │
│                    Chat client with HITL loop                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Single Agent (40 tools)                    │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────┐  │
│  │  Gatherers  │     MCP     │   Analysis  │    Generation   │  │
│  │  LinkedIn   │   GitHub    │  Skill gap  │   CV (MD+PDF)   │  │
│  │  Portfolio  │  Job boards │   Market    │                 │  │
│  │  Strengths  │   Tavily    │ Trajectory  │                 │  │
│  └─────────────┴─────────────┴─────────────┴─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │                              │              │
           ▼                              ▼              ▼
┌──────────────────┐          ┌──────────────────┐  ┌──────────┐
│    ChromaDB      │          │  FallbackLLM     │  │  File    │
│  RAG + Memory    │          │  OpenAI/Anthropic│  │  System  │
│  - Knowledge     │          │  Google/Azure    │  │          │
│  - Episodic      │          │  Ollama/Proxy    │  │          │
└──────────────────┘          └──────────────────┘  └──────────┘
```

## Data Flow

### Gathering

1. User runs `/gather`
2. Agent executes gatherer tools
3. Each gatherer returns `Section` NamedTuple
4. Sections indexed to ChromaDB with embeddings
5. User notified of completion

### Analysis

1. User requests analysis (e.g., "skill gaps for Staff Engineer")
2. Agent queries ChromaDB for relevant context
3. Agent calls analysis tools with context
4. `AnalysisSynthesisMiddleware` intercepts
5. Reasoning model generates focused synthesis
6. Response returned to user

### CV Generation

1. User requests CV generation
2. HITL interrupt prompts for confirmation
3. Agent gathers relevant profile data from ChromaDB
4. CV generator creates Markdown
5. WeasyPrint converts to PDF
6. Both formats returned to user

## Key Files

| File | Purpose |
|------|---------|
| `src/fu7ur3pr00f/agents/career_agent.py` | Single agent, singleton cache |
| `src/fu7ur3pr00f/agents/middleware.py` | Dynamic prompts, synthesis, tool repair |
| `src/fu7ur3pr00f/agents/orchestrator.py` | LangGraph workflows |
| `src/fu7ur3pr00f/llm/fallback.py` | Multi-provider fallback routing |
| `src/fu7ur3pr00f/memory/chroma/` | ChromaDB RAG + episodic memory |
| `src/fu7ur3pr00f/agents/tools/` | **40 tools** organized by domain |
| `src/fu7ur3pr00f/mcp/` | **12 MCP clients** for real-time data |
| `src/fu7ur3pr00f/gatherers/` | Data gathering tools |
| `src/fu7ur3pr00f/generators/` | CV generation (Markdown + PDF) |

See [Tools Reference](tools.md) for the complete list of all 40 tools.  
See [MCP Clients](mcp_clients.md) for the complete list of all 12 MCP clients.

## See Also

- [Configuration](configuration.md)
- [Contributing](../CONTRIBUTING.md)
- [QWEN.md](../QWEN.md)

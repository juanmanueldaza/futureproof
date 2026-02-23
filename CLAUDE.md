# FutureProof - Claude Code Guidelines

## Project Overview

FutureProof is a career intelligence system powered by a conversational AI agent. It gathers professional data from multiple sources (LinkedIn, portfolio sites, CliftonStrengths) and indexes it directly to ChromaDB (database-first, no intermediate files). Uses AI to analyze career trajectories, identify gaps, and generate optimized CVs — all through an interactive chat interface. GitHub data is accessed live via MCP client; GitLab via glab CLI.

## Tech Stack

- **Python 3.13** with type hints
- **LangChain/LangGraph** for AI orchestration
- **ChromaDB** for vector storage (knowledge base + episodic memory)
- **Pydantic** for configuration
- **Typer** for CLI (chat entry point)
- **pytest** for testing
- **pip** for package management

## Project Structure

```
src/futureproof/
├── agents/
│   ├── career_agent.py  # Single agent with create_agent(), system prompt, caching
│   ├── middleware.py    # build_dynamic_prompt, AnalysisSynthesisMiddleware, ToolCallRepairMiddleware
│   ├── orchestrator.py  # LangGraph Functional API (@entrypoint/@task) for analysis
│   ├── state.py         # TypedDict state definitions (CareerState, etc.)
│   ├── helpers/         # Orchestrator support (data_pipeline, llm_invoker, result_mapper)
│   └── tools/           # 39 agent tools organized by domain
├── chat/                # Streaming client with HITL, Rich verbose UI, summary echo stripping
├── gatherers/           # Data collection from external sources
│   ├── linkedin.py      # LinkedIn ZIP direct CSV parser (17 CSVs, 3 tiers)
│   ├── cliftonstrengths.py  # CliftonStrengths PDF parser (~850 lines)
│   ├── portfolio/       # Decomposed: Fetcher, HTMLExtractor, JSExtractor, MarkdownWriter
│   └── market/          # Job market, tech trends, content trends gatherers
│       └── source_registry.py  # OCP job source registry (JobSourceConfig)
├── generators/          # CV generation (Markdown + PDF via WeasyPrint)
├── llm/                 # FallbackLLMManager with init_chat_model()
├── memory/
│   ├── chromadb_store.py # ChromaDB base class (shared by knowledge + episodic)
│   ├── knowledge.py     # ChromaDB knowledge store (RAG)
│   ├── episodic.py      # ChromaDB episodic memory store
│   ├── chunker.py       # Markdown text chunker for indexing
│   ├── embeddings.py    # Azure OpenAI embedding functions with caching
│   ├── checkpointer.py  # SQLite conversation persistence
│   └── profile.py       # User profile (YAML, secure permissions)
├── mcp/                 # MCP client implementations (12 clients)
├── prompts/             # LLM prompt templates (analysis, CV, advice)
├── services/            # Business logic layer
│   └── exceptions.py   # ServiceError, NoDataError, AnalysisError
└── utils/               # Security, data loading, logging, console
```

## Commands

```bash
futureproof chat                    # Interactive chat (verbose by default)
futureproof chat --debug            # Also show debug logs in terminal
futureproof chat --thread work      # Named conversation thread
futureproof ask "question"          # One-off question
futureproof memory --threads        # List threads
futureproof memory --clear          # Clear history

pytest tests/ -q                    # Run tests
pyright src/futureproof             # Type checking
ruff check .                        # Lint
ruff check . --fix                  # Auto-fix
```

## Architecture Principles

- **SRP**: Each class has a single responsibility (e.g., PortfolioGatherer split into Fetcher, HTMLExtractor, JSExtractor, MarkdownWriter)
- **OCP**: MCP clients extensible via registry pattern; LLM providers configured declaratively
- **DIP**: High-level modules depend on `FallbackLLMManager` abstraction with `init_chat_model()` universal factory
- **DRY**: Service layer provides shared business logic for all agent tools
- **ISP**: CareerState split into focused TypedDicts (GatherInput, AnalyzeInput, etc.)

## Agent Architecture

All functionality is accessible through the **chat interface** via a single agent built with LangChain's `create_agent()`:

- **Single agent**: One agent with all 39 tools — profile, gathering, github, gitlab, analysis, generation, knowledge, market, financial, memory
- **Human-in-the-loop**: `interrupt()` on `generate_cv`, `gather_all_career_data`, and `clear_career_knowledge` for user confirmation
- **Dynamic system prompt**: `build_dynamic_prompt` (`@dynamic_prompt` middleware) generates the system prompt on every model call, injecting live profile summary and knowledge base stats (chunk counts per source) so the model knows what data is available without calling tools
- **State repair**: `ToolCallRepairMiddleware` detects orphaned `tool_calls` (parallel tool results lost during HITL resume) and injects synthetic error ToolMessages so the model can proceed
- **Context management**: `SummarizationMiddleware` auto-summarizes old messages (triggers at 32k tokens, keeps last 20 messages, uses separate cheaper model)
- **Memory**: ChromaDB for persistent episodic memory (decisions, applications) and career knowledge RAG
- **Auto-profile**: After gathering, the agent auto-populates an empty profile from knowledge base data (LinkedIn, portfolio)
- **Orchestrator**: LangGraph Functional API (`@entrypoint`/`@task`) in `orchestrator.py` for career analysis workflows (used by `AnalysisService`)
- **LLM**: `FallbackLLMManager` with purpose-based model routing — agent (tool calling), analysis, summarization can each use a different Azure deployment
- **Caching**: Agent singleton (`_cached_agent`), checkpointer singleton, embedding function singleton

### Agent Tools (39 tools in `agents/tools/`)

- **Profile** (7): `get_user_profile`, `update_user_name`, `update_current_role`, `update_salary_info`, `update_user_skills`, `set_target_roles`, `update_user_goal`
- **Gathering** (5): `gather_portfolio_data`, `gather_linkedin_data`, `gather_assessment_data`, `gather_all_career_data` (HITL), `get_stored_career_data` — all sources index directly to ChromaDB
- **GitHub** (3): `search_github_repos`, `get_github_repo`, `get_github_profile` — live queries via GitHub MCP server
- **GitLab** (3): `search_gitlab_projects`, `get_gitlab_project`, `get_gitlab_file` — live queries via glab CLI
- **Knowledge** (4): `search_career_knowledge`, `get_knowledge_stats`, `index_career_knowledge`, `clear_career_knowledge` (HITL)
- **Analysis** (3): `analyze_skill_gaps`, `analyze_career_alignment`, `get_career_advice`
- **Generation** (2): `generate_cv` (HITL), `generate_cv_draft`
- **Market** (6): `search_jobs`, `get_tech_trends`, `get_salary_insights`, `gather_market_data`, `analyze_market_fit`, `analyze_market_skills`
- **Financial** (2): `convert_currency`, `compare_salary_ppp` — real-time forex via ExchangeRate-API, PPP via World Bank
- **Memory** (4): `remember_decision`, `remember_job_application`, `recall_memories`, `get_memory_stats`

Shared async helper: `_async.py` with `run_async()` for sync tool → async service bridge.

## LLM Fallback Chain & Model Routing

`FallbackLLMManager` in `llm/fallback.py` tries models in order, auto-skipping on rate limits or errors:

1. Azure GPT-4.1
2. Azure GPT-5 Mini
3. Azure GPT-4o
4. Azure GPT-4.1 Mini
5. Azure GPT-4o Mini

Uses `init_chat_model()` with `azure_openai` provider. Reasoning models (o-series prefixes: o1, o3, o4) automatically skip `temperature` parameter.

**Purpose-based routing**: Each LLM call site declares its purpose (`"agent"`, `"analysis"`, `"summary"`, `"synthesis"`). If a purpose-specific deployment is configured (e.g., `AZURE_AGENT_DEPLOYMENT=gpt-5-mini`), that model is prepended to the fallback chain for that purpose. Unconfigured purposes use the default chain. Reasoning models (o-series) automatically skip temperature parameter.

| Purpose | Call Sites | Config Var | Recommended Model |
|---|---|---|---|
| `agent` | `create_agent()` | `AZURE_AGENT_DEPLOYMENT` | GPT-5 Mini (best instruction-following) |
| `analysis` | `invoke_llm()`, `CVGenerator` | `AZURE_ANALYSIS_DEPLOYMENT` | GPT-4.1 |
| `summary` | `SummarizationMiddleware` | `AZURE_SUMMARY_DEPLOYMENT` | GPT-4o Mini or GPT-4.1 Mini |
| `synthesis` | `AnalysisSynthesisMiddleware` | `AZURE_SYNTHESIS_DEPLOYMENT` | o4-mini (reasoning, precise instruction-following) |

## MCP Clients (`mcp/`)

12 MCP client implementations with registry pattern via `factory.py`:

- **Code platforms**: `github_client.py` (stdio MCP)
- **Search**: `tavily_client.py` (Tavily Search API, 1000 free queries/month)
- **Hacker News**: `hn_client.py` (Algolia API — stories, hiring trends, job postings with salary parsing)
- **Job boards**: `jobspy_client.py` (LinkedIn/Indeed/Glassdoor/ZipRecruiter via python-jobspy), `remoteok_client.py`, `himalayas_client.py`, `jobicy_client.py`, `weworkremotely_client.py`, `remotive_client.py`
- **Content trends**: `devto_client.py`, `stackoverflow_client.py`
- **Financial data**: `financial_client.py` (ExchangeRate-API for forex, World Bank for PPP — no auth required)
- **Infrastructure**: `base.py` (abstract base `MCPClient`), `http_client.py` (shared httpx client for 10 API-based clients), `job_schema.py` (unified job model), `salary_parser.py`

## Security

### PII Anonymization (`utils/security.py`)
- `anonymize_career_data(data, preserve_professional_emails)` — redacts emails, phones, addresses, social usernames (5 regex patterns)
- Applied before sending career data to external LLMs (in `CVGenerator`)
- Optional `preserve_professional_emails` mode keeps work email domains (e.g., `[USER]@company.com`)

### Other Protections
- **SSRF**: Portfolio fetcher blocks private IP ranges via `ipaddress.is_private`, validates resolved hostnames
- **Command injection**: `subprocess.run()` with list args, no `shell=True`, 30s timeout
- **File permissions**: Sensitive output files (CVs, profile) created with `0o600`

## Git Commits

- NEVER add `Co-Authored-By`, `Generated by`, or any AI attribution to commits
- NEVER claim authorship or credit in code, comments, or commit messages
- Commit messages: conventional commits style, concise subject, optional body with technical details

## Code Style

- Use `collections.abc` for type hints (`Mapping`, `Sequence` — not `typing`)
- Keep lines under 100 characters
- Avoid ambiguous single-letter variable names
- Remove unused imports and variables
- Use dependency injection for testability
- Prefer raising exceptions over returning error dicts

## Testing

- Tests in `tests/` directory
- Use fixtures from `conftest.py` for common test data
- Mock external services (LLM, HTTP) to avoid API calls
- Data loader tests mock `KnowledgeService` (no file I/O)

## Configuration

Settings loaded from environment variables via Pydantic (`config.py`). All have defaults; the app works with a single API key.

### Azure OpenAI (required)
- `AZURE_OPENAI_API_KEY` — Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` — Azure endpoint URL
- `AZURE_OPENAI_API_VERSION` — Azure API version (default: `2024-12-01-preview`)
- `AZURE_CHAT_DEPLOYMENT` — Azure chat model deployment name
- `AZURE_EMBEDDING_DEPLOYMENT` — Azure embedding deployment name
- `LLM_TEMPERATURE` — Generation temperature (default: `0.3`)
- `CV_TEMPERATURE` — CV generation temperature (default: `0.2`)

### Model Routing (optional)
- `AZURE_AGENT_DEPLOYMENT` — Deployment for tool calling (e.g. `gpt-5-mini`). Empty = use default chain.
- `AZURE_ANALYSIS_DEPLOYMENT` — Deployment for analysis/CV generation (e.g. `gpt-4.1`). Empty = use default chain.
- `AZURE_SUMMARY_DEPLOYMENT` — Deployment for summarization (e.g. `gpt-4o-mini`). Empty = use default chain.
- `AZURE_SYNTHESIS_DEPLOYMENT` — Deployment for post-analysis synthesis (e.g. `o4-mini`). Reasoning models (o-series) supported. Empty = use default chain.

### Data Sources
- `PORTFOLIO_URL` — Portfolio website URL

### MCP Servers
- `GITHUB_PERSONAL_ACCESS_TOKEN` — GitHub API token
- `GITHUB_MCP_TOKEN` — Alternative GitHub token for MCP
- `GITHUB_MCP_USE_DOCKER` — Use Docker for GitHub MCP server (default: `true`)
- `GITHUB_MCP_IMAGE` — Docker image (default: `ghcr.io/github/github-mcp-server`)
- `GITHUB_MCP_COMMAND` — Native binary command when not using Docker (default: `github-mcp-server`)

- `TAVILY_API_KEY` — Tavily search API key

### Market Intelligence
- `JOBSPY_ENABLED` — Enable JobSpy scraping (default: `true`)
- `HN_MCP_ENABLED` — Enable Hacker News trends (default: `true`)
- `MARKET_CACHE_HOURS` — Tech trends cache TTL (default: `24`)
- `JOB_CACHE_HOURS` — Job data cache TTL (default: `12`)
- `CONTENT_CACHE_HOURS` — Content trends cache TTL (default: `12`)
- `FOREX_CACHE_HOURS` — Exchange rate cache TTL (default: `4`)

### Knowledge Base
- `KNOWLEDGE_AUTO_INDEX` — Auto-index after gather (default: `true`)
- `KNOWLEDGE_CHUNK_MAX_TOKENS` — Max tokens per chunk (default: `500`)
- `KNOWLEDGE_CHUNK_MIN_TOKENS` — Min tokens per chunk (default: `50`)

## Key Modules

### `chat/ui.py`
Rich-based terminal UI components. Verbose mode display functions: `display_tool_start()` (category badge + args), `display_tool_result()` (full output in bordered Panel), `display_model_info()`, `display_model_switch()`, `display_timing()`, `display_node_transition()`, `display_indexing_result()`, `display_gather_result()`. Tool category styling maps all 39 tools to categories (profile, gathering, github, gitlab, knowledge, analysis, generation, market, financial, memory) with unique colors.

### `chat/client.py`
Streaming chat client with HITL interrupt loop (iterative, not recursive), summary echo stripping, fallback retry, tool timing. Always shows Rich UI output (tool badges, timing, model info) via `chat/ui.py`. `_stream_response()` handles the full stream lifecycle including sequential HITL interrupts via `while True` loop.

### `agents/career_agent.py`
Single agent with `create_agent()`, dynamic system prompt via `build_dynamic_prompt`, `ToolCallRepairMiddleware` + `SummarizationMiddleware`. Cached singleton pattern. Episodic memory persisted via ChromaDB (no runtime store). Functions: `create_career_agent()`, `get_agent_config()`, `get_agent_model_name()`, `reset_career_agent()`.

### `agents/middleware.py`
`build_dynamic_prompt` — `@dynamic_prompt` middleware that generates the system prompt on every model call. Injects live profile summary and knowledge base stats. `AnalysisSynthesisMiddleware` — two-pass `wrap_model_call`: (1) masks analysis tool results with markers so the agent can't rewrite them, (2) when the agent produces a final response (no tool_calls) and analysis tools ran in the current turn, discards the generic response and replaces it with a focused synthesis from a separate LLM call (purpose="synthesis", e.g. o4-mini). Only considers analysis tools after the last HumanMessage (current-turn scoping). `ToolCallRepairMiddleware` — detects orphaned `tool_calls` (parallel tool results lost during HITL resume) and injects synthetic error ToolMessages. Middleware order: `[build_dynamic_prompt, repair, analysis_synthesis, summarization]`.

### `agents/orchestrator.py`
LangGraph Functional API with `@entrypoint` and `@task` decorators. Used by `AnalysisService` for career analysis workflows (skill gaps, alignment, market analysis, advice).

### `llm/fallback.py`
`FallbackLLMManager` with 5-model Azure chain and purpose-based routing (agent, analysis, summary, synthesis). Uses `init_chat_model()` with `azure_openai` provider. `get_model_with_fallback(purpose=...)` builds purpose-specific chains by prepending configured deployments. Reasoning models (o-series) auto-detected by prefix — `temperature` skipped. Auto-detects rate limits and model errors, marks failed models, tries next in chain.

### `memory/chromadb_store.py`
`ChromaDBStore` — base class for ChromaDB-backed stores. Provides lazy-initialized PersistentClient/collection, shared `_add()`, `_query()`, `get_ids_by_filter()`, `delete_by_ids()`, `_count_by_values()`, `_get_stats()` helpers. Inherited by both `CareerKnowledgeStore` and `EpisodicStore`.

### `memory/knowledge.py`
`CareerKnowledgeStore` — ChromaDB wrapper for career data vectors. Collection: `career_knowledge`. Section-based: `index_sections()` accepts `list[Section]` NamedTuples, calls `chunk_section()` on each, builds metadata inline, batch-indexes to ChromaDB (groups of 100). No intermediate `KnowledgeChunk` class — metadata dicts built directly. `_fetch_sorted_docs()` shared helper for content retrieval. `search()` returns `list[dict]` with `excluded_sections`/`excluded_prefixes` over-fetch (3x) + post-filter. `KnowledgeSource` enum: linkedin, portfolio, assessment. Methods: `index_sections()`, `get_all_content()`, `get_filtered_content()`, `search()`, `clear_source()`, `get_stats()`.

### `memory/episodic.py`
`EpisodicStore` — ChromaDB wrapper for episodic memories. Collection: `career_memories`. `MemoryType` enum: DECISION, APPLICATION. Methods: `remember()`, `recall()`, `stats()`.

### `memory/chunker.py`
`MarkdownChunker` — splits content into size-bounded chunks. `Section` NamedTuple (name, content) carries section labels as structured data. `MarkdownChunk` has only `content` + `section_path`. `chunk_section()` does size-only splitting (split large by paragraphs) with `section_path=[section.name]` — no merge step, no header regex. Configurable max/min token limits.

### `utils/security.py`
PII anonymization for career data. `anonymize_career_data(data, preserve_professional_emails)` — 5 regex patterns redact emails, phones, addresses, social profile URLs. Used by `CVGenerator` before sending data to external LLMs.

### `utils/data_loader.py`
Thin wrapper around `KnowledgeService`. Functions: `load_career_data()` → dict (all sources), `load_career_data_for_analysis()` → dict (excludes social sections), `load_career_data_for_cv()` → formatted string (uses filtered data), `combine_career_data()` → combined string. No file I/O — all data comes from ChromaDB.

### `services/`
Business logic layer: `GathererService` (gathering + auto-indexing with timing), `AnalysisService` (LangGraph orchestrator invocation), `KnowledgeService` (indexing/search/filtering with social exclusion via `_EXCLUDED_SECTIONS`/`_EXCLUDED_PREFIXES`, `include_social` toggle, `get_filtered_content()`, `clear_source()`, `clear_all()`). CV generation is called directly via `CVGenerator` from agent tools.

### `gatherers/market/source_registry.py`
OCP-compliant job source registry. `JobSourceConfig` dataclass defines each source (name, tool, args builder, post-processor). `JOB_SOURCE_REGISTRY` list holds 6 job sources; `SALARY_SOURCE` holds Tavily salary config. Adding a new job source requires only a new registry entry.

### `services/exceptions.py`
Service layer exception hierarchy: `ServiceError` (base), `NoDataError` (no career data available), `AnalysisError` (analysis failure).

### `gatherers/portfolio/`
Decomposed portfolio scraper (SRP): `PortfolioFetcher` (SSRF-protected HTTP), `HTMLExtractor` (BeautifulSoup), `JSExtractor` (JavaScript content), `MarkdownWriter` (output formatting).

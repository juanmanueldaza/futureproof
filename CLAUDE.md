# FutureProof - Claude Code Guidelines

## Project Overview

FutureProof is a career intelligence system powered by a conversational AI agent. It gathers professional data from multiple sources (LinkedIn, portfolio sites, CliftonStrengths) and indexes it directly to ChromaDB (database-first, no intermediate files). Uses AI to analyze career trajectories, identify gaps, and generate optimized CVs — all through an interactive chat interface. GitHub and GitLab data is accessed live via MCP clients.

## Tech Stack

- **Python 3.13** with type hints
- **LangChain/LangGraph** for AI orchestration
- **ChromaDB** for vector storage (knowledge base + episodic memory)
- **Pydantic** for configuration
- **Typer** for CLI (chat entry point)
- **pytest** for testing
- **uv** for package management

## Project Structure

```
src/futureproof/
├── agents/
│   ├── career_agent.py  # Single agent with create_agent(), system prompt, caching
│   ├── orchestrator.py  # LangGraph Functional API (@entrypoint/@task) for analysis
│   ├── state.py         # TypedDict state definitions (CareerState, etc.)
│   ├── helpers/         # Orchestrator support (data_pipeline, llm_invoker, result_mapper)
│   └── tools/           # 30 agent tools organized by domain
├── chat/                # Streaming client with HITL, summary echo stripping
├── gatherers/           # Data collection from external sources
│   ├── linkedin.py      # LinkedIn ZIP via linkedin2md CLI
│   ├── cliftonstrengths.py  # CliftonStrengths PDF parser (~850 lines)
│   ├── portfolio/       # Decomposed: Fetcher, HTMLExtractor, JSExtractor, MarkdownWriter
│   └── market/          # Job market, tech trends, content trends gatherers
├── generators/          # CV generation (Markdown + PDF via WeasyPrint)
├── llm/                 # FallbackLLMManager with init_chat_model()
├── memory/
│   ├── store.py         # LangGraph InMemoryStore (runtime semantic search)
│   ├── knowledge.py     # ChromaDB knowledge store (RAG)
│   ├── episodic.py      # ChromaDB episodic memory store
│   ├── chunker.py       # Markdown text chunker for indexing
│   ├── embeddings.py    # Azure OpenAI embedding functions with caching
│   ├── checkpointer.py  # SQLite conversation persistence
│   └── profile.py       # User profile (YAML, secure permissions)
├── mcp/                 # MCP client implementations (13 clients)
├── prompts/             # LLM prompt templates (analysis, CV, advice)
├── services/            # Business logic layer
└── utils/               # Security, data loading, logging, console
```

## Commands

```bash
futureproof chat                    # Interactive chat
futureproof chat --verbose          # Show tool usage
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

- **Single agent**: One agent with all 36 tools — profile, gathering, github, gitlab, analysis, generation, knowledge, market, memory
- **Human-in-the-loop**: `interrupt()` on `generate_cv`, `gather_all_career_data`, and `clear_career_knowledge` for user confirmation
- **Context management**: `SummarizationMiddleware` auto-summarizes old messages (triggers at 8k tokens, keeps last 20 messages)
- **Memory**: Dual-write to `InMemoryStore` (runtime, cross-thread semantic search) + ChromaDB (persistent)
- **Auto-profile**: After gathering, the agent auto-populates an empty profile from knowledge base data (LinkedIn, portfolio)
- **Orchestrator**: LangGraph Functional API (`@entrypoint`/`@task`) in `orchestrator.py` for career analysis workflows (used by `AnalysisService`)
- **LLM**: Unified on `FallbackLLMManager` using `init_chat_model()` — Azure OpenAI only
- **Caching**: Agent singleton (`_cached_agent`), checkpointer singleton, embedding function singleton

### Agent Tools (36 tools in `agents/tools/`)

- **Profile** (6): `get_user_profile`, `update_user_name`, `update_current_role`, `update_user_skills`, `set_target_roles`, `update_user_goal`
- **Gathering** (5): `gather_portfolio_data`, `gather_linkedin_data`, `gather_assessment_data`, `gather_all_career_data` (HITL), `get_stored_career_data` — portfolio/assessment index directly to ChromaDB; LinkedIn reads CLI output files
- **GitHub** (3): `search_github_repos`, `get_github_repo`, `get_github_profile` — live queries via GitHub MCP server
- **GitLab** (3): `search_gitlab_projects`, `get_gitlab_project`, `get_gitlab_file` — live queries via GitLab MCP server
- **Knowledge** (4): `search_career_knowledge`, `get_knowledge_stats`, `index_career_knowledge`, `clear_career_knowledge` (HITL)
- **Analysis** (3): `analyze_skill_gaps`, `analyze_career_alignment`, `get_career_advice`
- **Generation** (2): `generate_cv` (HITL), `generate_cv_draft`
- **Market** (6): `search_jobs`, `get_tech_trends`, `get_salary_insights`, `gather_market_data`, `analyze_market_fit`, `analyze_market_skills`
- **Memory** (4): `remember_decision`, `remember_job_application`, `recall_memories`, `get_memory_stats`

Shared async helper: `_async.py` with `run_async()` for sync tool → async service bridge.

## LLM Fallback Chain

`FallbackLLMManager` in `llm/fallback.py` tries models in order, auto-skipping on rate limits or errors:

1. Azure GPT-4.1
2. Azure GPT-4.1 Mini

Uses `init_chat_model()` with `azure_openai` provider.

## MCP Clients (`mcp/`)

13 MCP client implementations with registry pattern via `factory.py`:

- **Code platforms**: `github_client.py` (stdio MCP), `gitlab_client.py` (stdio MCP)
- **Search**: `tavily_client.py` (Tavily Search API, 1000 free queries/month)
- **Hacker News**: `hn_client.py` (Algolia API — stories, hiring trends, job postings with salary parsing)
- **Job boards**: `jobspy_client.py` (LinkedIn/Indeed/Glassdoor/ZipRecruiter via python-jobspy), `remoteok_client.py`, `himalayas_client.py`, `jobicy_client.py`, `weworkremotely_client.py`, `remotive_client.py`
- **Content trends**: `devto_client.py`, `stackoverflow_client.py`
- **Infrastructure**: `base.py` (abstract base), `http_client.py` (shared httpx client), `job_schema.py` (unified job model), `salary_parser.py`

## Security

### Prompt Injection Protection (`utils/security.py`)
- 13 compiled regex patterns detect injection attempts
- `detect_prompt_injection(text)` → returns list of detected patterns
- `sanitize_user_input(text, strict)` → returns `SanitizationResult` with safety status
- Blocks: "ignore previous instructions", "reveal system prompt", system tag injection, etc.

### PII Anonymization
- `anonymize_career_data(data, preserve_professional_emails)` redacts emails, phones, addresses, social usernames
- Applied before sending career data to external LLMs (in `CVGenerator`)
- `anonymize_pii(text)` — general PII anonymization (9 patterns: email, phone, SSN, card, address, ZIP, ID, DOB)

### Other Protections
- **SSRF**: Portfolio fetcher blocks private IP ranges, validates resolved hostnames
- **Command injection**: `subprocess.run()` with list args, no `shell=True`, 5-min timeout
- **File permissions**: Sensitive output files (CVs, profile) created with `0o600`

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
- `LLM_MODEL` — Override model name (empty = provider default)
- `LLM_TEMPERATURE` — Generation temperature (default: `0.3`)
- `CV_TEMPERATURE` — CV generation temperature (default: `0.2`)

### Data Sources
- `PORTFOLIO_URL` — Portfolio website URL
- `DEFAULT_LANGUAGE` — `en` or `es` (default: `en`)

### MCP Servers
- `GITHUB_PERSONAL_ACCESS_TOKEN` — GitHub API token
- `GITHUB_MCP_TOKEN` — Alternative GitHub token for MCP
- `GITHUB_MCP_USE_DOCKER` — Use Docker for GitHub MCP server (default: `true`)
- `GITHUB_MCP_IMAGE` — Docker image (default: `ghcr.io/github/github-mcp-server`)
- `GITLAB_MCP_URL` — GitLab MCP server URL
- `GITLAB_MCP_TOKEN` — GitLab MCP token
- `TAVILY_API_KEY` — Tavily search API key

### Market Intelligence
- `JOBSPY_ENABLED` — Enable JobSpy scraping (default: `true`)
- `HN_MCP_ENABLED` — Enable Hacker News trends (default: `true`)
- `MARKET_CACHE_HOURS` — Tech trends cache TTL (default: `24`)
- `JOB_CACHE_HOURS` — Job data cache TTL (default: `12`)
- `CONTENT_CACHE_HOURS` — Content trends cache TTL (default: `12`)

### Knowledge Base
- `KNOWLEDGE_AUTO_INDEX` — Auto-index after gather (default: `true`)
- `KNOWLEDGE_CHUNK_MAX_TOKENS` — Max tokens per chunk (default: `500`)
- `KNOWLEDGE_CHUNK_MIN_TOKENS` — Min tokens per chunk (default: `50`)

## Key Modules

### `agents/career_agent.py`
Single agent with `create_agent()`, unified system prompt, `SummarizationMiddleware`. Cached singleton pattern. Functions: `create_career_agent()`, `chat()`, `achat()`, `get_agent_config()`, `reset_career_agent()`.

### `agents/orchestrator.py`
LangGraph Functional API with `@entrypoint` and `@task` decorators. Used by `AnalysisService` for career analysis workflows (skill gaps, alignment, market analysis, advice).

### `llm/fallback.py`
`FallbackLLMManager` with 2-model Azure chain. Uses `init_chat_model()` with `azure_openai` provider. Auto-detects rate limits and model errors via string matching, marks failed models, tries next in chain.

### `memory/knowledge.py`
`CareerKnowledgeStore` — ChromaDB wrapper for career data vectors. Collection: `career_knowledge`. Database-first: `index_content()` accepts raw strings (no file I/O). `get_all_content()` retrieves all chunks for a source. `KnowledgeSource` enum: linkedin, portfolio, assessment. Also has `index_markdown_file()` (for LinkedIn CLI files), `search()`, `clear_source()`, `get_stats()`.

### `memory/episodic.py`
`EpisodicStore` — ChromaDB wrapper for episodic memories. Collection: `career_memories`. `MemoryType` enum: DECISION, APPLICATION, CONVERSATION, MILESTONE, LEARNING, FEEDBACK. Methods: `remember()`, `recall()`, `get_recent()`, `forget()`, `stats()`.

### `memory/store.py`
`InMemoryStore` with Azure OpenAI semantic search embeddings. Used by the agent for runtime cross-thread memory. Passed to `create_agent()` as `store` param.

### `memory/chunker.py`
`MarkdownChunker` — splits markdown by `##` headers while preserving section hierarchy. Configurable max/min token limits. Merges small chunks, splits large ones.

### `utils/security.py`
Security utilities: `detect_prompt_injection()`, `sanitize_user_input()`, `anonymize_pii()`, `anonymize_career_data()`, `create_safe_prompt()`.

### `utils/data_loader.py`
Thin wrapper around `KnowledgeService.get_all_content()`. Functions: `load_career_data()` → dict, `load_career_data_for_cv()` → formatted string, `combine_career_data()` → combined string. No file I/O — all data comes from ChromaDB.

### `services/`
Business logic layer: `GathererService` (registry-based gathering + auto-indexing), `AnalysisService` (LangGraph orchestrator invocation), `GenerationService` (CV generation), `KnowledgeService` (indexing/search), `CareerService` (facade).

### `gatherers/portfolio/`
Decomposed portfolio scraper (SRP): `PortfolioFetcher` (SSRF-protected HTTP), `HTMLExtractor` (BeautifulSoup), `JSExtractor` (JavaScript content), `MarkdownWriter` (output formatting).

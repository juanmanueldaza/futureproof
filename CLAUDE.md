# FutureProof - Claude Code Guidelines

## Project Overview

FutureProof is a career intelligence system powered by a conversational AI agent. It gathers professional data from multiple sources (LinkedIn, GitHub, GitLab, portfolio sites, CliftonStrengths), uses AI to analyze career trajectories, identify gaps, and generate optimized CVs — all through an interactive chat interface.

## Tech Stack

- **Python 3.13** with type hints
- **LangChain/LangGraph** for AI orchestration
- **Pydantic** for configuration
- **Typer** for CLI (chat entry point)
- **pytest** for testing
- **uv** for package management

## Project Structure

```
src/futureproof/
├── agents/          # LangGraph orchestration and state management
│   ├── helpers/     # Orchestrator support (data_pipeline, llm_invoker, result_mapper)
│   └── tools/       # Modular agent tools (profile, gathering, analysis, market, etc.)
├── chat/            # Interactive chat interface
├── gatherers/       # Data collection from external sources
│   ├── portfolio/   # Decomposed portfolio gatherer (SRP)
│   └── market/      # Market intelligence gatherers
├── generators/      # CV generation
├── llm/             # LLM fallback manager with init_chat_model()
├── memory/          # Knowledge and memory storage
│   ├── chunker.py   # Markdown text chunker
│   ├── knowledge.py # ChromaDB knowledge store (RAG)
│   ├── episodic.py  # Episodic memory store
│   └── store.py     # LangGraph InMemoryStore (runtime semantic search)
├── mcp/             # MCP client implementations
├── prompts/         # AI prompt templates
├── services/        # Business logic layer
└── utils/           # Shared utilities (logging, data loading, security)
```

## Commands

```bash
# Run the chat agent
futureproof chat
futureproof chat --verbose      # Show tool usage
futureproof ask "What are my top skills?"

# Dev commands
pytest tests/ -q
pyright src/futureproof
ruff check .
ruff check . --fix
```

## Architecture Principles

This codebase follows SOLID, DRY, KISS, and YAGNI principles:

- **SRP**: Each class has a single responsibility (e.g., PortfolioGatherer split into Fetcher, HTMLExtractor, JSExtractor, MarkdownWriter)
- **OCP**: MCP clients extensible via registry pattern; LLM providers configured declaratively in `FallbackLLMManager`
- **DIP**: High-level modules depend on `FallbackLLMManager` abstraction with `init_chat_model()` universal factory
- **DRY**: Service layer provides shared business logic for all agent tools
- **ISP**: CareerState split into focused TypedDicts (GatherInput, AnalyzeInput, etc.)

## Agent Architecture

All functionality is accessible through the **chat interface** via a single agent built with LangChain's `create_agent()`:

- **Single agent**: One agent with all 32 tools — profile, gathering, analysis, generation, knowledge, market, memory.
- **Human-in-the-loop**: `interrupt()` on `generate_cv`, `gather_all_career_data`, and `clear_career_knowledge` for user confirmation.
- **Context management**: `SummarizationMiddleware` auto-summarizes old messages (triggers at 8k tokens, keeps last 20 messages).
- **Memory**: Dual-write to `InMemoryStore` (runtime, cross-thread semantic search) + ChromaDB (persistent).
- **Auto-profile**: After gathering, the agent auto-populates an empty profile from knowledge base data (LinkedIn, GitHub).
- **Orchestrator**: LangGraph Functional API (`@entrypoint`/`@task`) in `orchestrator.py` for career analysis workflows (used by `AnalysisService`).
- **LLM**: Unified on `FallbackLLMManager` using `init_chat_model()` — supports Azure, Groq, Gemini, Cerebras, SambaNova.

### Agent Tools (32 tools in `agents/tools/`)

- **Profile** (6): `get_user_profile`, `update_user_name`, `update_current_role`, `update_user_skills`, `set_target_roles`, `update_user_goal`
- **Gathering** (7): `gather_github_data`, `gather_gitlab_data`, `gather_portfolio_data`, `gather_linkedin_data`, `gather_assessment_data`, `gather_all_career_data` (HITL), `get_stored_career_data`
- **Knowledge** (4): `search_career_knowledge`, `get_knowledge_stats`, `index_career_knowledge`, `clear_career_knowledge` (HITL)
- **Analysis** (3): `analyze_skill_gaps`, `analyze_career_alignment`, `get_career_advice`
- **Generation** (2): `generate_cv` (HITL), `generate_cv_draft`
- **Market** (6): `search_jobs`, `get_tech_trends`, `get_salary_insights`, `gather_market_data`, `analyze_market_fit`, `analyze_market_skills`
- **Memory** (4): `remember_decision`, `remember_job_application`, `recall_memories`, `get_memory_stats`

## Security

The codebase implements security best practices:

### Prompt Injection Protection
- User inputs checked for injection patterns before inclusion in LLM prompts
- Security utilities in `utils/security.py`:
  - `detect_prompt_injection()` - detects common injection patterns
  - `sanitize_user_input()` - validates and sanitizes user input
  - Blocks patterns like "ignore previous instructions", "reveal system prompt"

### PII Anonymization
- Career data anonymized before sending to external LLM (Gemini API)
- `anonymize_career_data()` redacts:
  - Email addresses → `[EMAIL]` or `[USER]@domain.com`
  - Phone numbers → `[PHONE]`
  - Home addresses → `[HOME_ADDRESS]`
  - Social media usernames → `[USERNAME]`

### SSRF Protection
- Portfolio fetcher blocks private IP ranges (127.x, 10.x, 172.16-31.x, 192.168.x)
- Validates both direct IPs and resolved hostnames
- Only allows http/https schemes

### Path Traversal Protection
- All file operations use `_safe_path()` validation
- Paths resolved to absolute form and verified within base directory
- Symlink access blocked

### Command Injection Protection
- External CLI tools invoked via `subprocess.run()` with list arguments (no `shell=True`)
- 5-minute timeout on all subprocess calls

### File Permissions
- Sensitive output files created with `0o600` permissions (owner read/write only)

## Code Style

- Use `collections.abc` for type hints like `Mapping`, `Sequence` (not `typing`)
- Avoid ambiguous single-letter variable names (use `link` not `l`)
- Keep lines under 100 characters
- Remove unused imports and variables
- Use dependency injection for testability
- Prefer raising exceptions over returning error dicts

## Testing

- Tests are in `tests/` directory
- Use fixtures from `conftest.py` for common test data
- Mock external services (LLM, HTTP) to avoid API calls
- Clear data loader cache between tests with `clear_data_cache()`

## Configuration

Settings are loaded from environment variables via Pydantic (`config.py`):

### LLM Providers
- `GEMINI_API_KEY` - Gemini LLM and embeddings
- `GROQ_API_KEY` - Groq LLM (fast fallback)
- `CEREBRAS_API_KEY` - Cerebras LLM
- `SAMBANOVA_API_KEY` - SambaNova LLM
- `AZURE_OPENAI_API_KEY` - Azure OpenAI (top priority in fallback chain)
- `AZURE_OPENAI_ENDPOINT` - Azure endpoint URL
- `AZURE_OPENAI_API_VERSION` - Azure API version (default: `2024-12-01-preview`)
- `AZURE_CHAT_DEPLOYMENT` - Azure chat model deployment name
- `AZURE_EMBEDDING_DEPLOYMENT` - Azure embedding deployment name
- `LLM_PROVIDER` - Default provider: `gemini`, `groq`, or `azure`
- `LLM_MODEL` - Override model name (empty = provider default)
- `LLM_TEMPERATURE` - Generation temperature (default: `0.3`)
- `CV_TEMPERATURE` - CV generation temperature (default: `0.2`)

### Data Sources
- `GITHUB_USERNAME`, `GITLAB_USERNAME` - Profiles to gather
- `GITLAB_GROUPS` - Comma-separated GitLab groups (validated for safe characters)
- `PORTFOLIO_URL` - Portfolio website URL

### MCP Servers
- `GITHUB_PERSONAL_ACCESS_TOKEN` - GitHub API token
- `GITHUB_MCP_TOKEN` - Alternative GitHub token for MCP
- `GITHUB_MCP_USE_DOCKER` - Use Docker for GitHub MCP server (default: `true`)
- `GITLAB_MCP_URL` - GitLab MCP server URL
- `GITLAB_MCP_TOKEN` - GitLab MCP token
- `TAVILY_API_KEY` - Tavily search API key

### Market Intelligence
- `JOBSPY_ENABLED` - Enable JobSpy scraping (default: `true`)
- `HN_MCP_ENABLED` - Enable Hacker News trends (default: `true`)
- `MARKET_CACHE_HOURS` - Tech trends cache TTL (default: `24`)
- `JOB_CACHE_HOURS` - Job data cache TTL (default: `12`)
- `CONTENT_CACHE_HOURS` - Content trends cache TTL (default: `12`)

## Key Modules

### `utils/security.py`
Security utilities for input sanitization and PII protection:
- `detect_prompt_injection(text)` - Returns list of detected injection patterns
- `sanitize_user_input(text, strict)` - Returns `SanitizationResult` with safety status
- `anonymize_pii(text)` - General PII anonymization
- `anonymize_career_data(data, preserve_professional_emails)` - Career-specific anonymization

### `utils/data_loader.py`
Centralized data loading with security checks:
- Path traversal protection via `_safe_path()`
- Symlink blocking
- Memoization for performance

### `gatherers/portfolio/fetcher.py`
HTTP client with security features:
- SSRF protection via IP/hostname validation
- SSL verification enabled
- Redirect limiting (max 5)
- Request timeout (30 seconds)

### `mcp/`
MCP client implementations (13 clients) with registry pattern via `factory.py`:
- `github_client.py`, `gitlab_client.py` — Code platform APIs (stdio transport)
- `hn_client.py` — Hacker News via Algolia API (no auth)
- `tavily_client.py` — Web search API
- `jobspy_client.py` — Job board scraping (LinkedIn, Indeed, Glassdoor, ZipRecruiter)
- `remoteok_client.py`, `himalayas_client.py`, `jobicy_client.py`, `weworkremotely_client.py`, `remotive_client.py` — Remote job board APIs
- `devto_client.py`, `stackoverflow_client.py` — Developer content trends

## Knowledge Base Architecture

The knowledge base provides RAG (Retrieval Augmented Generation) for career data:

- **Location**: `src/futureproof/memory/knowledge.py`
- **Chunking**: `src/futureproof/memory/chunker.py`
- **Service**: `src/futureproof/services/knowledge_service.py`
- **Storage**: ChromaDB collection `career_knowledge` (separate from episodic memory)

### Data Flow
1. Gatherer collects data → `data/processed/{source}/`
2. Auto-index (if enabled) → chunks markdown by `##` headers
3. Agent searches → `search_career_knowledge()` tool
4. Relevant chunks returned → used in response generation

### Key Classes

**`MarkdownChunker`** (`memory/chunker.py`):
- Splits markdown by `##` headers while preserving context
- Configurable max/min token limits (default: 500/50)
- Tracks section hierarchy for metadata

**`CareerKnowledgeStore`** (`memory/knowledge.py`):
- ChromaDB wrapper for career data vectors
- Supports filtering by source (github, gitlab, linkedin, portfolio, assessment)
- Methods: `index_markdown_file()`, `search()`, `clear_source()`, `get_stats()`

**`KnowledgeService`** (`services/knowledge_service.py`):
- Orchestrates indexing and search operations
- Maps source names to file paths in `data/processed/`
- Methods: `index_source()`, `index_all()`, `search()`, `get_stats()`

### Agent Tools (`agents/tools/knowledge.py`)

```python
search_career_knowledge(query, sources, limit)   # Search indexed career data
get_knowledge_stats()                              # Show indexing status
index_career_knowledge(source)                     # Index gathered data
clear_career_knowledge(source)                     # Clear indexed data (HITL)
```

### Auto-Indexing

After each gather operation, the `GathererService` automatically indexes the source if `KNOWLEDGE_AUTO_INDEX=true` (default). Market intelligence data (ephemeral JSON with TTL) is NOT indexed.

### Knowledge Base Configuration

See `KNOWLEDGE_AUTO_INDEX`, `KNOWLEDGE_CHUNK_MAX_TOKENS`, `KNOWLEDGE_CHUNK_MIN_TOKENS` in the Configuration section above.

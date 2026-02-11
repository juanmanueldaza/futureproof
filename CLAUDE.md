# FutureProof - Claude Code Guidelines

## Project Overview

FutureProof is a career intelligence CLI tool that gathers professional data from multiple sources (LinkedIn, GitHub, GitLab, portfolio sites) and uses AI to analyze career trajectories, identify gaps, and generate optimized CVs.

## Tech Stack

- **Python 3.13** with type hints
- **LangChain/LangGraph** for AI orchestration
- **Pydantic** for configuration and validation
- **Typer** for CLI
- **pytest** for testing
- **uv** for package management

## Project Structure

```
src/futureproof/
├── agents/          # LangGraph orchestration and state management
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
├── utils/           # Shared utilities (logging, data loading, security)
└── validation/      # Pydantic input validation models
```

## Commands

```bash
# Run tests
pytest tests/ -q

# Type checking
pyright src/futureproof

# Linting
ruff check .

# Fix lint issues
ruff check . --fix

# Run CLI
futureproof --help
futureproof gather all
futureproof analyze full
futureproof generate cv
```

## Architecture Principles

This codebase follows SOLID, DRY, KISS, and YAGNI principles:

- **SRP**: Each class has a single responsibility (e.g., PortfolioGatherer split into Fetcher, HTMLExtractor, JSExtractor, MarkdownWriter)
- **OCP**: MCP clients extensible via registry pattern; LLM providers configured declaratively in `FallbackLLMManager`
- **DIP**: High-level modules depend on `FallbackLLMManager` abstraction with `init_chat_model()` universal factory
- **DRY**: Service layer eliminates CLI command duplication; CareerDataLoader consolidates data loading
- **ISP**: CareerState split into focused TypedDicts (GatherInput, AnalyzeInput, etc.)

## Agent Architecture

The chat agent uses a **multi-agent supervisor pattern** built on LangGraph:

- **Supervisor agent**: Handles profile management, analysis, CV generation, and memory tools. Routes to research agent when data gathering or market intelligence is needed.
- **Research agent**: Handles data gathering (GitHub, GitLab, portfolio), knowledge search, and market intelligence (jobs, trends, salaries).
- **Handoff tools**: `transfer_to_research` and `transfer_to_supervisor` use `Command(goto=..., graph=Command.PARENT)` for inter-agent routing.
- **Human-in-the-loop**: `interrupt()` on `generate_cv` and `gather_all_career_data` for user confirmation.
- **Context management**: `SummarizationMiddleware` auto-summarizes old messages (triggers at 8k tokens, keeps last 20 messages).
- **Memory**: Dual-write to `InMemoryStore` (runtime, cross-thread semantic search) + ChromaDB (persistent).
- **State**: `add_messages` reducer from `langgraph.graph.message` for message deduplication by ID.
- **Orchestrator**: LangGraph Functional API (`@entrypoint`/`@task`) in `orchestrator.py` for parallel gatherer execution.
- **LLM**: Unified on `FallbackLLMManager` using `init_chat_model()` — supports Azure, Groq, Gemini, Cerebras, SambaNova.

## Security

The codebase implements security best practices:

### Input Validation
- All user inputs validated via Pydantic models (`validation/models.py`)
- GitHub/GitLab usernames validated with strict regex patterns
- GitLab groups validated before CLI execution to prevent argument injection
- URLs validated with Pydantic's `HttpUrl` type

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

Settings are loaded from environment variables via Pydantic:

- `GEMINI_API_KEY` - For Gemini LLM and embeddings
- `AZURE_OPENAI_API_KEY` - For Azure OpenAI (top priority in fallback chain)
- `GROQ_API_KEY` - For Groq LLM
- `GITHUB_USERNAME`, `GITLAB_USERNAME` - For data gathering
- `GITLAB_GROUPS` - Comma-separated GitLab groups (validated for safe characters)
- `PORTFOLIO_URL` - Portfolio website URL

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

### Agent Tools

Two tools available to the career agent (`agents/tools.py`):

```python
@tool
def search_career_knowledge(query: str, sources: list[str] | None = None, limit: int = 5) -> str:
    """Search the career knowledge base for relevant information."""

@tool
def get_knowledge_stats() -> str:
    """Get statistics about the career knowledge base."""
```

### Auto-Indexing

After each gather operation, the `GathererService` automatically indexes the source if `KNOWLEDGE_AUTO_INDEX=true` (default). Market intelligence data (ephemeral JSON with TTL) is NOT indexed.

### Configuration

```bash
KNOWLEDGE_AUTO_INDEX=true       # Auto-index after gather (default: true)
KNOWLEDGE_CHUNK_MAX_TOKENS=500  # Max tokens per chunk
KNOWLEDGE_CHUNK_MIN_TOKENS=50   # Min tokens per chunk
```

### CLI Commands

```bash
futureproof index [SOURCE]      # Index all or specific source
futureproof knowledge stats     # Show knowledge base stats
futureproof knowledge search    # Search knowledge base
futureproof knowledge clear     # Clear indexed data
futureproof chat --verbose      # Show tool usage during chat
```

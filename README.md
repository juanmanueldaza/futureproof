# FutureProof

Career intelligence system that gathers your professional data, analyzes your career trajectory, and generates optimized CVs — all through a conversational AI agent.

## Description

FutureProof aggregates data from LinkedIn, GitHub, GitLab, portfolio websites, and CliftonStrengths assessments into a searchable knowledge base. It uses AI to identify skill gaps, assess market fit, track tech trends, and generate ATS-optimized CVs. Everything happens through an interactive chat interface powered by a single LangChain agent with 32 specialized tools.

### Key capabilities

- **Data gathering** from GitHub, GitLab, LinkedIn exports, portfolio sites, and CliftonStrengths PDFs
- **Knowledge base** with RAG-powered semantic search over all your career data
- **Career analysis** — skill gaps, career alignment, market fit, strategic advice
- **Market intelligence** — job search across 7+ boards, tech trends from Hacker News, salary insights
- **CV generation** in English/Spanish, ATS or creative format (Markdown + PDF)
- **Episodic memory** — remembers your decisions, job applications, and preferences across sessions
- **Privacy protection** — PII anonymization before sending data to external LLMs

## Installation

```bash
cd futureproof
uv sync

cp .env.example .env
# Edit .env with your API keys
```

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

### External tools (optional)

These CLI tools provide fallback when MCP servers are unavailable:

- [github2md](https://github.com/juanmanueldaza/github2md) — GitHub profile to markdown
- [gitlab2md](https://github.com/juanmanueldaza/gitlab2md) — GitLab profile to markdown
- [linkedin2md](https://github.com/juanmanueldaza/linkedin2md) — LinkedIn export ZIP to markdown

## Usage

### Interactive chat

```bash
futureproof chat                    # Start chat session
futureproof chat --verbose          # Show tool usage
futureproof chat --thread work      # Use a named thread
```

### Quick questions

```bash
futureproof ask "What are my top skills?"
futureproof ask "Analyze my gaps for ML Engineer"
```

### Memory management

```bash
futureproof memory --threads        # List conversation threads
futureproof memory --clear          # Clear all history
```

### What you can ask

**Data gathering:**
- "Gather my GitHub data"
- "Import my LinkedIn export"
- "Gather all my data" (auto-detects configured sources)

**Knowledge & analysis:**
- "Search my knowledge base for Python projects"
- "Analyze my skill gaps for Staff Engineer"
- "How do I fit the current job market?"

**Market intelligence:**
- "Search for remote Python developer jobs"
- "What are the latest tech trends?"
- "Get salary insights for ML Engineer"

**CV generation:**
- "Generate my CV in ATS format"
- "Generate a CV draft for DevOps Engineer"

### Data sources setup

Place data exports in `data/raw/`:
- **LinkedIn**: Download your data export ZIP from LinkedIn Settings > Data Privacy
- **CliftonStrengths**: Download Gallup PDF reports (Top 5, All 34, etc.)

Configure environment variables for live sources:
```bash
GITHUB_USERNAME=your_username
GITLAB_USERNAME=your_username
PORTFOLIO_URL=https://your-site.com
```

See [docs/SOURCES.md](docs/SOURCES.md) for the complete setup guide.

## Configuration

Copy `.env.example` and set your keys:

```bash
cp .env.example .env
```

**Minimum (one key is enough):**
```bash
GEMINI_API_KEY=AIza...
```

**Recommended:**
```bash
GEMINI_API_KEY=AIza...                          # LLM + embeddings
GROQ_API_KEY=gsk_...                            # Fast fallback
GITHUB_USERNAME=your_username
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...            # GitHub data via MCP
PORTFOLIO_URL=https://your-site.com
TAVILY_API_KEY=tvly-...                         # Market research
```

The LLM fallback chain tries models in order: Azure GPT-4.1 → Groq Llama 3.3 → Gemini 2.5 Flash → Cerebras → SambaNova. Configure any provider and it works.

## Project structure

```
src/futureproof/
├── cli.py                  # Typer CLI (chat, ask, memory)
├── config.py               # Pydantic settings from env vars
├── agents/
│   ├── career_agent.py     # Single agent with create_agent()
│   ├── orchestrator.py     # LangGraph Functional API for analysis workflows
│   ├── state.py            # TypedDict state definitions
│   ├── helpers/            # Orchestrator support (data pipeline, LLM invoker)
│   └── tools/              # 32 agent tools organized by domain
│       ├── profile.py      # User profile management (6 tools)
│       ├── gathering.py    # Data collection (7 tools)
│       ├── knowledge.py    # RAG search & indexing (4 tools)
│       ├── analysis.py     # Career analysis (3 tools)
│       ├── market.py       # Market intelligence (6 tools)
│       ├── generation.py   # CV generation (2 tools)
│       └── memory.py       # Episodic memory (4 tools)
├── chat/                   # Streaming chat client with HITL support
├── gatherers/
│   ├── github.py           # GitHub via MCP or github2md CLI
│   ├── gitlab.py           # GitLab via MCP or gitlab2md CLI
│   ├── linkedin.py         # LinkedIn ZIP via linkedin2md CLI
│   ├── cliftonstrengths.py # CliftonStrengths PDF parser
│   ├── portfolio/          # Website scraper (fetcher, HTML/JS extractors)
│   └── market/             # Job market, tech trends, content trends
├── generators/             # CV generation (Markdown + PDF via WeasyPrint)
├── llm/                    # FallbackLLMManager with init_chat_model()
├── memory/
│   ├── store.py            # LangGraph InMemoryStore (runtime semantic search)
│   ├── knowledge.py        # ChromaDB knowledge store (RAG)
│   ├── episodic.py         # ChromaDB episodic memory
│   ├── chunker.py          # Markdown chunker for indexing
│   ├── embeddings.py       # Gemini/Azure embedding functions
│   ├── checkpointer.py     # SQLite conversation persistence
│   └── profile.py          # User profile (YAML)
├── mcp/                    # 13 MCP clients (GitHub, GitLab, HN, Tavily, job boards)
├── prompts/                # LLM prompt templates
├── services/               # Business logic layer
└── utils/                  # Security, data loading, logging
```

## Security

- **Prompt injection protection** — user inputs screened for 13 injection patterns
- **PII anonymization** — emails, phones, addresses redacted before external LLM calls
- **SSRF protection** — portfolio scraper blocks private IP ranges
- **Path traversal protection** — file operations validated within base directory
- **Command injection protection** — external tools invoked without shell expansion
- **Secure file permissions** — sensitive files created with 0600 permissions

## Development

```bash
pytest tests/ -q              # Run tests
pyright src/futureproof       # Type checking
ruff check .                  # Lint
ruff check . --fix            # Auto-fix lint issues
```

## Tech stack

- **Python 3.13+** with type hints
- **LangChain + LangGraph** — agent orchestration, `create_agent()`, `SummarizationMiddleware`
- **ChromaDB** — vector storage for knowledge base and episodic memory
- **Pydantic** — settings management
- **Typer + Rich** — CLI and terminal UI
- **httpx** — async HTTP client
- **WeasyPrint** — PDF generation
- **uv** — package management

## License

[GPL-2.0](LICENSE)

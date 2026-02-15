# FutureProof

[![CI](https://github.com/juanmanueldaza/futureproof/actions/workflows/ci.yml/badge.svg)](https://github.com/juanmanueldaza/futureproof/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v2](https://img.shields.io/badge/License-GPL_v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)

Career intelligence system that gathers your professional data, analyzes your career trajectory, and generates optimized CVs — all through a conversational AI agent.

## Description

FutureProof aggregates data from LinkedIn, GitHub, GitLab, portfolio websites, and CliftonStrengths assessments into a searchable knowledge base. It uses AI to identify skill gaps, assess market fit, track tech trends, and generate ATS-optimized CVs. Everything happens through an interactive chat interface powered by a single LangChain agent with 36 specialized tools.

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
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

cp .env.example .env
# Edit .env with your API keys
```

### Prerequisites

- Python 3.13+

## Usage

### Interactive chat

```bash
futureproof chat                    # Start chat session (verbose by default)
futureproof chat --debug            # Also show debug logs in terminal
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

**Minimum:**
```bash
AZURE_OPENAI_API_KEY=abc123...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_CHAT_DEPLOYMENT=gpt-4.1
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

**Recommended:**
```bash
AZURE_OPENAI_API_KEY=abc123...                  # LLM + embeddings
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_CHAT_DEPLOYMENT=gpt-4.1
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_AGENT_DEPLOYMENT=gpt-4o                   # Best model for tool calling
AZURE_ANALYSIS_DEPLOYMENT=gpt-4.1               # Analysis & CV generation
AZURE_SUMMARY_DEPLOYMENT=gpt-4o-mini            # Cheap model for summarization
GITHUB_USERNAME=your_username
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...            # GitHub data via MCP
PORTFOLIO_URL=https://your-site.com
TAVILY_API_KEY=tvly-...                         # Market research
```

The LLM fallback chain tries Azure models in order: GPT-4.1 → GPT-4o → GPT-4.1 Mini → GPT-4o Mini, auto-switching on rate limits. Purpose-based model routing lets you assign different models to agent tool calling, analysis, and summarization via env vars.

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
│   └── tools/              # 36 agent tools organized by domain
│       ├── profile.py      # User profile management (6 tools)
│       ├── gathering.py    # Data collection (5 tools)
│       ├── github.py       # Live GitHub queries via MCP (3 tools)
│       ├── gitlab.py       # Live GitLab queries via glab CLI (3 tools)
│       ├── knowledge.py    # RAG search & indexing (4 tools)
│       ├── analysis.py     # Career analysis (3 tools)
│       ├── market.py       # Market intelligence (6 tools)
│       ├── generation.py   # CV generation (2 tools)
│       └── memory.py       # Episodic memory (4 tools)
├── chat/                   # Streaming chat client with HITL support
├── gatherers/
│   ├── linkedin.py         # LinkedIn ZIP direct CSV parser
│   ├── cliftonstrengths.py # CliftonStrengths PDF parser
│   ├── portfolio/          # Website scraper (fetcher, HTML/JS extractors)
│   └── market/             # Job market, tech trends, content trends
├── generators/             # CV generation (Markdown + PDF via WeasyPrint)
├── llm/                    # FallbackLLMManager with purpose-based model routing
├── memory/
│   ├── knowledge.py        # ChromaDB knowledge store (RAG)
│   ├── episodic.py         # ChromaDB episodic memory
│   ├── chunker.py          # Markdown chunker for indexing
│   ├── embeddings.py       # Azure OpenAI embedding functions
│   ├── checkpointer.py     # SQLite conversation persistence
│   └── profile.py          # User profile (YAML)
├── mcp/                    # 12 MCP clients (GitHub, HN, Tavily, job boards)
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
pip install -r requirements-dev.txt
pip install -e .

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
- **pip** — package management

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for details on how to contribute to this project.

## License

[GPL-2.0](LICENSE)

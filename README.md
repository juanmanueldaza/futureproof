# FutureProof

**Career Intelligence System** - Know thyself through your data.

A conversational AI agent that aggregates professional data from LinkedIn, GitHub, GitLab, and your personal portfolio, then uses AI to generate optimized CVs, provide career analysis, and surface market intelligence — all through an interactive chat interface.

## Features

- **Interactive Chat Agent** - Conversational interface powered by a single AI agent with 32 specialized tools
- **Data Gathering** - Pull professional data from GitHub, GitLab, LinkedIn, portfolio sites, and CliftonStrengths
- **CV Generation** - Produce ATS-optimized CVs in English and Spanish (with human-in-the-loop confirmation)
- **Career Analysis** - Compare stated goals vs actual behavior, identify gaps, assess market fit
- **Market Intelligence** - Real-time job market data, tech trends, salary insights, and skill demand analysis
- **Knowledge Base** - RAG-powered semantic search over your career data
- **Privacy Protection** - PII anonymization before sending data to external LLMs

## Installation

```bash
# Clone and enter directory
cd futureproof

# Install with uv
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

### External Tools

- **github2md** - CLI fallback when GitHub MCP server is unavailable
- **gitlab2md** - CLI fallback when GitLab MCP server is unavailable
- **linkedin2md** - Processes LinkedIn data export ZIP files

### MCP Integration (Recommended)

FutureProof supports [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers for real-time data access, with automatic fallback to CLI tools if unavailable.

**GitHub MCP Server** (requires Docker):
```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."
```

**GitLab MCP Server** (HTTP transport):
```bash
export GITLAB_MCP_URL="https://gitlab.com/api/v4/mcp"
export GITLAB_MCP_TOKEN="glpat-..."
```

## Usage

### Chat (Primary Interface)

```bash
# Start interactive chat session
futureproof chat

# Show tool usage and agent reasoning
futureproof chat --verbose

# Quick one-off question
futureproof ask "What are my top skills?"
futureproof ask "Analyze my gaps for ML Engineer role"

# Manage conversation memory
futureproof memory --threads
futureproof memory --clear
```

Everything is accessible through the chat agent. Just ask:

- **"Gather my GitHub data"** - Fetches your GitHub profile and repos
- **"Import my LinkedIn export"** - Processes a LinkedIn ZIP from data/raw/
- **"Gather all my data"** - Auto-detects and gathers from all configured sources
- **"Index my career data"** - Creates searchable embeddings in the knowledge base
- **"Search my knowledge base for Python projects"** - Semantic search over gathered data
- **"Analyze my skill gaps for ML Engineer"** - AI-powered gap analysis
- **"How do I fit the current job market?"** - Market fit analysis against trends
- **"Search for remote Python developer jobs"** - Job market search
- **"What are the latest tech trends?"** - Trending technologies from Hacker News
- **"Generate my CV in ATS format"** - Creates an optimized CV (with confirmation)

### Data Sources Setup

Place data exports in `data/raw/` for auto-detection:
- **LinkedIn**: Download your data export ZIP from LinkedIn Settings > Data Privacy
- **CliftonStrengths**: Download Gallup PDF reports

Configure environment variables for live data sources:
```bash
GITHUB_USERNAME=your_username
GITLAB_USERNAME=your_username
PORTFOLIO_URL=https://your-site.com
```

See [docs/SOURCES.md](docs/SOURCES.md) for the complete setup guide.

## Configuration

```bash
cp .env.example .env
```

**Quick start (minimum config):**
```bash
GEMINI_API_KEY=your_key_here
```

**Recommended config:**
```bash
GEMINI_API_KEY=AIza...                          # LLM + embeddings
GROQ_API_KEY=gsk_...                            # Fast fallback
GITHUB_USERNAME=your_username
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...            # GitHub data
PORTFOLIO_URL=https://your-site.com
TAVILY_API_KEY=tvly-...                         # Market research
```

## Project Structure

```
futureproof/
├── src/futureproof/
│   ├── cli.py              # Typer CLI (chat, ask, memory)
│   ├── config.py           # Pydantic settings
│   ├── agents/             # Single agent with tool modules
│   │   ├── career_agent.py # Single agent with create_agent()
│   │   ├── helpers/        # Orchestrator support
│   │   └── tools/          # Agent tool modules
│   │       ├── profile.py      # User profile management
│   │       ├── gathering.py    # Data collection tools
│   │       ├── analysis.py     # Career analysis tools
│   │       ├── market.py       # Market intelligence tools
│   │       ├── generation.py   # CV generation tools
│   │       ├── knowledge.py    # RAG search & indexing tools
│   │       └── memory.py       # Episodic memory tools
│   ├── chat/               # Chat client (streaming, HITL)
│   ├── gatherers/          # Data collectors (MCP + CLI fallback)
│   │   ├── github.py       # GitHub gatherer
│   │   ├── gitlab.py       # GitLab gatherer
│   │   ├── linkedin.py     # LinkedIn ZIP processor
│   │   ├── cliftonstrengths.py  # CliftonStrengths PDF processor
│   │   ├── portfolio/      # Portfolio website scraper
│   │   └── market/         # Market intelligence gatherers
│   ├── generators/         # CV generators
│   ├── llm/                # LLM fallback manager
│   ├── memory/             # Knowledge & memory storage
│   ├── mcp/                # MCP client implementations
│   ├── prompts/            # LLM prompt templates
│   ├── services/           # Business logic layer
│   └── utils/              # Utilities (security, data loading)
├── data/
│   ├── raw/                # Raw data exports (LinkedIn ZIPs, Gallup PDFs)
│   ├── processed/          # Processed markdown files
│   └── output/             # Generated CVs
└── tests/                  # Unit tests
```

## Security Features

- **Prompt Injection Protection** - User inputs screened for injection attempts before LLM calls
- **PII Anonymization** - Personal data redacted before sending to external APIs
- **SSRF Protection** - Portfolio scraper blocks requests to private IP ranges
- **Path Traversal Protection** - File operations validated to prevent directory escape
- **Command Injection Protection** - External tools invoked safely without shell expansion
- **Secure File Permissions** - Sensitive output files created with owner-only permissions (0600)

## Tech Stack

- **Python 3.13+** with type hints
- **LangChain + LangGraph** for AI orchestration
- **Multi-provider LLM** (Azure, Gemini, Groq, Cerebras, SambaNova) with automatic fallback
- **Typer** for CLI
- **Pydantic** for configuration
- **httpx** for HTTP requests
- **BeautifulSoup4** for HTML parsing
- **WeasyPrint** for PDF generation
- **ChromaDB** for vector storage (knowledge base)
- **pytest** for testing
- **uv** for package management

## Development

```bash
# Run tests
pytest tests/ -q

# Type checking
pyright src/futureproof

# Linting
ruff check .

# Fix lint issues
ruff check . --fix
```

## License

GPL-2.0

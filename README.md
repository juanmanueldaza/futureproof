# FutureProof

**Career Intelligence System** - Know thyself through your data.

A Python CLI tool that aggregates professional data from LinkedIn, GitHub, GitLab, and your personal portfolio, then uses AI to generate optimized CVs and provide career alignment analysis.

## Features

- **Data Gathering** - Pull professional data from multiple sources into normalized markdown
- **CV Generation** - Produce ATS-optimized CVs in English and Spanish (MD + PDF)
- **Career Analysis** - Compare stated goals vs actual behavior, identify gaps
- **Market Intelligence** - Real-time job market data, tech trends, and skill demand analysis
- **Strategic Advice** - Get actionable recommendations using Gemini AI
- **Privacy Protection** - PII anonymization before sending data to external LLMs

## Installation

```bash
# Clone and enter directory
cd futureproof

# Install with uv
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY
```

### External Tools

The following CLI tools are used for data gathering (as fallback):

- **github2md** - Included as dependency (extracts GitHub profile data)
- **gitlab2md** - Included as dependency (extracts GitLab profile data)
- **linkedin2md** - Included as dependency (processes LinkedIn data export)

### MCP Integration (Recommended)

FutureProof supports [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers for real-time data access, with automatic fallback to CLI tools if unavailable.

**GitHub MCP Server** (requires Docker):
```bash
# Set your GitHub Personal Access Token
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."

# The MCP server runs in Docker automatically
futureproof gather github
```

**GitLab MCP Server** (HTTP transport):
```bash
# Set GitLab MCP endpoint and token
export GITLAB_MCP_URL="https://gitlab.com/api/v4/mcp"
export GITLAB_MCP_TOKEN="glpat-..."

futureproof gather gitlab
```

Benefits of MCP over CLI tools:
- **Real-time data** - No stale cache
- **Targeted queries** - Fetch only what's needed
- **Official implementations** - Maintained by GitHub/GitLab

## Usage

### Gather Data

```bash
# Gather from all configured sources
futureproof gather all

# Individual sources
futureproof gather github
futureproof gather github --username other-user
futureproof gather gitlab
futureproof gather gitlab --username other-user
futureproof gather portfolio
futureproof gather portfolio --url https://example.com
futureproof gather linkedin path/to/LinkedInDataExport.zip
```

### Generate CVs

```bash
# Generate specific version
futureproof generate cv --lang en --format ats
futureproof generate cv --lang es --format creative

# Generate all combinations (en/es × ats/creative)
futureproof generate cv --all
```

Output files are saved to `data/output/` as both Markdown and PDF.

### Analyze Career

```bash
# Full comprehensive analysis
futureproof analyze full

# Specific aspects
futureproof analyze goals     # What you say you want
futureproof analyze reality   # What you're actually doing
futureproof analyze gaps      # The delta between them
```

### Get Strategic Advice

```bash
futureproof advise --target "AI Engineer in Europe"
futureproof advise --target "Senior Backend Developer at FAANG"
```

### Knowledge Base (RAG)

FutureProof maintains a semantic knowledge base of your career data for intelligent retrieval:

```bash
# Index all gathered data
futureproof index

# Index specific source
futureproof index github
futureproof index gitlab
futureproof index linkedin
futureproof index portfolio
futureproof index assessment

# Check what's indexed
futureproof knowledge stats

# Search knowledge base directly
futureproof knowledge search "Python projects"

# Clear indexed data (for re-indexing)
futureproof knowledge clear
futureproof knowledge clear --source github
```

**How it works:**
- Career data (GitHub, GitLab, LinkedIn, Portfolio, CliftonStrengths) is chunked and embedded
- The agent searches relevant sections instead of loading everything into context
- Auto-indexes after each gather operation (configurable)

**Verbose mode** shows agent reasoning and tool usage:
```bash
futureproof chat --verbose
# Shows: 🔧 Using tool: search_career_knowledge
```

### Market Intelligence

Gather real-time market data to inform your career decisions:

```bash
# Gather all market intelligence data
futureproof market gather

# Get current tech trends from Hacker News
futureproof market trends
futureproof market trends --query "AI agents"

# Search job market for specific roles
futureproof market jobs --role "AI Engineer" --location "Berlin"
futureproof market jobs --role "Backend Developer" --location "Remote"

# Analyze how your profile fits current market demands
futureproof market fit
futureproof market fit --refresh  # Refresh cached market data

# Identify skill gaps based on market demands
futureproof market skills
futureproof market skills --refresh
```

**Data Sources:**
- **Hacker News** - Technology trends and discussions (free, no API key)
- **Tavily** - Web search for salary data and market research (free, no credit card)
- **JobSpy** - Job listings from LinkedIn, Indeed, Glassdoor, ZipRecruiter (free)

## Configuration

Create a `.env` file (copy from `.env.example`):

```bash
# Required
GEMINI_API_KEY=your_key_here

# Data gathering (defaults shown)
GITHUB_USERNAME=yourusername
GITLAB_USERNAME=yourusername
GITLAB_GROUPS=group1,group2
PORTFOLIO_URL=https://yoursite.com

# Output preferences
DEFAULT_LANGUAGE=en  # en or es

# LLM settings (optional)
LLM_MODEL=gemini-3-flash
LLM_TEMPERATURE=0.3
CV_TEMPERATURE=0.2

# MCP Integration (optional - enables real-time data access)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...  # GitHub MCP (requires Docker)
GITLAB_MCP_URL=https://gitlab.com/api/v4/mcp
GITLAB_MCP_TOKEN=glpat-...

# Market Intelligence (optional)
TAVILY_API_KEY=tvly-...  # For Tavily Search (free at https://tavily.com/)

# Knowledge Base (optional)
KNOWLEDGE_AUTO_INDEX=true      # Auto-index after gather (default: true)
KNOWLEDGE_CHUNK_MAX_TOKENS=500 # Max tokens per chunk
KNOWLEDGE_CHUNK_MIN_TOKENS=50  # Min tokens per chunk
```

## Project Structure

```
futureproof/
├── src/futureproof/
│   ├── cli.py              # Typer CLI entry point
│   ├── config.py           # Pydantic settings
│   ├── agents/             # LangGraph orchestration
│   ├── gatherers/          # Data collectors (MCP + CLI fallback)
│   │   ├── github.py       # GitHub gatherer
│   │   ├── gitlab.py       # GitLab gatherer
│   │   ├── linkedin.py     # LinkedIn ZIP processor
│   │   ├── portfolio/      # Portfolio website scraper
│   │   └── market/         # Market intelligence gatherers
│   │       ├── job_market_gatherer.py   # Job listings (JobSpy)
│   │       └── tech_trends_gatherer.py  # Tech trends (HN, Brave)
│   ├── generators/         # CV generators
│   ├── llm/                # LLM provider abstraction
│   ├── memory/             # Knowledge storage
│   │   ├── chunker.py       # Markdown text chunker
│   │   ├── knowledge.py     # ChromaDB knowledge store (RAG)
│   │   └── episodic.py      # Episodic memory store
│   ├── mcp/                # MCP client implementations
│   │   ├── base.py         # MCPClient ABC & exceptions
│   │   ├── factory.py      # MCPClientFactory
│   │   ├── github_client.py # GitHub MCP (stdio/Docker)
│   │   ├── gitlab_client.py # GitLab MCP (HTTP transport)
│   │   ├── tavily_client.py # Tavily Search API
│   │   ├── hn_client.py     # Hacker News API
│   │   └── jobspy_client.py # JobSpy job scraper
│   ├── prompts/            # LLM prompt templates
│   ├── services/           # Business logic layer
│   ├── utils/              # Utilities
│   │   ├── data_loader.py  # Career data loading
│   │   ├── security.py     # Input sanitization & PII protection
│   │   └── logging.py      # Logging configuration
│   └── validation/         # Pydantic input models
├── data/
│   ├── raw/                # Raw data exports
│   ├── processed/          # Processed markdown files
│   └── output/             # Generated CVs (MD + PDF)
└── tests/                  # Unit tests
```

## Security Features

FutureProof implements security best practices:

- **Input Validation** - All user inputs validated via Pydantic with strict patterns
- **Prompt Injection Protection** - User inputs screened for injection attempts before LLM calls
- **PII Anonymization** - Personal data (emails, phones, addresses) redacted before sending to Gemini API
- **SSRF Protection** - Portfolio scraper blocks requests to private IP ranges
- **Path Traversal Protection** - File operations validated to prevent directory escape
- **Command Injection Protection** - External CLI tools invoked safely without shell expansion
- **Secure File Permissions** - Sensitive output files created with owner-only permissions (0600)

## Tech Stack

- **Python 3.13+** with type hints
- **LangChain + LangGraph** for AI orchestration
- **Gemini API** (Google) for LLM operations
- **Typer** for CLI
- **Pydantic** for configuration and validation
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

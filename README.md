# FutureProof

**Career Intelligence System** - Know thyself through your data.

A Python CLI tool that aggregates professional data from LinkedIn, GitHub, GitLab, and your personal portfolio, then uses AI to generate optimized CVs and provide career alignment analysis.

## Features

- **Data Gathering** - Pull professional data from multiple sources into normalized markdown
- **CV Generation** - Produce ATS-optimized CVs in English and Spanish (MD + PDF)
- **Career Analysis** - Compare stated goals vs actual behavior, identify gaps
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
│   │   └── portfolio/      # Portfolio website scraper
│   ├── generators/         # CV generators
│   ├── llm/                # LLM provider abstraction
│   ├── mcp/                # MCP client implementations
│   │   ├── base.py         # MCPClient ABC & exceptions
│   │   ├── factory.py      # MCPClientFactory
│   │   ├── github_client.py # GitHub MCP (stdio/Docker)
│   │   └── gitlab_client.py # GitLab MCP (HTTP transport)
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

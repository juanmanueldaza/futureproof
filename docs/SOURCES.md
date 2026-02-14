# Data Sources Setup Guide

FutureProof connects to many data sources. **None are strictly required** -- the system works with whatever you configure and gracefully skips the rest.

**Minimum to get started:** Azure OpenAI API key and endpoint.

---

## Table of Contents

- [LLM Provider](#llm-provider)
- [Career Data Sources](#career-data-sources)
- [Market Intelligence Sources](#market-intelligence-sources)
- [Embeddings (Knowledge Base)](#embeddings-knowledge-base)
- [Quick Reference](#quick-reference)

---

## LLM Provider

FutureProof uses **Azure OpenAI** with a 2-model fallback chain — if GPT-4.1 hits a rate limit or errors, it automatically falls back to GPT-4.1 Mini.

### Azure OpenAI / AI Foundry

| | |
|---|---|
| **Free tier** | $200 credits (new accounts) |
| **Env vars** | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_CHAT_DEPLOYMENT`, `AZURE_EMBEDDING_DEPLOYMENT` |
| **Sign up** | [ai.azure.com](https://ai.azure.com/) |
| **Credit card** | Yes (but $200 free credits) |

**Setup steps:**
1. Create an Azure account at [azure.microsoft.com](https://azure.microsoft.com/free/)
2. Go to [AI Foundry](https://ai.azure.com/) and create a project
3. Deploy a chat model (e.g., `gpt-4.1`) and an embedding model (e.g., `text-embedding-3-small`)
4. Copy the endpoint URL and API key from the deployment

```bash
AZURE_OPENAI_API_KEY=abc123...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_CHAT_DEPLOYMENT=gpt-4.1
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

---

## Career Data Sources

These are the primary sources for your professional profile.

### GitHub

Gathers your profile, repositories, pull requests, issues, and code reviews.

**Option A: MCP Server (recommended)** -- real-time data via Docker

| | |
|---|---|
| **Env var** | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| **Get token** | [github.com/settings/tokens](https://github.com/settings/tokens) |
| **Scopes needed** | `repo`, `read:user`, `user:email` |
| **Requires** | Docker (for MCP server container) |

```bash
GITHUB_USERNAME=your_username
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
```

**Option B: CLI fallback** -- uses `github2md` (included as dependency, no token needed for public repos)

```bash
GITHUB_USERNAME=your_username
# No token needed for public data
```

**Docker config (optional):**
```bash
GITHUB_MCP_USE_DOCKER=true                              # default
GITHUB_MCP_IMAGE=ghcr.io/github/github-mcp-server       # default
```

### GitLab

Search projects, read repo contents, and browse files via `glab` CLI.

| | |
|---|---|
| **Install** | [gitlab.com/gitlab-org/cli](https://gitlab.com/gitlab-org/cli) or `brew install glab` |
| **Authenticate** | `glab auth login` |

```bash
# Authenticate once — no env vars needed
glab auth login
```

### LinkedIn

Processes your LinkedIn data export (ZIP file).

| | |
|---|---|
| **How to get** | [linkedin.com/mypreferences/d/download-my-data](https://www.linkedin.com/mypreferences/d/download-my-data) |
| **Format** | ZIP file |
| **Tool** | `linkedin2md` (included as dependency) |

**Steps:**
1. Go to LinkedIn Settings > Data Privacy > Get a copy of your data
2. Request your data and wait for the email (can take up to 24 hours)
3. Download the ZIP file
4. Run: `futureproof gather linkedin path/to/LinkedInDataExport.zip`

### Portfolio Website

Scrapes and extracts content from your personal website.

| | |
|---|---|
| **Env var** | `PORTFOLIO_URL` |
| **Requires** | A publicly accessible URL |

```bash
PORTFOLIO_URL=https://your-portfolio.com
```

The scraper extracts: HTML content, section structure, JSON-LD structured data, and JavaScript-rendered content. SSRF protection prevents scraping private/internal networks.

### CliftonStrengths Assessment

Processes your Gallup CliftonStrengths PDF reports.

| | |
|---|---|
| **How to get** | [gallup.com/cliftonstrengths](https://www.gallup.com/cliftonstrengths/) |
| **Format** | PDF files placed in `data/raw/` |
| **Requires** | `pdftotext` (from `poppler-utils` package) |

**Supported report types:** Top 5, Top 10, All 34, Action Planning, Leadership Insight, Discovery Development.

```bash
# Install pdftotext
sudo apt install poppler-utils    # Debian/Ubuntu
brew install poppler              # macOS

# Place PDFs in data/raw/ then run
futureproof gather assessment
```

---

## Market Intelligence Sources

These provide real-time job market data, tech trends, and salary insights. Most require **no configuration** at all.

### No Auth Required (always available)

These sources work out of the box with zero configuration:

| Source | What it provides | Rate limit |
|--------|-----------------|------------|
| **JobSpy** | Jobs from LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs | No limit |
| **Hacker News** | Tech trends, "Who is Hiring?" threads, freelancing discussions | 10,000 req/hour |
| **RemoteOK** | Remote job listings | No limit |
| **Himalayas** | Remote jobs with salary data | No limit |
| **Jobicy** | Remote jobs worldwide | No limit |
| **WeWorkRemotely** | Remote job listings with salary extraction | No limit |
| **Remotive** | Remote jobs with tags and location data | No limit |
| **Dev.to** | Trending tech articles by topic | No limit |
| **Stack Overflow** | Tag popularity, trending questions | 300/day |

To disable specific sources:
```bash
JOBSPY_ENABLED=false       # default: true
HN_MCP_ENABLED=false       # default: true
```

### Tavily Search (optional, auth required)

Enhances salary research and market analysis with web search.

| | |
|---|---|
| **Free tier** | 1,000 queries/month |
| **Env var** | `TAVILY_API_KEY` |
| **Get key** | [tavily.com](https://tavily.com/) |
| **Credit card** | No |

```bash
TAVILY_API_KEY=tvly-...
```

---

## Embeddings (Knowledge Base)

The knowledge base uses embeddings for semantic search over your career data. Azure OpenAI embeddings are used when configured:

| Priority | Provider | Env var | Notes |
|----------|----------|---------|-------|
| 1 | Azure OpenAI | `AZURE_OPENAI_API_KEY` + `AZURE_EMBEDDING_DEPLOYMENT` | Best quality, uses your Azure credits |
| 2 | ChromaDB default | None | Local sentence-transformers (slower, no API needed) |

No extra configuration needed -- if you have Azure configured, embeddings use it automatically.

---

## Quick Reference

### Minimum Setup (one command away)

```bash
cp .env.example .env
# Add your Azure credentials:
echo "AZURE_OPENAI_API_KEY=your_key_here" >> .env
echo "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/" >> .env
echo "AZURE_CHAT_DEPLOYMENT=gpt-4.1" >> .env
echo "AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small" >> .env
```

This gives you: LLM chat, CV generation, career analysis, embeddings, and all no-auth market intelligence sources.

### Recommended Setup

```bash
# .env
AZURE_OPENAI_API_KEY=abc123...                  # LLM + embeddings
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_CHAT_DEPLOYMENT=gpt-4.1
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
GITHUB_USERNAME=your_username
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...            # GitHub data gathering
PORTFOLIO_URL=https://your-site.com
TAVILY_API_KEY=tvly-...                         # Enhanced market research
```

### All Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| **Azure OpenAI** | | | |
| `AZURE_OPENAI_API_KEY` | Yes | `""` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Yes | `""` | Azure endpoint URL |
| `AZURE_OPENAI_API_VERSION` | No | `2024-12-01-preview` | Azure API version |
| `AZURE_CHAT_DEPLOYMENT` | Yes | `""` | Azure chat model deployment name |
| `AZURE_EMBEDDING_DEPLOYMENT` | Yes | `""` | Azure embedding deployment name |
| **Career Data** | | | |
| `GITHUB_USERNAME` | No | `""` | GitHub username |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | No | `""` | GitHub PAT for MCP |
| `GITLAB_USERNAME` | No | `""` | GitLab username |
| `PORTFOLIO_URL` | No | `""` | Portfolio website URL |
| `DEFAULT_LANGUAGE` | No | `en` | `en` or `es` |
| **Market Intelligence** | | | |
| `TAVILY_API_KEY` | No | `""` | Tavily search API key |
| `JOBSPY_ENABLED` | No | `true` | Enable JobSpy job aggregation |
| `HN_MCP_ENABLED` | No | `true` | Enable Hacker News trends |
| `MARKET_CACHE_HOURS` | No | `24` | Tech trends cache (hours) |
| `JOB_CACHE_HOURS` | No | `12` | Job listings cache (hours) |
| `CONTENT_CACHE_HOURS` | No | `12` | Content trends cache (hours) |
| **Knowledge Base** | | | |
| `KNOWLEDGE_AUTO_INDEX` | No | `true` | Auto-index after gather |
| `KNOWLEDGE_CHUNK_MAX_TOKENS` | No | `500` | Max tokens per chunk |
| `KNOWLEDGE_CHUNK_MIN_TOKENS` | No | `50` | Min tokens per chunk |
| **LLM Settings** | | | |
| `LLM_MODEL` | No | `""` | Override model name |
| `LLM_TEMPERATURE` | No | `0.3` | General LLM temperature |
| `CV_TEMPERATURE` | No | `0.2` | CV generation temperature |

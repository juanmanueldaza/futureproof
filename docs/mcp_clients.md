# MCP Clients Reference

The career agent uses **12 MCP (Model Context Protocol) clients** to access real-time data from external services. All clients are defined in `src/fu7ur3pr00f/mcp/`.

## MCP Clients Overview

| Client | Server Type | Category | Auth Required |
|--------|-------------|----------|---------------|
| GitHub | `github` | Career Data | ✅ Token |
| Hacker News | `hn` | Market Intelligence | ❌ |
| Tavily | `tavily` | Market Intelligence | ✅ Token |
| JobSpy | `jobspy` | Job Search | ❌ |
| RemoteOK | `remoteok` | Job Search | ❌ |
| Himalayas | `himalayas` | Job Search | ❌ |
| Jobicy | `jobicy` | Job Search | ❌ |
| Dev.to | `devto` | Tech Content | ❌ |
| Stack Overflow | `stackoverflow` | Tech Content | ❌ |
| We Work Remotely | `weworkremotely` | Job Search | ❌ |
| Remotive | `remotive` | Job Search | ❌ |
| Financial | `financial` | Financial Data | ❌ |

**Availability defaults:** All clients without auth are enabled by default. GitHub and Tavily require tokens. JobSpy and HN can be disabled via env vars.

---

## Career Data Clients (1)

### GitHub MCP Client

**File:** `mcp/github_client.py`  
**Server Type:** `github`  
**Auth:** `GITHUB_PERSONAL_ACCESS_TOKEN` in `~/.fu7ur3pr00f/.env`

Connects to the native `github-mcp-server` binary (bundled in the .deb package).

| Tool | Description |
|------|-------------|
| `search_repos` | Search user's repositories |
| `get_repo` | Get repository details |
| `get_profile` | Get GitHub profile and contributions |
| `get_readme` | Get repository README |
| `get_languages` | Get repository languages |

**Required scopes:** `repo`, `read:user`, `user:email`

---

## Market Intelligence Clients (2)

### Hacker News MCP Client

**File:** `mcp/hn_client.py`  
**Server Type:** `hn`  
**Auth:** None (Algolia public API)  
**Config:** `HN_MCP_ENABLED=true` (default: enabled)

| Tool | Description |
|------|-------------|
| `search_hn` | Search Hacker News posts |
| `get_hiring_threads` | Get "Who is hiring?" threads |
| `analyze_tech_trends` | Analyze tech trends from HN |
| `get_top_stories` | Get top stories |
| `get_freelancing_threads` | Get freelancing threads |
| `get_seeking_work_threads` | Get "Seeking work" threads |
| `extract_job_postings` | Extract job postings from threads |

### Tavily MCP Client

**File:** `mcp/tavily_client.py`  
**Server Type:** `tavily`  
**Auth:** `TAVILY_API_KEY` in `~/.fu7ur3pr00f/.env`

| Tool | Description |
|------|-------------|
| `web_search` | General web search |
| `search_salary` | Search salary data |

**Free tier:** 1,000 queries/month, no credit card required

---

## Job Search Clients (7)

### JobSpy MCP Client

**File:** `mcp/jobspy_client.py`  
**Server Type:** `jobspy`  
**Auth:** None  
**Config:** `JOBSPY_ENABLED=true` (default: enabled)

| Tool | Description |
|------|-------------|
| `search_jobs` | Search multiple job boards |
| `get_job_details` | Get job posting details |

**Aggregates:** LinkedIn, Indeed, Glassdoor, and more

### RemoteOK MCP Client

**File:** `mcp/remoteok_client.py`  
**Server Type:** `remoteok`  
**Auth:** None (always enabled)

| Tool | Description |
|------|-------------|
| `search_remote_jobs` | Search remote jobs by category |

### Himalayas MCP Client

**File:** `mcp/himalayas_client.py`  
**Server Type:** `himalayas`  
**Auth:** None (always enabled)

| Tool | Description |
|------|-------------|
| `search_jobs` | Search remote jobs |
| `get_job_categories` | Get job categories |

### Jobicy MCP Client

**File:** `mcp/jobicy_client.py`  
**Server Type:** `jobicy`  
**Auth:** None (always enabled)

| Tool | Description |
|------|-------------|
| `search_remote_jobs` | Search remote jobs |

### We Work Remotely MCP Client

**File:** `mcp/weworkremotely_client.py`  
**Server Type:** `weworkremotely`  
**Auth:** None (always enabled)

| Tool | Description |
|------|-------------|
| `search_jobs` | Search jobs by category |

### Remotive MCP Client

**File:** `mcp/remotive_client.py`  
**Server Type:** `remotive`  
**Auth:** None (always enabled)

| Tool | Description |
|------|-------------|
| `search_jobs` | Search jobs by category |

---

## Tech Content Clients (2)

### Dev.to MCP Client

**File:** `mcp/devto_client.py`  
**Server Type:** `devto`  
**Auth:** None (always enabled)

| Tool | Description |
|------|-------------|
| `search_articles` | Search articles |
| `get_trending` | Get trending articles |
| `get_by_tag` | Get articles by tag |

### Stack Overflow MCP Client

**File:** `mcp/stackoverflow_client.py`  
**Server Type:** `stackoverflow`  
**Auth:** None (300 requests/day without key; always enabled)

| Tool | Description |
|------|-------------|
| `get_tag_popularity` | Get tag popularity stats |
| `get_trending_tags` | Get trending tags |
| `get_tag_info` | Get tag information |
| `get_popular_questions` | Get popular questions |

---

## Financial Data Clients (1)

### Financial MCP Client

**File:** `mcp/financial_client.py`  
**Server Type:** `financial`  
**Auth:** None (always enabled)

| Tool | Description |
|------|-------------|
| `convert_currency` | Real-time currency conversion |
| `compare_salary_ppp` | Compare purchasing power parity |

**Data source:** Free exchange rate APIs

---

## MCP Architecture

### Client Factory

**File:** `mcp/factory.py`

`MCPClientFactory` creates and manages MCP clients using a registry pattern (OCP-compliant — add new clients by updating the dict, not the factory logic):

```python
from fu7ur3pr00f.mcp.factory import MCPClientFactory

# Create client
client = MCPClientFactory.create("github")

# Check availability
if MCPClientFactory.is_available("github"):
    # Use client
    ...
```

### Connection Pool

**File:** `mcp/pool.py`

Manages persistent connections via a single background daemon thread running a persistent asyncio event loop:

- Connected clients are cached by server type
- Per-server `asyncio.Lock` serializes concurrent calls (required for stdio/session-based protocols like GitHub MCP)
- Automatic reconnection on failure
- `atexit` cleanup disconnects all clients on process exit

```python
from fu7ur3pr00f.mcp.pool import call_mcp

# Call tool through pool
result = await call_mcp("github", "get_profile", {})
```

### Base Classes

**File:** `mcp/base.py`

- `MCPClient` — Abstract base class for all clients
- `HTTPMCPClient` (`mcp/http_client.py`) — Base for HTTP API clients
- `MCPToolResult` — Standardized result type
- `MCPConnectionError`, `MCPToolError` — Error types

---

## Adding New MCP Clients

1. Create client class in `mcp/`:

```python
from .http_client import HTTPMCPClient

class MyNewMCPClient(HTTPMCPClient):
    server_type = "mynew"
    base_url = "https://api.example.com"
    
    async def _tool_search(self, args: dict) -> MCPToolResult:
        ...
```

2. Register in `MCPClientFactory._get_clients()`:

```python
"mynew": MyNewMCPClient,
```

3. Add availability checker in `MCPClientFactory.AVAILABILITY_CHECKERS`:

```python
"mynew": lambda: True,  # or lambda: settings.has_mynew_key
```

4. Add `"mynew"` to the `MCPServerType` Literal in `factory.py`

---

## Configuration

```bash
# GitHub MCP (requires token)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...

# Tavily MCP (requires token)
TAVILY_API_KEY=...

# Disable HN (enabled by default)
HN_MCP_ENABLED=false

# Disable JobSpy (enabled by default)
JOBSPY_ENABLED=false
```

Market data is cached to avoid redundant API calls:

```bash
MARKET_CACHE_HOURS=24      # Tech trends
JOB_CACHE_HOURS=12         # Job postings
CONTENT_CACHE_HOURS=12     # Dev.to / Stack Overflow
FOREX_CACHE_HOURS=4        # Exchange rates
```

Cache is stored in `~/.fu7ur3pr00f/data/cache/market/`.

---

## See Also

- [Tools Reference](tools.md) — Agent tools that use MCP clients
- [Architecture](architecture.md) — MCP integration design
- [Configuration](configuration.md) — MCP settings

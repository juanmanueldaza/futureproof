# Configuration

## Quick Start

Run `/setup` in the chat client to configure interactively, or edit `~/.fu7ur3pr00f/.env` manually.

## LLM Provider

Pick **ONE** provider. Auto-detected from available keys if not specified.

| Provider | Variable | Notes |
|----------|----------|-------|
| FutureProof Proxy | `FUTUREPROOF_PROXY_KEY` | Default, zero config, free starter tokens |
| OpenAI | `OPENAI_API_KEY` | Requires OpenAI account |
| Anthropic | `ANTHROPIC_API_KEY` | Requires Anthropic account |
| Google | `GOOGLE_API_KEY` | Gemini models |
| Azure | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` | Azure OpenAI Service / AI Foundry |
| Ollama | `OLLAMA_BASE_URL` | Local, offline, free |

### Auto-detection Priority

When `LLM_PROVIDER` is not set, the active provider is picked in this order:

1. FutureProof Proxy (`FUTUREPROOF_PROXY_KEY`)
2. Azure (`AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT`)
3. OpenAI (`OPENAI_API_KEY` starting with `sk-`)
4. Anthropic (`ANTHROPIC_API_KEY`)
5. Google (`GOOGLE_API_KEY`)
6. Ollama (`OLLAMA_BASE_URL`)

### Example

```bash
# ~/.fu7ur3pr00f/.env

# Option 1: FutureProof Proxy (recommended for getting started)
FUTUREPROOF_PROXY_KEY=fp-...

# Option 2: OpenAI
OPENAI_API_KEY=sk-...

# Option 3: Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Option 4: Google Gemini
GOOGLE_API_KEY=...

# Option 5: Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com

# Option 6: Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
```

## Purpose-Based Model Routing

Override the default fallback chain for specific purposes:

```bash
AGENT_MODEL=gpt-4o-mini        # Tool calling
ANALYSIS_MODEL=gpt-4.1         # Analysis / CV generation
SUMMARY_MODEL=gpt-4o-mini      # Summarization (context compression)
SYNTHESIS_MODEL=o4-mini        # Synthesis (reasoning model)
EMBEDDING_MODEL=text-embedding-3-small
```

Default fallback chains per provider are defined in `llm/fallback.py`. For example, the FutureProof proxy defaults to: GPT-4.1 → GPT-5 Mini → GPT-4o → GPT-4o Mini.

## Azure OpenAI Specific

```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Purpose-specific deployment names (optional — override defaults)
AZURE_AGENT_DEPLOYMENT=gpt-5-mini
AZURE_ANALYSIS_DEPLOYMENT=gpt-4.1
AZURE_SUMMARY_DEPLOYMENT=gpt-4o-mini
AZURE_SYNTHESIS_DEPLOYMENT=o4-mini
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

**AI Foundry endpoints:** The `/api/projects/...` suffix is stripped automatically. Paste the full AI Foundry URL and it will be normalized.

## GitHub MCP

```bash
# Create token at: https://github.com/settings/tokens
# Required scopes: repo, read:user, user:email
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
```

## GitLab

GitLab uses the `glab` CLI for authentication:

```bash
# Install: https://gitlab.com/gitlab-org/cli
glab auth login
```

No env variable required.

## Market Intelligence

Most sources require no configuration (JobSpy, HN, RemoteOK, Himalayas, Jobicy, WeWorkRemotely, Remotive, Dev.to, Stack Overflow, Financial).

### Tavily Search

For salary data and targeted market research:

```bash
# Get free key at: https://tavily.com/ (1,000 queries/month, no credit card)
TAVILY_API_KEY=...
```

### Disabling Sources

```bash
# Disable JobSpy (enabled by default)
JOBSPY_ENABLED=false

# Disable HN (enabled by default)
HN_MCP_ENABLED=false
```

## Portfolio

```bash
# URL scraped by gather_portfolio_data tool
PORTFOLIO_URL=https://your-portfolio.com
```

## Knowledge Base

```bash
# Auto-index career data after gathering (default: true)
KNOWLEDGE_AUTO_INDEX=true

# Chunking for RAG
KNOWLEDGE_CHUNK_MAX_TOKENS=500
KNOWLEDGE_CHUNK_MIN_TOKENS=50
```

## LLM Settings

```bash
LLM_TEMPERATURE=0.3    # General temperature (0.0–1.0)
CV_TEMPERATURE=0.2     # CV generation (lower = more consistent)
```

## Market Cache

```bash
MARKET_CACHE_HOURS=24      # Tech trends cache
JOB_CACHE_HOURS=12         # Job postings cache
CONTENT_CACHE_HOURS=12     # Dev.to / Stack Overflow cache
FOREX_CACHE_HOURS=4        # Exchange rates cache
```

## Full Reference

See [`.env.example`](../.env.example) for all available options with comments.

## File Permissions

Config and secrets are stored with `0600` permissions:

```bash
ls -la ~/.fu7ur3pr00f/.env
# -rw------- 1 user user ...
```

The `/setup` wizard enforces this automatically.

## Troubleshooting

### Provider not detected

1. Check variable names match exactly (case-sensitive)
2. Restart the chat client after editing `.env`
3. Run `fu7ur3pr00f --debug` for verbose logs
4. Use `/verbose` in chat to confirm active provider

### Azure endpoint format

If you paste an AI Foundry URL (contains `/api/projects/`), it is stripped automatically to extract the base endpoint. If you see a validation error, ensure the endpoint starts with `https://`.

### MCP not working

1. Verify tokens are set in `~/.fu7ur3pr00f/.env`
2. Run `fu7ur3pr00f --debug` and look for MCP errors
3. Test GitHub: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user`

## See Also

- [Architecture](architecture.md)
- [README](../README.md)
- [Troubleshooting](troubleshooting.md)

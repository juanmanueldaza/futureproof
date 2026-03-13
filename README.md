# FutureProof

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v2](https://img.shields.io/badge/License-GPL_v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)

Career intelligence agent that gathers professional data, searches job boards, analyzes career trajectories, and generates ATS-optimized CVs — all through conversational chat. Built with LangChain, LangGraph, and ChromaDB. Supports OpenAI, Anthropic, Google, Azure, and Ollama.

## What It Does

```
You:   Gather all my career data
Agent: [gathers LinkedIn, portfolio, CliftonStrengths → indexes to ChromaDB]

You:   Analyze my skill gaps for Staff Engineer
Agent: [runs skill gap analysis using your data + market trends]

You:   Search for remote Python developer jobs in Europe
Agent: [queries 7 job boards + Hacker News hiring threads]

You:   Generate my CV targeting that Staff Engineer role
Agent: [generates ATS-optimized CV in Markdown + PDF]
```

One agent, 40 tools, 12 MCP clients. Data sources: LinkedIn CSV export, GitHub (live MCP), GitLab (glab CLI), portfolio websites, CliftonStrengths PDF, 7 job boards, Hacker News, Dev.to, Stack Overflow, Tavily search.

## Architecture

```mermaid
graph LR
    User <-->|Rich UI, HITL| Chat[Chat Client]
    Chat <--> Agent[Single Agent<br/>40 tools]

    Agent --> Gather[Gatherers]
    Agent --> MCP[12 MCP Clients]
    Agent --> Analysis[Career Analysis]
    Agent --> Gen[CV Generator]

    Gather -->|LinkedIn CSV, Portfolio,<br/>CliftonStrengths| ChromaDB[(ChromaDB)]
    MCP -->|GitHub, 7 job boards,<br/>HN, Tavily, Dev.to, SO| Agent
    Analysis --> LLM[Multi-Provider LLM<br/>Fallback Chain]
    Gen -->|Markdown + PDF| Output[CV Output]

    ChromaDB -->|RAG search| Agent
    ChromaDB -->|Episodic memory| Agent
    LLM -->|Purpose-based routing| Agent
```

**Key design decisions:**

- **Single agent** — multi-agent handoffs failed with GPT-4.1 (over-delegation, lost context). One agent with all tools is simpler and more reliable.
- **Database-first pipeline** — gatherers return `Section` NamedTuples and index directly to ChromaDB. No intermediate files, no markdown header roundtrip.
- **Two-pass synthesis** — GPT-4o genericizes analysis responses regardless of prompt engineering. `AnalysisSynthesisMiddleware` lets the agent do tool calling, then replaces its generic response with focused synthesis from a reasoning model.
- **Multi-provider fallback** — supports OpenAI, Anthropic, Google, Azure, Ollama, and FutureProof proxy. Provider-specific fallback chains with automatic rate-limit recovery and purpose-based routing (agent/analysis/summary/synthesis).
- **HITL confirmation** — destructive or expensive operations (CV generation, full data gathering, knowledge clearing) require user approval via LangGraph's `interrupt()`.

## Quick Start

```bash
pipx install fu7ur3pr00f
fu7ur3pr00f
```

If `fu7ur3pr00f` is not found, run `pipx ensurepath` and restart your shell.

On first launch, the `/setup` wizard prompts you to configure an LLM provider. Supports OpenAI, Anthropic, Google, Azure, Ollama, or the FutureProof proxy. Settings are saved to `~/.fu7ur3pr00f/.env`. Everything happens inside the chat — use `/help` to see all commands.

## Install via apt (Debian/Ubuntu, amd64)

```bash
curl -fsSL https://juanmanueldaza.github.io/fu7ur3pr00f/fu7ur3pr00f-archive-keyring.gpg | \
  sudo tee /usr/share/keyrings/fu7ur3pr00f-archive-keyring.gpg >/dev/null

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/fu7ur3pr00f-archive-keyring.gpg] \
https://juanmanueldaza.github.io/fu7ur3pr00f stable main" | \
  sudo tee /etc/apt/sources.list.d/fu7ur3pr00f.list >/dev/null

sudo apt update
sudo apt install fu7ur3pr00f
```

During installation, the package bootstraps the Python environment and downloads
Python dependencies into `/opt/fu7ur3pr00f/venv`, so internet access is required.

The apt package bundles `github-mcp-server` and installs `glab`, `poppler-utils`,
and WeasyPrint system libraries as dependencies.

> **PDF generation** (CVs) requires system libraries for text rendering. Without them the app works fine — you just get Markdown output instead of PDF.
>
> Ubuntu/Debian: `sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libfontconfig1 libgdk-pixbuf-2.0-0 poppler-utils`
>
> macOS: `brew install pango cairo gdk-pixbuf poppler`

## Project Structure

```
src/fu7ur3pr00f/
├── agents/
│   ├── career_agent.py     # Single agent: create_agent(), 4 middlewares, singleton cache
│   ├── middleware.py        # Dynamic prompt, synthesis, tool repair, summarization
│   ├── orchestrator.py      # LangGraph Functional API for analysis workflows
│   ├── helpers/             # Orchestrator support (data pipeline, LLM invoker)
│   └── tools/              # 40 tools by domain (profile, gathering, analysis, market, settings)
├── chat/                   # Streaming client, HITL interrupt loop, Rich UI, /setup wizard
├── gatherers/              # LinkedIn CSV, CliftonStrengths PDF, portfolio scraper, market data
├── generators/             # CV generation (Markdown + PDF via WeasyPrint)
├── llm/                    # FallbackLLMManager: multi-provider fallback, purpose-based routing
├── memory/                 # ChromaDB (knowledge RAG + episodic), chunker, profile, embeddings
├── mcp/                    # 12 MCP clients: GitHub, Tavily, financial, 7 job boards (incl. HN), Dev.to, SO
├── prompts/                # System + analysis + CV prompt templates
├── services/               # GathererService, AnalysisService, KnowledgeService
└── utils/                  # PII anonymization, data loading, logging
```

## Development

```bash
git clone https://github.com/juanmanueldaza/fu7ur3pr00f.git
cd fu7ur3pr00f
pip install -e .
pip install pyright pytest ruff    # dev tools

pytest tests/ -q              # Unit tests
pyright src/fu7ur3pr00f       # Type checking
ruff check .                  # Lint
```

## Fresh Install Connectivity Check

Use this to validate a clean pipx install plus MCP/LLM connectivity from a temporary HOME.

```bash
scripts/fresh_install_check.sh --source local --config-from .env
scripts/fresh_install_check.sh --source pypi --config-from .env
```

## Tech Stack

**Python 3.13** · [LangChain](https://python.langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/) · [ChromaDB](https://www.trychroma.com/) · Multi-provider LLM (OpenAI, Anthropic, Google, Azure, Ollama) · [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) · [WeasyPrint](https://weasyprint.org/) · [httpx](https://www.python-httpx.org/)

---

Licensed under [GPL-2.0](LICENSE).

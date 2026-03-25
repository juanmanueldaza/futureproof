# Development Guide

## Setup

```bash
git clone https://github.com/juanmanueldaza/fu7ur3pr00f.git
cd fu7ur3pr00f
pip install -e .
pip install pyright pytest ruff
```

## Quality Checks

```bash
# Lint
ruff check .
ruff check . --fix  # Auto-fix

# Type check
pyright src/fu7ur3pr00f

# Tests
pytest tests/ -q
pytest tests/ -k test_name  # Specific test
pytest tests/ --cov=src     # With coverage

# Or use the test runner script
python scripts/run_tests.py
```

## Project Structure

```
src/fu7ur3pr00f/
├── agents/           # Single agent, middleware, orchestrator, tools, specialists
│   ├── career_agent.py       # Main agent (singleton, middleware stack)
│   ├── middleware.py         # Dynamic prompt, synthesis, tool repair
│   ├── orchestrator.py       # LangGraph Functional API (analyze/advise tasks)
│   ├── multi_agent.py        # Multi-agent system (/multi command)
│   ├── specialists/          # Specialist agents (Coach, Learning, Jobs, Code, Founder)
│   ├── helpers/              # Pipeline, LLM invoker, result mapper
│   └── tools/                # 41 tools by domain
├── chat/             # CLI client, HITL loop, Rich UI
│   ├── client.py             # Chat loop, slash commands, streaming
│   ├── ui.py                 # Rich panels, tool display, help
│   └── setup.py              # First-run setup wizard
├── gatherers/        # LinkedIn, CV, portfolio, CliftonStrengths, market
│   ├── market/               # Market data gatherers (tech trends, jobs, content)
│   └── portfolio/            # Portfolio scraper (fetcher, HTML/JS extractors)
├── generators/       # CV generation (Markdown + PDF via WeasyPrint)
├── llm/              # Multi-provider fallback routing
├── memory/           # ChromaDB (episodic/) + SQLite (memory.db) checkpointer
├── mcp/              # 12 MCP clients (GitHub, Tavily, job boards, financial)
├── prompts/          # System + analysis + CV prompts (md/*.md)
├── services/         # Business logic (gatherer, analysis, knowledge services)
└── utils/            # Security, logging, console, data loading
```

## Adding a Tool

1. Create tool function in `src/fu7ur3pr00f/agents/tools/<domain>.py`
2. Register in `tools/__init__.py` — both the import and the `_ALL_TOOLS` list
3. Add tests in `tests/agents/tools/`

```python
# Example tool
from langchain.tools import tool

@tool
def my_new_tool(param: str) -> str:
    """Tool description for the LLM.
    
    Args:
        param: Parameter description
        
    Returns:
        Result description
    """
    ...
```

```python
# In tools/__init__.py
from .mymodule import my_new_tool

_ALL_TOOLS = [
    ...
    my_new_tool,   # Add here
]
```

## Adding a Gatherer

1. Create gatherer in `src/fu7ur3pr00f/gatherers/`
2. Return `Section` NamedTuple(s)
3. Index to ChromaDB via `KnowledgeService`
4. Add tests

```python
from collections import namedtuple

Section = namedtuple("Section", ["title", "content", "metadata"])

def gather_my_source(path) -> list[Section]:
    """Gather data from my source."""
    return [Section(title="My Data", content="...", metadata={})]
```

## Testing

### Unit Tests

Use fixtures from `tests/conftest.py`:

```python
def test_gatherer(mock_chromadb, mock_llm):
    ...
```

Mock external services:

```python
from unittest.mock import patch

@patch("httpx.get")
def test_portfolio_fetch(mock_get):
    mock_get.return_value.status_code = 200
    ...
```

### Running Tests

```bash
pytest tests/ -q                    # All tests
pytest tests/ -k "gather"           # By keyword
pytest tests/ --cov=src             # With coverage
python scripts/run_tests.py         # Via test runner script
```

### Integration Tests: Fresh Install Check

Validate a clean pipx install plus MCP/LLM connectivity:

```bash
# From local source
scripts/fresh_install_check.sh --source local --config-from .env

# From PyPI
scripts/fresh_install_check.sh --source pypi --config-from .env
```

This script:
- Creates a temporary HOME directory
- Installs fu7ur3pr00f via pipx
- Tests LLM connectivity
- Tests MCP client connectivity
- Cleans up afterward

### Apt Package Validation (Docker)

Test .deb package installs/uninstalls cleanly:

```bash
# Build the package first
scripts/build_deb.sh

# Validate in Docker containers
scripts/validate_apt_artifact.sh dist/deb/fu7ur3pr00f_*.deb
```

Tests in:
- `ubuntu:24.04`
- `debian:12`

Verifies: install → version → reinstall → remove → purge → clean

### Vagrant Testing

Use Vagrant for isolated testing of the apt installation path.

**Requirements:** Vagrant + VirtualBox (or another provider)

**Available Boxes:**

| Box | Description |
|-----|-------------|
| `ubuntu2404` | Ubuntu 24.04 LTS |
| `debian12` | Debian 12 (Bookworm) |

```bash
# Test Ubuntu 24.04
scripts/run_vagrant_apt_smoke.sh ubuntu2404

# Test Debian 12
scripts/run_vagrant_apt_smoke.sh debian12

# Test all boxes
scripts/run_vagrant_apt_smoke.sh all

# Keep VM after test (for debugging)
scripts/run_vagrant_apt_smoke.sh debian12 --keep
```

**Multi-agent Vagrant test:**
```bash
scripts/vagrant_test_multi.sh
```

**Manual Vagrant usage:**

```bash
cd vagrant

# Boot and provision
vagrant up ubuntu2404 --provision
vagrant up debian12 --provision

# Destroy
vagrant destroy -f ubuntu2404 debian12
```

**Development VM:**

```bash
scripts/vagrant_dev_setup.sh setup   # Copy data/.env and start VM
scripts/vagrant_dev_setup.sh ssh     # SSH into VM
scripts/vagrant_dev_setup.sh destroy # Clean up
```

See `vagrant/README.md` for details.

## Debugging

```bash
fu7ur3pr00f --debug  # Verbose logging to terminal
```

Or toggle inside chat with `/debug`.

Full logs always at `~/.fu7ur3pr00f/data/fu7ur3pr00f.log`.

## Pre-commit Hooks

```bash
# Set up pre-commit hooks
scripts/setup_precommit.sh

# Or manually
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

The `.pre-commit-config.yaml` runs ruff lint and format checks.

## Cleaning Up

```bash
# Remove build artifacts (__pycache__, dist/, data/cache/)
scripts/clean_dev_artifacts.sh
```

See [Scripts Reference](scripts.md) for all available scripts.

## Key Environment Files

| File | Purpose |
|------|---------|
| `.env` | Local development settings (gitignored) |
| `.env.example` | Template with all available options |
| `~/.fu7ur3pr00f/.env` | User-level settings (written by `/setup`) |

## See Also

- [Architecture](architecture.md)
- [Scripts Reference](scripts.md)
- [QWEN.md](../QWEN.md)

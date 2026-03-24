# Qwen Code — Project Context

**Project**: FutureProof — Career intelligence agent  
**Stack**: Python 3.13, LangChain, LangGraph, ChromaDB, MCP  
**LLM**: Multi-provider (OpenAI, Anthropic, Google, Azure, Ollama, FutureProof proxy)

## How Qwen Should Work Here

### 1. Understand Before Acting

Read the code. Don't assume. When modifying:
1. Find the relevant module
2. Check existing tests
3. Match the existing patterns

### 2. Coding Standards

**Imports**: Use `collections.abc` types, not `typing`

```python
from collections.abc import Mapping, Sequence  # Good
from typing import Dict, List                  # Bad
```

**Error handling**: Raise exceptions, never return error dicts

```python
raise ServiceError("Connection failed")  # Good
return {"error": "..."}                   # Bad
```

**Line length**: 100 (ruff enforces this)

**Type hints**: Required. Python 3.13 syntax.

### 3. Testing Rules

- Mock external services (LLMs, HTTP, ChromaDB) — no real API calls
- Tests mirror source: `tests/gatherers/` for `src/fu7ur3pr00f/gatherers/`
- Use fixtures from `tests/conftest.py`
- Run: `pytest tests/ -q`

### 4. Architecture Awareness

**Single agent design**: One agent with 40+ tools. No multi-agent handoffs.

**Database-first**: Gatherers index directly to ChromaDB. No intermediate files.

**Two-pass synthesis**: `AnalysisSynthesisMiddleware` replaces generic LLM output with focused reasoning.

**HITL**: Destructive/expensive operations use LangGraph `interrupt()`.

### 5. When Qwen Modifies Code

**Before**:
- Check `pyproject.toml` for dependencies
- Read existing code for patterns
- Check if tests exist

**After**:
- `ruff check . --fix`
- `pyright src/fu7ur3pr00f`
- `pytest tests/ -q`

### 6. Files Qwen Should Know

| File | Purpose |
|------|---------|
| `src/fu7ur3pr00f/agents/career_agent.py` | Single agent, singleton cache |
| `src/fu7ur3pr00f/agents/middleware.py` | Dynamic prompts, synthesis, tool repair |
| `src/fu7ur3pr00f/agents/orchestrator.py` | LangGraph workflows |
| `src/fu7ur3pr00f/memory/chroma/` | ChromaDB RAG + episodic memory |
| `src/fu7ur3pr00f/llm/fallback.py` | Multi-provider fallback routing |
| `src/fu7ur3pr00f/agents/tools/` | **40 tools** organized by domain |
| `tests/conftest.py` | Shared pytest fixtures |

See [docs/tools.md](docs/tools.md) for the complete list of all 40 tools.

### 7. What Qwen Should NOT Do

- Don't add AI attribution comments
- Don't create intermediate files for data pipeline
- Don't bypass `utils/security.py` (PII anonymization, SSRF protection)
- Don't mock in production code
- Don't add dependencies without checking `pyproject.toml`

### 8. Common Tasks

**Add a tool**: Add to `src/fu7ur3pr00f/agents/tools/`, register in `career_agent.py`

**Add a gatherer**: Create in `src/fu7ur3pr00f/gatherers/`, index to ChromaDB

**Modify prompts**: Edit `src/fu7ur3pr00f/prompts/md/`

**Debug LLM calls**: Run with `fu7ur3pr00f --debug`

**Build .deb package**: `scripts/build_deb.sh`

**Test apt package**: `scripts/validate_apt_artifact.sh path/to.deb`

**Test in Vagrant VMs**: `scripts/run_vagrant_apt_smoke.sh all`

**Clean artifacts**: `scripts/clean_dev_artifacts.sh`

See [docs/scripts.md](docs/scripts.md) for all scripts.

### 9. Security

- PII is anonymized before LLM calls (`utils/security.py`)
- Portfolio fetchers enforce SSRF protection (no private IP access)
- Secrets in `~/.fu7ur3pr00f/.env` with `0o600` permissions

### 10. When in Doubt

1. Read the existing code
2. Check `CONTRIBUTING.md`
3. Ask for clarification

---

*This file is for Qwen Code. Keep it updated when patterns change.*

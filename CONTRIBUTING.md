# Contributing to FutureProof

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/juanmanueldaza/futureproof.git
cd futureproof

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies + dev tools
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env with your Azure OpenAI keys (minimum required)
```

## Running Checks

All checks must pass before submitting a PR:

```bash
pytest tests/ -q         # Tests (94 tests, < 1s)
ruff check .             # Linting
pyright src/futureproof  # Type checking
```

Auto-fix lint issues:

```bash
ruff check . --fix
```

## Making Changes

1. **Branch from `main`** — use a descriptive branch name (e.g., `feat/docker-support`, `fix/linkedin-parsing`)
2. **Use conventional commits** — prefix with `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
3. **Write tests** for new functionality
4. **Run all checks** before pushing
5. **Open a PR** against `main`

### Commit examples

```
feat: add Docker support for easier onboarding
fix: handle empty LinkedIn ZIP files gracefully
test: add tests for GitHub MCP client
docs: add troubleshooting section to README
refactor: extract job parsing into shared utility
```

## Code Style

- **Python 3.13+** with type hints on all functions
- **Line length**: 100 characters (enforced by ruff)
- **Imports**: sorted by ruff (`isort` compatible)
- **Type imports**: use `collections.abc` (not `typing`) for `Mapping`, `Sequence`, etc.
- **Error handling**: catch specific exceptions, never bare `except:`
- **Logging**: use `logging.getLogger(__name__)`, not `print()`

## Architecture

The project follows a chat-first architecture — all functionality is accessible through a single LangChain agent with 39 tools. See `CLAUDE.md` for detailed architecture documentation.

Key areas:
- `agents/tools/` — Agent tools organized by domain
- `gatherers/` — Data collection from external sources
- `mcp/` — MCP client implementations
- `memory/` — ChromaDB knowledge store + episodic memory
- `services/` — Business logic layer

## Finding Issues

Look for issues labeled [`good first issue`](https://github.com/juanmanueldaza/futureproof/labels/good%20first%20issue) — these are scoped and approachable for newcomers.

Areas that welcome contributions:
- **Tests** — agent tools, MCP clients, and services need test coverage
- **Docker** — Dockerfile and docker-compose for easier onboarding
- **Documentation** — tutorials, examples, troubleshooting guides
- **New MCP clients** — additional job boards or data sources

## Questions?

Open an issue or start a discussion — happy to help you get started.

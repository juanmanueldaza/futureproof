# FutureProof - Claude Code Guidelines

## Project Overview

FutureProof is a career intelligence CLI tool that gathers professional data from multiple sources (LinkedIn, GitHub, GitLab, portfolio sites) and uses AI to analyze career trajectories, identify gaps, and generate optimized CVs.

## Tech Stack

- **Python 3.13** with type hints
- **LangChain/LangGraph** for AI orchestration
- **Pydantic** for configuration and validation
- **Typer** for CLI
- **pytest** for testing
- **uv** for package management

## Project Structure

```
src/futureproof/
├── agents/          # LangGraph orchestration and state management
├── gatherers/       # Data collection from external sources
│   └── portfolio/   # Decomposed portfolio gatherer (SRP)
├── generators/      # CV generation
├── llm/             # LLM provider abstraction (DIP)
├── prompts/         # AI prompt templates
├── services/        # Business logic layer
├── utils/           # Shared utilities (logging, data loading, security)
└── validation/      # Pydantic input validation models
```

## Commands

```bash
# Run tests
pytest tests/ -q

# Type checking
pyright src/futureproof

# Linting
ruff check .

# Fix lint issues
ruff check . --fix

# Run CLI
futureproof --help
futureproof gather all
futureproof analyze full
futureproof generate cv
```

## Architecture Principles

This codebase follows SOLID, DRY, KISS, and YAGNI principles:

- **SRP**: Each class has a single responsibility (e.g., PortfolioGatherer split into Fetcher, HTMLExtractor, JSExtractor, MarkdownWriter)
- **OCP**: LLM providers are extensible via registry pattern without modifying existing code
- **DIP**: High-level modules depend on abstractions (LLMProvider ABC)
- **DRY**: Service layer eliminates CLI command duplication; CareerDataLoader consolidates data loading
- **ISP**: CareerState split into focused TypedDicts (GatherInput, AnalyzeInput, etc.)

## Security

The codebase implements security best practices:

### Input Validation
- All user inputs validated via Pydantic models (`validation/models.py`)
- GitHub/GitLab usernames validated with strict regex patterns
- GitLab groups validated before CLI execution to prevent argument injection
- URLs validated with Pydantic's `HttpUrl` type

### Prompt Injection Protection
- User inputs checked for injection patterns before inclusion in LLM prompts
- Security utilities in `utils/security.py`:
  - `detect_prompt_injection()` - detects common injection patterns
  - `sanitize_user_input()` - validates and sanitizes user input
  - Blocks patterns like "ignore previous instructions", "reveal system prompt"

### PII Anonymization
- Career data anonymized before sending to external LLM (Gemini API)
- `anonymize_career_data()` redacts:
  - Email addresses → `[EMAIL]` or `[USER]@domain.com`
  - Phone numbers → `[PHONE]`
  - Home addresses → `[HOME_ADDRESS]`
  - Social media usernames → `[USERNAME]`

### SSRF Protection
- Portfolio fetcher blocks private IP ranges (127.x, 10.x, 172.16-31.x, 192.168.x)
- Validates both direct IPs and resolved hostnames
- Only allows http/https schemes

### Path Traversal Protection
- All file operations use `_safe_path()` validation
- Paths resolved to absolute form and verified within base directory
- Symlink access blocked

### Command Injection Protection
- External CLI tools invoked via `subprocess.run()` with list arguments (no `shell=True`)
- 5-minute timeout on all subprocess calls

### File Permissions
- Sensitive output files created with `0o600` permissions (owner read/write only)

## Code Style

- Use `collections.abc` for type hints like `Mapping`, `Sequence` (not `typing`)
- Avoid ambiguous single-letter variable names (use `link` not `l`)
- Keep lines under 100 characters
- Remove unused imports and variables
- Use dependency injection for testability
- Prefer raising exceptions over returning error dicts

## Testing

- Tests are in `tests/` directory
- Use fixtures from `conftest.py` for common test data
- Mock external services (LLM, HTTP) to avoid API calls
- Clear data loader cache between tests with `clear_data_cache()`

## Configuration

Settings are loaded from environment variables via Pydantic:

- `GEMINI_API_KEY` - Required for LLM operations
- `LLM_PROVIDER` - Provider type (default: "gemini")
- `LLM_MODEL` - Model name (default: "gemini-3-flash")
- `GITHUB_USERNAME`, `GITLAB_USERNAME` - For data gathering
- `GITLAB_GROUPS` - Comma-separated GitLab groups (validated for safe characters)
- `PORTFOLIO_URL` - Portfolio website URL

## Key Modules

### `utils/security.py`
Security utilities for input sanitization and PII protection:
- `detect_prompt_injection(text)` - Returns list of detected injection patterns
- `sanitize_user_input(text, strict)` - Returns `SanitizationResult` with safety status
- `anonymize_pii(text)` - General PII anonymization
- `anonymize_career_data(data, preserve_professional_emails)` - Career-specific anonymization

### `utils/data_loader.py`
Centralized data loading with security checks:
- Path traversal protection via `_safe_path()`
- Symlink blocking
- Memoization for performance

### `gatherers/portfolio/fetcher.py`
HTTP client with security features:
- SSRF protection via IP/hostname validation
- SSL verification enabled
- Redirect limiting (max 5)
- Request timeout (30 seconds)

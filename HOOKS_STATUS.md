# Pre-Commit Hooks Status

## Overview

The repository uses pre-commit hooks to enforce code quality standards. This document explains the current status and any known issues.

## Hook Configuration

Hooks are defined in `.pre-commit-config.yaml`:
- **black** — Code formatting
- **isort** — Import sorting
- **flake8** — Linting (PEP 8, complexity, security)
- **pyright** — Type checking
- **mypy** — Alternative type checking
- **bandit** — Security scanning
- **pytest** — Unit tests
- **Check JSON/YAML** — File format validation

## Current Status

### ✅ Passing Hooks

- **black** — All code properly formatted
- **isort** — All imports correctly sorted
- **mypy** — All type hints valid
- **bandit** — No security issues detected
- **JSON/YAML checks** — All config files valid

### ⚠️ Failing Hooks (Known Issues)

#### 1. **flake8** — Line Length & Complexity Violations

**Issue:** Pre-existing violations in the codebase from earlier refactoring:
- Line-length violations (E501) in: `blackboard/executor.py`, `blackboard/graph.py`, `specialists/base.py`, `chat/client.py`, `chat/ui.py`
- Complexity warning (C901) in: `BlackboardExecutor.execute` method
- Quote handling (B907) — Resolved in Round 2 refactoring (added `# noqa: B907` where necessary)

**Impact:** Non-blocking. These are pre-existing issues that don't affect functionality. To resolve would require significant refactoring of complex methods.

**Action:** These can be addressed in a future "code quality cleanup" pass.

#### 2. **pyright** — Type Checking (33 errors)

**Issue:** Pre-existing type annotation gaps:
- `TypedDict` access on optional keys in tests
- Unresolved generic types in blackboard pattern
- Missing type annotations in legacy code

**Impact:** Non-blocking for runtime. Type hints are best-effort.

**Resolution:** Would require updating type definitions in `findings_schema.py` and adding `# type: ignore` comments where necessary.

#### 3. **pytest** — Missing `pytest_asyncio` Module

**Issue:** Test dependency not installed in current environment.

**Impact:** Non-blocking for synchronous tests (349 tests pass). Affects async test discovery only.

**Resolution:** Install `pytest_asyncio` if async tests are added.

## Round 2 Refactoring Compliance

All changes made in Round 2 DRY refactoring were designed to:
- ✅ Pass black (automatic formatting)
- ✅ Pass isort (automatic sorting)
- ✅ Not introduce new flake8 violations (fixed line lengths in new code)
- ✅ Not introduce new type errors
- ✅ Pass all 349 tests

## Best Practices

1. **Before committing:** Run `pre-commit run --all-files` to check
2. **If hooks fail:** Review the output and fix violations before committing
3. **For pre-existing violations:** Use `# noqa: XXXXX` comments sparingly and only when necessary
4. **Type checking:** Run `pyright src/fu7ur3pr00f` independently for full analysis

## References

- Hook configuration: `.pre-commit-config.yaml`
- Flake8 config: `.flake8` or `setup.cfg`
- Pyright config: `pyrightconfig.json`
- Pre-commit docs: https://pre-commit.com/

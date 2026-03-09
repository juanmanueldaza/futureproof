"""Cached prompt loader for .md template files."""

from functools import lru_cache
from pathlib import Path

_MD_DIR = Path(__file__).parent / "md"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """Load a prompt template from the md/ directory.

    Args:
        name: Prompt file stem (e.g. "system", "market_fit").

    Returns:
        Prompt content as a string, ready for .format() substitution.

    Raises:
        ValueError: If name contains path traversal.
        FileNotFoundError: If prompt file does not exist.
    """
    path = (_MD_DIR / f"{name}.md").resolve()
    if not path.is_relative_to(_MD_DIR.resolve()):
        raise ValueError(f"Invalid prompt name: {name}")
    return path.read_text(encoding="utf-8")

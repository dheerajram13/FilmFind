"""
Prompt versioning helper.

Prompts live as plain text files: app/prompts/{name}_v{version}.txt
Load them with load_prompt(name, version) — version defaults to "1".
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str, version: str = "1") -> str:
    """Load a versioned prompt from the prompts directory."""
    path = _PROMPTS_DIR / f"{name}_v{version}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()

"""Versioned prompt templates for AI explanations."""

from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template by name (e.g., 'stock_overview_v1')."""
    path = _PROMPT_DIR / f"{name}.txt"
    return path.read_text()


def get_prompt_version(name: str) -> str:
    """Extract the version suffix from a prompt name."""
    # 'stock_overview_v1' → 'v1'
    parts = name.rsplit("_", 1)
    return parts[-1] if len(parts) > 1 else "v1"

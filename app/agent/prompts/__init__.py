"""Versioned prompt loading.

Prompts live as Markdown files under `app/agent/prompts/{version}/{name}.md` so a
prompt change is a reviewable diff that triggers evals — never an inline string.
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS = Path(__file__).parent


def load_prompt(version: str, name: str) -> str:
    """Return the text of `prompts/{version}/{name}.md`."""
    return (_PROMPTS / version / f"{name}.md").read_text(encoding="utf-8")

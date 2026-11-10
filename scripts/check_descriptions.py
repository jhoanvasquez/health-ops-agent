#!/usr/bin/env python3
"""Fail CI when a tool or skill description is missing or incomplete.

Per the project's description standard (`.claude/rules/tools-and-skills.md`):
the model picks tools and skills by reading their descriptions, so a weak
description is a real defect. This check starts with an empty tool registry
and grows as tools are added.

Checks:
  - Each tool in the registry has a description covering: what it does,
    "Use when", "Do NOT use", "Input", and "Returns".
  - Each SKILL.md has a non-empty `description:` of at least 200 characters.

Exit code 0 = all good, 1 = at least one problem.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Make the repo root importable whether or not the package is installed, so
# running `python scripts/check_descriptions.py` directly behaves like CI.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_REGISTRY_MODULE = "app.agent.tools.registry"

TOOL_REQUIRED_PHRASES = ("use when", "do not use", "input", "returns")
TOOL_MIN_LEN = 120
SKILL_MIN_LEN = 200


def load_tools() -> list[tuple[str, str]]:
    """Return (name, description) for every registered tool.

    The registry may not exist yet (Phase 2). That is not an error — an empty
    registry passes, and the check grows as tools land.
    """
    try:
        from app.agent.tools.registry import REGISTRY
    except ModuleNotFoundError as exc:
        # Tolerate ONLY "the registry does not exist yet"; a missing dependency
        # inside the registry's import chain is a real failure and must surface.
        if exc.name == _REGISTRY_MODULE:
            return []
        raise
    return [(tool.name, tool.description) for tool in REGISTRY]


def check_tool(name: str, description: str) -> list[str]:
    problems: list[str] = []
    desc = (description or "").strip()
    if len(desc) < TOOL_MIN_LEN:
        problems.append(f"description too short ({len(desc)} < {TOOL_MIN_LEN} chars)")
    lowered = desc.lower()
    for phrase in TOOL_REQUIRED_PHRASES:
        if phrase not in lowered:
            problems.append(f'missing required element: "{phrase}"')
    return [f"tool '{name}': {p}" for p in problems]


def extract_skill_description(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8")
    match = re.search(r"^description:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def check_skill(skill_md: Path) -> list[str]:
    rel = skill_md.relative_to(ROOT)
    description = extract_skill_description(skill_md)
    if not description:
        return [f"skill '{rel}': missing `description:` in frontmatter"]
    if len(description) < SKILL_MIN_LEN:
        return [
            f"skill '{rel}': description too short ({len(description)} < {SKILL_MIN_LEN} chars)"
        ]
    return []


def main() -> int:
    problems: list[str] = []

    tools = load_tools()
    for name, description in tools:
        problems.extend(check_tool(name, description))

    skills = sorted(ROOT.glob("**/SKILL.md"))
    for skill_md in skills:
        problems.extend(check_skill(skill_md))

    if problems:
        print("Description check FAILED:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"Description check passed ({len(tools)} tools, {len(skills)} skills).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

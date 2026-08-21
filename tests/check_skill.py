#!/usr/bin/env python3
"""Minimal dependency-free validation for the published Skill package."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "longform-webnovel"
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.S)


def main() -> None:
    skill_md = SKILL / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match, "SKILL.md needs YAML frontmatter"
    frontmatter = match.group("body")
    assert re.search(r"^name:\s*longform-webnovel\s*$", frontmatter, re.M)
    assert re.search(r"^description:\s*\S.+$", frontmatter, re.M)
    assert (SKILL / "agents" / "openai.yaml").is_file()
    assert (SKILL / "references" / "review-system.md").is_file()
    assert (SKILL / "references" / "market-research.md").is_file()
    assert (SKILL / "scripts" / "validate_project.py").is_file()
    assert (SKILL / "scripts" / "prose_lint.py").is_file()
    assert (SKILL / "scripts" / "market_brief.py").is_file()
    print("Skill structure is valid")


if __name__ == "__main__":
    main()

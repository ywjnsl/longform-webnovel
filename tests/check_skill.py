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
    assert (SKILL / "references" / "performance-feedback.md").is_file()
    assert (SKILL / "references" / "reference-adaptation.md").is_file()
    assert (SKILL / "references" / "prose-naturalization.md").is_file()
    assert (SKILL / "references" / "relationship-regret.md").is_file()
    assert (SKILL / "references" / "length-modes.md").is_file()
    assert (SKILL / "references" / "short-story-information-flow.md").is_file()
    assert (SKILL / "references" / "cover-typography.md").is_file()
    assert (SKILL / "scripts" / "validate_project.py").is_file()
    assert (SKILL / "scripts" / "prose_lint.py").is_file()
    assert (SKILL / "scripts" / "market_brief.py").is_file()
    assert (SKILL / "scripts" / "opening_audit.py").is_file()
    assert (SKILL / "scripts" / "story_overlap.py").is_file()
    assert (SKILL / "scripts" / "reference_guard.py").is_file()
    assert (SKILL / "scripts" / "performance_feedback.py").is_file()
    assert "relationship-regret.md" in text
    assert "relationship-regret.md" in (SKILL / "references" / "genre-routing.md").read_text(encoding="utf-8")
    print("Skill structure is valid")


if __name__ == "__main__":
    main()

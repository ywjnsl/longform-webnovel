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
    assert (SKILL / "references" / "ensemble.md").is_file()
    assert (SKILL / "references" / "ensemble-character.md").is_file()
    assert (SKILL / "references" / "scene-craft.md").is_file()
    assert (SKILL / "references" / "webnovel-naturalness-review.md").is_file()
    assert (SKILL / "references" / "fanqie-signing-quality.md").is_file()
    assert (SKILL / "references" / "fanqie-character-craft.md").is_file()
    assert (SKILL / "references" / "fanqie-new-book.md").is_file()
    assert (SKILL / "references" / "fanqie-consistency.md").is_file()
    assert (SKILL / "references" / "fanqie-revision.md").is_file()
    assert (SKILL / "templates" / "character" / "SKILL.md").is_file()
    assert "ensemble.md" in text
    assert "scene-craft.md" in text
    assert "webnovel-naturalness-review.md" in text
    assert "fanqie-signing-quality.md" in text
    assert "fanqie-character-craft.md" in text
    assert "fanqie-new-book.md" in text
    assert "fanqie-consistency.md" in text
    assert "fanqie-revision.md" in text
    assert "先参考再动笔" in text or "先读" in text
    assert "接下去发生的这一件事" in text
    assert "贯穿线" in text
    assert "不自动写下一卷" in text
    assert "不锁在第 3、5、15 章" in text
    workflow_text = (SKILL / "references" / "task-workflows.md").read_text(encoding="utf-8")
    assert "task-workflows.md" in text
    assert "writer-context.md" in text
    assert (SKILL / "references" / "writer-context.md").is_file()
    assert "presence" in workflow_text
    assert "细纲最后一拍" not in text
    assert "lengthSignal" in workflow_text and "continue" in workflow_text
    length_text = (SKILL / "references" / "length-modes.md").read_text(encoding="utf-8")
    craft_text = (SKILL / "references" / "chapter-craft.md").read_text(encoding="utf-8")
    outline_text = (SKILL / "references" / "chapter-outline.md").read_text(encoding="utf-8")
    assert "场景拍细纲" not in length_text or "不写场景拍细纲" in length_text
    assert "切下一章" in craft_text
    assert "不写场景拍细纲" in outline_text
    assert "像人在场" in craft_text
    assert "不是正文的四段" in (SKILL / "references" / "scene-craft.md").read_text(encoding="utf-8")
    assert "同一张嘴" in (SKILL / "references" / "dialogue-craft.md").read_text(encoding="utf-8")
    assert "支流" in outline_text
    engine_text = (SKILL / "references" / "continuation-engine.md").read_text(encoding="utf-8")
    assert "一卷一条贯穿线" in engine_text
    assert "不占章号" in engine_text
    assert "最后一段必须是贯穿线落地" in engine_text
    assert (SKILL / "scripts" / "validate_project.py").is_file()
    assert (SKILL / "scripts" / "prose_lint.py").is_file()
    assert (SKILL / "scripts" / "market_brief.py").is_file()
    assert (SKILL / "scripts" / "opening_audit.py").is_file()
    assert (SKILL / "scripts" / "story_overlap.py").is_file()
    assert (SKILL / "scripts" / "reference_guard.py").is_file()
    assert (SKILL / "scripts" / "performance_feedback.py").is_file()
    assert (SKILL / "scripts" / "repetition_audit.py").is_file()
    assert "repetition_audit.py" in text
    review_text = (SKILL / "references" / "webnovel-naturalness-review.md").read_text(encoding="utf-8")
    assert "rhetorical-symmetry" in review_text
    assert "externalNaturalness" in review_text
    assert "truncated-ending" in review_text
    signing_text = (SKILL / "references" / "fanqie-signing-quality.md").read_text(encoding="utf-8")
    character_text = (SKILL / "references" / "fanqie-character-craft.md").read_text(encoding="utf-8")
    new_book_text = (SKILL / "references" / "fanqie-new-book.md").read_text(encoding="utf-8")
    consistency_text = (SKILL / "references" / "fanqie-consistency.md").read_text(encoding="utf-8")
    revision_text = (SKILL / "references" / "fanqie-revision.md").read_text(encoding="utf-8")
    assert "最后一场" in signing_text
    assert "真实代价" in character_text
    assert "微创新" in new_book_text
    assert "法则库" in consistency_text
    assert "不改" in revision_text
    assert "relationship-regret.md" in text
    assert "relationship-regret.md" in (SKILL / "references" / "genre-routing.md").read_text(encoding="utf-8")
    print("Skill structure is valid")


if __name__ == "__main__":
    main()

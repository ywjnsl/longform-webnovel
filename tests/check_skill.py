#!/usr/bin/env python3
"""Validate package resources and local links without locking editorial wording."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "longform-webnovel"
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.S)
LINK_RE = re.compile(r"\]\(([^)]+)\)")
SCRIPT_RE = re.compile(r"scripts/([a-z_]+\.py)")


def main() -> None:
    entry = SKILL / "SKILL.md"
    text = entry.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match, "SKILL.md needs YAML frontmatter"
    frontmatter = match.group("body")
    assert re.search(r"^name:\s*longform-webnovel\s*$", frontmatter, re.M)
    assert re.search(r"^description:\s*\S.+$", frontmatter, re.M)
    for relative in (
        "agents/openai.yaml",
        "templates/character/SKILL.md",
        "templates/character/state.json",
    ):
        assert (SKILL / relative).is_file(), f"Missing package resource: {relative}"

    # Follow the entrypoint's routing graph; detect broken and orphaned references.
    pending = [entry]
    visited: set[Path] = set()
    link_count = 0
    while pending:
        document = pending.pop().resolve()
        if document in visited:
            continue
        visited.add(document)
        content = document.read_text(encoding="utf-8")
        for destination in LINK_RE.findall(content):
            url = urlsplit(destination.strip("<>"))
            if url.scheme or url.netloc or not url.path:
                continue
            target = (document.parent / unquote(url.path)).resolve()
            assert target.is_relative_to(SKILL.resolve()), f"Link leaves package: {document}: {destination}"
            assert target.is_file(), f"Broken link in {document}: {destination}"
            link_count += 1
            if target.suffix == ".md":
                pending.append(target)
        for script in SCRIPT_RE.findall(content):
            assert (SKILL / "scripts" / script).is_file(), f"Missing script referenced by {document}: {script}"

    references = {path.resolve() for path in (SKILL / "references").glob("*.md")}
    orphaned = sorted(str(path.relative_to(SKILL.resolve())) for path in references - visited)
    assert not orphaned, f"References unreachable from SKILL.md: {orphaned}"
    print(f"Skill structure is valid ({len(visited)} routed documents, {link_count} local links)")


if __name__ == "__main__":
    main()

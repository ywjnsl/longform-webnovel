#!/usr/bin/env python3
"""Merge committed webnovel chapters into one manuscript file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from webnovel_io import content_char_count, load_json, write_text_atomic


CHAPTER_RE = re.compile(r"^第(\d{4,})章-.+\.md$")
TITLE_RE = re.compile(r"^#\s+第\d{4,}章(?:\s+.*)?$")


def find_chapters(project: Path, committed: int) -> list[tuple[int, Path]]:
    chapters: dict[int, Path] = {}
    chapter_dir = project / "chapters"
    if not chapter_dir.is_dir():
        raise ValueError(f"Missing chapters directory: {chapter_dir}")
    for path in chapter_dir.glob("*.md"):
        match = CHAPTER_RE.match(path.name)
        if not match:
            continue
        number = int(match.group(1))
        if number <= committed:
            if number in chapters:
                raise ValueError(f"Multiple files use chapter number {number}")
            chapters[number] = path
    missing = [number for number in range(1, committed + 1) if number not in chapters]
    if missing:
        raise ValueError(f"Missing committed chapter(s): {', '.join(map(str, missing))}")
    return sorted(chapters.items())


def chapter_body(text: str, strip_headings: bool) -> str:
    lines = text.splitlines()
    if strip_headings and lines and TITLE_RE.match(lines[0].strip()):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strip-headings", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    manifest = load_json(project / "project.json")
    committed = manifest.get("lastCommittedChapter")
    if not isinstance(committed, int) or committed <= 0:
        raise ValueError("project.json needs a positive lastCommittedChapter")

    output = (args.output or (project / f"{manifest.get('title', 'manuscript')}-合并稿.md")).expanduser().resolve()
    if project / "chapters" in output.parents:
        raise ValueError("Merged output must not be written inside chapters/")
    if output.exists() and not args.force:
        raise ValueError(f"Output already exists; use --force to replace it: {output}")

    chapter_paths = find_chapters(project, committed)
    source_total = sum(content_char_count(path.read_text(encoding="utf-8")) for _, path in chapter_paths)
    bodies = [chapter_body(path.read_text(encoding="utf-8"), args.strip_headings) for _, path in chapter_paths]
    merged = "\n\n".join(body for body in bodies if body) + "\n"
    merged_total = content_char_count(merged)
    if merged_total != source_total:
        raise ValueError(f"Merged content chars {merged_total} do not match source total {source_total}")
    if args.strip_headings and any(TITLE_RE.match(line.strip()) for line in merged.splitlines()):
        raise ValueError("Chapter headings remain after --strip-headings")

    write_text_atomic(output, merged)
    print(json.dumps({
        "ok": True,
        "output": str(output),
        "chapters": committed,
        "contentChars": merged_total,
        "headingsStripped": args.strip_headings,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

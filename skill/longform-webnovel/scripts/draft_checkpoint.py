#!/usr/bin/env python3
"""Persist cut drafts and check their predecessor before resuming; no canon writes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from webnovel_io import content_char_count, load_json, story_mode, utc_now, write_json_atomic


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def body_sha(raw: bytes) -> str:
    # A post-cut title and file newline conventions are not narrative changes.
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").strip()
    text = re.sub(r"^# [^\n]*(?:\n|$)", "", text, count=1).strip()
    return sha(text.encode("utf-8"))


def project_context(root: Path) -> int:
    project = load_json(root / "project.json")
    if story_mode(project) not in {"serial", "novella"}:
        raise ValueError("Draft checkpoints are for serial and novella projects")
    chapter = project.get("lastCommittedChapter")
    if type(chapter) is not int or chapter < 0:
        raise ValueError("Invalid lastCommittedChapter")
    return chapter


def checkpoint_dir(root: Path, chapter: int) -> Path:
    directory = root / "drafts" / "continuations" / f"after-{chapter:04d}"
    if not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError("Checkpoint must remain inside the project")
    return directory


def save(root: Path, chapter: int, source: Path, head: Path, tail: Path) -> dict:
    committed = project_context(root)
    if chapter < 1 or chapter not in {committed, committed + 1}:
        raise ValueError("after-chapter must be the current or next committed chapter")
    raw, first, rest = (p.read_bytes() for p in (source, head, tail))
    for item in (raw, first, rest):
        item.decode("utf-8")
    if first + rest != raw:
        raise ValueError("Head and tail must reassemble the source byte for byte")
    if not content_char_count(first.decode("utf-8")):
        raise ValueError("Head must contain prose")
    record = {
        "schemaVersion": 1,
        "afterChapter": chapter,
        "createdAt": utc_now(),
        "sourceSha256": sha(raw),
        "headSha256": sha(first),
        "tailSha256": sha(rest),
        "headBodySha256": body_sha(first),
        "checks": [],
    }
    directory = checkpoint_dir(root, chapter)
    # Reserve a new directory; never replace an earlier recovery point.
    directory.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in (("source.md", raw), ("head.md", first), ("tail.md", rest), ("tail-working.md", rest)):
            (directory / name).write_bytes(data)
        write_json_atomic(directory / "checkpoint.json", record)
    except BaseException:
        shutil.rmtree(directory)
        raise
    return {"status": "saved", "afterChapter": chapter, "checkpoint": str(directory.resolve())}


def inspect(root: Path) -> tuple[dict, Path | None, dict | None]:
    chapter = project_context(root)
    directory = checkpoint_dir(root, chapter)
    report = {"afterChapter": chapter, "status": "no-checkpoint"}
    # A newer cut means the next chapter has already been drafted. Recover its
    # edit/commit work before offering the previous tail for another continuation.
    upcoming = checkpoint_dir(root, chapter + 1)
    if upcoming.exists():
        report.update(status="awaiting-commit", checkpoint=str(upcoming.resolve()), pendingChapter=chapter + 1)
        return report, None, None
    if not directory.exists():
        return report, None, None
    record = load_json(directory / "checkpoint.json")
    if record.get("schemaVersion") != 1 or record.get("afterChapter") != chapter:
        raise ValueError("Checkpoint metadata does not match the chapter")
    raw, first, rest = ((directory / name).read_bytes() for name in ("source.md", "head.md", "tail.md"))
    if (
        sha(raw) != record.get("sourceSha256")
        or sha(first) != record.get("headSha256")
        or sha(rest) != record.get("tailSha256")
        or body_sha(first) != record.get("headBodySha256")
        or first + rest != raw
    ):
        raise ValueError("Recovery snapshots changed; restore them before resuming")
    chapters = list((root / "chapters").glob(f"第{chapter:04d}章-*.md"))
    if len(chapters) != 1:
        raise ValueError("Expected one committed predecessor chapter")
    predecessor = chapters[0]
    current = body_sha(predecessor.read_bytes())
    working_path = directory / "tail-working.md"
    working = working_path.read_bytes()
    tail_chars = content_char_count(working.decode("utf-8"))
    checks = record.get("checks")
    if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
        raise ValueError("Invalid checkpoint checks")
    last_check = checks[-1] if checks else {}
    unchanged = current == record["headBodySha256"] and sha(working) == record["tailSha256"]
    checked = last_check.get("predecessorBodySha256") == current and last_check.get("workingTailSha256") == sha(working)
    report.update(
        status="ready" if unchanged or checked else "review-required",
        checkpoint=str(directory.resolve()),
        predecessor=str(predecessor.resolve()),
        workingTail=str(working_path.resolve()),
        predecessorBodySha256=current,
        workingTailSha256=sha(working),
        predecessorChanged=current != record["headBodySha256"],
        workingTailChanged=sha(working) != record["tailSha256"],
        tailChars=tail_chars,
        emptyTail=not working.strip(),
        claim="version-check-only-not-semantic-continuity-validation",
    )
    return report, directory, record


def confirm(root: Path, note: str) -> dict:
    if not note.strip():
        raise ValueError("Describe the actual continuity check in --note")
    report, directory, record = inspect(root)
    if directory is None:
        raise ValueError("No checkpoint for the current committed predecessor")
    record["checks"].append({
        "checkedAt": utc_now(),
        "predecessorBodySha256": report["predecessorBodySha256"],
        "workingTailSha256": report["workingTailSha256"],
        "note": note.strip(),
    })
    write_json_atomic(directory / "checkpoint.json", record)
    return inspect(root)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest="operation", required=True)
    for name in ("save", "check", "confirm"):
        sub = operations.add_parser(name)
        sub.add_argument("--project", required=True, type=Path)
        if name == "save":
            sub.add_argument("--after-chapter", required=True, type=int)
            for filename in ("source", "head", "tail"):
                sub.add_argument(f"--{filename}", required=True, type=Path)
        elif name == "confirm":
            sub.add_argument("--note", required=True, help="Record an actual context check, not a version-only approval")
    args = parser.parse_args()
    try:
        if args.operation == "save":
            report = save(args.project, args.after_chapter, args.source, args.head, args.tail)
        elif args.operation == "confirm":
            report = confirm(args.project, args.note)
        else:
            report = inspect(args.project)[0]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["status"] in {"review-required", "awaiting-commit"} else 0
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

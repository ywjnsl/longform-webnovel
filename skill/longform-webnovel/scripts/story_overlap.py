#!/usr/bin/env python3
"""Compare a candidate story package with existing webnovel projects."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


CJK_RUN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]{2,}")
ASCII_WORD_RE = re.compile(r"[A-Za-z0-9]{3,}")
STORY_FILES = (
    "canon/story-contract.md",
    "canon/characters.md",
)
RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def load_text(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    chunks = []
    project_path = path / "project.json"
    if project_path.is_file():
        metadata = json.loads(project_path.read_text(encoding="utf-8"))
        title = metadata.get("title")
        if isinstance(title, str) and title.strip():
            chunks.append(title.strip())
    for relative in STORY_FILES:
        candidate = path / relative
        if candidate.is_file():
            chunks.append(candidate.read_text(encoding="utf-8"))
    if not chunks:
        raise ValueError(f"No story package found at {path}")
    return "\n".join(chunks)


def story_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or re.fullmatch(r"[|:\-`\s]+", line):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
            separators = [position for marker in ("：", ":") if (position := line.find(marker)) >= 0]
            if separators:
                line = line[min(separators) + 1 :].strip()
        lines.append(line)
    return "\n".join(lines)


def grams(text: str, size: int = 3) -> set[str]:
    text = story_text(text)
    result = {word.lower() for word in ASCII_WORD_RE.findall(text)}
    for run in CJK_RUN_RE.findall(text):
        if len(run) < size:
            result.add(run)
        else:
            result.update(run[index : index + size] for index in range(len(run) - size + 1))
    return result


def recurring_grams(text: str, size: int = 3) -> set[str]:
    counts: Counter[str] = Counter()
    for run in CJK_RUN_RE.findall(story_text(text)):
        if len(run) >= size:
            counts.update(run[index : index + size] for index in range(len(run) - size + 1))
    return {value for value, count in counts.items() if count >= 2}


def compare(left: set[str], right: set[str], priority: set[str] | None = None) -> tuple[float, list[str]]:
    shared = left & right
    if not left or not right:
        return 0.0, []
    containment = len(shared) / min(len(left), len(right))
    jaccard = len(shared) / len(left | right)
    score = round((containment * 0.7) + (jaccard * 0.3), 4)
    priority = priority or set()
    examples = sorted(shared, key=lambda item: (item not in priority, -len(item), item))[:12]
    return score, examples


def risk(score: float, recurring_count: int = 0) -> str:
    if score >= 0.30 or recurring_count >= 3:
        return "high"
    if score >= 0.10 or recurring_count:
        return "medium"
    return "low"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path, help="Candidate Markdown file or project directory")
    parser.add_argument("--library", required=True, type=Path, help="Directory containing historical projects")
    args = parser.parse_args()

    candidate = args.candidate.expanduser().resolve()
    library = args.library.expanduser().resolve()
    candidate_text = load_text(candidate)
    candidate_grams = grams(candidate_text)
    candidate_recurring = recurring_grams(candidate_text)
    rows = []
    for project_file in sorted(library.rglob("project.json")):
        relative_parts = project_file.relative_to(library).parts
        if any(part.startswith(".") for part in relative_parts):
            continue
        project = project_file.parent.resolve()
        if project == candidate or project in candidate.parents or candidate in project.parents:
            continue
        project_text = load_text(project)
        recurring = candidate_recurring & recurring_grams(project_text)
        score, examples = compare(candidate_grams, grams(project_text), recurring)
        metadata = json.loads(project_file.read_text(encoding="utf-8"))
        rows.append(
            {
                "project": str(project),
                "title": metadata.get("title", project.name),
                "score": score,
                "risk": risk(score, len(recurring)),
                "sharedRecurringSignals": sorted(recurring),
                "sharedSignals": examples,
            }
        )
    rows.sort(key=lambda row: row["score"], reverse=True)
    highest = max((row["risk"] for row in rows), key=RISK_ORDER.__getitem__, default="none")
    output = {
        "ok": highest != "high",
        "candidate": str(candidate),
        "library": str(library),
        "comparedProjectCount": len(rows),
        "highestRisk": highest,
        "comparisons": rows,
        "note": "Scores are editorial similarity signals, not plagiarism or platform-penalty determinations.",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if highest == "high" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

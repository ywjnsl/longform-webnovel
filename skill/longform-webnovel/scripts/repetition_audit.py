#!/usr/bin/env python3
"""Find exact and high-similarity sentence repetition in Chinese fiction."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from webnovel_io import load_json, story_mode, write_json_atomic

CHAPTER_RE = re.compile(r"^第(\d{4,})章-.+\.md$")
UNIT_RE = re.compile(r"[^。！？!?]+[。！？!?]?")
CONTENT_RE = re.compile(r"[A-Za-z0-9\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
NORMALIZE_RE = re.compile(r"[^A-Za-z0-9\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
EXACT_MIN_CHARS = 14
NEAR_MIN_CHARS = 18
DEFAULT_NEAR_THRESHOLD = 0.82


def normalize(text: str) -> str:
    return NORMALIZE_RE.sub("", text).lower()


def visible_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    in_fence = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped or stripped.startswith("#"):
            continue
        paragraphs.append(re.sub(r"!?(?:\[([^]]*)\])\([^)]*\)", r"\1", stripped))
    return paragraphs


def units(path: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for paragraph_number, paragraph in enumerate(visible_paragraphs(path.read_text(encoding="utf-8")), 1):
        sentence_number = 0
        for match in UNIT_RE.finditer(paragraph):
            text = match.group(0).strip()
            normalized = normalize(text)
            if not normalized:
                continue
            sentence_number += 1
            result.append(
                {
                    "file": f"chapters/{path.name}",
                    "paragraph": paragraph_number,
                    "sentence": sentence_number,
                    "text": text,
                    "normalized": normalized,
                    "contentChars": len(CONTENT_RE.findall(text)),
                }
            )
    return result


def shingles(value: str, size: int = 3) -> set[str]:
    if len(value) <= size:
        return {value}
    return {value[index : index + size] for index in range(len(value) - size + 1)}


def jaccard(left: str, right: str) -> float:
    left_set = shingles(left)
    right_set = shingles(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def finding_id(code: str, occurrences: list[dict[str, object]]) -> str:
    identity = [(item["file"], item["paragraph"], item["sentence"], item["normalized"]) for item in occurrences]
    payload = json.dumps([code, identity], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def public_occurrence(item: dict[str, object]) -> dict[str, object]:
    return {key: item[key] for key in ("file", "paragraph", "sentence", "text")}


def analyze_paths(
    primary: Path,
    comparisons: list[Path],
    near_threshold: float = DEFAULT_NEAR_THRESHOLD,
) -> dict:
    primary = primary.resolve()
    paths = [primary]
    for comparison in comparisons:
        resolved = comparison.resolve()
        if resolved not in paths:
            paths.append(resolved)
    all_units = [item for path in paths for item in units(path)]
    primary_file = f"chapters/{primary.name}"
    findings: list[dict[str, object]] = []
    exact_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in all_units:
        if item["contentChars"] >= EXACT_MIN_CHARS:
            exact_groups[str(item["normalized"])].append(item)
    for normalized, group in exact_groups.items():
        if len(group) < 2 or not any(item["file"] == primary_file for item in group):
            continue
        occurrences = [public_occurrence(item) for item in group]
        findings.append(
            {
                "id": finding_id("exact-sentence-duplicate", group),
                "code": "exact-sentence-duplicate",
                "severity": "block",
                "similarity": 1.0,
                "occurrences": occurrences,
            }
        )
    eligible = [item for item in all_units if item["contentChars"] >= NEAR_MIN_CHARS]
    for index, left in enumerate(eligible):
        for right in eligible[index + 1 :]:
            if left["normalized"] == right["normalized"]:
                continue
            if primary_file not in {left["file"], right["file"]}:
                continue
            similarity = jaccard(str(left["normalized"]), str(right["normalized"]))
            if similarity < near_threshold:
                continue
            pair = [left, right]
            findings.append(
                {
                    "id": finding_id("near-sentence-duplicate", pair),
                    "code": "near-sentence-duplicate",
                    "severity": "review",
                    "similarity": round(similarity, 3),
                    "occurrences": [public_occurrence(item) for item in pair],
                }
            )
    findings.sort(key=lambda item: (item["code"], item["id"]))
    chapter_match = CHAPTER_RE.match(primary.name)
    return {
        "schemaVersion": 1,
        "chapter": int(chapter_match.group(1)) if chapter_match else None,
        "reviewedTextSha256": hashlib.sha256(primary.read_bytes()).hexdigest(),
        "claim": "editorial-repetition-signals-not-authorship-detection",
        "scopeFiles": [f"chapters/{path.name}" for path in paths],
        "thresholds": {
            "exactMinChars": EXACT_MIN_CHARS,
            "nearMinChars": NEAR_MIN_CHARS,
            "nearJaccard": near_threshold,
        },
        "status": "review" if findings else "pass",
        "findings": findings,
    }


def project_comparisons(primary: Path, project_root: Path) -> list[Path]:
    match = CHAPTER_RE.match(primary.name)
    if match is None:
        return []
    current = int(match.group(1))
    candidates: list[tuple[int, Path]] = []
    for path in (project_root / "chapters").glob("第*章-*.md"):
        candidate_match = CHAPTER_RE.match(path.name)
        if candidate_match and int(candidate_match.group(1)) < current:
            candidates.append((int(candidate_match.group(1)), path))
    candidates.sort(key=lambda item: item[0])
    paths = [path for _, path in candidates]
    project = load_json(project_root / "project.json")
    return paths if story_mode(project) == "fanqie-short-story" else paths[-5:]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter", type=Path)
    parser.add_argument("--compare", action="append", default=[], type=Path)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--near-threshold", type=float, default=DEFAULT_NEAR_THRESHOLD)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0.0 < args.near_threshold <= 1.0:
        raise SystemExit("--near-threshold must be greater than 0 and at most 1")
    comparisons = [*args.compare]
    if args.project:
        comparisons.extend(project_comparisons(args.chapter, args.project.resolve()))
    result = analyze_paths(args.chapter, comparisons, args.near_threshold)
    if args.output:
        write_json_atomic(args.output.resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

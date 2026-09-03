#!/usr/bin/env python3
"""Screen a reference-based draft for exact text reuse and forbidden story terms."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from webnovel_io import ASCII_WORD_RE, CJK_RE, strip_markdown, write_json_atomic


UNIT_RE = re.compile(f"(?:{CJK_RE.pattern})|(?:{ASCII_WORD_RE.pattern})")
MAX_POSITIONS_PER_SHINGLE = 128


def text_units(text: str) -> list[str]:
    return [match.group(0).lower() for match in UNIT_RE.finditer(strip_markdown(text))]


def make_shingles(units: list[str], size: int) -> list[tuple[str, ...]]:
    if not units:
        return []
    actual_size = min(size, len(units))
    return [tuple(units[index : index + actual_size]) for index in range(len(units) - actual_size + 1)]


def phrase_containment(source: list[str], candidate: list[str], size: int) -> tuple[float, int]:
    actual_size = min(size, len(source), len(candidate))
    if actual_size <= 0:
        return 0.0, actual_size
    source_shingles = set(make_shingles(source, actual_size))
    candidate_shingles = make_shingles(candidate, actual_size)
    matched = sum(shingle in source_shingles for shingle in candidate_shingles)
    return round(matched / len(candidate_shingles), 4), actual_size


def longest_shared_run(source: list[str], candidate: list[str], size: int) -> tuple[int, int | None]:
    actual_size = min(size, len(source), len(candidate))
    if actual_size <= 0:
        return 0, None
    positions: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for source_index, shingle in enumerate(make_shingles(source, actual_size)):
        if len(positions[shingle]) < MAX_POSITIONS_PER_SHINGLE:
            positions[shingle].append(source_index)

    active: dict[int, int] = {}
    best_shingles = 0
    best_candidate_start = None
    for candidate_index, shingle in enumerate(make_shingles(candidate, actual_size)):
        next_active: dict[int, int] = {}
        for source_index in positions.get(shingle, []):
            run = active.get(source_index - 1, 0) + 1
            next_active[source_index] = max(next_active.get(source_index, 0), run)
            if run > best_shingles:
                best_shingles = run
                best_candidate_start = candidate_index - run + 1
        active = next_active
    if not best_shingles:
        return 0, None
    return best_shingles + actual_size - 1, best_candidate_start


def contains_sequence(haystack: list[str], needle: list[str]) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    width = len(needle)
    return any(haystack[index : index + width] == needle for index in range(len(haystack) - width + 1))


def risk_level(
    longest_run: int,
    containment: float,
    forbidden_terms: list[str],
    high_run: int,
    medium_run: int,
    high_containment: float,
    medium_containment: float,
) -> str:
    if forbidden_terms or longest_run >= high_run or containment >= high_containment:
        return "high"
    if longest_run >= medium_run or containment >= medium_containment:
        return "medium"
    return "low"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Reference story text")
    parser.add_argument("--candidate", required=True, type=Path, help="New draft to screen")
    parser.add_argument("--forbid-term", action="append", default=[], help="Reference-specific name or term that must not recur")
    parser.add_argument("--shingle-size", type=int, default=12)
    parser.add_argument("--high-run", type=int, default=60)
    parser.add_argument("--medium-run", type=int, default=30)
    parser.add_argument("--high-containment", type=float, default=0.12)
    parser.add_argument("--medium-containment", type=float, default=0.05)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.shingle_size <= 0 or args.medium_run <= 0 or args.high_run <= args.medium_run:
        raise SystemExit("Require positive shingle/medium-run values and high-run greater than medium-run")
    if not 0 <= args.medium_containment < args.high_containment <= 1:
        raise SystemExit("Require 0 <= medium-containment < high-containment <= 1")

    source = text_units(args.source.expanduser().read_text(encoding="utf-8"))
    candidate = text_units(args.candidate.expanduser().read_text(encoding="utf-8"))
    if not source or not candidate:
        raise SystemExit("Source and candidate must both contain effective text")

    containment, actual_shingle_size = phrase_containment(source, candidate, args.shingle_size)
    longest_run, candidate_start = longest_shared_run(source, candidate, args.shingle_size)
    invalid_terms = [term for term in args.forbid_term if not text_units(term)]
    if invalid_terms:
        raise SystemExit("Forbidden terms must contain effective text")
    matched_terms = [term for term in args.forbid_term if contains_sequence(candidate, text_units(term))]
    risk = risk_level(
        longest_run,
        containment,
        matched_terms,
        args.high_run,
        args.medium_run,
        args.high_containment,
        args.medium_containment,
    )
    excerpt = ""
    if candidate_start is not None:
        excerpt = "".join(candidate[candidate_start : candidate_start + min(longest_run, 80)])
    result = {
        "ok": risk != "high",
        "risk": risk,
        "source": str(args.source.expanduser().resolve()),
        "candidate": str(args.candidate.expanduser().resolve()),
        "sourceUnits": len(source),
        "candidateUnits": len(candidate),
        "shingleSize": actual_shingle_size,
        "candidatePhraseContainment": containment,
        "maxSharedRunUnits": longest_run,
        "longestSharedCandidateExcerpt": excerpt,
        "matchedForbiddenTerms": matched_terms,
        "thresholds": {
            "highRun": args.high_run,
            "mediumRun": args.medium_run,
            "highContainment": args.high_containment,
            "mediumContainment": args.medium_containment,
        },
        "note": "Editorial exact-reuse signal only; this is not a plagiarism or legal determination.",
    }
    if args.output:
        write_json_atomic(args.output.expanduser(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if risk == "high" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

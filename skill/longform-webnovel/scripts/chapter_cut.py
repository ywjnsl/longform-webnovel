#!/usr/bin/env python3
"""Locate a prose boundary near the cut threshold; optionally export two exact slices."""

from __future__ import annotations

import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import re

from webnovel_io import ASCII_WORD_RE, CJK_RE, content_char_count


LINK_RE = re.compile(r"!?(?:\[([^]]*)\])\([^)]*\)")
END_RE = re.compile(r'''(?:[。！？!?]+|…{2,}|\.{3,}|\.(?=\s|$))[”’」』）】〉》"')]*''')
PARAGRAPH_RE = re.compile(r"\r?\n[ \t]*\r?\n")


def content_end_positions(text: str) -> list[int]:
    """Map counted tokens through link labels, including joined English words."""
    projected = []
    positions = []
    in_fence = False
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        parts = raw_line.splitlines()
        line = parts[0] if parts else ""
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and not line.lstrip().startswith("#"):
            projected.append("\n")
            positions.append(offset)
            start = 0
            for match in LINK_RE.finditer(line):
                projected.extend((line[start:match.start()], match.group(1)))
                positions.extend(range(offset + start, offset + match.start()))
                positions.extend(range(offset + match.start(1), offset + match.end(1)))
                start = match.end()
            projected.append(line[start:])
            positions.extend(range(offset + start, offset + len(line)))
        offset += len(raw_line)
    body = "".join(projected)
    return sorted(
        positions[match.end() - 1] + 1
        for pattern in (CJK_RE, ASCII_WORD_RE)
        for match in pattern.finditer(body)
    )


def masked_prose(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Match strip_markdown's counting rules while keeping original offsets."""
    lines = []
    protected = []
    in_fence = False
    fence_start = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            if in_fence:
                fence_start = offset
            else:
                protected.append((fence_start, offset + len(line)))
            line = re.sub(r"[^\r\n]", " ", line)
        elif in_fence or line.lstrip().startswith("#"):
            if not in_fence:
                protected.append((offset, offset + len(line)))
            line = re.sub(r"[^\r\n]", " ", line)
        else:
            def mask_link(match: re.Match) -> str:
                protected.append((offset + match.start(), offset + match.end()))
                return (
                    " " * (match.start(1) - match.start())
                    + match.group(1)
                    + " " * (match.end() - match.end(1))
                )
            line = LINK_RE.sub(mask_link, line)
        lines.append(line)
        offset += len(line)
    if in_fence:
        protected.append((fence_start, len(text)))
    return "".join(lines), sorted(protected)


def suggest_cut(text: str, target: int = 2500, window: int = 100, *, final: bool = False) -> dict:
    if target <= 0 or window < 0:
        raise ValueError("target must be positive and window non-negative")
    masked, protected = masked_prose(text)
    protected_starts = [start for start, _ in protected]
    token_ends = content_end_positions(text)
    total = len(token_ends)
    if total != content_char_count(text):
        raise ValueError("Cannot map the draft to the shared effective-character count")
    result = {"status": "continue", "target": target, "contentChars": total, "window": window, "cutPoint": None}
    if not total:
        result["status"] = "empty"
        return result
    if total < target:
        if final:
            result.update(status="ready", cutPoint={"offset": len(text), "headChars": total, "tailChars": 0, "boundary": "event-end"})
        return result

    candidates = {}
    for boundary, pattern in (("sentence", END_RE), ("paragraph", PARAGRAPH_RE)):
        for match in pattern.finditer(masked):
            offset = match.end()
            protected_index = bisect_right(protected_starts, offset) - 1
            if protected_index >= 0 and protected[protected_index][0] < offset < protected[protected_index][1]:
                continue
            # Keep existing whitespace with the preceding slice, byte for byte.
            while offset < len(text) and text[offset].isspace():
                offset += 1
            count = bisect_right(token_ends, offset)
            if count:
                candidates.setdefault(offset, (count, boundary))
    if final:
        candidates.setdefault(len(text), (total, "event-end"))
    if not candidates:
        result["status"] = "needs-boundary"
        return result
    for offset in sorted(candidates, key=lambda pos: (abs(candidates[pos][0] - target), candidates[pos][0] < target, pos)):
        count, boundary = candidates[offset]
        if content_char_count(text[:offset]) == count and content_char_count(text[offset:]) == total - count:
            break
    else:
        result["status"] = "needs-boundary"
        return result
    result["cutPoint"] = {
        "offset": offset,  # Python Unicode string index, not a UTF-8 byte offset.
        "headChars": count,
        "tailChars": total - count,
        "boundary": boundary,
    }
    result["status"] = "ready" if abs(count - target) <= window else "needs-boundary"
    return result


def export_slices(source: Path, head: Path, tail: Path, text: str, offset: int) -> None:
    paths = [source.resolve(), head.resolve(), tail.resolve()]
    if len(set(paths)) != 3:
        raise ValueError("Source, head and tail must be different paths")
    if head.exists() or tail.exists():
        raise ValueError("Output files already exist; choose new paths")
    created = []
    try:
        for path, part in ((head, text[:offset]), (tail, text[offset:])):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                created.append(path)
                handle.write(part.encode("utf-8"))
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("--target", type=int, default=2500)
    parser.add_argument("--window", type=int, default=100, help="Maximum effective-character distance for automatic export")
    parser.add_argument("--final", action="store_true", help="The event ended; its remaining text may end at EOF")
    parser.add_argument("--head", type=Path, help="Export the current slice to a new file")
    parser.add_argument("--tail", type=Path, help="Export the remaining draft to a new file")
    args = parser.parse_args()
    if bool(args.head) != bool(args.tail):
        parser.error("--head and --tail must be provided together")
    try:
        raw = args.draft.read_bytes()
        text = raw.decode("utf-8")
        report = suggest_cut(text, args.target, args.window, final=args.final)
        report["sourceSha256"] = hashlib.sha256(raw).hexdigest()
        if args.head:
            if report["status"] != "ready":
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1
            offset = report["cutPoint"]["offset"]
            export_slices(args.draft, args.head, args.tail, text, offset)
            report["outputs"] = {"head": str(args.head.resolve()), "tail": str(args.tail.resolve())}
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

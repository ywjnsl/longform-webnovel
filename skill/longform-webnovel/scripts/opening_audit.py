#!/usr/bin/env python3
"""Extract deterministic opening windows for short-story semantic review."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from webnovel_io import ASCII_WORD_RE, CJK_RE, strip_markdown, write_json_atomic


TOKEN_RE = re.compile(f"(?:{CJK_RE.pattern})|(?:{ASCII_WORD_RE.pattern})")
DIALOGUE_RE = re.compile(r"[“\"]([^”\"]+)[”\"]")


def effective_count(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def effective_slice(text: str, start: int, end: int) -> str:
    """Return effective units [start, end), preserving punctuation within the slice."""
    matches = list(TOKEN_RE.finditer(text))
    if start >= len(matches) or start >= end:
        return ""
    first = 0 if start == 0 else matches[start].start()
    last = matches[min(end, len(matches)) - 1].end()
    return text[first:last].strip()


def audit(text: str, window: int = 300) -> dict[str, object]:
    body = strip_markdown(text).strip()
    total = effective_count(body)
    opening = effective_slice(body, 0, window)
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", opening) if item.strip()]
    dialogue_chars = sum(effective_count(item) for item in DIALOGUE_RE.findall(opening))

    segment_size = 100
    segments = []
    for start in range(0, window, segment_size):
        end = min(start + segment_size, window)
        segments.append(
            {
                "range": f"{start + 1}-{end}",
                "contentChars": effective_count(effective_slice(body, start, end)),
                "text": effective_slice(body, start, end),
            }
        )

    return {
        "schemaVersion": 1,
        "window": window,
        "totalContentChars": total,
        "openingContentChars": effective_count(opening),
        "windowFilled": total >= window,
        "paragraphs": len(paragraphs),
        "dialogueRatio": round(dialogue_chars / max(effective_count(opening), 1), 3),
        "segments": segments,
        "openingText": opening,
        "reviewQuestions": [
            "谁遇到了什么正在发生的事件或压力？",
            "主角在前300字内主动做了什么？",
            "这个选择会失去什么具体的人、钱、身份、机会、时间或关系？",
            "读者接下来等待哪个能由后文回答的问题？",
            "标题承诺的人物关系、事件或独特物件是否已经在正文运行？",
        ],
        "note": "Metrics and excerpts support editorial review; they do not score story quality or predict traffic.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter", type=Path)
    parser.add_argument("--window", type=int, default=300)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.window < 100:
        raise SystemExit("--window must be at least 100")

    result = audit(args.chapter.read_text(encoding="utf-8"), args.window)
    if args.output:
        write_json_atomic(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

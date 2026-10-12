#!/usr/bin/env python3
"""Report useful, non-prescriptive metrics for a Chinese webnovel chapter."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from webnovel_io import ASCII_WORD_RE, CJK_RE, strip_markdown


DIALOGUE_RE = re.compile(r"[“\"]([^”\"]+)[”\"]")


def metrics(text: str, target: int) -> dict[str, object]:
    body = strip_markdown(text)
    content_chars = len(CJK_RE.findall(body)) + len(ASCII_WORD_RE.findall(body))
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    dialogue_chars = sum(len(CJK_RE.findall(m)) + len(ASCII_WORD_RE.findall(m)) for m in DIALOGUE_RE.findall(body))
    normalized = [re.sub(r"\s+", "", p) for p in paragraphs if len(re.sub(r"\s+", "", p)) >= 20]
    repeated = sorted([p for p, count in Counter(normalized).items() if count > 1])
    long_paragraphs = sum(1 for p in normalized if len(p) > 180)
    lower = round(target * 0.9)
    upper = round(target * 1.14)
    if content_chars < lower:
        length_signal = "continue"
        length_action = "write-the-event"
        note = f"未到切章字数。事情还没完结，就接着写这件事，写到约 {target} 再切下一章。不要回头补回合、物件或手续。事情已经完结，就停在完结处，不要补字。"
    elif content_chars <= upper:
        length_signal = "cut"
        length_action = "next-chapter"
        note = "已到切章字数。本章停在这里。事情未完结就新开下一章接着写，不要把后文补回本章，也不要补字。"
    else:
        length_signal = "overflow"
        length_action = "move-excess"
        note = "超过切章字数。多出来的后文放进下一章。不要为了留在本章再加字。"
    return {
        "contentChars": content_chars,
        "target": target,
        "cutRange": [lower, upper],
        "lengthSignal": length_signal,
        "lengthAction": length_action,
        "paragraphs": len(paragraphs),
        "longParagraphsOver180Chars": long_paragraphs,
        "dialogueRatio": round(dialogue_chars / content_chars, 3) if content_chars else 0,
        "repeatedParagraphCount": len(repeated),
        "repeatedParagraphSamples": repeated[:3],
        "note": note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter", type=Path)
    parser.add_argument("--target", type=int, default=2500)
    args = parser.parse_args()
    if args.target <= 0:
        raise SystemExit("--target must be positive")
    text = args.chapter.read_text(encoding="utf-8")
    print(json.dumps(metrics(text, args.target), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

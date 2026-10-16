#!/usr/bin/env python3
"""Measure prose for chapter cutting; --target is a cut threshold, not a story-length goal."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from chapter_cut import suggest_cut
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
    cut = suggest_cut(text, target)
    if content_chars < target:
        length_signal = "continue"
        length_action = "write-the-event"
        note = f"连续推进当前事件并保存草稿，约 {target} 个有效字时切片。"
    elif cut["status"] != "ready":
        length_signal = "overflow"
        length_action = "inspect-boundary"
        note = "阈值附近没有可用的句段边界。核对已有正文，不改写情节以匹配章长。"
    elif content_chars <= target + cut["window"]:
        length_signal = "cut"
        length_action = "next-chapter"
        note = "已接近切分阈值。在已有文本的完整句子或段落间断开，不等待事件结束，也不补章尾。切点后已写文字原样留给下一章；事情未完就从断处接着写。"
    else:
        length_signal = "overflow"
        length_action = "move-excess"
        note = "已超过切分范围。在阈值附近切开已有文本，尾后文字原样留给下一章，不压缩前文、不丢后文，也不把事件赶到结局来匹配一章长度。"
    return {
        "contentChars": content_chars,
        "target": target,
        "cutPoint": cut["cutPoint"],
        "cutStatus": cut["status"],
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
    parser.add_argument("--target", type=int, default=2500, help="Effective-character cut threshold; not a per-chapter plot or padding target")
    args = parser.parse_args()
    if args.target <= 0:
        raise SystemExit("--target must be positive")
    text = args.chapter.read_text(encoding="utf-8")
    print(json.dumps(metrics(text, args.target), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

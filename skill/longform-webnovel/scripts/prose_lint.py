#!/usr/bin/env python3
"""Scan Chinese fiction for template-like prose risks without claiming AI authorship."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from webnovel_io import content_char_count, strip_markdown, write_json_atomic


CHAPTER_RE = re.compile(r"^第(\d{4,})章-.+\.md$")
SENTENCE_SPLIT_RE = re.compile(r"[。！？!?]+")
CJK_ONLY_RE = re.compile(r"[^\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
DIALOGUE_RE = re.compile(r"[“「『](.*?)[”」』]", re.S)
MICRO_ACTIONS = ("深吸一口气", "眼中闪过", "嘴角勾起", "心中一震", "瞳孔骤缩", "下意识地")
EXPLANATION_MARKERS = ("显然", "这意味着", "换句话说", "他意识到", "她意识到", "可想而知", "毋庸置疑")
SIMILE_MARKERS = ("仿佛", "犹如", "宛若", "如同", "像是")
SUMMARY_ENDINGS = ("他终于明白", "她终于明白", "这一刻他明白", "这一刻她明白", "从这一刻起", "这意味着")
CORRECTIVE_PATTERNS = (
    ("不是…而是/只是…", re.compile(r"不是[^。！？!?\n]{0,48}(?:而是|只是)")),
    ("没有…而是/只是…", re.compile(r"没有[^。！？!?\n]{0,48}(?:而是|只是)")),
    ("并非…而是/只是…", re.compile(r"并非[^。！？!?\n]{0,48}(?:而是|只是)")),
    ("不是…。而是/只是…", re.compile(r"不是[^。！？!?\n]{0,64}[。！？!?]\s*(?:我|他|她|他们|她们|这|那)?(?:而是|只是)")),
    ("没有…。而是/只是…", re.compile(r"没有[^。！？!?\n]{0,64}[。！？!?]\s*(?:我|他|她|他们|她们|这|那)?(?:而是|只是)")),
)
THEME_CLOSURE_MARKERS = (
    "我没有拿到",
    "我拿回了",
    "他没有得到",
    "她没有得到",
    "真正的答案",
    "真正重要的",
    "原来真正",
    "这才是",
)
REASONING_OPENING_RE = re.compile(r"^(?:我|他|她|他们|她们|这|那)(?:没有|不是|只是|终于|才发现|才明白)")


def mean(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def coefficient_of_variation(values: list[int]) -> float:
    average = mean(values)
    if not values or average == 0:
        return 0.0
    variance = sum((value - average) ** 2 for value in values) / len(values)
    return math.sqrt(variance) / average


def text_metrics(text: str) -> dict:
    body = strip_markdown(text)
    paragraphs = [line.strip() for line in body.splitlines() if line.strip()]
    sentences = [segment.strip() for segment in SENTENCE_SPLIT_RE.split(body) if segment.strip()]
    sentence_lengths = [content_char_count(sentence) for sentence in sentences if content_char_count(sentence)]
    paragraph_lengths = [content_char_count(paragraph) for paragraph in paragraphs if content_char_count(paragraph)]
    dialogue_chars = sum(content_char_count(match) for match in DIALOGUE_RE.findall(body))
    total = content_char_count(text)
    return {
        "contentChars": total,
        "paragraphs": len(paragraphs),
        "sentences": len(sentence_lengths),
        "meanSentenceChars": round(mean(sentence_lengths), 2),
        "sentenceLengthCv": round(coefficient_of_variation(sentence_lengths), 3),
        "meanParagraphChars": round(mean(paragraph_lengths), 2),
        "paragraphLengthCv": round(coefficient_of_variation(paragraph_lengths), 3),
        "dialogueRatio": round(dialogue_chars / total, 3) if total else 0.0,
    }


def count_markers(text: str, markers: tuple[str, ...]) -> tuple[int, list[str]]:
    counts = [(marker, text.count(marker)) for marker in markers]
    return sum(count for _, count in counts), [marker for marker, count in counts if count]


def count_regex_patterns(text: str, patterns: tuple[tuple[str, re.Pattern[str]], ...]) -> tuple[int, list[str]]:
    matches: list[str] = []
    for _, pattern in patterns:
        matches.extend(match.group(0) for match in pattern.finditer(text))
    return len(matches), matches


def repeated_reasoning_openings(text: str) -> list[tuple[str, int]]:
    sentences = [segment.strip() for segment in SENTENCE_SPLIT_RE.split(strip_markdown(text)) if segment.strip()]
    openings: Counter[str] = Counter()
    for sentence in sentences:
        normalized = CJK_ONLY_RE.sub("", sentence)
        match = REASONING_OPENING_RE.match(normalized)
        if match:
            openings[match.group(0)] += 1
    return sorted(
        ((opening, count) for opening, count in openings.items() if count >= 3),
        key=lambda item: (-item[1], item[0]),
    )[:4]


def repeated_ngrams(text: str, size: int = 8) -> list[tuple[str, int]]:
    normalized = CJK_ONLY_RE.sub("", strip_markdown(text))
    if len(normalized) < size:
        return []
    counts = Counter(normalized[index : index + size] for index in range(len(normalized) - size + 1))
    candidates = [(phrase, count) for phrase, count in counts.items() if count >= 3 and len(set(phrase)) >= 4]
    candidates.sort(key=lambda item: (-item[1], item[0]))
    selected: list[tuple[str, int]] = []
    for phrase, count in candidates:
        if any(phrase in existing or existing in phrase for existing, _ in selected):
            continue
        selected.append((phrase, count))
        if len(selected) == 3:
            break
    return selected


def analyze(text: str, baseline_texts: list[str]) -> dict:
    metrics = text_metrics(text)
    body = strip_markdown(text)
    findings: list[dict] = []
    unit = max(metrics["contentChars"] / 1000, 1.0)

    micro_count, micro_evidence = count_markers(body, MICRO_ACTIONS)
    if micro_count / unit > 2.0:
        findings.append(
            {
                "code": "repeated-micro-actions",
                "severity": "review",
                "count": micro_count,
                "evidence": micro_evidence[:4],
                "message": "High-frequency stock micro-actions may flatten character-specific behavior.",
            }
        )

    explanation_count, explanation_evidence = count_markers(body, EXPLANATION_MARKERS)
    if explanation_count / unit > 2.5:
        findings.append(
            {
                "code": "explanation-density",
                "severity": "review",
                "count": explanation_count,
                "evidence": explanation_evidence[:4],
                "message": "Frequent explanation markers may tell readers what to conclude instead of letting the scene carry it.",
            }
        )

    corrective_count, corrective_evidence = count_regex_patterns(body, CORRECTIVE_PATTERNS)
    if corrective_count >= 3 or (corrective_count >= 2 and corrective_count / unit > 0.7):
        findings.append(
            {
                "code": "corrective-scaffold-density",
                "severity": "review",
                "count": corrective_count,
                "evidence": corrective_evidence[:4],
                "message": "Corrective constructions recur densely; inspect whether they repeatedly pre-package conclusions or create a uniform quotable cadence.",
            }
        )

    simile_count, simile_evidence = count_markers(body, SIMILE_MARKERS)
    if simile_count / unit > 3.0:
        findings.append(
            {
                "code": "simile-density",
                "severity": "review",
                "count": simile_count,
                "evidence": simile_evidence[:4],
                "message": "Dense simile markers may create a generic ornamental layer; inspect whether each image belongs to the viewpoint.",
            }
        )

    ending = body[-180:]
    ending_hits = [marker for marker in SUMMARY_ENDINGS if marker in ending]
    if ending_hits:
        findings.append(
            {
                "code": "summary-ending",
                "severity": "review",
                "count": len(ending_hits),
                "evidence": ending_hits,
                "message": "The ending may summarize its meaning; verify that action, image, dialogue, or consequence would create stronger forward pull.",
            }
        )

    theme_closure_hits = [marker for marker in THEME_CLOSURE_MARKERS if marker in body[-320:]]
    if theme_closure_hits:
        findings.append(
            {
                "code": "theme-closure-ending",
                "severity": "review",
                "count": len(theme_closure_hits),
                "evidence": theme_closure_hits,
                "message": "The final passage may restate the theme after the outcome is already visible; verify whether a concrete consequence can carry the ending.",
            }
        )

    if metrics["sentences"] >= 12 and metrics["sentenceLengthCv"] < 0.28:
        findings.append(
            {
                "code": "uniform-sentence-rhythm",
                "severity": "review",
                "count": metrics["sentences"],
                "evidence": [],
                "message": "Sentence lengths are unusually uniform; inspect whether pressure and attention shifts are audible in the rhythm.",
            }
        )
    if metrics["paragraphs"] >= 8 and metrics["paragraphLengthCv"] < 0.22:
        findings.append(
            {
                "code": "uniform-paragraph-rhythm",
                "severity": "review",
                "count": metrics["paragraphs"],
                "evidence": [],
                "message": "Paragraph lengths are unusually uniform; inspect for outline-like beat packaging.",
            }
        )

    repeated = repeated_ngrams(text)
    if repeated:
        findings.append(
            {
                "code": "repeated-long-phrases",
                "severity": "review",
                "count": sum(count for _, count in repeated),
                "evidence": [phrase for phrase, _ in repeated],
                "message": "Long phrases recur at least three times; distinguish intentional motifs from accidental echoes.",
            }
        )

    repeated_openings = repeated_reasoning_openings(text)
    if repeated_openings:
        findings.append(
            {
                "code": "repeated-reasoning-openings",
                "severity": "review",
                "count": sum(count for _, count in repeated_openings),
                "evidence": [opening for opening, _ in repeated_openings],
                "message": "Several sentences share the same corrective or reflective opening; inspect for deliberate voice or an unintended repetitive reasoning cadence.",
            }
        )

    baseline_metrics = [text_metrics(item) for item in baseline_texts]
    baseline = None
    if baseline_metrics:
        baseline = {
            key: round(sum(item[key] for item in baseline_metrics) / len(baseline_metrics), 3)
            for key in ("meanSentenceChars", "sentenceLengthCv", "meanParagraphChars", "paragraphLengthCv", "dialogueRatio")
        }
        for key, label, threshold in (
            ("meanSentenceChars", "mean sentence length", 0.45),
            ("meanParagraphChars", "mean paragraph length", 0.55),
            ("dialogueRatio", "dialogue ratio", 0.25),
        ):
            expected = baseline[key]
            actual = metrics[key]
            difference = abs(actual - expected)
            relative = difference / expected if expected else difference
            if relative > threshold:
                findings.append(
                    {
                        "code": f"baseline-drift-{key}",
                        "severity": "review",
                        "count": 1,
                        "evidence": [],
                        "message": f"Draft {label} ({actual}) differs materially from the approved-project baseline ({expected}); treat this as a question, not an automatic defect.",
                    }
                )

    return {"status": "review" if findings else "pass", "metrics": metrics, "baseline": baseline, "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter", type=Path)
    parser.add_argument("--baseline", action="append", default=[], type=Path, help="Approved chapter to use as a voice baseline; repeatable")
    parser.add_argument("--output", type=Path, help="Write JSON atomically instead of stdout only")
    args = parser.parse_args()

    chapter_path = args.chapter.expanduser().resolve()
    text = chapter_path.read_text(encoding="utf-8")
    match = CHAPTER_RE.match(chapter_path.name)
    chapter = int(match.group(1)) if match else None
    baseline_paths = [path.expanduser().resolve() for path in args.baseline]
    result = {
        "schemaVersion": 1,
        "chapter": chapter,
        "reviewedTextSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "claim": "editorial-risk-signals-not-authorship-detection",
        "baselineFiles": [path.name for path in baseline_paths],
        **analyze(text, [path.read_text(encoding="utf-8") for path in baseline_paths]),
    }
    if args.output:
        write_json_atomic(args.output.expanduser().resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

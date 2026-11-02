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


CHAPTER_RE = re.compile(r"^第(\d{4,})章-.+\.(?:txt|md)$")
SENTENCE_SPLIT_RE = re.compile(r"[。！？!?]+")
CJK_ONLY_RE = re.compile(r"[^\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
DIALOGUE_RE = re.compile(r"[“「『](.*?)[”」』]", re.S)
MICRO_ACTIONS = (
    "深吸一口气",
    "眼中闪过",
    "嘴角勾起",
    "心中一震",
    "瞳孔骤缩",
    "下意识地",
    "不禁",
    "心中暗道",
    "映入眼帘",
    "脸色一变",
)
EXPLANATION_MARKERS = (
    "显然",
    "这意味着",
    "换句话说",
    "他意识到",
    "她意识到",
    "可想而知",
    "毋庸置疑",
    "之所以",
    "一下子通透了",
    "心里通透了",
    "分明是把",
    "说白了就是",
)
NARRATOR_INTRUSION = ("她不知道的是", "他不知道的是", "殊不知", "多年以后", "仿佛预示")
DIALOGUE_TAGS = ("说道", "问道", "笑道", "冷声道", "沉声道", "淡淡地说", "缓缓开口")
MODIFIER_MARKERS = ("其实", "显然", "忽然", "突然", "缓缓", "轻轻", "微微", "默默", "下意识地", "终于", "只是", "竟然")
SIMILE_MARKERS = ("仿佛", "犹如", "宛若", "如同", "像是")
SUMMARY_ENDINGS = (
    "他终于明白",
    "她终于明白",
    "这一刻他明白",
    "这一刻她明白",
    "从这一刻起",
    "这意味着",
    "他不知道的是",
    "她不知道的是",
)
CORRECTIVE_PATTERNS = (
    ("不是…而是/只是…", re.compile(r"不是[^。！？!?\n]{0,48}(?:而是|只是)")),
    ("没有…而是/只是…", re.compile(r"没有[^。！？!?\n]{0,48}(?:而是|只是)")),
    ("并非…而是/只是…", re.compile(r"并非[^。！？!?\n]{0,48}(?:而是|只是)")),
    ("不是…。而是/只是…", re.compile(r"不是[^。！？!?\n]{0,64}[。！？!?]\s*(?:我|他|她|他们|她们|这|那)?(?:而是|只是)")),
    ("没有…。而是/只是…", re.compile(r"没有[^。！？!?\n]{0,64}[。！？!?]\s*(?:我|他|她|他们|她们|这|那)?(?:而是|只是)")),
    ("不是…，是…", re.compile(r"不是[^，,。！？!?\n“”]{1,20}[，,]\s*(?:而)?是[^，,。！？!?\n]{1,24}")),
    ("不是…。是…", re.compile(r"(?:我|他|她|这|那)?不是[^。！？!?\n“”]{1,20}[。！？!?]\s*(?:我|他|她|这|那)?是[^。！？!?\n]{1,28}")),
)
ANADIPLOSIS_PATTERNS = (
    re.compile(r"([\u3400-\u9fff]{1,6}?)(?:了)?[。！？!?]\s*\1(?:的|了|时|候|时候|之后|以后|一次|一|就|才|不|也|还|都)"),
    re.compile(r"([\u3400-\u9fff]{2,6})[。！？!?]\s*\1"),
    re.compile(r"([\u3400-\u9fff]{1,3}?)(?:了|住|着)?[，,]\s*\1得[\u3400-\u9fff]{1,6}"),
)
DEGREE_COMPLEMENT_RE = re.compile(r"[\u3400-\u9fff]得(?:很|太|格外|有些|有点|异常|十分)[\u3400-\u9fff]{1,3}")
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
ANTITHETICAL_COUPLET_PATTERNS = (
    ("你的…用来…，我的…用来…", re.compile(r"你的[^，。！？!?\n]{1,12}用来[^，。！？!?\n]{1,24}[，,]\s*我的[^，。！？!?\n]{1,12}用来")),
    ("我的…用来…，你的…用来…", re.compile(r"我的[^，。！？!?\n]{1,12}用来[^，。！？!?\n]{1,24}[，,]\s*你的[^，。！？!?\n]{1,12}用来")),
    ("X可以，X不能", re.compile(r"([\u3400-\u9fff]{2,6})可以[，,]\1不能")),
    ("X不X…不管", re.compile(r"([\u3400-\u9fff]{1,3})不\1[^。！？!?\n]{0,10}不管")),
)
MOTIF_RECITATION_RE = re.compile(
    r"(?:买|替人|替他|替她)[^。！？!?\n]{0,8}(?:嘴|说话|张嘴)|买人说话|被人买走|买你吗|买不走|传话"
)
OCCUPATION_CRAFT_MARKERS = (
    "拧螺丝",
    "换螺母",
    "抹机油",
    "拧死",
    "碘伏",
    "热敷",
    "吸奶",
    "含接",
    "刮猪",
    "乳头霜",
    "腹带",
    "擦了身",
    "擦身",
    "倒扣在晾架",
    "刷开",
)
REASONING_OPENING_RE = re.compile(r"^(?:我|他|她|他们|她们|这|那)(?:没有|不是|只是|终于|才发现|才明白)")
SYMMETRY_PATTERNS = (
    re.compile(r"[\u3400-\u9fff]{1,8}在[，,、][\u3400-\u9fff]{1,8}在"),
    re.compile(r"([\u3400-\u9fff]{1,8})归\1[，,、]([\u3400-\u9fff]{1,8})归\2"),
    re.compile(r"[一二两三四五六七八九十][\u3400-\u9fff]{1,6}[。！？][一二两三四五六七八九十][\u3400-\u9fff]{1,6}[。！？]"),
)
TRIAD_PATTERNS = (
    re.compile(r"不是[^，,。！？!?\n]{1,20}[，,](?:也)?不是[^，,。！？!?\n]{1,20}[，,](?:而)?是"),
    re.compile(r"没有[^，,。！？!?\n]{1,16}[，,]没有[^，,。！？!?\n]{1,16}[，,](?:只|唯)?有"),
    re.compile(r"既不[^，,。！？!?\n]{1,16}[，,]也不[^，,。！？!?\n]{1,16}[，,]"),
)
DASH_CHAIN_RE = re.compile(r"(?:——|—)(?:[^。！？!?\n]{0,48}(?:——|—))+")
INDIRECT_SPEECH_RE = re.compile(
    r"(?:他|她|[\u3400-\u9fff]{2,3})(?:又|只|才|还|便|就|先|也)?(?:说|问|答|回|喊|骂|叮嘱|嘀咕|嘟囔)[，,：:]?(?!\s*[“「『])"
)


def mean(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def coefficient_of_variation(values: list[int]) -> float:
    average = mean(values)
    if not values or average == 0:
        return 0.0
    variance = sum((value - average) ** 2 for value in values) / len(values)
    return math.sqrt(variance) / average


def quantile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def text_metrics(text: str) -> dict:
    body = strip_markdown(text)
    paragraphs = [line.strip() for line in body.splitlines() if line.strip()]
    sentences = [segment.strip() for segment in SENTENCE_SPLIT_RE.split(body) if segment.strip()]
    sentence_lengths = [content_char_count(sentence) for sentence in sentences if content_char_count(sentence)]
    paragraph_lengths = [content_char_count(paragraph) for paragraph in paragraphs if content_char_count(paragraph)]
    dialogue_chars = sum(content_char_count(match) for match in DIALOGUE_RE.findall(body))
    total = content_char_count(text)
    question_count = body.count("？") + body.count("?")
    modifier_count = sum(body.count(marker) for marker in MODIFIER_MARKERS)
    sentence_count = len(sentence_lengths)
    unit = max(total / 1000, 1.0)
    return {
        "contentChars": total,
        "paragraphs": len(paragraphs),
        "sentences": len(sentence_lengths),
        "meanSentenceChars": round(mean(sentence_lengths), 2),
        "sentenceLengthCv": round(coefficient_of_variation(sentence_lengths), 3),
        "sentenceLengthP25": round(quantile(sentence_lengths, 0.25), 2),
        "sentenceLengthP50": round(quantile(sentence_lengths, 0.50), 2),
        "sentenceLengthP75": round(quantile(sentence_lengths, 0.75), 2),
        "meanParagraphChars": round(mean(paragraph_lengths), 2),
        "paragraphLengthCv": round(coefficient_of_variation(paragraph_lengths), 3),
        "dialogueRatio": round(dialogue_chars / total, 3) if total else 0.0,
        "questionRatio": round(question_count / sentence_count, 3) if sentence_count else 0.0,
        "modifierRatePer1k": round(modifier_count / unit, 3),
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


def modifier_clusters(text: str) -> list[str]:
    sentences = [item.strip() for item in SENTENCE_SPLIT_RE.split(strip_markdown(text)) if item.strip()]
    evidence: list[str] = []
    for index in range(max(0, len(sentences) - 2)):
        window = sentences[index : index + 3]
        joined = "。".join(window)
        hits = [marker for marker in MODIFIER_MARKERS for _ in range(joined.count(marker))]
        if len(hits) >= 5 and len(set(hits)) >= 3:
            evidence.append(joined)
    return list(dict.fromkeys(evidence))[:3]


def rhetorical_symmetry(text: str) -> list[str]:
    body = strip_markdown(text)
    matches = [match.group(0) for pattern in SYMMETRY_PATTERNS for match in pattern.finditer(body)]
    unique = list(dict.fromkeys(matches))
    return unique[:4] if len(unique) >= 2 else []


def cadence_packages(text: str) -> list[str]:
    lines = [line.strip() for line in strip_markdown(text).splitlines() if line.strip()]
    candidates: list[str] = []
    conclusion_markers = (*EXPLANATION_MARKERS, "这说明", "所以", "原来")
    for index in range(len(lines) - 2):
        action, dialogue, conclusion = lines[index : index + 3]
        if (
            0 < content_char_count(action) <= 8
            and DIALOGUE_RE.search(dialogue)
            and any(marker in conclusion for marker in conclusion_markers)
        ):
            candidates.append(" / ".join((action, dialogue, conclusion)))
    return candidates[:3] if len(candidates) >= 2 else []


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

    intrusion_count, intrusion_evidence = count_markers(body, NARRATOR_INTRUSION)
    if intrusion_count >= 2:
        findings.append(
            {
                "code": "narrator-intrusion",
                "severity": "review",
                "count": intrusion_count,
                "evidence": intrusion_evidence[:4],
                "message": "The narrator may be previewing facts outside the current viewpoint; keep a character's own judgment, cut authorial spoilers.",
            }
        )

    tag_count, tag_evidence = count_markers(body, DIALOGUE_TAGS)
    if tag_count >= 4 and tag_count / unit > 3:
        findings.append(
            {
                "code": "dialogue-tag-density",
                "severity": "review",
                "count": tag_count,
                "evidence": tag_evidence[:4],
                "message": "Dialogue tags recur densely; a plain 说 can stay, but a tag wall may replace action and distinct voices.",
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

    triad_count, triad_evidence = count_regex_patterns(body, tuple((pattern.pattern, pattern) for pattern in TRIAD_PATTERNS))
    if triad_count >= 2:
        findings.append(
            {
                "code": "classic-triad",
                "severity": "review",
                "count": triad_count,
                "evidence": triad_evidence[:4],
                "message": "Classic three-part sentences recur; keep a triad only when each item changes the choice, otherwise state the landing point.",
            }
        )

    dash_chains = [match.group(0) for match in DASH_CHAIN_RE.finditer(body)]
    if len(dash_chains) >= 2:
        findings.append(
            {
                "code": "dash-reveal-chain",
                "severity": "review",
                "count": len(dash_chains),
                "evidence": dash_chains[:3],
                "message": "Narration uses dash chains to stage a reveal; a single interrupted line of dialogue can stay, stacked dashes should become a comma, period, or next action.",
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

    modifier_evidence = modifier_clusters(text)
    if modifier_evidence:
        findings.append(
            {
                "code": "modifier-cluster",
                "severity": "review",
                "count": len(modifier_evidence),
                "evidence": modifier_evidence,
                "message": "Modifier clusters recur across adjacent sentences; inspect whether they replace character-specific action rather than deleting modifiers by rule.",
            }
        )

    symmetry_evidence = rhetorical_symmetry(text)
    if symmetry_evidence:
        findings.append(
            {
                "code": "rhetorical-symmetry",
                "severity": "review",
                "count": len(symmetry_evidence),
                "evidence": symmetry_evidence,
                "message": "Several symmetrical constructions appear together; inspect whether they create an unintended quotable cadence or serve a deliberate character voice.",
            }
        )

    anadiplosis_hits = [
        match.group(0).strip()
        for pattern in ANADIPLOSIS_PATTERNS
        for match in pattern.finditer(body)
    ]
    unique_anadiplosis = list(dict.fromkeys(anadiplosis_hits))
    if len(anadiplosis_hits) >= 3 or (len(anadiplosis_hits) >= 2 and len(anadiplosis_hits) / unit > 0.8):
        findings.append(
            {
                "code": "anadiplosis-chain",
                "severity": "review",
                "count": len(anadiplosis_hits),
                "evidence": unique_anadiplosis[:4],
                "message": "Tail-to-head word echoing (顶真/回环) or verb-plus-得 repetition recurs densely; merge into natural speech instead of chaining clause endings.",
            }
        )

    degree_hits = [match.group(0) for match in DEGREE_COMPLEMENT_RE.finditer(body)]
    if len(degree_hits) >= 5 and len(degree_hits) / unit > 1.2:
        findings.append(
            {
                "code": "degree-complement-cluster",
                "severity": "review",
                "count": len(degree_hits),
                "evidence": list(dict.fromkeys(degree_hits))[:4],
                "message": "Frequent 'X得很Y' degree complements may make action descriptions sound mechanically annotated; keep concrete physical results instead.",
            }
        )

    couplet_count, couplet_evidence = count_regex_patterns(body, ANTITHETICAL_COUPLET_PATTERNS)
    if couplet_count >= 2:
        findings.append(
            {
                "code": "antithetical-couplet-density",
                "severity": "review",
                "count": couplet_count,
                "evidence": couplet_evidence[:4],
                "message": "Antithetical theme couplets recur (你的X用来A，我的X用来B / X可以，X不能); keep only the half that changes money or relation.",
            }
        )

    motif_hits = [match.group(0) for match in MOTIF_RECITATION_RE.finditer(body)]
    if len(motif_hits) >= 4:
        findings.append(
            {
                "code": "motif-recitation-cluster",
                "severity": "review",
                "count": len(motif_hits),
                "evidence": list(dict.fromkeys(motif_hits))[:4],
                "message": "A title-level metaphor (买嘴/传话/替人张嘴) is restated across scenes; say it once at the clash, then move to a new concrete obstacle.",
            }
        )

    paragraphs_list = [line.strip() for line in body.splitlines() if line.strip()]
    max_window_craft = 0
    for idx in range(max(1, len(paragraphs_list))):
        window_text = "\n".join(paragraphs_list[idx : idx + 5])
        window_hits = sum(1 for marker in OCCUPATION_CRAFT_MARKERS if marker in window_text)
        if window_hits > max_window_craft:
            max_window_craft = window_hits
    craft_hits = [marker for marker in OCCUPATION_CRAFT_MARKERS if marker in body]
    total_craft_occurrences = sum(body.count(marker) for marker in OCCUPATION_CRAFT_MARKERS)
    if len(craft_hits) >= 5 and (max_window_craft >= 4 or total_craft_occurrences / unit >= 1.2):
        findings.append(
            {
                "code": "occupation-micro-action-cluster",
                "severity": "review",
                "count": total_craft_occurrences,
                "evidence": craft_hits[:6],
                "message": "Occupational process verbs cluster densely in a scene (repair, postpartum care, sewing, kitchen); keep only the step that snags or changes a choice, not a full craft checklist.",
            }
        )

    if metrics["sentences"] >= 20 and (metrics["meanSentenceChars"] < 12.5 or metrics["sentenceLengthP50"] <= 10.0):
        findings.append(
            {
                "code": "staccato-sentence-clipping",
                "severity": "review",
                "count": metrics["sentences"],
                "evidence": [f"mean={metrics['meanSentenceChars']}", f"p50={metrics['sentenceLengthP50']}"],
                "message": "Sentences are clipped into short staccato beats; let clauses flow with natural spoken breath instead of chopping every action into 5-10 character fragments.",
            }
        )

    if metrics["sentences"] >= 30 and metrics["sentenceLengthP25"] >= 17.5:
        findings.append(
            {
                "code": "over-smoothed-sentence-flow",
                "severity": "review",
                "count": metrics["sentences"],
                "evidence": [
                    f"p25={metrics['sentenceLengthP25']}",
                    f"mean={metrics['meanSentenceChars']}",
                    f"dialogueRatio={metrics['dialogueRatio']}",
                ],
                "message": "Even the shortest 25% of sentences are long (>=17.5 chars), often from turning live dialogue into a wall of '他说/她说' indirect narration; restore short spoken retorts and direct quotes.",
            }
        )

    indirect_hits = [match.group(0) for match in INDIRECT_SPEECH_RE.finditer(body)]
    if metrics["contentChars"] >= 1800 and metrics["dialogueRatio"] < 0.22 and len(indirect_hits) / unit >= 4.0:
        findings.append(
            {
                "code": "summary-narration-flatten",
                "severity": "review",
                "count": len(indirect_hits),
                "evidence": [
                    f"dialogueRatio={metrics['dialogueRatio']}",
                    f"indirectPer1k={round(len(indirect_hits) / unit, 2)}",
                    *list(dict.fromkeys(indirect_hits))[:4],
                ],
                "message": "Live scenes are flattened into indirect '他说/她说' summary narration (low direct dialogue ratio), which causes short drafts and forces artificial mid-story padding; write out real-time quoted exchanges.",
            }
        )

    cadence_evidence = cadence_packages(text)
    if cadence_evidence:
        findings.append(
            {
                "code": "cadence-packaging",
                "severity": "review",
                "count": len(cadence_evidence),
                "evidence": cadence_evidence,
                "message": "Repeated action-dialogue-conclusion packages may pre-package reader response; inspect whether each three-beat unit follows the scene's specific pressure.",
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
            for key in (
                "meanSentenceChars",
                "sentenceLengthCv",
                "sentenceLengthP25",
                "sentenceLengthP50",
                "sentenceLengthP75",
                "meanParagraphChars",
                "paragraphLengthCv",
                "dialogueRatio",
                "questionRatio",
                "modifierRatePer1k",
            )
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
        if len(baseline_metrics) >= 3:
            for key, label, threshold in (
                ("questionRatio", "question ratio", 0.18),
                ("modifierRatePer1k", "modifier rate per 1,000 characters", 3.0),
            ):
                actual = metrics[key]
                expected = baseline[key]
                if abs(actual - expected) > threshold:
                    findings.append(
                        {
                            "code": f"baseline-drift-{key}",
                            "severity": "review",
                            "count": 1,
                            "evidence": [],
                            "message": f"Draft {label} ({actual}) differs from the approved-project baseline ({expected}); inspect the cause rather than optimizing the number.",
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

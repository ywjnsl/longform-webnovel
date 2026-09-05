#!/usr/bin/env python3
"""Validate a longform-webnovel project and flag continuity debt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from market_brief import validate_snapshot
from publishing_package import analyze_title
from webnovel_io import (
    CURRENT_CAST_SCHEMA,
    CURRENT_PROJECT_SCHEMA,
    CURRENT_REWARD_SCHEMA,
    VALID_STORY_MODES,
    content_char_count,
    short_story_anchors,
    story_mode,
)


REQUIRED = (
    "project.json",
    "canon/story-contract.md",
    "canon/characters.md",
    "canon/world.md",
    "canon/laws.md",
    "canon/style-profile.md",
    "canon/publishing-package.md",
    "canon/market-brief.md",
    "canon/timeline.md",
    "planning/series-map.md",
    "planning/current-volume.md",
    "planning/rolling-outline.md",
    "planning/current-arc.md",
    "state/story-state.json",
    "state/threads.json",
    "state/rewards.json",
    "state/cast-arcs.json",
    "state/decisions.json",
)
VALID_THREAD_STATUS = {"open", "advanced", "deferred", "resolved", "transformed"}
VALID_THREAD_KIND = {"main", "subplot", "promise", "foreshadow"}
VALID_REWARD_LEVEL = {"small", "major"}
VALID_REWARD_STATUS = {"planned", "delivered", "needs-review"}
VALID_CAST_TIER = {"anchor", "recurring", "cameo"}
VALID_CAST_ROLE = {"ally", "rival", "antagonist", "foil", "mentor", "family", "romantic", "civilian", "other"}
VALID_CAST_STATUS = {"active", "deferred", "resolved", "departed", "dead"}
VALID_ARC_PHASE = {"none", "setup", "pressure", "choice", "consequence", "changed", "closed"}
VALID_RELATION_KIND = {
    "love",
    "loyalty",
    "rivalry",
    "debt",
    "family",
    "friendship",
    "mentorship",
    "duty",
    "ideology",
    "belonging",
    "fear",
    "interest",
    "other",
}
VALID_RELATION_STATUS = {
    "latent",
    "active",
    "strained",
    "mutual",
    "hostile",
    "broken",
    "ended",
    "transformed",
    "hidden",
    "expressed",
    "reciprocated",
    "rejected",
    "complicated",
}
VALID_REWARD_TYPE = {
    "power",
    "status",
    "relationship",
    "truth",
    "resource",
    "revenge",
    "emotional",
    "escape",
    "achievement",
    "other",
}
VALID_EDITOR_STATUS = {"pass", "pass-with-notes", "blocked"}
VALID_EDITOR_PRIORITY = {"high", "medium", "low"}
VALID_EDITOR_DIMENSION = {"promise", "causality", "structure", "character", "voice", "continuity", "line"}
VALID_READER_STATUS = {"engaged", "mixed", "drop-risk"}
VALID_COMPLETION_INTENT = {"continue", "uncertain", "stop"}
VALID_READER_CHANNEL = {"transportation", "aesthetic", "social", "curiosity", "flow"}
VALID_READER_VALENCE = {"positive", "negative", "mixed"}
VALID_RESOLUTION_ACTION = {"accepted", "revised", "author-approved"}
VALID_NATURALNESS_STATUS = {"pass", "pass-with-notes", "needs-revision"}
VALID_NATURALNESS_PRIORITY = {"high", "medium", "low"}
VALID_NATURALNESS_CATEGORY = {
    "over-explanation",
    "corrective-syntax",
    "expository-dialogue",
    "same-voice",
    "over-engineered-causality",
    "generic-reaction",
    "theme-closure",
}
VALID_NATURALNESS_REVISION_ACTION = {"not-needed", "revised", "author-approved"}
FINAL_REVIEW_CHECKS = (
    "promise",
    "causality",
    "continuity",
    "setupPayoff",
    "characterConsequences",
    "titleResonance",
    "endingBoundary",
)
CHAPTER_RE = re.compile(r"^第(\d{4,})章-.+\.md$")
PLACEHOLDER_VALUES = {"待填写", "待规划", "待复核", "tbd", "todo"}
CORE_TEXT_FILES = (
    "canon/story-contract.md",
    "canon/characters.md",
    "canon/world.md",
    "canon/laws.md",
    "canon/style-profile.md",
    "canon/publishing-package.md",
    "planning/current-volume.md",
    "planning/rolling-outline.md",
    "planning/current-arc.md",
)
UNRESOLVED_MARKERS = ("待填写", "待确认", "待规划")


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid JSON {path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"Expected object in {path.name}")
        return {}
    return value


def is_concrete(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in PLACEHOLDER_VALUES


def validate_string_list(value: object, label: str, errors: list[str], minimum: int = 0) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if len(value) < minimum:
        errors.append(f"{label} needs at least {minimum} item(s)")
    strings: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label} item #{index + 1} must be a non-empty string")
        else:
            strings.append(item.strip())
    return strings


def validate_market_research(root: Path, project: dict, errors: list[str], warnings: list[str]) -> None:
    metadata = project.get("marketResearch")
    if not isinstance(metadata, dict):
        errors.append("project.json needs marketResearch")
        return
    status = metadata.get("status")
    if status not in {"unrequested", "completed"}:
        errors.append(f"marketResearch.status is invalid: {status}")
        return
    if not isinstance(metadata.get("updatedAt"), str) or not metadata["updatedAt"].strip():
        errors.append("marketResearch.updatedAt must be a non-empty timestamp string")
    brief = (root / "canon/market-brief.md").read_text(encoding="utf-8")
    if f"- 研究状态：`{status}`" not in brief:
        errors.append("canon/market-brief.md status does not match project.json")

    as_of = metadata.get("asOfDate")
    source_count = metadata.get("sourceCount")
    sample_count = metadata.get("sampleCount")
    if status == "unrequested":
        if as_of is not None or source_count != 0 or sample_count != 0:
            errors.append("Unrequested marketResearch must have null asOfDate and zero source/sample counts")
        return
    if not isinstance(as_of, str) or not as_of.strip():
        errors.append("Completed marketResearch needs asOfDate")
    if not isinstance(source_count, int) or isinstance(source_count, bool) or source_count < 2:
        errors.append("Completed marketResearch needs sourceCount >= 2")
    if not isinstance(sample_count, int) or isinstance(sample_count, bool) or sample_count < 5:
        errors.append("Completed marketResearch needs sampleCount >= 5")

    snapshots = []
    snapshot_dir = root / "research" / "market-snapshots"
    if snapshot_dir.is_dir():
        for path in sorted(snapshot_dir.glob("*.json")):
            snapshot = load_json(path, errors)
            snapshot_errors = validate_snapshot(snapshot)
            errors.extend(f"Market snapshot {path.name}: {message}" for message in snapshot_errors)
            if not snapshot_errors:
                snapshots.append((path, snapshot))
    matching = [(path, snapshot) for path, snapshot in snapshots if snapshot.get("asOfDate") == as_of]
    if not matching:
        errors.append(f"Completed marketResearch needs a valid snapshot dated {as_of}")
    elif not any(len(snapshot["sources"]) == source_count and len(snapshot["samples"]) == sample_count for _, snapshot in matching):
        errors.append("marketResearch source/sample counts do not match its dated snapshot")
    if len(matching) > 1:
        warnings.append(f"Multiple market snapshots share asOfDate {as_of}; confirm which one informs positioning")


def validate_evidence_snippet(value: object, label: str, chapter_text: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty exact chapter substring")
    elif value not in chapter_text:
        errors.append(f"{label} is not an exact chapter substring: {value!r}")


def confirmed_decision_ids(decision_doc: dict) -> set[str]:
    decisions = decision_doc.get("decisions", [])
    if not isinstance(decisions, list):
        return set()
    return {
        item["id"]
        for item in decisions
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item.get("status") in {"confirmed", "approved"}
    }


def confirmed_naturalness_decision_ids(decision_doc: dict, chapter: int, digest: str) -> set[str]:
    decisions = decision_doc.get("decisions", [])
    if not isinstance(decisions, list):
        return set()
    return {
        item["id"]
        for item in decisions
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item.get("status") in {"confirmed", "approved"}
        and item.get("kind") == "naturalness-exception"
        and item.get("chapter") == chapter
        and item.get("reviewedTextSha256") == digest
    }


def validate_naturalness_reviews(
    root: Path,
    chapter_files: dict[int, Path],
    committed: int,
    gate: dict,
    decision_doc: dict,
    errors: list[str],
) -> None:
    if gate.get("naturalnessRequired") is not True:
        return
    enforce_from = gate.get("naturalnessEnforceFromChapter")
    if not isinstance(enforce_from, int) or isinstance(enforce_from, bool) or enforce_from <= 0:
        return

    for chapter in range(enforce_from, committed + 1):
        chapter_path = chapter_files.get(chapter)
        if chapter_path is None:
            continue
        chapter_text = chapter_path.read_text(encoding="utf-8")
        digest = hashlib.sha256(chapter_text.encode("utf-8")).hexdigest()
        review_path = root / "reviews" / f"第{chapter:04d}章-review.json"
        if not review_path.is_file():
            errors.append(f"Chapter {chapter} needs reviews/{review_path.name}")
            continue

        review = load_json(review_path, errors)
        if review.get("schemaVersion") != 1:
            errors.append(f"Chapter {chapter} review schemaVersion must be 1")
        if review.get("chapter") != chapter:
            errors.append(f"Chapter {chapter} review chapter number does not match")
        if review.get("reviewedTextSha256") != digest:
            errors.append(f"Chapter {chapter} review hash does not match chapter text")

        naturalness = review.get("naturalness")
        if not isinstance(naturalness, dict):
            errors.append(f"Chapter {chapter} review needs naturalness object")
            continue
        status = naturalness.get("status")
        if status not in VALID_NATURALNESS_STATUS:
            errors.append(f"Chapter {chapter} naturalness status is invalid: {status}")
        if not is_concrete(naturalness.get("diagnosis")):
            errors.append(f"Chapter {chapter} naturalness review needs a concrete diagnosis")
        if naturalness.get("reviewedTextSha256") != digest:
            errors.append(f"Chapter {chapter} naturalness hash does not match chapter text")

        findings = naturalness.get("findings")
        unresolved_high = False
        if not isinstance(findings, list):
            errors.append(f"Chapter {chapter} naturalness findings must be an array")
            findings = []
        for index, finding in enumerate(findings):
            label = f"Chapter {chapter} naturalness finding #{index + 1}"
            if not isinstance(finding, dict):
                errors.append(f"{label} must be an object")
                continue
            if finding.get("priority") not in VALID_NATURALNESS_PRIORITY:
                errors.append(f"{label} has invalid priority")
            if finding.get("category") not in VALID_NATURALNESS_CATEGORY:
                errors.append(f"{label} has invalid category")
            evidence = validate_string_list(finding.get("evidence"), f"{label} evidence", errors, minimum=1)
            for evidence_index, snippet in enumerate(evidence):
                if snippet not in chapter_text:
                    errors.append(
                        f"{label} evidence #{evidence_index + 1} must be copied verbatim from chapter text"
                    )
            if not is_concrete(finding.get("readerCost")) or not is_concrete(finding.get("direction")):
                errors.append(f"{label} needs readerCost and revision direction")
            if not isinstance(finding.get("resolved"), bool):
                errors.append(f"{label} resolved must be boolean")
            if finding.get("priority") == "high" and finding.get("resolved") is False:
                unresolved_high = True

        if status == "pass" and findings:
            errors.append(f"Chapter {chapter} naturalness pass status cannot contain findings")
        if status == "needs-revision" and not findings:
            errors.append(f"Chapter {chapter} naturalness needs-revision status requires findings")

        revision = naturalness.get("revision")
        if not isinstance(revision, dict):
            errors.append(f"Chapter {chapter} naturalness review needs revision object")
            continue
        action = revision.get("action")
        if action not in VALID_NATURALNESS_REVISION_ACTION:
            errors.append(f"Chapter {chapter} naturalness revision action is invalid: {action}")
        if not is_concrete(revision.get("notes")):
            errors.append(f"Chapter {chapter} naturalness revision needs concrete notes")
        if action == "revised":
            before_digest = revision.get("beforeTextSha256")
            if (
                not isinstance(before_digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", before_digest) is None
                or before_digest == digest
            ):
                errors.append(
                    f"Chapter {chapter} revised naturalness review needs a distinct beforeTextSha256"
                )
            changed_categories = validate_string_list(
                revision.get("changedCategories"),
                f"Chapter {chapter} revised naturalness review changedCategories",
                errors,
                minimum=1,
            )
            if not changed_categories:
                errors.append(f"Chapter {chapter} revised naturalness review needs changedCategories")
            for category in changed_categories:
                if category not in VALID_NATURALNESS_CATEGORY:
                    errors.append(
                        f"Chapter {chapter} revised naturalness review has invalid changed category: {category}"
                    )
        approved_ids = confirmed_naturalness_decision_ids(decision_doc, chapter, digest)
        exception_approved = action == "author-approved" and revision.get("decisionId") in approved_ids
        if action == "author-approved" and not exception_approved:
            errors.append(
                f"Chapter {chapter} naturalness author-approved revision needs a confirmed decisionId"
            )
        if status == "needs-revision" and not exception_approved:
            errors.append(f"Chapter {chapter} naturalness review still needs revision")
        if unresolved_high and not exception_approved:
            errors.append(f"Chapter {chapter} has an unresolved high-priority naturalness finding")


def validate_chapter_reviews(
    root: Path,
    project: dict,
    chapter_files: dict[int, Path],
    committed: object,
    decision_doc: dict,
    errors: list[str],
) -> None:
    gate = project.get("reviewGate")
    if not isinstance(gate, dict):
        errors.append("project.json needs reviewGate")
        return
    enforce_from = gate.get("enforceFromChapter")
    if not isinstance(enforce_from, int) or isinstance(enforce_from, bool) or enforce_from <= 0:
        errors.append("reviewGate.enforceFromChapter must be a positive integer")
        return
    for field in ("editorRequired", "readerRequired", "lintRequired"):
        if not isinstance(gate.get(field), bool):
            errors.append(f"reviewGate.{field} must be boolean")
    if gate.get("naturalnessRequired") is not True:
        errors.append("reviewGate.naturalnessRequired must be true")
    naturalness_enforce_from = gate.get("naturalnessEnforceFromChapter")
    if (
        not isinstance(naturalness_enforce_from, int)
        or isinstance(naturalness_enforce_from, bool)
        or naturalness_enforce_from <= 0
    ):
        errors.append("reviewGate.naturalnessEnforceFromChapter must be a positive integer")
    if not isinstance(committed, int) or isinstance(committed, bool):
        return

    approved_ids = confirmed_decision_ids(decision_doc)
    validate_naturalness_reviews(root, chapter_files, committed, gate, decision_doc, errors)
    for chapter in range(enforce_from, committed + 1):
        chapter_path = chapter_files.get(chapter)
        if chapter_path is None:
            continue
        chapter_text = chapter_path.read_text(encoding="utf-8")
        digest = hashlib.sha256(chapter_text.encode("utf-8")).hexdigest()
        lint_path = root / "reviews" / f"第{chapter:04d}章-lint.json"
        review_path = root / "reviews" / f"第{chapter:04d}章-review.json"

        if gate.get("lintRequired"):
            if not lint_path.is_file():
                errors.append(f"Chapter {chapter} needs reviews/{lint_path.name}")
            else:
                lint = load_json(lint_path, errors)
                if lint.get("schemaVersion") != 1:
                    errors.append(f"Chapter {chapter} lint schemaVersion must be 1")
                if lint.get("chapter") != chapter:
                    errors.append(f"Chapter {chapter} lint chapter number does not match")
                if lint.get("reviewedTextSha256") != digest:
                    errors.append(f"Chapter {chapter} lint hash does not match chapter text")
                if lint.get("claim") != "editorial-risk-signals-not-authorship-detection":
                    errors.append(f"Chapter {chapter} lint must use the editorial-risk, non-authorship claim")
                if lint.get("status") not in {"pass", "review"}:
                    errors.append(f"Chapter {chapter} lint status must be pass or review")
                findings = lint.get("findings")
                if not isinstance(findings, list):
                    errors.append(f"Chapter {chapter} lint findings must be an array")
                else:
                    for index, finding in enumerate(findings):
                        label = f"Chapter {chapter} lint finding #{index + 1}"
                        if not isinstance(finding, dict):
                            errors.append(f"{label} must be an object")
                            continue
                        if not is_concrete(finding.get("code")) or finding.get("severity") != "review":
                            errors.append(f"{label} needs a code and severity review")
                        if not isinstance(finding.get("count"), int) or isinstance(finding.get("count"), bool) or finding["count"] < 0:
                            errors.append(f"{label} count must be a non-negative integer")
                        evidence = validate_string_list(finding.get("evidence"), f"{label} evidence", errors)
                        for snippet in evidence:
                            validate_evidence_snippet(snippet, f"{label} evidence", chapter_text, errors)
                        if not is_concrete(finding.get("message")):
                            errors.append(f"{label} needs a concrete message")

        if not (gate.get("editorRequired") or gate.get("readerRequired")):
            continue
        if not review_path.is_file():
            errors.append(f"Chapter {chapter} needs reviews/{review_path.name}")
            continue
        review = load_json(review_path, errors)
        if review.get("schemaVersion") != 1:
            errors.append(f"Chapter {chapter} review schemaVersion must be 1")
        if review.get("chapter") != chapter:
            errors.append(f"Chapter {chapter} review chapter number does not match")
        if review.get("reviewedTextSha256") != digest:
            errors.append(f"Chapter {chapter} review hash does not match chapter text")

        editor = review.get("editor")
        unresolved_high = False
        if gate.get("editorRequired"):
            if not isinstance(editor, dict):
                errors.append(f"Chapter {chapter} review needs editor object")
            else:
                editor_status = editor.get("status")
                if editor_status not in VALID_EDITOR_STATUS:
                    errors.append(f"Chapter {chapter} editor status is invalid: {editor_status}")
                if not is_concrete(editor.get("diagnosis")):
                    errors.append(f"Chapter {chapter} editor needs a concrete diagnosis")
                validate_string_list(editor.get("strengths"), f"Chapter {chapter} editor strengths", errors)
                findings = editor.get("findings")
                if not isinstance(findings, list):
                    errors.append(f"Chapter {chapter} editor findings must be an array")
                    findings = []
                for index, finding in enumerate(findings):
                    label = f"Chapter {chapter} editor finding #{index + 1}"
                    if not isinstance(finding, dict):
                        errors.append(f"{label} must be an object")
                        continue
                    if finding.get("priority") not in VALID_EDITOR_PRIORITY:
                        errors.append(f"{label} has invalid priority")
                    if finding.get("dimension") not in VALID_EDITOR_DIMENSION:
                        errors.append(f"{label} has invalid dimension")
                    validate_evidence_snippet(finding.get("evidence"), f"{label} evidence", chapter_text, errors)
                    if not is_concrete(finding.get("readerCost")) or not is_concrete(finding.get("direction")):
                        errors.append(f"{label} needs readerCost and revision direction")
                    if not isinstance(finding.get("resolved"), bool):
                        errors.append(f"{label} resolved must be boolean")
                    if finding.get("priority") == "high" and finding.get("resolved") is False:
                        unresolved_high = True

        reader = review.get("reader")
        reader_blocks = False
        if gate.get("readerRequired"):
            if not isinstance(reader, dict):
                errors.append(f"Chapter {chapter} review needs reader object")
            else:
                reader_status = reader.get("status")
                completion_intent = reader.get("completionIntent")
                if reader_status not in VALID_READER_STATUS:
                    errors.append(f"Chapter {chapter} reader status is invalid: {reader_status}")
                if not is_concrete(reader.get("persona")):
                    errors.append(f"Chapter {chapter} reader needs a concrete persona")
                if completion_intent not in VALID_COMPLETION_INTENT:
                    errors.append(f"Chapter {chapter} reader completionIntent is invalid: {completion_intent}")
                moments = reader.get("moments")
                if not isinstance(moments, list) or not moments:
                    errors.append(f"Chapter {chapter} reader moments needs at least one item")
                    moments = []
                for index, moment in enumerate(moments):
                    label = f"Chapter {chapter} reader moment #{index + 1}"
                    if not isinstance(moment, dict):
                        errors.append(f"{label} must be an object")
                        continue
                    validate_evidence_snippet(moment.get("evidence"), f"{label} evidence", chapter_text, errors)
                    if not is_concrete(moment.get("reaction")):
                        errors.append(f"{label} needs a concrete reaction")
                    if moment.get("channel") not in VALID_READER_CHANNEL:
                        errors.append(f"{label} has invalid channel")
                    if moment.get("valence") not in VALID_READER_VALENCE:
                        errors.append(f"{label} has invalid valence")
                validate_string_list(reader.get("openQuestions"), f"Chapter {chapter} reader openQuestions", errors)
                reader_blocks = reader_status == "drop-risk" or completion_intent == "stop"

        resolution = review.get("resolution")
        if not isinstance(resolution, dict):
            errors.append(f"Chapter {chapter} review needs resolution object")
            continue
        action = resolution.get("action")
        if action not in VALID_RESOLUTION_ACTION:
            errors.append(f"Chapter {chapter} resolution action is invalid: {action}")
        if not is_concrete(resolution.get("notes")):
            errors.append(f"Chapter {chapter} resolution needs concrete notes")
        exception_approved = action == "author-approved" and resolution.get("decisionId") in approved_ids
        if action == "author-approved" and not exception_approved:
            errors.append(f"Chapter {chapter} author-approved resolution needs a confirmed decisionId")
        if isinstance(editor, dict) and editor.get("status") == "blocked" and not exception_approved:
            errors.append(f"Chapter {chapter} editor review is blocked")
        if unresolved_high and not exception_approved:
            errors.append(f"Chapter {chapter} has an unresolved high-priority editor finding")
        if reader_blocks and not exception_approved:
            errors.append(f"Chapter {chapter} reader simulation reports drop-risk or stop intent")


def chapter_bundle_digest(chapter_files: dict[int, Path], committed: int) -> str:
    """Hash the ordered committed chapter bundle for the full-story review gate."""
    digest = hashlib.sha256()
    for chapter in range(1, committed + 1):
        path = chapter_files.get(chapter)
        if path is None:
            continue
        digest.update(f"chapter:{chapter:04d}:{path.name}\n".encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_final_review(
    root: Path,
    project: dict,
    chapter_files: dict[int, Path],
    committed: object,
    mode: str,
    short_status: object,
    errors: list[str],
) -> None:
    """Require an external-reader full-story review before a short story is complete."""
    if mode != "fanqie-short-story" or short_status != "complete":
        return
    if not isinstance(committed, int) or committed <= 0:
        return

    path = root / "reviews" / "final-review.json"
    if not path.is_file():
        errors.append("Completed short story needs reviews/final-review.json")
        return
    review = load_json(path, errors)
    if review.get("schemaVersion") != 1:
        errors.append("Full-story review schemaVersion must be 1")
    if review.get("storyMode") != "fanqie-short-story":
        errors.append("Full-story review storyMode must be fanqie-short-story")
    if review.get("reviewedThroughChapter") != committed:
        errors.append("Full-story review must cover every committed chapter")
    if review.get("perspective") != "external-reader":
        errors.append("Full-story review perspective must be external-reader")
    expected_digest = chapter_bundle_digest(chapter_files, committed)
    if review.get("reviewedTextSha256") != expected_digest:
        errors.append("Full-story review hash does not match the committed chapter bundle")

    if review.get("editorStatus") != "pass":
        errors.append("Full-story review editorStatus must be pass")
    if review.get("readerStatus") != "engaged":
        errors.append("Full-story review readerStatus must be engaged")
    if review.get("completionIntent") != "complete":
        errors.append("Full-story review completionIntent must be complete")
    checks = review.get("checks")
    if not isinstance(checks, dict):
        errors.append("Full-story review needs checks object")
    else:
        for check in FINAL_REVIEW_CHECKS:
            if checks.get(check) != "pass":
                errors.append(f"Full-story review check {check} must be pass")
    if not is_concrete(review.get("resolution")):
        errors.append("Full-story review needs a concrete resolution")


VALID_ENSEMBLE_OUTCOMES = {"progress", "setback", "reroute", "expose", "pause-with-scar"}
ENSEMBLE_INTENT_REQUIRED = ("characterId", "chapter", "beat", "emotion", "wantNow", "wouldDo")


def validate_ensemble(root: Path, project: dict, committed: object, errors: list[str]) -> None:
    """校验群像仿真配置，以及强制章之后的合同/意图/裁判文件。"""
    ensemble = project.get("ensemble")
    if not isinstance(ensemble, dict):
        errors.append("project.json needs ensemble; run migrate_project.py")
        return
    enabled = ensemble.get("enabled")
    if not isinstance(enabled, bool):
        errors.append("ensemble.enabled must be boolean")
        enabled = True
    protagonist_id = ensemble.get("protagonistId")
    if not isinstance(protagonist_id, str) or not protagonist_id.strip() or protagonist_id.strip() == "protagonist":
        errors.append("ensemble.protagonistId must be a non-empty id other than 'protagonist'")
        protagonist_id = ""
    beats_default = ensemble.get("explorationBeatsDefault")
    max_on_stage = ensemble.get("maxOnStage")
    enforce_from = ensemble.get("enforceFromChapter")
    if not isinstance(beats_default, int) or isinstance(beats_default, bool) or not 1 <= beats_default <= 6:
        errors.append("ensemble.explorationBeatsDefault must be an integer from 1 to 6")
    if not isinstance(max_on_stage, int) or isinstance(max_on_stage, bool) or not 2 <= max_on_stage <= 6:
        errors.append("ensemble.maxOnStage must be an integer from 2 to 6")
        max_on_stage = 4
    if not isinstance(enforce_from, int) or isinstance(enforce_from, bool) or enforce_from <= 0:
        errors.append("ensemble.enforceFromChapter must be a positive integer")
        return
    if protagonist_id:
        if not (root / "cast" / protagonist_id / "SKILL.md").is_file():
            errors.append(f"missing cast/{protagonist_id}/SKILL.md")
        if not (root / "cast" / protagonist_id / "state.json").is_file():
            errors.append(f"missing cast/{protagonist_id}/state.json")
    if not enabled or not isinstance(committed, int) or committed < enforce_from:
        return
    for chapter in range(enforce_from, committed + 1):
        contract_path = root / "contracts" / f"chapter-{chapter:04d}.json"
        if not contract_path.is_file():
            errors.append(f"Chapter {chapter} needs contracts/{contract_path.name}")
            continue
        contract = load_json(contract_path, errors)
        if contract.get("chapter") != chapter:
            errors.append(f"{contract_path.name} chapter does not match filename")
        illegal = set(contract.get("illegalOutcomes") or [])
        legal = set(contract.get("legalOutcomes") or [])
        if "status-quo" not in illegal:
            errors.append(f"{contract_path.name}: illegalOutcomes must include status-quo")
        if "status-quo" in legal:
            errors.append(f"{contract_path.name}: status-quo cannot be legal")
        if not legal.intersection(VALID_ENSEMBLE_OUTCOMES):
            errors.append(f"{contract_path.name}: legalOutcomes must include a known unfinished-arc outcome")
        if contract.get("arcStatus") not in {"open", "resolved", "failed"}:
            errors.append(f"{contract_path.name}: bad arcStatus")
        on_stage = contract.get("onStage") or []
        if not isinstance(on_stage, list) or not on_stage:
            errors.append(f"{contract_path.name}: onStage must be a non-empty array")
            on_stage = []
        elif len(on_stage) > max_on_stage:
            errors.append(f"{contract_path.name}: onStage exceeds ensemble.maxOnStage")
        if protagonist_id and protagonist_id not in on_stage:
            errors.append(f"{contract_path.name}: protagonistId must be onStage")
        intent_dir = root / "intents" / f"chapter-{chapter:04d}"
        ruling_path = intent_dir / "ruling.json"
        if not ruling_path.is_file():
            errors.append(f"Chapter {chapter} needs intents/chapter-{chapter:04d}/ruling.json")
        for character_id in on_stage:
            if not isinstance(character_id, str) or not character_id.strip():
                errors.append(f"{contract_path.name}: onStage ids must be strings")
                continue
            intent_path = intent_dir / f"{character_id}.json"
            if not intent_path.is_file():
                errors.append(f"Chapter {chapter} needs {intent_path.relative_to(root)}")
                continue
            try:
                payload = json.loads(intent_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{intent_path.name}: {exc}")
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    errors.append(f"{intent_path.name}: intent must be object")
                    continue
                for key in ENSEMBLE_INTENT_REQUIRED:
                    if key not in item:
                        errors.append(f"{intent_path.name}: missing {key}")
                emotion = item.get("emotion") or {}
                if isinstance(emotion, dict) and not emotion.get("trigger"):
                    errors.append(f"{intent_path.name}: emotion.trigger required")
                if item.get("characterId") != character_id:
                    errors.append(f"{intent_path.name}: characterId must match filename")


def validate_cast_arcs(cast_doc: dict, committed: object, mode: str, errors: list[str], warnings: list[str]) -> None:
    if cast_doc.get("schemaVersion") != CURRENT_CAST_SCHEMA:
        errors.append(f"cast-arcs.json schemaVersion must be {CURRENT_CAST_SCHEMA}; run migrate_project.py")
    as_of = cast_doc.get("asOfChapter")
    legacy_through = cast_doc.get("legacyUnauditedThrough", 0)
    if not isinstance(as_of, int) or isinstance(as_of, bool) or as_of < 0:
        errors.append("cast-arcs.json asOfChapter must be a non-negative integer")
        as_of = 0
    if not isinstance(legacy_through, int) or isinstance(legacy_through, bool) or not 0 <= legacy_through <= as_of:
        errors.append("cast-arcs.json legacyUnauditedThrough must be between 0 and asOfChapter")
        legacy_through = 0
    elif legacy_through:
        warnings.append(f"Supporting-cast arcs through chapter {legacy_through} were not audited before v4 migration")

    characters = cast_doc.get("characters")
    if not isinstance(characters, list):
        errors.append("cast-arcs.json field 'characters' must be an array")
        return

    ids: set[str] = set()
    pending_targets: list[tuple[str, str]] = []
    active_anchors = 0
    recent_arc_chapters: list[int] = []
    anchor_arc_chapters: list[int] = []
    for index, character in enumerate(characters):
        if not isinstance(character, dict):
            errors.append(f"Cast character #{index + 1} is not an object")
            continue
        cast_id = character.get("id")
        label = cast_id if isinstance(cast_id, str) and cast_id.strip() else f"#{index + 1}"
        if not isinstance(cast_id, str) or not cast_id.strip():
            errors.append(f"Cast character {label} needs a stable id")
            continue
        if cast_id == "protagonist":
            errors.append("Cast id 'protagonist' is reserved for relationship targets")
        elif cast_id in ids:
            errors.append(f"Duplicate cast character id: {cast_id}")
        else:
            ids.add(cast_id)
        if not is_concrete(character.get("name")):
            errors.append(f"Cast character {label} needs a concrete name")
        tier = character.get("tier")
        role = character.get("narrativeRole")
        status = character.get("status")
        phase = character.get("arcPhase")
        if tier not in VALID_CAST_TIER:
            errors.append(f"Cast character {label} has invalid tier: {tier}")
        if role not in VALID_CAST_ROLE:
            errors.append(f"Cast character {label} has invalid narrativeRole: {role}")
        if status not in VALID_CAST_STATUS:
            errors.append(f"Cast character {label} has invalid status: {status}")
        if phase not in VALID_ARC_PHASE:
            errors.append(f"Cast character {label} has invalid arcPhase: {phase}")
        elif tier != "cameo" and phase == "none":
            errors.append(f"Non-cameo cast character {label} needs an active arcPhase")

        introduced = character.get("introducedChapter")
        last_advanced = character.get("lastAdvancedChapter")
        if not isinstance(introduced, int) or isinstance(introduced, bool) or not 0 <= introduced <= as_of:
            errors.append(f"Cast character {label} has invalid introducedChapter")
            introduced = 0
        if not isinstance(last_advanced, int) or isinstance(last_advanced, bool) or not introduced <= last_advanced <= as_of:
            errors.append(f"Cast character {label} has invalid lastAdvancedChapter")
            last_advanced = introduced

        if tier in {"anchor", "recurring"}:
            for field in ("ownWant", "independentGoal"):
                if not is_concrete(character.get(field)):
                    errors.append(f"{tier} cast character {label} needs a concrete {field}")
        if tier == "anchor" and not is_concrete(character.get("privateConstraint")):
            errors.append(f"Anchor cast character {label} needs a concrete privateConstraint")

        if status in {"active", "deferred"} and tier in {"anchor", "recurring"}:
            window = character.get("nextTurnWindow")
            if not (
                isinstance(window, list)
                and len(window) == 2
                and all(isinstance(value, int) and not isinstance(value, bool) for value in window)
                and 0 < window[0] <= window[1]
            ):
                errors.append(f"Active cast character {label} needs a positive nextTurnWindow [start, end]")
            elif isinstance(committed, int) and committed > window[1]:
                warnings.append(f"Cast character {label} missed the planned turn window ending at chapter {window[1]}")
        if status == "active" and tier == "anchor":
            active_anchors += 1
            if isinstance(committed, int) and committed - last_advanced > 8:
                warnings.append(f"Anchor cast character {label} has not advanced for {committed - last_advanced} chapters")

        history = character.get("history", [])
        history_chapters: set[int] = set()
        if not isinstance(history, list):
            errors.append(f"Cast character {label} history must be an array")
        else:
            for history_index, event in enumerate(history):
                if not isinstance(event, dict):
                    errors.append(f"Cast character {label} history #{history_index + 1} is not an object")
                    continue
                event_chapter = event.get("chapter")
                if not isinstance(event_chapter, int) or isinstance(event_chapter, bool) or not introduced <= event_chapter <= as_of:
                    errors.append(f"Cast character {label} history #{history_index + 1} has invalid chapter")
                else:
                    history_chapters.add(event_chapter)
                    recent_arc_chapters.append(event_chapter)
                    if tier == "anchor":
                        anchor_arc_chapters.append(event_chapter)
                if not is_concrete(event.get("choice")):
                    errors.append(f"Cast character {label} history #{history_index + 1} needs the character's choice")
                if not is_concrete(event.get("delta")):
                    errors.append(f"Cast character {label} history #{history_index + 1} needs a resulting delta")
        if last_advanced > introduced and last_advanced not in history_chapters:
            errors.append(f"Cast character {label} lastAdvancedChapter needs matching choice/delta history evidence")

        relationships = character.get("relationships", [])
        if not isinstance(relationships, list):
            errors.append(f"Cast character {label} relationships must be an array")
        else:
            for relation_index, relation in enumerate(relationships):
                relation_label = f"Cast character {label} relationship #{relation_index + 1}"
                if not isinstance(relation, dict):
                    errors.append(f"{relation_label} is not an object")
                    continue
                target = relation.get("targetId")
                if not isinstance(target, str) or not target.strip() or target == cast_id:
                    errors.append(f"{relation_label} needs a different, non-empty targetId")
                else:
                    pending_targets.append((relation_label, target))
                kind = relation.get("kind")
                if kind not in VALID_RELATION_KIND:
                    errors.append(f"{relation_label} has invalid kind: {kind}")
                relation_status = relation.get("status")
                if relation_status not in VALID_RELATION_STATUS:
                    errors.append(f"{relation_label} has invalid status: {relation_status}")
                since = relation.get("sinceChapter")
                if not isinstance(since, int) or isinstance(since, bool) or not 0 <= since <= as_of:
                    errors.append(f"{relation_label} has invalid sinceChapter")
                if not is_concrete(relation.get("basis")):
                    errors.append(f"{relation_label} needs a concrete basis")
                if kind == "love" and not is_concrete(relation.get("cost")):
                    errors.append(f"{relation_label} needs a concrete cost so love is not a free label or reward")
                evidence = relation.get("evidenceChapters", [])
                if not isinstance(evidence, list) or not all(
                    isinstance(chapter, int) and not isinstance(chapter, bool) and 0 <= chapter <= as_of for chapter in evidence
                ):
                    errors.append(f"{relation_label} evidenceChapters must contain valid chapter numbers")
                elif kind == "love" and isinstance(since, int) and since > 0 and not evidence:
                    errors.append(f"{relation_label} needs evidenceChapters for love established after chapter 0")

    for relation_label, target in pending_targets:
        if target != "protagonist" and target not in ids:
            errors.append(f"{relation_label} references unknown targetId: {target}")
    anchor_limit = 3 if mode == "fanqie-short-story" else 5
    if active_anchors > anchor_limit:
        warnings.append(f"High anchor-cast load: {active_anchors}; merge arcs or demote characters that do not need full trajectories")
    if mode == "serial" and isinstance(committed, int) and committed - legacy_through >= 5 and not any(
        isinstance(character, dict)
        and character.get("tier") == "anchor"
        and isinstance(character.get("introducedChapter"), int)
        and character["introducedChapter"] <= committed
        for character in characters
    ):
        errors.append("By five audited chapters, the project needs at least one anchor supporting character with an independent arc")
    if mode == "serial" and isinstance(committed, int) and committed - legacy_through >= 5 and active_anchors:
        recent_start = max(legacy_through + 1, committed - 4)
        if not any(recent_start <= chapter <= committed for chapter in recent_arc_chapters):
            warnings.append(f"No supporting-cast choice/consequence advanced in chapters {recent_start}-{committed}")
    if mode == "serial" and isinstance(committed, int) and committed - legacy_through >= 15:
        cycle_start = committed - 14
        if not any(cycle_start <= chapter <= committed for chapter in anchor_arc_chapters):
            errors.append(f"At least one anchor supporting character must advance by choice/consequence in chapters {cycle_start}-{committed}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    root = args.project.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"Missing {relative}")
    for relative in ("chapters", "reviews", "sessions"):
        if not (root / relative).is_dir():
            errors.append(f"Missing directory {relative}/")
    if errors:
        print(json.dumps({"ok": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 1

    project = load_json(root / "project.json", errors)
    state = load_json(root / "state/story-state.json", errors)
    thread_doc = load_json(root / "state/threads.json", errors)
    reward_doc = load_json(root / "state/rewards.json", errors)
    cast_doc = load_json(root / "state/cast-arcs.json", errors)
    decision_doc = load_json(root / "state/decisions.json", errors)

    if project.get("schemaVersion") != CURRENT_PROJECT_SCHEMA:
        errors.append(f"project.json schemaVersion must be {CURRENT_PROJECT_SCHEMA}; run migrate_project.py for older projects")
    if reward_doc.get("schemaVersion") != CURRENT_REWARD_SCHEMA:
        errors.append(f"rewards.json schemaVersion must be {CURRENT_REWARD_SCHEMA}; run migrate_project.py for older projects")

    mode = story_mode(project)
    if mode not in VALID_STORY_MODES:
        errors.append(f"project.json storyMode is invalid: {mode}")
    short_story = project.get("shortStory")
    planned_sections = None
    short_status = None
    target_total = None
    if mode == "fanqie-short-story":
        if not isinstance(short_story, dict):
            errors.append("fanqie-short-story project needs shortStory settings")
            short_story = {}
        target_total = short_story.get("targetTotalChars")
        if target_total is not None and (
            not isinstance(target_total, int) or isinstance(target_total, bool) or target_total <= 0
        ):
            errors.append("shortStory.targetTotalChars must be null or a positive integer")
        planned_sections = short_story.get("plannedSections")
        if (
            not isinstance(planned_sections, int)
            or isinstance(planned_sections, bool)
            or not 1 <= planned_sections <= 300
        ):
            errors.append("shortStory.plannedSections must be between 1 and 300")
            planned_sections = None
        short_status = short_story.get("status")
        if short_status not in {"planning", "drafting", "complete"}:
            errors.append(f"shortStory.status is invalid: {short_status}")
        if short_story.get("endingType") not in {"closed", "open"}:
            errors.append("shortStory.endingType must be closed or open")

    style = project.get("styleProfile")
    style_primary = None
    style_status = None
    if not isinstance(style, dict):
        errors.append("project.json needs styleProfile")
    else:
        style_primary = style.get("primary")
        style_secondary = style.get("secondary")
        style_status = style.get("status")
        if not isinstance(style_primary, str) or not style_primary.strip():
            errors.append("styleProfile.primary must be a non-empty string")
        if style_secondary is not None and (not isinstance(style_secondary, str) or not style_secondary.strip()):
            errors.append("styleProfile.secondary must be null or a non-empty string")
        if style_secondary == style_primary:
            errors.append("styleProfile.secondary must differ from styleProfile.primary")
        if style_status not in {"unconfirmed", "active", "observed"}:
            errors.append(f"styleProfile.status is invalid: {style_status}")
        if not isinstance(style.get("updatedAt"), str) or not style["updatedAt"].strip():
            errors.append("styleProfile.updatedAt must be a non-empty timestamp string")

    style_text = (root / "canon/style-profile.md").read_text(encoding="utf-8")
    if style_status in {"active", "observed"}:
        if f"- 状态：`{style_status}`" not in style_text:
            errors.append("canon/style-profile.md status does not match project.json")
        if isinstance(style_primary, str) and f"- 主风格：`{style_primary}`" not in style_text:
            errors.append("canon/style-profile.md primary style does not match project.json")

    title = project.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("project.json title must be a non-empty string")
        title = ""
    package = project.get("publishingPackage")
    package_status = None
    if not isinstance(package, dict):
        errors.append("project.json needs publishingPackage")
    else:
        package_status = package.get("status")
        allowed_package_values = {
            "active": ("confirmed", "completed", "ready"),
            "legacy": ("legacy", "legacy-unverified", "legacy-existing"),
            "unconfirmed": ("unconfirmed", "unconfirmed", "unconfirmed"),
        }
        if package_status not in allowed_package_values:
            errors.append(f"publishingPackage.status is invalid: {package_status}")
        else:
            expected = allowed_package_values[package_status]
            actual = (package.get("titleStatus"), package.get("uniquenessStatus"), package.get("coverPromptStatus"))
            if actual != expected:
                errors.append(f"publishingPackage status fields do not match {package_status}: {actual}")
        if not isinstance(package.get("updatedAt"), str) or not package["updatedAt"].strip():
            errors.append("publishingPackage.updatedAt must be a non-empty timestamp string")

    package_text = (root / "canon/publishing-package.md").read_text(encoding="utf-8")
    if package_status in {"active", "legacy"}:
        if f"- 包装状态：`{package_status}`" not in package_text:
            errors.append("canon/publishing-package.md status does not match project.json")
        if title and f"- 小说名：{title}" not in package_text:
            errors.append("canon/publishing-package.md title does not match project.json")
    if package_status == "active":
        for marker in ("- 定名状态：`confirmed`", "- 唯一性检查：`completed`", "- 封面提示词状态：`ready`"):
            if marker not in package_text:
                errors.append(f"canon/publishing-package.md is missing active marker: {marker}")
        layout_heading = "## 书名排版与字体说明"
        if layout_heading not in package_text:
            errors.append("canon/publishing-package.md is missing title layout and typography instructions")
        else:
            layout_text = package_text.split(layout_heading, 1)[1]
            for required_term in ("位置", "字体", "字色"):
                if required_term not in layout_text:
                    errors.append(f"canon/publishing-package.md title layout is missing {required_term} guidance")
        title_result = analyze_title(title)
        errors.extend(f"Title quality: {message}" for message in title_result["errors"])
        warnings.extend(f"Title quality: {message}" for message in title_result["warnings"])

    validate_market_research(root, project, errors, warnings)

    committed = project.get("lastCommittedChapter")
    draft = project.get("latestDraftChapter")
    as_of = state.get("asOfChapter")
    threads_as_of = thread_doc.get("asOfChapter")
    rewards_as_of = reward_doc.get("asOfChapter")
    cast_as_of = cast_doc.get("asOfChapter")
    chapter_files: dict[int, Path] = {}
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in (committed, draft, as_of, threads_as_of, rewards_as_of, cast_as_of)):
        errors.append("Chapter counters must be non-negative integers")
    else:
        if committed > draft:
            errors.append("lastCommittedChapter cannot exceed latestDraftChapter")
        if as_of != committed or threads_as_of != committed or rewards_as_of != committed or cast_as_of != committed:
            errors.append("Committed chapter must match story-state, threads, rewards, and cast-arcs snapshots")
        if draft > committed:
            warnings.append(f"Chapter {draft} has draft content not fully committed to state")

        for path in (root / "chapters").glob("*.md"):
            match = CHAPTER_RE.match(path.name)
            if not match:
                warnings.append(f"Chapter filename does not match 第NNNN章-标题.md: {path.name}")
                continue
            number = int(match.group(1))
            if number in chapter_files:
                errors.append(f"Multiple chapter files use chapter number {number}")
            else:
                chapter_files[number] = path
        missing = [number for number in range(1, committed + 1) if number not in chapter_files]
        if missing:
            preview = ", ".join(str(number) for number in missing[:10])
            suffix = "..." if len(missing) > 10 else ""
            errors.append(f"Missing committed chapter file(s): {preview}{suffix}")
        if draft > 0 and draft not in chapter_files:
            errors.append(f"latestDraftChapter {draft} has no matching chapter file")
        total_content_chars = project.get("totalContentChars")
        if not isinstance(total_content_chars, int) or isinstance(total_content_chars, bool) or total_content_chars < 0:
            errors.append("project.json totalContentChars must be a non-negative integer")
        elif not missing:
            measured_total = sum(content_char_count(chapter_files[number].read_text(encoding="utf-8")) for number in range(1, committed + 1))
            if total_content_chars != measured_total:
                errors.append(f"project.json totalContentChars is {total_content_chars}, but committed chapters contain {measured_total}")
        if committed > 0:
            if style_status == "unconfirmed" or style_primary == "unselected":
                errors.append("Committed project must confirm a language style profile")
            if package_status == "unconfirmed":
                errors.append("Committed project must confirm its title and provide a cover prompt before prose")
            for relative in CORE_TEXT_FILES:
                content = (root / relative).read_text(encoding="utf-8")
                markers = [marker for marker in UNRESOLVED_MARKERS if marker in content]
                if markers:
                    errors.append(f"Committed project still has unresolved marker(s) in {relative}: {', '.join(markers)}")

        if mode == "fanqie-short-story" and isinstance(planned_sections, int):
            if committed > 0 and target_total is None:
                errors.append("Short story needs shortStory.targetTotalChars before the first section is committed")
            if short_status == "planning" and committed > 0:
                errors.append("shortStory.status must change from planning to drafting before the first section is committed")
            if committed > planned_sections:
                errors.append("Committed short-story sections exceed shortStory.plannedSections")
            if short_status == "complete" and committed != planned_sections:
                errors.append("Completed short story must commit exactly shortStory.plannedSections sections")

    validate_chapter_reviews(root, project, chapter_files, committed, decision_doc, errors)
    validate_final_review(root, project, chapter_files, committed, mode, short_status, errors)

    seen: set[str] = set()
    active = 0
    thread_items = thread_doc.get("threads", [])
    if not isinstance(thread_items, list):
        errors.append("threads.json field 'threads' must be an array")
        thread_items = []
    for index, thread in enumerate(thread_items):
        if not isinstance(thread, dict):
            errors.append(f"Thread #{index + 1} is not an object")
            continue
        thread_id = thread.get("id")
        if not isinstance(thread_id, str) or not thread_id.strip():
            errors.append(f"Thread #{index + 1} has no id")
        elif thread_id in seen:
            errors.append(f"Duplicate thread id: {thread_id}")
        else:
            seen.add(thread_id)
        status = thread.get("status")
        if status not in VALID_THREAD_STATUS:
            errors.append(f"Thread {thread_id or index + 1} has invalid status: {status}")
        kind = thread.get("kind")
        if kind not in VALID_THREAD_KIND:
            errors.append(f"Thread {thread_id or index + 1} has invalid kind: {kind}")
        opened = thread.get("openedChapter")
        last = thread.get("lastAdvancedChapter")
        if not isinstance(opened, int) or isinstance(opened, bool) or opened < 0:
            errors.append(f"Thread {thread_id or index + 1} needs a non-negative openedChapter")
        if not isinstance(last, int) or isinstance(last, bool) or last < 0:
            errors.append(f"Thread {thread_id or index + 1} needs a non-negative lastAdvancedChapter")
        if isinstance(threads_as_of, int):
            if isinstance(opened, int) and opened > threads_as_of:
                errors.append(f"Thread {thread_id or index + 1} opens after the state snapshot")
            if isinstance(last, int) and last > threads_as_of:
                errors.append(f"Thread {thread_id or index + 1} advances after the state snapshot")
        if status in {"open", "advanced", "deferred"}:
            active += 1
            window = thread.get("dueWindow")
            if not (isinstance(window, list) and len(window) == 2 and all(isinstance(v, int) and not isinstance(v, bool) for v in window)):
                errors.append(f"Active thread {thread_id or index + 1} needs integer dueWindow [start, end]")
            else:
                if window[0] <= 0 or window[0] > window[1]:
                    errors.append(f"Thread {thread_id or index + 1} has invalid dueWindow order")
                elif isinstance(committed, int) and committed > window[1]:
                    warnings.append(f"Thread {thread_id} is overdue; advance, defer with a new window, transform, or resolve it")
            if isinstance(committed, int) and isinstance(last, int) and committed - last > 8:
                warnings.append(f"Thread {thread_id} has not advanced for {committed - last} chapters")

    active_limit = 3 if mode == "fanqie-short-story" else 8
    if active > active_limit:
        warnings.append(f"High active-thread load: {active}; resolve, merge, or defer before opening more")
    if mode == "fanqie-short-story" and short_status == "complete" and active:
        errors.append("Completed short story cannot retain open, advanced, or deferred threads")

    validate_cast_arcs(cast_doc, committed, mode, errors, warnings)
    validate_ensemble(root, project, committed, errors)

    cadence = project.get("rewardCadence")
    if not isinstance(cadence, dict):
        errors.append("project.json needs rewardCadence")
        cadence = {}
    small_every = cadence.get("smallEvery")
    major_every = cadence.get("majorEvery")
    supercycle = cadence.get("supercycle")
    overlap = cadence.get("overlapPolicy")
    enforce_from = cadence.get("enforceFromChapter")
    if not isinstance(small_every, int) or isinstance(small_every, bool) or small_every <= 0:
        errors.append("rewardCadence.smallEvery must be a positive integer")
    if not isinstance(major_every, int) or isinstance(major_every, bool) or major_every <= 0:
        errors.append("rewardCadence.majorEvery must be a positive integer")
    if not isinstance(supercycle, int) or isinstance(supercycle, bool) or supercycle <= 0:
        errors.append("rewardCadence.supercycle must be a positive integer")
    elif isinstance(small_every, int) and small_every > 0 and isinstance(major_every, int) and major_every > 0:
        expected_supercycle = math.lcm(small_every, major_every)
        if supercycle != expected_supercycle:
            errors.append(f"rewardCadence.supercycle must equal lcm(smallEvery, majorEvery): {expected_supercycle}")
    if overlap != "major-absorbs-small":
        errors.append("rewardCadence.overlapPolicy must be major-absorbs-small")
    if not isinstance(enforce_from, int) or isinstance(enforce_from, bool) or enforce_from <= 0:
        errors.append("rewardCadence.enforceFromChapter must be a positive integer")

    legacy_through = reward_doc.get("legacyUnauditedThrough", 0)
    if not isinstance(legacy_through, int) or isinstance(legacy_through, bool) or legacy_through < 0:
        errors.append("rewards.json legacyUnauditedThrough must be a non-negative integer")
        legacy_through = 0
    elif legacy_through:
        warnings.append(f"Legacy chapters through {legacy_through} have not been fully audited against the v2 reward ledger")
        if isinstance(enforce_from, int) and enforce_from <= legacy_through:
            errors.append("rewardCadence.enforceFromChapter must be after legacyUnauditedThrough")

    if isinstance(committed, int) and committed > legacy_through:
        session_pattern = f"*chapter-{committed:04d}*.md"
        if not any((root / "sessions").glob(session_pattern)):
            errors.append(f"Committed chapter {committed} needs a matching sessions/{session_pattern} handoff record")

    beats = reward_doc.get("beats", [])
    if not isinstance(beats, list):
        errors.append("rewards.json field 'beats' must be an array")
        beats = []
    beat_by_chapter: dict[int, dict] = {}
    pattern_sequences: dict[str, list[tuple[int, str, str, str]]] = {"small": [], "major": []}
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            errors.append(f"Reward beat #{index + 1} is not an object")
            continue
        chapter = beat.get("chapter")
        level = beat.get("level")
        status = beat.get("status")
        label = chapter if isinstance(chapter, int) else index + 1
        if not isinstance(chapter, int) or isinstance(chapter, bool) or chapter <= 0:
            errors.append(f"Reward beat #{index + 1} needs a positive chapter")
            continue
        if chapter in beat_by_chapter:
            errors.append(f"Multiple reward beats for chapter {chapter}; overlap chapters need one major beat")
        else:
            beat_by_chapter[chapter] = beat
        if level not in VALID_REWARD_LEVEL:
            errors.append(f"Reward beat {label} has invalid level: {level}")
        if status not in VALID_REWARD_STATUS:
            errors.append(f"Reward beat {label} has invalid status: {status}")

        reward_type = beat.get("rewardType")
        if reward_type == "unassigned":
            if status != "planned":
                errors.append(f"Reward beat {chapter} may use rewardType unassigned only while planned")
        elif reward_type not in VALID_REWARD_TYPE:
            errors.append(f"Reward beat {chapter} has invalid rewardType: {reward_type}")

        if status == "planned" and isinstance(rewards_as_of, int) and chapter <= rewards_as_of:
            errors.append(f"Reward beat {chapter} is still planned at or before the rewards snapshot")
        if status == "needs-review":
            if chapter > legacy_through:
                errors.append(f"Reward beat {chapter} may use needs-review only within the legacy unaudited range")
            continue
        if status != "delivered":
            if level in VALID_REWARD_LEVEL and reward_type in VALID_REWARD_TYPE:
                conflict = beat.get("conflictType")
                solution = beat.get("solutionType")
                if is_concrete(conflict) and is_concrete(solution):
                    pattern_sequences[level].append((chapter, reward_type, conflict.strip(), solution.strip()))
            continue

        if isinstance(rewards_as_of, int) and chapter > rewards_as_of:
            errors.append(f"Reward beat {chapter} is delivered after the rewards snapshot")
        if not is_concrete(beat.get("payoff")):
            errors.append(f"Delivered reward beat {chapter} needs a concrete payoff")

        setup = beat.get("setupChapters")
        if not isinstance(setup, list):
            errors.append(f"Delivered reward beat {chapter} setupChapters must be an array")
        else:
            seen_setup: set[int] = set()
            for setup_chapter in setup:
                if not isinstance(setup_chapter, int) or isinstance(setup_chapter, bool) or setup_chapter <= 0 or setup_chapter >= chapter:
                    errors.append(f"Delivered reward beat {chapter} has invalid prior setup chapter: {setup_chapter}")
                elif setup_chapter in seen_setup:
                    errors.append(f"Delivered reward beat {chapter} repeats setup chapter {setup_chapter}")
                else:
                    seen_setup.add(setup_chapter)
                    if setup_chapter not in chapter_files:
                        errors.append(f"Delivered reward beat {chapter} references missing setup chapter {setup_chapter}")

        evidence = validate_string_list(beat.get("evidence"), f"Delivered reward beat {chapter} evidence", errors, minimum=1)
        chapter_path = chapter_files.get(chapter)
        chapter_text = chapter_path.read_text(encoding="utf-8") if chapter_path else None
        if chapter_text is None:
            errors.append(f"Delivered reward beat {chapter} has no chapter file for evidence checking")
        for snippet in evidence:
            if not 6 <= len(snippet) <= 120:
                errors.append(f"Delivered reward beat {chapter} evidence must be 6-120 characters: {snippet!r}")
            elif chapter_text is not None and snippet not in chapter_text:
                errors.append(f"Delivered reward beat {chapter} evidence is not an exact chapter substring: {snippet!r}")

        minimum_deltas = 2 if level == "major" else 1
        deltas = validate_string_list(
            beat.get("stateDeltas"),
            f"Delivered {level} reward beat {chapter} stateDeltas",
            errors,
            minimum=minimum_deltas,
        )
        for delta in deltas:
            if not is_concrete(delta):
                errors.append(f"Delivered reward beat {chapter} has a non-concrete state delta: {delta!r}")
        if level == "major" and not is_concrete(beat.get("cost")):
            errors.append(f"Delivered major reward beat {chapter} needs a concrete cost")

        source_ids = validate_string_list(beat.get("sourceThreadIds"), f"Delivered reward beat {chapter} sourceThreadIds", errors)
        for thread_id in source_ids:
            if thread_id not in seen:
                errors.append(f"Delivered reward beat {chapter} references unknown thread id: {thread_id}")
        conflict = beat.get("conflictType")
        solution = beat.get("solutionType")
        if not is_concrete(conflict):
            errors.append(f"Delivered reward beat {chapter} needs a concrete conflictType")
        if not is_concrete(solution):
            errors.append(f"Delivered reward beat {chapter} needs a concrete solutionType")
        if level in VALID_REWARD_LEVEL and reward_type in VALID_REWARD_TYPE and is_concrete(conflict) and is_concrete(solution):
            pattern_sequences[level].append((chapter, reward_type, conflict.strip(), solution.strip()))

    for level, sequence in pattern_sequences.items():
        sequence.sort(key=lambda item: item[0])
        for previous, current in zip(sequence, sequence[1:]):
            if previous[1:] == current[1:]:
                errors.append(
                    f"Consecutive {level} reward beats {previous[0]} and {current[0]} repeat the same conflictType + solutionType + rewardType pattern"
                )
        for first, second, third in zip(sequence, sequence[1:], sequence[2:]):
            if first[1] == second[1] == third[1]:
                warnings.append(
                    f"Three consecutive {level} reward beats {first[0]}, {second[0]}, and {third[0]} use rewardType {first[1]}"
                )

    cadence_valid = all(
        isinstance(value, int) and not isinstance(value, bool) and value > 0
        for value in (small_every, major_every, enforce_from)
    )
    if mode == "serial" and isinstance(committed, int) and cadence_valid:
        for chapter in range(enforce_from, committed + 1):
            required = "major" if chapter % major_every == 0 else ("small" if chapter % small_every == 0 else None)
            if required is None:
                continue
            beat = beat_by_chapter.get(chapter)
            if not beat or beat.get("status") != "delivered":
                errors.append(f"Chapter {chapter} is missing its delivered {required} reward beat")
            elif required == "major" and beat.get("level") != "major":
                errors.append(f"Chapter {chapter} requires a major reward beat")
            elif required == "small" and beat.get("level") not in {"small", "major"}:
                errors.append(f"Chapter {chapter} requires at least a small reward beat")

        future_start = max(committed + 1, enforce_from)
        for chapter in range(future_start, future_start + 10):
            required = "major" if chapter % major_every == 0 else ("small" if chapter % small_every == 0 else None)
            if required is None:
                continue
            beat = beat_by_chapter.get(chapter)
            if not beat:
                warnings.append(f"Rolling outline has no planned {required} reward beat for chapter {chapter}")
            elif required == "major" and beat.get("level") != "major":
                warnings.append(f"Planned reward for chapter {chapter} must be major")
    elif mode == "fanqie-short-story" and isinstance(committed, int) and isinstance(planned_sections, int):
        anchors = short_story_anchors(planned_sections)
        for chapter, anchor in anchors.items():
            required = anchor["reward"]
            if required is None:
                continue
            beat = beat_by_chapter.get(chapter)
            if chapter <= committed:
                if not beat or beat.get("status") != "delivered":
                    errors.append(f"Short-story structural anchor at section {chapter} is missing its delivered {required} reward beat")
                elif required == "major" and beat.get("level") != "major":
                    errors.append(f"Short-story structural anchor at section {chapter} requires a major reward beat")
                elif required == "small" and beat.get("level") not in {"small", "major"}:
                    errors.append(f"Short-story structural anchor at section {chapter} requires at least a small reward beat")
            elif not beat:
                warnings.append(f"Short-story outline has no planned {required} reward beat for structural section {chapter}")
            elif required == "major" and beat.get("level") != "major":
                warnings.append(f"Planned short-story reward for section {chapter} must be major")

    decisions = decision_doc.get("decisions", [])
    if not isinstance(decisions, list):
        errors.append("decisions.json field 'decisions' must be an array")
        decisions = []
    pending = [decision for decision in decisions if isinstance(decision, dict) and decision.get("status") == "pending"]
    if pending:
        warnings.append(f"{len(pending)} major decision(s) await author confirmation")

    result = {"ok": not errors, "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

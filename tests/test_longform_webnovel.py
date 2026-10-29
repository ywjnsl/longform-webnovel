#!/usr/bin/env python3
"""Integration checks for the staged longform-webnovel v8 skill."""

from __future__ import annotations

import hashlib
import json
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skill" / "longform-webnovel" / "scripts"
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
ASCII_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(args, check=False, text=True, capture_output=True)
    if completed.returncode != expect:
        raise AssertionError(
            f"Expected exit {expect}, got {completed.returncode}: {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def content_chars(text: str) -> int:
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    body = "\n".join(lines)
    return len(CJK_RE.findall(body)) + len(ASCII_WORD_RE.findall(body))


def initialize(path: Path, title: str, *, mode: str = "serial") -> None:
    run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(path), "--title", title, "--style", "fanqie-clean", "--mode", mode)
    for relative in (
        "canon/story-contract.md",
        "canon/characters.md",
        "canon/world.md",
        "canon/laws.md",
        "planning/current-volume.md",
        "planning/rolling-outline.md",
        "planning/current-arc.md",
    ):
        (path / relative).write_text(f"# {relative}\n\n测试项目已有明确内容。\n", encoding="utf-8")
    project = read_json(path / "project.json")
    project["publishingPackage"] = {
        "status": "active",
        "titleStatus": "confirmed",
        "uniquenessStatus": "completed",
        "coverPromptStatus": "ready",
        "updatedAt": project["createdAt"],
    }
    write_json(path / "project.json", project)
    (path / "canon/publishing-package.md").write_text(
        "# 书名与封面包装\n\n"
        "- 包装状态：`active`\n"
        "- 定名状态：`confirmed`\n"
        "- 唯一性检查：`completed`\n"
        "- 封面提示词状态：`ready`\n"
        f"- 小说名：{title}\n\n"
        "## 封面主提示词\n\n测试用的独特封面构图和主体。\n\n"
        "## 书名排版与字体说明\n\n"
        "书名位置在上方安全区，字体使用思源宋体 Heavy，字色为暖白并配深色描边。\n",
        encoding="utf-8",
    )
    cast_doc = read_json(path / "state/cast-arcs.json")
    cast_doc["characters"] = [
        {
            "id": "anchor-test",
            "name": "测试配角",
            "tier": "anchor",
            "narrativeRole": "ally",
            "status": "active",
            "arcPhase": "setup",
            "introducedChapter": 0,
            "lastAdvancedChapter": 0,
            "ownWant": "守住自己负责的旧档案室",
            "independentGoal": "查清失窃档案的真正去向",
            "privateConstraint": "公开调查会使家人失去庇护",
            "nextTurnWindow": [1, 15],
            "history": [],
            "relationships": [],
        }
    ]
    write_json(path / "state/cast-arcs.json", cast_doc)


def create_legacy_project(path: Path) -> None:
    initialize(path, "旧项目")
    project = read_json(path / "project.json")
    project["schemaVersion"] = 1
    project.pop("styleProfile", None)
    project.pop("publishingPackage", None)
    project.pop("marketResearch", None)
    project.pop("reviewGate", None)
    project["lastCommittedChapter"] = 3
    project["latestDraftChapter"] = 3
    project["rewardCadence"] = {"smallEvery": 3, "majorEvery": 5, "overlapPolicy": "major-absorbs-small"}
    write_json(path / "project.json", project)
    (path / "canon/style-profile.md").unlink()
    (path / "canon/publishing-package.md").unlink()
    (path / "canon/market-brief.md").unlink()
    (path / "state/cast-arcs.json").unlink()
    for relative in ("state/story-state.json", "state/threads.json"):
        document = read_json(path / relative)
        document["asOfChapter"] = 3
        write_json(path / relative, document)
    rewards = {
        "schemaVersion": 1,
        "asOfChapter": 3,
        "beats": [
            {
                "chapter": 3,
                "level": "small",
                "status": "delivered",
                "payoff": "旧版只记了一句结果",
                "stateDeltas": ["主角拿到线索"],
            }
        ],
    }
    write_json(path / "state/rewards.json", rewards)
    for chapter in range(1, 4):
        (path / "chapters" / f"第{chapter:04d}章-旧章.md").write_text(f"# 第{chapter}章\n\n旧正文第{chapter}章。\n", encoding="utf-8")


def make_beat(chapter: int, level: str, conflict: str, solution: str, *, evidence: str | None = None) -> dict:
    snippet = evidence or f"第{chapter}章的关键兑现终于落在众人眼前。"
    return {
        "chapter": chapter,
        "level": level,
        "status": "delivered",
        "role": "测试兑现",
        "rewardType": "truth",
        "payoff": f"第{chapter}章揭开关键真相并改变局面",
        "setupChapters": [chapter - 1] if chapter > 1 else [],
        "evidence": [snippet],
        "cost": "对手因此改变策略并锁定主角" if level == "major" else "",
        "stateDeltas": ["公开信息发生变化", "对手行动升级"] if level == "major" else ["主角获得有效情报"],
        "sourceThreadIds": [],
        "conflictType": conflict,
        "solutionType": solution,
    }


def prepare_stage(
    project_root: Path,
    stage: Path,
    chapter: int,
    beat: dict | None = None,
    *,
    body_evidence: str | None = None,
    overwrite_first: bool = False,
) -> None:
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    project = read_json(project_root / "project.json")
    project["lastCommittedChapter"] = chapter
    project["latestDraftChapter"] = chapter

    for relative in ("state/story-state.json", "state/threads.json", "state/rewards.json", "state/cast-arcs.json"):
        document = read_json(project_root / relative)
        document["asOfChapter"] = chapter
        if relative == "state/rewards.json" and beat is not None:
            document["beats"].append(beat)
        write_json(stage / relative, document)

    snippet = body_evidence or f"第{chapter}章的关键兑现终于落在众人眼前。"
    chapter_path = stage / "chapters" / f"第{chapter:04d}章-测试章.md"
    chapter_path.parent.mkdir(parents=True, exist_ok=True)
    chapter_text = f"# 第{chapter}章\n\n局面持续推进。{snippet}\n"
    chapter_path.write_text(chapter_text, encoding="utf-8")
    review_dir = stage / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    run(
        sys.executable,
        str(SCRIPTS / "prose_lint.py"),
        str(chapter_path),
        "--output",
        str(review_dir / f"第{chapter:04d}章-lint.json"),
    )
    digest = hashlib.sha256(chapter_text.encode("utf-8")).hexdigest()
    previous = sorted(
        (int(match.group(1)), path)
        for path in (project_root / "chapters").glob("第*章-*.md")
        if (match := re.match(r"^第(\d{4,})章-.+\.md$", path.name))
        and int(match.group(1)) < chapter
    )
    compared = previous if project.get("storyMode") == "fanqie-short-story" else previous[-5:]
    write_json(
        review_dir / f"第{chapter:04d}章-repetition.json",
        {
            "schemaVersion": 1,
            "chapter": chapter,
            "reviewedTextSha256": digest,
            "claim": "editorial-repetition-signals-not-authorship-detection",
            "scopeFiles": [
                f"chapters/{chapter_path.name}",
                *(f"chapters/{path.name}" for _, path in compared),
            ],
            "thresholds": {
                "exactMinChars": 14,
                "nearMinChars": 18,
                "nearJaccard": 0.82,
            },
            "status": "pass",
            "findings": [],
        },
    )
    write_json(
        review_dir / f"第{chapter:04d}章-review.json",
        {
            "schemaVersion": 1,
            "chapter": chapter,
            "reviewedTextSha256": digest,
            "naturalness": {
                "status": "pass",
                "diagnosis": "未发现影响沉浸的自然度问题簇。",
                "reviewedTextSha256": digest,
                "findings": [],
                "revision": {
                    "action": "not-needed",
                    "notes": "没有证据支持额外修改。",
                },
            },
            "editor": {
                "status": "pass",
                "diagnosis": "本章因果清楚，兑现证据与下一步行动能够衔接。",
                "strengths": ["关键兑现落在可见行动上"],
                "findings": [],
            },
            "reader": {
                "status": "engaged",
                "persona": "偏好快节奏悬念与明确阶段回报的移动端读者",
                "completionIntent": "continue",
                "moments": [
                    {
                        "evidence": snippet,
                        "reaction": "兑现清楚，愿意继续确认它带来的后果。",
                        "channel": "curiosity",
                        "valence": "positive",
                    }
                ],
                "openQuestions": ["对手会怎样回应这次局面变化"],
            },
            "resolution": {"action": "accepted", "notes": "测试夹具模拟通过结论，不代表真实独立审阅。"},
        },
    )
    project["totalContentChars"] = project.get("totalContentChars", 0) + content_chars(chapter_text)
    if overwrite_first:
        replacement = "# 被预览替换，但不应污染正式项目\n\n替换后的正文仍然有效。\n"
        original = (project_root / "chapters" / "第0001章-测试章.md").read_text(encoding="utf-8")
        (stage / "chapters" / "第0001章-测试章.md").write_text(replacement, encoding="utf-8")
        project["totalContentChars"] += content_chars(replacement) - content_chars(original)
    write_json(stage / "project.json", project)
    session = stage / "sessions" / f"test-chapter-{chapter:04d}.md"
    session.parent.mkdir(parents=True, exist_ok=True)
    session.write_text(f"# 第 {chapter} 章交接\n\n状态已同步。\n", encoding="utf-8")
    write_ensemble_stage(project_root, stage, chapter)


def write_ensemble_stage(project_root: Path, stage: Path, chapter: int) -> None:
    """群像强制章提交时附带合同、意图、裁判和当前弧。"""
    ensemble = read_json(project_root / "project.json").get("ensemble") or {}
    if ensemble.get("enabled") is False:
        return
    enforce_from = ensemble.get("enforceFromChapter", 1)
    if not isinstance(enforce_from, int) or chapter < enforce_from:
        return
    protagonist_id = str(ensemble.get("protagonistId") or "main")
    write_json(
        stage / "contracts" / f"chapter-{chapter:04d}.json",
        {
            "chapter": chapter,
            "arcId": "test-arc",
            "arcGoal": "推进测试局面",
            "arcStatus": "open",
            "estimatedChapters": [1, 8],
            "thisChapterMust": "推进或加压一格",
            "legalOutcomes": ["progress", "setback", "reroute", "expose", "pause-with-scar"],
            "illegalOutcomes": ["status-quo"],
            "explorationBeats": 3,
            "onStage": [protagonist_id],
            "payoffLevel": "none",
            "publicFactsForCast": ["测试场面已经开场"],
        },
    )
    write_json(
        stage / "intents" / f"chapter-{chapter:04d}" / f"{protagonist_id}.json",
        {
            "characterId": protagonist_id,
            "chapter": chapter,
            "beat": 1,
            "emotion": {
                "from": "冷静",
                "to": "更急",
                "trigger": "对手逼近档案室",
                "shown": "少话",
            },
            "wantNow": "先确认档案还在不在",
            "wouldDo": "绕到侧门查看",
            "wouldSay": ["先别进去。"],
            "wouldNeverSay": ["我知道结局"],
        },
    )
    write_json(
        stage / "intents" / f"chapter-{chapter:04d}" / "ruling.json",
        {"allowed": True, "vetoes": [], "offstage": []},
    )
    (stage / "planning").mkdir(parents=True, exist_ok=True)
    shutil.copy2(project_root / "planning/current-arc.md", stage / "planning/current-arc.md")
    state_src = project_root / "cast" / protagonist_id / "state.json"
    if state_src.is_file():
        state = read_json(state_src)
        state["chapter"] = chapter
        state["emotion"] = {"label": "更急", "trigger": "对手逼近档案室", "shown": "少话"}
        write_json(stage / "cast" / protagonist_id / "state.json", state)


def commit(
    project: Path,
    stage: Path,
    *,
    dry_run: bool = False,
    allow_revision: bool = False,
    expect: int = 0,
) -> dict:
    args = [sys.executable, str(SCRIPTS / "commit_chapter.py"), "--project", str(project), "--staging", str(stage)]
    if dry_run:
        args.append("--dry-run")
    if allow_revision:
        args.append("--allow-revision")
    completed = run(*args, expect=expect)
    stream = completed.stdout if expect == 0 else completed.stderr
    return json.loads(stream)


def test_initialization_and_cadence(base: Path) -> None:
    project = base / "initial"
    initialize(project, "初始化测试")
    assert (project / "performance/snapshots").is_dir()
    assert (project / "research/reference-adaptations").is_dir()
    assert read_json(project / "project.json")["performanceFeedback"]["status"] == "unrequested"
    result = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert result["ok"]
    dry = json.loads(run(sys.executable, str(SCRIPTS / "plan_cadence.py"), str(project), "--count", "15", "--json").stdout)
    assert dry["chapters"] == []
    assert dry["spineCadence"]["smallEverySpineSegments"] == 3
    assert dry["spineCadence"]["majorEverySpineSegments"] == 5
    assert dry["spineCadence"]["sideExcludedUnlessPaysSpine"] is True
    written = json.loads(
        run(sys.executable, str(SCRIPTS / "plan_cadence.py"), str(project), "--count", "15", "--write", "--json").stdout
    )
    assert written["added"] == 0
    assert read_json(project / "state/rewards.json")["beats"] == []


def test_short_story_mode(base: Path) -> None:
    project = base / "short-story"
    run(
        sys.executable,
        str(SCRIPTS / "init_project.py"),
        "--path",
        str(project),
        "--title",
        "短故事模式测试",
        "--style",
        "fanqie-clean",
        "--mode",
        "fanqie-short-story",
        "--target-total-chars",
        "10000",
        "--sections",
        "5",
    )
    index = read_json(project / "project.json")
    assert index["storyMode"] == "fanqie-short-story"
    assert index["shortStory"] == {
        "targetTotalChars": 10000,
        "plannedSections": 5,
        "status": "planning",
        "endingType": "closed",
    }
    assert "短故事全文结构" in (project / "planning/current-volume.md").read_text(encoding="utf-8")

    planned = json.loads(run(sys.executable, str(SCRIPTS / "plan_cadence.py"), str(project), "--json").stdout)
    assert planned["mode"] == "fanqie-short-story"
    assert planned["count"] == 5
    assert max(row["chapter"] for row in planned["chapters"]) == 5
    assert "结局收束" in planned["chapters"][-1]["role"]
    assert planned["chapters"][-1]["reward"] == "major"
    single = json.loads(
        run(sys.executable, str(SCRIPTS / "plan_cadence.py"), str(project), "--count", "1", "--json").stdout
    )
    assert len(single["chapters"]) == 1
    assert "开局扰动" in single["chapters"][0]["role"] and "结局收束" in single["chapters"][0]["role"]
    assert single["chapters"][0]["reward"] == "major"
    written = json.loads(run(sys.executable, str(SCRIPTS / "plan_cadence.py"), str(project), "--write", "--json").stdout)
    assert written["added"] >= 2
    validation = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert validation["ok"]
    assert not any("chapter 15" in warning.lower() for warning in validation["warnings"])

    index = read_json(project / "project.json")
    index["shortStory"]["status"] = "complete"
    write_json(project / "project.json", index)
    incomplete = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("must commit exactly" in error for error in incomplete["errors"])
    index["shortStory"]["status"] = "planning"
    write_json(project / "project.json", index)

    index.pop("storyMode")
    index.pop("shortStory")
    write_json(project / "project.json", index)
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

    index["storyMode"] = "unknown-mode"
    write_json(project / "project.json", index)
    invalid = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("storyMode is invalid" in error for error in invalid["errors"])


def test_novella_mode(base: Path) -> None:
    raw = base / "novella-raw"
    run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(raw), "--title", "短中篇建项", "--mode", "novella")
    index = read_json(raw / "project.json")
    assert index["storyMode"] == "novella"
    assert index["finiteStory"] == {
        "targetTotalChars": 50000, "minTotalChars": None,
        "status": "planning", "endingType": "closed",
    }
    assert "shortStory" not in index
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(raw)).stdout)["ok"]
    rewards_before = (raw / "state/rewards.json").read_bytes()
    plan = json.loads(run(sys.executable, str(SCRIPTS / "plan_cadence.py"), str(raw), "--write", "--json").stdout)
    assert plan["mode"] == "novella" and len(plan["stages"]) == 5
    assert plan["chapters"] == [] and plan["added"] == 0
    assert (raw / "state/rewards.json").read_bytes() == rewards_before
    run(sys.executable, str(SCRIPTS / "plan_cadence.py"), str(raw), "--count", "20", expect=1)
    rejected = base / "novella-invalid"
    run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(rejected), "--title", "错误参数", "--mode", "novella", "--sections", "20", expect=1)
    assert not rejected.exists()
    run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(rejected), "--title", "错误下限", "--mode", "novella", "--target-total-chars", "30000", "--min-total-chars", "40000", expect=1)
    assert not rejected.exists()

    project = base / "novella-commit"
    initialize(project, "有限小说测试", mode="novella")
    index = read_json(project / "project.json")
    index["finiteStory"]["status"] = "drafting"
    write_json(project / "project.json", index)
    stage = base / "novella-stage"
    # Ordinary chapters, including chapter 3, need no numbered structural reward.
    for chapter in range(1, 4):
        prepare_stage(project, stage, chapter)
        assert commit(project, stage)["ok"]
    prepare_stage(project, stage, 4, make_beat(4, "major", "exposure", "evidence-reversal"))
    candidate = read_json(stage / "project.json")
    candidate["finiteStory"]["status"] = "complete"
    write_json(stage / "project.json", candidate)
    before = (project / "project.json").read_bytes()
    missing = commit(project, stage, expect=1)
    assert "final-review.json" in str(missing)
    assert (project / "project.json").read_bytes() == before

    digest = hashlib.sha256()
    for chapter in range(1, 5):
        parent = stage if chapter == 4 else project
        path = parent / "chapters" / f"第{chapter:04d}章-测试章.md"
        digest.update(f"chapter:{chapter:04d}:{path.name}\n".encode("utf-8"))
        digest.update(path.read_bytes())
    final = {
        "schemaVersion": 1, "storyMode": "novella", "reviewedThroughChapter": 4,
        "reviewedTextSha256": digest.hexdigest(), "perspective": "external-reader",
        "editorStatus": "pass", "readerStatus": "engaged", "completionIntent": "complete",
        "checks": {name: "pass" for name in (
            "promise", "causality", "continuity", "setupPayoff", "characterConsequences",
            "titleResonance", "endingBoundary", "subplots", "characterDestinations", "lengthContract",
        )},
        "resolution": "主承诺与人物归宿已收束，副线已闭合；测试未设置最低字数。",
    }
    write_json(stage / "reviews/final-review.json", final)
    candidate["finiteStory"]["minTotalChars"] = candidate["totalContentChars"] + 1
    write_json(stage / "project.json", candidate)
    too_short = commit(project, stage, expect=1)
    assert "below finiteStory.minTotalChars" in str(too_short)
    assert (project / "project.json").read_bytes() == before
    candidate["finiteStory"]["minTotalChars"] = 1
    write_json(stage / "project.json", candidate)
    final["checks"]["subplots"] = "fail"
    write_json(stage / "reviews/final-review.json", final)
    assert "subplots must be pass" in str(commit(project, stage, expect=1))
    final["checks"]["subplots"] = "pass"
    write_json(stage / "reviews/final-review.json", final)
    assert commit(project, stage)["ok"]
    assert read_json(project / "project.json")["lastCommittedChapter"] == 4
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

    # Ending evidence, full-text version, mode and thread closure all remain gates.
    rewards = read_json(project / "state/rewards.json")
    write_json(project / "state/rewards.json", {**rewards, "beats": []})
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("major ending reward" in error for error in errors)
    write_json(project / "state/rewards.json", rewards)
    bad_final = {**final, "storyMode": "fanqie-short-story", "reviewedTextSha256": "0" * 64}
    write_json(project / "reviews/final-review.json", bad_final)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("storyMode must be novella" in error for error in errors)
    assert any("hash does not match" in error for error in errors)
    write_json(project / "reviews/final-review.json", final)
    threads = read_json(project / "state/threads.json")
    write_json(project / "state/threads.json", {**threads, "threads": [{
        "id": "unclosed", "kind": "main", "status": "open", "summary": "尚未找到的证据",
        "introducedChapter": 1, "lastAdvancedChapter": 4, "dueWindow": [1, 4],
    }]})
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("cannot retain open" in error for error in errors)
    write_json(project / "state/threads.json", threads)
    prepare_stage(project, stage, 5)
    assert "cannot continue automatically" in str(commit(project, stage, expect=1))


def test_committed_project_guards(base: Path) -> None:
    project = base / "guard-errors"
    run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(project), "--title", "错误防线")
    chapter = project / "chapters" / "第0001章-未同步.md"
    chapter.write_text("# 第一章\n\n这里已经出现正文，但索引字数没有同步。\n", encoding="utf-8")
    index = read_json(project / "project.json")
    index["lastCommittedChapter"] = 1
    index["latestDraftChapter"] = 1
    write_json(project / "project.json", index)
    for relative in ("state/story-state.json", "state/rewards.json"):
        document = read_json(project / relative)
        document["asOfChapter"] = 1
        write_json(project / relative, document)
    threads = read_json(project / "state/threads.json")
    threads["asOfChapter"] = 1
    threads["threads"] = [
        {
            "id": "bad-window",
            "kind": "main",
            "status": "open",
            "openedChapter": 0,
            "lastAdvancedChapter": 0,
            "dueWindow": [0, 0],
        }
    ]
    write_json(project / "state/threads.json", threads)
    failed = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    joined = "\n".join(failed["errors"])
    assert "totalContentChars" in joined
    assert "unresolved marker" in joined
    assert "invalid dueWindow" in joined
    assert "handoff record" in joined


def test_style_profiles(base: Path) -> None:
    unselected = base / "style-unselected"
    run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(unselected), "--title", "待选风格")
    assert read_json(unselected / "project.json")["schemaVersion"] == 8
    assert read_json(unselected / "project.json")["ensemble"]["protagonistId"] == "main"
    assert (unselected / "cast/main/SKILL.md").is_file()
    assert read_json(unselected / "project.json")["styleProfile"]["status"] == "unconfirmed"
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(unselected)).stdout)["ok"]

    listed = json.loads(run(sys.executable, str(SCRIPTS / "style_profile.py"), "--list").stdout)
    assert len(listed) == 8 and listed["fanqie-clean"] == "清晰推进"
    shown = run(sys.executable, str(SCRIPTS / "style_profile.py"), "--show", "suspense-tight").stdout
    assert "冷峻悬疑" in shown and "公平可见" in shown

    before = (unselected / "project.json").read_text(encoding="utf-8")
    preview = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "style_profile.py"),
            "--project",
            str(unselected),
            "--primary",
            "suspense-tight",
            "--secondary",
            "lyrical-restrained",
            "--dry-run",
        ).stdout
    )
    assert preview["dryRun"] and (unselected / "project.json").read_text(encoding="utf-8") == before
    applied = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "style_profile.py"),
            "--project",
            str(unselected),
            "--primary",
            "suspense-tight",
            "--secondary",
            "lyrical-restrained",
        ).stdout
    )
    assert Path(applied["backup"]).is_dir()
    metadata = read_json(unselected / "project.json")["styleProfile"]
    assert metadata["primary"] == "suspense-tight" and metadata["secondary"] == "lyrical-restrained"
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(unselected)).stdout)["ok"]

    technique = base / "technique-card.md"
    technique.write_text(
        "- 参考范围：公开访谈与用户提供的短样章。\n"
        "- 核心功能：用克制对白承载权力试探，不复刻任何原句。\n"
        "- 叙事距离：第三人称限知，事实与判断分开。\n"
        "- 句式节奏：铺垫使用中句，转折落在短句。\n"
        "- 对白机制：答非所问暴露利益冲突，每场最多一次明显机锋。\n"
        "- 失控风险：金句过密、全员同声、为了留白省略必要因果。\n",
        encoding="utf-8",
    )
    custom = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "style_profile.py"),
            "--project",
            str(unselected),
            "--custom-id",
            "restrained-dialogue",
            "--custom-title",
            "克制对白",
            "--custom-file",
            str(technique),
        ).stdout
    )
    assert custom["primary"] == "custom:restrained-dialogue"
    assert "不复刻任何原句" in (unselected / "canon/style-profile.md").read_text(encoding="utf-8")
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(unselected)).stdout)["ok"]

    index = read_json(unselected / "project.json")
    index["lastCommittedChapter"] = 1
    write_json(unselected / "project.json", index)
    refused = run(
        sys.executable,
        str(SCRIPTS / "style_profile.py"),
        "--project",
        str(unselected),
        "--primary",
        "warm-grounded",
        expect=1,
    )
    assert "major decision" in refused.stderr
    confirmed = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "style_profile.py"),
            "--project",
            str(unselected),
            "--primary",
            "warm-grounded",
            "--confirmed",
        ).stdout
    )
    assert confirmed["primary"] == "warm-grounded"


def test_publishing_package(base: Path) -> None:
    project = base / "publishing"
    run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(project), "--title", "暂定书名", "--style", "suspense-tight")
    generic = json.loads(run(sys.executable, str(SCRIPTS / "publishing_package.py"), "--check-title", "重生归来").stdout)
    assert not generic["ok"] and generic["requiresPublicExactSearch"]
    distinctive = json.loads(run(sys.executable, str(SCRIPTS / "publishing_package.py"), "--check-title", "雾城收件人").stdout)
    assert distinctive["ok"]

    positioning = base / "positioning.txt"
    cover = base / "cover-prompt.txt"
    title_layout = base / "title-layout.txt"
    negative = base / "negative-prompt.txt"
    research = base / "title-research.txt"
    positioning.write_text("都市超自然悬疑：失踪邮件会提前一天寄到唯一能看见它们的人手中。", encoding="utf-8")
    cover.write_text(
        "中文网文竖版 2:3，无文字底图。雨夜旧城区的狭长邮局门口，一名年轻收件人侧身握住正在渗出白雾的黑色信封，"
        "远处整条街的门牌同时缺失。人物位于下方三分之一，信封是唯一高亮主体，冷青环境与一束暖黄门灯对照，"
        "上方保留干净的中文书名安全区，写实悬疑插画，细节清楚但背景不过度拥挤。",
        encoding="utf-8",
    )
    title_layout.write_text(
        "书名《雾城收件人》位置在画面上方 18% 的安全区，分两行居中对齐；字体使用思源黑体 Heavy，"
        "字色为暖白，配 2px 深青描边和轻微阴影，书名宽度约占画面 72%。作者名置于书名下方，字号为书名的 24%。",
        encoding="utf-8",
    )
    negative.write_text("乱码文字，水印，平台标识，多余人物，主体裁切，过度霓虹，廉价素材拼贴，模仿具体艺术家。", encoding="utf-8")
    research.write_text("2026-08-21 检查通用搜索引擎与目标网文平台的完整标题及核心短语，未发现高热度同名作品；存在零散非小说用语，混淆风险低。", encoding="utf-8")
    args = (
        sys.executable,
        str(SCRIPTS / "publishing_package.py"),
        "--project",
        str(project),
        "--title",
        "雾城收件人",
        "--positioning-file",
        str(positioning),
        "--cover-prompt-file",
        str(cover),
        "--title-layout-file",
        str(title_layout),
        "--negative-prompt-file",
        str(negative),
        "--research-notes-file",
        str(research),
    )
    before = (project / "project.json").read_text(encoding="utf-8")
    preview = json.loads(run(*args, "--dry-run").stdout)
    assert preview["dryRun"] and (project / "project.json").read_text(encoding="utf-8") == before
    applied = json.loads(run(*args).stdout)
    assert Path(applied["backup"]).is_dir()
    assert read_json(project / "project.json")["title"] == "雾城收件人"
    package_text = (project / "canon/publishing-package.md").read_text(encoding="utf-8")
    assert "雨夜旧城区" in package_text
    assert "思源黑体 Heavy" in package_text and "书名排版与字体说明" in package_text
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

    styled_args = list(args)
    layout_flag = styled_args.index("--title-layout-file")
    del styled_args[layout_flag : layout_flag + 2]
    styled_args.extend(("--cover-style", "classical-calligraphy"))
    styled = json.loads(run(*styled_args).stdout)
    assert styled["coverStyle"] == "classical-calligraphy"
    styled_text = (project / "canon/publishing-package.md").read_text(encoding="utf-8")
    assert "飞白" in styled_text and "纵排 2–3 列" in styled_text and "120×160" in styled_text
    run(*args)

    (project / "canon/publishing-package.md").write_text(
        package_text.replace("## 书名排版与字体说明", "## 排版说明"), encoding="utf-8"
    )
    invalid_layout = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("title layout and typography" in error for error in invalid_layout["errors"])
    run(*args)

    index = read_json(project / "project.json")
    index["lastCommittedChapter"] = 1
    write_json(project / "project.json", index)
    changed_args = list(args)
    changed_args[changed_args.index("雾城收件人")] = "昨日寄来的死信"
    refused = run(*changed_args, expect=1)
    assert "major decision" in refused.stderr
    confirmed = json.loads(run(*changed_args, "--confirmed").stdout)
    assert confirmed["title"] == "昨日寄来的死信"


def test_drafting_with_unconfirmed_package(base: Path) -> None:
    project = base / "unconfirmed-package"
    stage = base / "unconfirmed-package-stage"
    initialize(project, "暂定书名")
    index = read_json(project / "project.json")
    index["publishingPackage"] = {
        "status": "unconfirmed",
        "titleStatus": "unconfirmed",
        "uniquenessStatus": "unconfirmed",
        "coverPromptStatus": "unconfirmed",
        "updatedAt": index["createdAt"],
    }
    write_json(project / "project.json", index)
    # Use the real unconfirmed template, including its unfinished packaging fields.
    template = base / "unconfirmed-template"
    run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(template), "--title", "暂定书名")
    shutil.copy2(template / "canon/publishing-package.md", project / "canon/publishing-package.md")

    prepare_stage(project, stage, 1)
    (stage / "reviews/第0001章-review.json").unlink()
    rejected = commit(project, stage, expect=1)
    assert "review.json" in rejected["error"]
    assert read_json(project / "project.json")["lastCommittedChapter"] == 0

    prepare_stage(project, stage, 1)
    committed = commit(project, stage)
    assert any("before publication" in warning for warning in committed["warnings"])
    assert read_json(project / "project.json")["publishingPackage"]["status"] == "unconfirmed"
    validated = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert validated["ok"]

    contract = project / "canon/story-contract.md"
    original_contract = contract.read_text(encoding="utf-8")
    contract.write_text("# 故事合同\n\n待确认\n", encoding="utf-8")
    rejected = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("unresolved marker" in error and "story-contract.md" in error for error in rejected["errors"])
    contract.write_text(original_contract, encoding="utf-8")

    # Deferring packaging must not permit a false active/confirmed declaration.
    index = read_json(project / "project.json")
    index["publishingPackage"]["status"] = "active"
    write_json(project / "project.json", index)
    rejected = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("publishingPackage status fields" in error for error in rejected["errors"])


def test_market_research(base: Path) -> None:
    project = base / "market-research"
    initialize(project, "雾港回声簿")
    source_urls = ["https://example.com/public-ranking", "https://example.org/public-list"]
    snapshot = {
        "schemaVersion": 1,
        "asOfDate": "2026-08-21",
        "platform": "番茄小说",
        "scope": {
            "audience": "偏好都市悬疑与强情节的移动端读者",
            "genre": "都市悬疑",
            "ranking": "公开热读榜与新书榜",
            "sampleWindow": "各榜公开前十中符合题材的作品",
        },
        "sources": [
            {"title": "公开热读榜", "url": source_urls[0], "accessedAt": "2026-08-21"},
            {"title": "公开新书榜", "url": source_urls[1], "accessedAt": "2026-08-21"},
        ],
        "samples": [
            {
                "title": f"观察样本{index}",
                "sourceUrl": source_urls[index % 2],
                "tags": ["都市", "悬疑"],
                "observedSignals": [f"公开简介在第{index}个信息点给出明确异常"],
            }
            for index in range(1, 6)
        ],
        "observations": ["五个样本均在简介中给出具体异常", "标题多使用具象职业或地点", "公开简介强调短期目标"],
        "hypotheses": [
            {"claim": "具体异常比抽象氛围更利于首屏理解", "confidence": "medium", "evidenceTitles": ["观察样本1", "观察样本2"]},
            {"claim": "职业与地点组合仍有差异化空间", "confidence": "low", "evidenceTitles": ["观察样本3", "观察样本4"]},
        ],
        "opportunities": ["用少见职业承载悬疑机制", "把阶段目标写进简介而不泄露谜底"],
        "avoidCopying": ["不复用样本书名结构与专有词", "不拼接样本人设、机制和情节"],
    }
    snapshot_path = base / "valid-market.json"
    write_json(snapshot_path, snapshot)
    args = (sys.executable, str(SCRIPTS / "market_brief.py"), "--project", str(project), "--snapshot", str(snapshot_path))
    preview = json.loads(run(*args, "--dry-run").stdout)
    assert preview["dryRun"] and read_json(project / "project.json")["marketResearch"]["status"] == "unrequested"
    applied = json.loads(run(*args).stdout)
    assert applied["sourceCount"] == 2 and applied["sampleCount"] == 5
    assert "观察事实" in (project / "canon/market-brief.md").read_text(encoding="utf-8")
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

    invalid = dict(snapshot)
    invalid["sources"] = snapshot["sources"][:1]
    invalid["samples"] = snapshot["samples"][:4]
    invalid["hypotheses"] = [
        {"claim": "证据不足", "confidence": "certain", "evidenceTitles": ["不存在"]},
        {"claim": "仍然不足", "confidence": "certain", "evidenceTitles": ["观察样本1"]},
    ]
    invalid_path = base / "invalid-market.json"
    write_json(invalid_path, invalid)
    failed = json.loads(run(sys.executable, str(SCRIPTS / "market_brief.py"), "--project", str(project), "--snapshot", str(invalid_path), expect=1).stdout)
    joined = "\n".join(failed["errors"])
    assert "at least 2 public sources" in joined and "at least 5 observed works" in joined and "confidence" in joined


def test_short_story_market_boundary(base: Path) -> None:
    project = base / "short-story-market"
    run(
        sys.executable,
        str(SCRIPTS / "init_project.py"),
        "--path",
        str(project),
        "--title",
        "短故事市场边界",
        "--mode",
        "fanqie-short-story",
    )
    source_urls = ["https://example.com/short-story", "https://example.org/short-story"]
    snapshot = {
        "schemaVersion": 1,
        "asOfDate": "2026-09-03",
        "platform": "番茄小说",
        "scope": {
            "audience": "短故事读者",
            "genre": "古言悬疑",
            "ranking": "短故事频道公开样本",
            "sampleWindow": "频道内五个近期样本",
            "contentForm": "short-story",
        },
        "sources": [
            {"title": "短故事页一", "url": source_urls[0], "accessedAt": "2026-09-03", "contentForm": "short-story"},
            {"title": "短故事页二", "url": source_urls[1], "accessedAt": "2026-09-03", "contentForm": "short-story"},
        ],
        "samples": [
            {
                "title": f"短故事样本{index}",
                "sourceUrl": source_urls[index % 2],
                "tags": ["短故事", "悬疑"],
                "observedSignals": [f"样本{index}公开展示了具体入口冲突"],
            }
            for index in range(1, 6)
        ],
        "observations": ["入口冲突具体", "主角目标清楚", "短篇结局闭合"],
        "hypotheses": [
            {"claim": "具体危机便于理解", "confidence": "medium", "evidenceTitles": ["短故事样本1"]},
            {"claim": "身份反差仍有空间", "confidence": "low", "evidenceTitles": ["短故事样本2"]},
        ],
        "opportunities": ["改造冲突机制", "避开重复身份"],
        "avoidCopying": ["不复用书名", "不拼接情节"],
    }
    snapshot_path = base / "short-story-market.json"
    write_json(snapshot_path, snapshot)
    args = (sys.executable, str(SCRIPTS / "market_brief.py"), "--project", str(project), "--snapshot", str(snapshot_path))
    assert json.loads(run(*args, "--dry-run").stdout)["ok"]

    wrong_scope = json.loads(json.dumps(snapshot, ensure_ascii=False))
    wrong_scope["scope"]["contentForm"] = "longform"
    wrong_scope_path = base / "wrong-short-story-scope.json"
    write_json(wrong_scope_path, wrong_scope)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "market_brief.py"), "--project", str(project), "--snapshot", str(wrong_scope_path), expect=1).stdout)["errors"]
    assert any("scope.contentForm=short-story" in error for error in errors)

    wrong_source = json.loads(json.dumps(snapshot, ensure_ascii=False))
    wrong_source["sources"][0]["contentForm"] = "mixed"
    wrong_source_path = base / "wrong-short-story-source.json"
    write_json(wrong_source_path, wrong_source)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "market_brief.py"), "--project", str(project), "--snapshot", str(wrong_source_path), expect=1).stdout)["errors"]
    assert any("source #1 must use contentForm=short-story" in error for error in errors)


def make_story_project(path: Path, title: str, contract: str, characters: str) -> None:
    write_json(path / "project.json", {"title": title})
    (path / "canon").mkdir(parents=True, exist_ok=True)
    (path / "canon/story-contract.md").write_text(f"# 故事合同\n\n{contract}\n", encoding="utf-8")
    (path / "canon/characters.md").write_text(f"# 人物\n\n{characters}\n", encoding="utf-8")


def test_story_overlap(base: Path) -> None:
    library = base / "story-library"
    make_story_project(
        library / "old-palace-story",
        "病王爷的药账",
        "谢昭宁嫁给病王爷萧砚川，借接管药房追查北境军饷和姐姐冤案。",
        "谢昭宁擅长辨药记账，萧砚川掌握北境旧部，柳含章藏着药房钥匙。",
    )
    make_story_project(
        library / "old-modern-story",
        "深夜末班车",
        "公交司机周闻发现每逢暴雨就多出一站，他必须在黎明前找到失踪乘客。",
        "周闻熟悉城市路线，记者林遥追查旧站拆迁档案，两人没有医术或王府背景。",
    )
    make_story_project(
        library / "old-modern-story" / ".webnovel" / "backups" / "files",
        "不应参与比较的备份",
        "谢昭宁嫁给病王爷萧砚川，借接管药房追查北境军饷和姐姐冤案。",
        "谢昭宁、萧砚川与柳含章。",
    )
    similar = base / "similar-candidate.md"
    similar.write_text(
        "# 候选\n\n谢昭宁嫁给病王爷萧砚川，以争宠为名接管药房，追查北境军饷和姐姐冤案。\n",
        encoding="utf-8",
    )
    similar_result = json.loads(
        run(sys.executable, str(SCRIPTS / "story_overlap.py"), "--candidate", str(similar), "--library", str(library), expect=1).stdout
    )
    assert similar_result["highestRisk"] == "high"
    assert similar_result["comparedProjectCount"] == 2
    assert not any(".webnovel" in row["project"] for row in similar_result["comparisons"])
    assert "plagiarism" in similar_result["note"]

    distinct = base / "distinct-candidate.md"
    distinct.write_text(
        "# 候选\n\n极地气象员顾雪在通信中断后修复冰芯钻机，并决定公开海洋污染记录。\n",
        encoding="utf-8",
    )
    distinct_result = json.loads(
        run(sys.executable, str(SCRIPTS / "story_overlap.py"), "--candidate", str(distinct), "--library", str(library)).stdout
    )
    assert distinct_result["highestRisk"] == "low"


def test_reference_guard(base: Path) -> None:
    source = base / "reference-story.md"
    copied = base / "copied-draft.md"
    distinct = base / "distinct-draft.md"
    forbidden = base / "forbidden-name-draft.md"
    report = base / "reference-report.json"
    exact_block = (
        "林照晚把旧城铜铃放进火盆时，门外的报丧人忽然改口，说死者昨夜还在码头签过货单。"
        "她没有追问，先锁住账房，再让伙计把当日所有船票铺在院中。"
    )
    source.write_text(
        "# 参考故事\n\n" + exact_block + "铜铃里藏着失踪船主留下的盐税暗码，林照晚必须在涨潮前找到沉船。\n",
        encoding="utf-8",
    )
    copied.write_text("# 候选\n\n新人物走进院子。" + exact_block + "随后她决定继续调查。\n", encoding="utf-8")
    copied_result = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "reference_guard.py"),
            "--source",
            str(source),
            "--candidate",
            str(copied),
            "--output",
            str(report),
            expect=1,
        ).stdout
    )
    assert copied_result["risk"] == "high" and copied_result["maxSharedRunUnits"] >= 60
    assert read_json(report)["candidatePhraseContainment"] == copied_result["candidatePhraseContainment"]
    assert "not a plagiarism or legal determination" in copied_result["note"]

    distinct.write_text(
        "# 候选\n\n极地气象员顾雪发现卫星回传被人替换。她关闭自动站，用冰芯年代反推污染船航线，并在风暴前公开数据。\n",
        encoding="utf-8",
    )
    distinct_result = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "reference_guard.py"),
            "--source",
            str(source),
            "--candidate",
            str(distinct),
            "--forbid-term",
            "林照晚",
            "--forbid-term",
            "旧城铜铃",
        ).stdout
    )
    assert distinct_result["risk"] == "low" and not distinct_result["matchedForbiddenTerms"]

    forbidden.write_text("# 候选\n\n林照晚在空间站修复了失控的氧气循环。\n", encoding="utf-8")
    forbidden_result = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "reference_guard.py"),
            "--source",
            str(source),
            "--candidate",
            str(forbidden),
            "--forbid-term",
            "林照晚",
            expect=1,
        ).stdout
    )
    assert forbidden_result["risk"] == "high" and forbidden_result["matchedForbiddenTerms"] == ["林照晚"]


def test_performance_feedback(base: Path) -> None:
    project = base / "performance-feedback"
    initialize(project, "发布反馈测试")
    data = {
        "schemaVersion": 1,
        "platform": "番茄小说",
        "windowStart": "2026-08-29",
        "windowEnd": "2026-08-31",
        "recommendationStatus": "initial-complete",
        "impressions": 17,
        "reads": 4,
        "completedReads": None,
        "unlocks": None,
        "likes": 0,
        "comments": 0,
        "bookshelves": 0,
        "notes": "后台统计样本",
    }
    input_path = base / "performance-input.json"
    write_json(input_path, data)
    args = (sys.executable, str(SCRIPTS / "performance_feedback.py"), "--project", str(project), "--input", str(input_path))
    before = (project / "project.json").read_text(encoding="utf-8")
    dry = json.loads(run(*args, "--dry-run").stdout)
    assert dry["stage"] == "insufficient-exposure" and dry["readRate"] == 0.2353
    assert (project / "project.json").read_text(encoding="utf-8") == before
    assert not (project / "performance/latest-diagnosis.md").exists()

    applied = json.loads(run(*args).stdout)
    assert applied["stage"] == "insufficient-exposure"
    assert read_json(project / "project.json")["performanceFeedback"]["snapshotCount"] == 1
    assert read_json(project / "performance/snapshots/2026-08-29-to-2026-08-31.json")["impressions"] == 17
    diagnosis = (project / "performance/latest-diagnosis.md").read_text(encoding="utf-8")
    assert "样本不足，不据此改正文或判断包装成败" in diagnosis
    assert "不是番茄官方流量标准" in diagnosis

    invalid = dict(data)
    invalid.update({"windowStart": "2026-09-01", "windowEnd": "2026-08-31", "reads": 18})
    invalid_path = base / "invalid-performance.json"
    write_json(invalid_path, invalid)
    failed = json.loads(run(sys.executable, str(SCRIPTS / "performance_feedback.py"), "--project", str(project), "--input", str(invalid_path), expect=1).stdout)
    joined = "\n".join(failed["errors"])
    assert "reads cannot exceed impressions" in joined and "windowStart cannot be after windowEnd" in joined


def test_opening_audit(base: Path) -> None:
    chapter = base / "opening-audit.md"
    chapter.write_text(
        "# 第一节\n\n"
        + "谢昭宁推开灵堂大门，当众扣下陪葬名册。宗正寺的人拔刀拦她，她把王府金印压在棺盖上。" * 12
        + "\n\n“今日谁敢封棺，我就让谁把名字写进验尸记录。”她说。\n",
        encoding="utf-8",
    )
    output = base / "opening-audit.json"
    result = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "opening_audit.py"),
            str(chapter),
            "--window",
            "300",
            "--output",
            str(output),
        ).stdout
    )
    assert result["windowFilled"] and result["openingContentChars"] == 300
    assert [segment["range"] for segment in result["segments"]] == ["1-100", "101-200", "201-300"]
    assert read_json(output)["openingText"] == result["openingText"]
    assert "predict traffic" in result["note"]


def test_prose_lint(base: Path) -> None:
    risky = base / "第0001章-风险文本.md"
    risky.write_text(
        "# 第一章\n\n"
        + "深吸一口气，他眼中闪过冷光，显然这一切仿佛早有安排。" * 5
        + "\n\n他终于明白，这意味着真正的麻烦才刚刚开始。\n",
        encoding="utf-8",
    )
    baseline = base / "第0000章-基线.md"
    baseline.write_text("# 基线\n\n“走。”他说，“现在就走，不要回头。”\n“为什么？”她问，“门后到底有什么？”\n", encoding="utf-8")
    result = json.loads(
        run(sys.executable, str(SCRIPTS / "prose_lint.py"), str(risky), "--baseline", str(baseline)).stdout
    )
    codes = {finding["code"] for finding in result["findings"]}
    assert result["claim"] == "editorial-risk-signals-not-authorship-detection"
    assert "repeated-micro-actions" in codes and "summary-ending" in codes
    assert any(code.startswith("baseline-drift-") for code in codes)

    single_modifier = base / "第0002章-单个副词.md"
    single_modifier.write_text("# 第二章\n\n她忽然停住，听见楼下有人叫她。\n", encoding="utf-8")
    single_codes = {
        item["code"]
        for item in json.loads(
            run(sys.executable, str(SCRIPTS / "prose_lint.py"), str(single_modifier)).stdout
        )["findings"]
    }
    assert "modifier-cluster" not in single_codes

    modifier_cluster = base / "第0003章-副词簇.md"
    modifier_cluster.write_text(
        "# 第三章\n\n她忽然回头，微微皱眉。她轻轻关门，又缓缓坐下。她默默低头，终于开口。\n",
        encoding="utf-8",
    )
    cluster_codes = {
        item["code"]
        for item in json.loads(
            run(sys.executable, str(SCRIPTS / "prose_lint.py"), str(modifier_cluster)).stdout
        )["findings"]
    }
    assert "modifier-cluster" in cluster_codes

    symmetry = base / "第0004章-工整句.md"
    symmetry.write_text(
        "# 第四章\n\n合同在，镯子在。人情归人情，生意归生意。两张纸。两个签名。\n",
        encoding="utf-8",
    )
    symmetry_codes = {
        item["code"]
        for item in json.loads(
            run(sys.executable, str(SCRIPTS / "prose_lint.py"), str(symmetry)).stdout
        )["findings"]
    }
    assert "rhetorical-symmetry" in symmetry_codes

    cadence = base / "第0005章-包装节拍.md"
    cadence.write_text(
        "# 第五章\n\n他抬眼。\n“你说谎。”\n这意味着她已经输了。\n"
        "她合上文件。\n“证据呢？”\n这说明他根本没有准备好。\n",
        encoding="utf-8",
    )
    cadence_codes = {
        item["code"]
        for item in json.loads(
            run(sys.executable, str(SCRIPTS / "prose_lint.py"), str(cadence)).stdout
        )["findings"]
    }
    assert "cadence-packaging" in cadence_codes

    baseline_paths: list[str] = []
    for index in range(3):
        path = base / f"第{index + 10:04d}章-人工基线.md"
        path.write_text(
            "# 基线\n\n“账对了吗？”她问。\n“还差多少？”他没抬头。\n",
            encoding="utf-8",
        )
        baseline_paths.extend(("--baseline", str(path)))
    drift_result = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "prose_lint.py"),
            str(modifier_cluster),
            *baseline_paths,
        ).stdout
    )
    drift_codes = {item["code"] for item in drift_result["findings"]}
    assert "baseline-drift-modifierRatePer1k" in drift_codes


def test_review_gate(base: Path) -> None:
    project = base / "review-gate"
    stage = base / "review-stage"
    initialize(project, "独立审稿测试")

    prepare_stage(project, stage, 1)
    (stage / "reviews/第0001章-lint.json").unlink()
    assert "第0001章-lint.json" in commit(project, stage, expect=1)["error"]

    prepare_stage(project, stage, 1)
    (stage / "reviews/第0001章-review.json").unlink()
    assert "第0001章-review.json" in commit(project, stage, expect=1)["error"]

    prepare_stage(project, stage, 1)
    review_path = stage / "reviews/第0001章-review.json"
    review = read_json(review_path)
    review["reviewedTextSha256"] = "0" * 64
    write_json(review_path, review)
    assert "review hash does not match" in commit(project, stage, expect=1)["error"]

    prepare_stage(project, stage, 1)
    review = read_json(review_path)
    review["editor"]["status"] = "blocked"
    write_json(review_path, review)
    assert "editor review is blocked" in commit(project, stage, expect=1)["error"]

    prepare_stage(project, stage, 1)
    review = read_json(review_path)
    review["reader"]["moments"][0]["evidence"] = "这不是正文里的句子"
    write_json(review_path, review)
    assert "not an exact chapter substring" in commit(project, stage, expect=1)["error"]

    prepare_stage(project, stage, 1)
    review = read_json(review_path)
    review["reader"].update({"status": "drop-risk", "completionIntent": "stop"})
    write_json(review_path, review)
    assert "drop-risk or stop intent" in commit(project, stage, expect=1)["error"]

    prepare_stage(project, stage, 1)
    commit(project, stage)


def test_migration(base: Path) -> None:
    project = base / "legacy"
    create_legacy_project(project)
    before = (project / "project.json").read_text(encoding="utf-8")
    preview = json.loads(run(sys.executable, str(SCRIPTS / "migrate_project.py"), str(project), "--dry-run").stdout)
    assert preview["changed"] and preview["dryRun"]
    assert (project / "project.json").read_text(encoding="utf-8") == before

    migrated = json.loads(run(sys.executable, str(SCRIPTS / "migrate_project.py"), str(project)).stdout)
    assert migrated["changed"] and Path(migrated["backup"]).is_dir()
    assert read_json(project / "project.json")["rewardCadence"]["enforceFromChapter"] == 4
    rewards = read_json(project / "state/rewards.json")
    assert rewards["legacyUnauditedThrough"] == 3
    assert read_json(project / "state/cast-arcs.json")["legacyUnauditedThrough"] == 3
    assert rewards["beats"][0]["status"] == "needs-review"
    assert rewards["beats"][0]["rewardType"] == "other"
    validation = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert validation["ok"] and any("Legacy chapters through 3" in warning for warning in validation["warnings"])

    legacy_revision_stage = base / "legacy-revision-stage"
    legacy_chapter_text = (project / "chapters" / "第0003章-旧章.md").read_text(encoding="utf-8")
    prepare_stage(project, legacy_revision_stage, 3)
    generated_chapter = legacy_revision_stage / "chapters" / "第0003章-测试章.md"
    generated_chapter.replace(legacy_revision_stage / "chapters" / "第0003章-旧章.md")
    staged_index = read_json(legacy_revision_stage / "project.json")
    staged_index["totalContentChars"] -= content_chars(legacy_chapter_text)
    write_json(legacy_revision_stage / "project.json", staged_index)
    legacy_review_path = legacy_revision_stage / "reviews" / "第0003章-review.json"
    legacy_review = read_json(legacy_review_path)
    legacy_review.pop("naturalness")
    write_json(legacy_review_path, legacy_review)
    rejected_revision = commit(project, legacy_revision_stage, allow_revision=True, expect=1)
    assert "review needs naturalness object" in rejected_revision["error"]

    prepare_stage(project, legacy_revision_stage, 3)
    generated_chapter = legacy_revision_stage / "chapters" / "第0003章-测试章.md"
    generated_chapter.replace(legacy_revision_stage / "chapters" / "第0003章-旧章.md")
    staged_index = read_json(legacy_revision_stage / "project.json")
    staged_index["totalContentChars"] -= content_chars(legacy_chapter_text)
    write_json(legacy_revision_stage / "project.json", staged_index)
    legacy_review_path = legacy_revision_stage / "reviews" / "第0003章-review.json"
    legacy_review = read_json(legacy_review_path)
    legacy_review.pop("reader")
    write_json(legacy_review_path, legacy_review)
    rejected_revision = commit(project, legacy_revision_stage, allow_revision=True, expect=1)
    assert "review needs reader object" in rejected_revision["error"]

    prepare_stage(project, legacy_revision_stage, 3)
    generated_chapter = legacy_revision_stage / "chapters" / "第0003章-测试章.md"
    generated_chapter.replace(legacy_revision_stage / "chapters" / "第0003章-旧章.md")
    staged_index = read_json(legacy_revision_stage / "project.json")
    staged_index["totalContentChars"] -= content_chars(legacy_chapter_text)
    write_json(legacy_revision_stage / "project.json", staged_index)
    commit(project, legacy_revision_stage, allow_revision=True)

    backups_before = list((project / ".webnovel" / "backups").iterdir())
    repeated = json.loads(run(sys.executable, str(SCRIPTS / "migrate_project.py"), str(project)).stdout)
    backups_after = list((project / ".webnovel" / "backups").iterdir())
    assert not repeated["changed"]
    assert len(backups_before) == len(backups_after)

    hybrid = base / "hybrid-schema"
    create_legacy_project(hybrid)
    hybrid_index = read_json(hybrid / "project.json")
    hybrid_index["schemaVersion"] = 2
    hybrid_index["rewardCadence"].update({"supercycle": 15, "enforceFromChapter": 1})
    write_json(hybrid / "project.json", hybrid_index)
    mixed = json.loads(run(sys.executable, str(SCRIPTS / "migrate_project.py"), str(hybrid)).stdout)
    assert mixed["fromVersion"] == 2 and mixed["rewardsFromVersion"] == 1
    assert read_json(hybrid / "project.json")["rewardCadence"]["enforceFromChapter"] == 4
    assert read_json(hybrid / "state/rewards.json")["legacyUnauditedThrough"] == 3

    previous_v2 = base / "previous-v2"
    initialize(previous_v2, "雾港旧案簿")
    previous_index = read_json(previous_v2 / "project.json")
    previous_index["schemaVersion"] = 2
    previous_index.pop("styleProfile")
    previous_index.pop("publishingPackage")
    write_json(previous_v2 / "project.json", previous_index)
    (previous_v2 / "canon/style-profile.md").unlink()
    (previous_v2 / "canon/publishing-package.md").unlink()
    (previous_v2 / "state/cast-arcs.json").unlink()
    upgraded = json.loads(run(sys.executable, str(SCRIPTS / "migrate_project.py"), str(previous_v2)).stdout)
    assert upgraded["fromVersion"] == 2 and upgraded["rewardsFromVersion"] == 2
    assert upgraded["legacyUnauditedThrough"] == 0
    upgraded_index = read_json(previous_v2 / "project.json")
    assert upgraded_index["schemaVersion"] == 8
    assert upgraded_index["ensemble"]["enabled"] is True
    assert upgraded_index["rewardCadence"]["enforceFromChapter"] == 1
    assert upgraded_index["styleProfile"]["status"] == "unconfirmed"
    assert upgraded_index["publishingPackage"]["status"] == "unconfirmed"
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(previous_v2)).stdout)["ok"]

    previous_v3 = base / "previous-v3"
    initialize(previous_v3, "旧版配角迁移")
    previous_v3_index = read_json(previous_v3 / "project.json")
    previous_v3_index["schemaVersion"] = 3
    write_json(previous_v3 / "project.json", previous_v3_index)
    (previous_v3 / "state/cast-arcs.json").unlink()
    upgraded_v3 = json.loads(run(sys.executable, str(SCRIPTS / "migrate_project.py"), str(previous_v3)).stdout)
    assert upgraded_v3["fromVersion"] == 3 and upgraded_v3["castLegacyUnauditedThrough"] == 0
    assert read_json(previous_v3 / "project.json")["schemaVersion"] == 8
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(previous_v3)).stdout)["ok"]

    previous_v4 = base / "previous-v4"
    initialize(previous_v4, "旧版审稿迁移")
    previous_v4_stage = base / "previous-v4-stage"
    prepare_stage(previous_v4, previous_v4_stage, 1)
    commit(previous_v4, previous_v4_stage)
    previous_v4_index = read_json(previous_v4 / "project.json")
    previous_v4_index["schemaVersion"] = 4
    previous_v4_index.pop("marketResearch")
    previous_v4_index.pop("reviewGate")
    write_json(previous_v4 / "project.json", previous_v4_index)
    (previous_v4 / "canon/market-brief.md").unlink()
    shutil.rmtree(previous_v4 / "reviews")
    (previous_v4 / "reviews").mkdir()
    upgraded_v4 = json.loads(run(sys.executable, str(SCRIPTS / "migrate_project.py"), str(previous_v4)).stdout)
    assert upgraded_v4["fromVersion"] == 4
    assert read_json(previous_v4 / "project.json")["reviewGate"]["enforceFromChapter"] == 2
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(previous_v4)).stdout)["ok"]


def test_cast_arcs(base: Path) -> None:
    project = base / "cast-arcs"
    initialize(project, "群像关系测试")
    cast_path = project / "state/cast-arcs.json"
    cast_doc = read_json(cast_path)
    cast_doc["characters"] = [
        {
            "id": "archivist",
            "name": "沈砚秋",
            "tier": "anchor",
            "narrativeRole": "foil",
            "status": "active",
            "arcPhase": "pressure",
            "introducedChapter": 0,
            "lastAdvancedChapter": 0,
            "ownWant": "保住被查封的民间档案馆",
            "independentGoal": "证明城中失踪案由官方旧令造成",
            "privateConstraint": "她公开证据就会连累仍在体制内的姐姐",
            "nextTurnWindow": [1, 6],
            "history": [],
            "relationships": [
                {
                    "targetId": "warden",
                    "kind": "love",
                    "status": "hidden",
                    "sinceChapter": 0,
                    "basis": "两人曾共同从封城灾难中救出一批孩子",
                    "cost": "她必须在感情与公布对方罪证之间作出选择",
                    "evidenceChapters": [],
                }
            ],
        },
        {
            "id": "warden",
            "name": "陆沉钟",
            "tier": "recurring",
            "narrativeRole": "antagonist",
            "status": "active",
            "arcPhase": "setup",
            "introducedChapter": 0,
            "lastAdvancedChapter": 0,
            "ownWant": "让封城秩序继续运转",
            "independentGoal": "销毁会引发全城清算的旧令原件",
            "privateConstraint": "他必须维持下属对制度的信任",
            "nextTurnWindow": [1, 8],
            "history": [],
            "relationships": [            ],
        },
    ]
    write_json(cast_path, cast_doc)
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

    offline = read_json(cast_path)
    offline["characters"][0]["presence"] = {"state": "offline", "return": "continues"}
    write_json(cast_path, offline)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("returnWhen" in error for error in errors)
    offline["characters"][0]["presence"] = {
        "state": "offline",
        "return": "continues",
        "returnWhen": "档案室开门之后",
        "returnThread": "失踪案旧令",
    }
    write_json(cast_path, offline)
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]
    write_json(cast_path, cast_doc)

    non_romantic = read_json(cast_path)
    non_romantic["characters"][0]["relationships"][0].update(
        {
            "kind": "mentorship",
            "status": "strained",
            "basis": "对方传授档案鉴伪术，却要求她维护旧制度",
            "cost": "追查真相会公开否定恩师的毕生选择",
        }
    )
    write_json(cast_path, non_romantic)
    assert json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]
    write_json(cast_path, cast_doc)

    unknown = read_json(cast_path)
    unknown["characters"][0]["relationships"][0]["targetId"] = "missing-person"
    write_json(cast_path, unknown)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("unknown targetId" in error for error in errors)

    missing_love_fields = read_json(cast_path)
    missing_love_fields["characters"][0]["relationships"][0].update({"targetId": "warden", "basis": "", "cost": ""})
    write_json(cast_path, missing_love_fields)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("concrete basis" in error for error in errors) and any("concrete cost" in error for error in errors)

    missing_goal = read_json(cast_path)
    missing_goal["characters"][0]["relationships"][0].update(
        {"basis": "共同救过人", "cost": "公开真相会失去对方"}
    )
    missing_goal["characters"][0]["independentGoal"] = ""
    write_json(cast_path, missing_goal)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("concrete independentGoal" in error for error in errors)

    missing_love_evidence = read_json(cast_path)
    missing_love_evidence["asOfChapter"] = 1
    missing_love_evidence["characters"][0]["independentGoal"] = "查清旧令来源"
    missing_love_evidence["characters"][0]["relationships"][0]["sinceChapter"] = 1
    write_json(cast_path, missing_love_evidence)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("needs evidenceChapters for love" in error for error in errors)

    missing_history = read_json(cast_path)
    missing_history["asOfChapter"] = 1
    missing_history["characters"][0]["independentGoal"] = "查清旧令来源"
    missing_history["characters"][0]["lastAdvancedChapter"] = 1
    missing_history["characters"][0]["relationships"][0]["evidenceChapters"] = [1]
    write_json(cast_path, missing_history)
    errors = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("matching choice/delta history evidence" in error for error in errors)

    no_anchor = read_json(cast_path)
    no_anchor["asOfChapter"] = 5
    no_anchor["characters"] = []
    write_json(cast_path, no_anchor)
    index = read_json(project / "project.json")
    index["lastCommittedChapter"] = 5
    index["latestDraftChapter"] = 5
    write_json(project / "project.json", index)
    report = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("No anchor supporting character" in warning for warning in report["warnings"])
    assert not any("anchor supporting character" in error for error in report["errors"])

    no_anchor_progress = read_json(cast_path)
    no_anchor_progress["asOfChapter"] = 15
    no_anchor_progress["characters"] = [
        {
            "id": "stalled-anchor",
            "name": "停滞配角",
            "tier": "anchor",
            "narrativeRole": "ally",
            "status": "active",
            "arcPhase": "setup",
            "introducedChapter": 0,
            "lastAdvancedChapter": 0,
            "ownWant": "守住自己的产业",
            "independentGoal": "查明账册去向",
            "privateConstraint": "调查会暴露家族旧债",
            "nextTurnWindow": [1, 20],
            "history": [],
            "relationships": [],
        }
    ]
    write_json(cast_path, no_anchor_progress)
    index["lastCommittedChapter"] = 15
    index["latestDraftChapter"] = 15
    write_json(project / "project.json", index)
    report = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("No anchor supporting-cast choice/consequence" in warning for warning in report["warnings"])
    assert not any("anchor supporting" in error for error in report["errors"])

    # Check the cast gate independently: unfinished arcs may span many text slices,
    # while fabricated choice/delta history must still be rejected.
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("cast_gate_test", SCRIPTS / "validate_project.py")
        assert spec and spec.loader
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        for document, chapter in ((no_anchor, 5), (no_anchor_progress, 15)):
            cast_errors, cast_warnings = [], []
            validator.validate_cast_arcs(document, chapter, "serial", cast_errors, cast_warnings)
            assert not cast_errors, cast_errors
            assert cast_warnings
        no_anchor_progress["characters"][0]["lastAdvancedChapter"] = 15
        cast_errors = []
        validator.validate_cast_arcs(no_anchor_progress, 15, "serial", cast_errors, [])
        assert any("matching choice/delta history evidence" in error for error in cast_errors)
    finally:
        sys.path.remove(str(SCRIPTS))


def test_commit_validation_and_restore(base: Path) -> None:
    project = base / "commits"
    stage = base / "stage"
    initialize(project, "提交测试")

    prepare_stage(project, stage, 1)
    (stage / "state/cast-arcs.json").unlink()
    rejected_missing_cast = commit(project, stage, expect=1)
    assert "state/cast-arcs.json" in rejected_missing_cast["error"]
    assert read_json(project / "project.json")["lastCommittedChapter"] == 0

    prepare_stage(project, stage, 1)
    dry = commit(project, stage, dry_run=True)
    assert dry["dryRun"] and read_json(project / "project.json")["lastCommittedChapter"] == 0
    first = commit(project, stage)
    first_backup = Path(first["backup"])
    assert read_json(project / "project.json")["lastCommittedChapter"] == 1
    original_first = (project / "chapters" / "第0001章-测试章.md").read_text(encoding="utf-8")

    prepare_stage(project, stage, 2)
    commit(project, stage, dry_run=True)
    assert (project / "chapters" / "第0001章-测试章.md").read_text(encoding="utf-8") == original_first

    restored = json.loads(
        run(
            sys.executable,
            str(SCRIPTS / "commit_chapter.py"),
            "--project",
            str(project),
            "--restore",
            str(first_backup),
        ).stdout
    )
    assert restored["validation"]["ok"]
    assert read_json(project / "project.json")["lastCommittedChapter"] == 0
    assert not (project / "chapters" / "第0001章-测试章.md").exists()

    prepare_stage(project, stage, 1)
    commit(project, stage)
    prepare_stage(project, stage, 2)
    commit(project, stage)

    missing = "这段文字没有出现在第三章正文里"
    bad_three = make_beat(3, "small", "public-doubt", "evidence-reveal", evidence=missing)
    prepare_stage(project, stage, 3, bad_three)
    rejected = commit(project, stage, expect=1)
    assert "not an exact chapter substring" in rejected["error"]
    assert read_json(project / "project.json")["lastCommittedChapter"] == 2

    good_three = make_beat(3, "small", "public-doubt", "evidence-reveal")
    prepare_stage(project, stage, 3, good_three)
    commit(project, stage)
    prepare_stage(project, stage, 4)
    commit(project, stage)
    five = make_beat(5, "major", "institutional-block", "rule-reversal")
    prepare_stage(project, stage, 5, five)
    commit(project, stage)

    repeated_six = make_beat(6, "small", "public-doubt", "evidence-reveal")
    prepare_stage(project, stage, 6, repeated_six)
    rejected = commit(project, stage, expect=1)
    assert "repeat the same conflictType + solutionType + rewardType pattern" in rejected["error"]
    assert read_json(project / "project.json")["lastCommittedChapter"] == 5

    six = make_beat(6, "small", "resource-shortage", "alliance-trade")
    prepare_stage(project, stage, 6, six)
    commit(project, stage)
    prepare_stage(project, stage, 7)
    commit(project, stage)
    prepare_stage(project, stage, 8)
    commit(project, stage)
    nine = make_beat(9, "small", "hidden-route", "deduction-test")
    prepare_stage(project, stage, 9, nine)
    final = commit(project, stage)
    assert any("Three consecutive small reward beats 3, 6, and 9" in warning for warning in final["warnings"])

    ten = make_beat(10, "major", "authority-seizure", "public-countermand")
    prepare_stage(project, stage, 10, ten)
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("commit_chapter_rollback_test", SCRIPTS / "commit_chapter.py")
        assert spec and spec.loader
        commit_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(commit_module)
        original_copy = commit_module.copy_file_atomic
        root_writes = 0

        def fail_second_root_write(source: Path, destination: Path) -> None:
            nonlocal root_writes
            destination = destination.resolve()
            if project.resolve() in destination.parents and ".webnovel" not in destination.relative_to(project.resolve()).parts:
                root_writes += 1
                if root_writes == 2:
                    raise OSError("simulated mid-commit failure")
            original_copy(source, destination)

        commit_module.copy_file_atomic = fail_second_root_write
        old_argv = sys.argv
        sys.argv = ["commit_chapter.py", "--project", str(project), "--staging", str(stage)]
        try:
            commit_module.main()
            raise AssertionError("Simulated commit failure did not occur")
        except OSError as exc:
            assert "simulated mid-commit failure" in str(exc)
        finally:
            sys.argv = old_argv
    finally:
        sys.path.remove(str(SCRIPTS))
    assert read_json(project / "project.json")["lastCommittedChapter"] == 9
    assert not (project / "chapters" / "第0010章-测试章.md").exists()
    rollback_validation = json.loads(run(sys.executable, str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert rollback_validation["ok"]


def test_event_context_carry_forward(base: Path) -> None:
    project, stage = base / "event-carry", base / "event-carry-stage"
    initialize(project, "跨章意图复用")
    prepare_stage(project, stage, 1)
    contract = read_json(stage / "contracts/chapter-0001.json")
    contract["eventId"] = "side-door-check"
    write_json(stage / "contracts/chapter-0001.json", contract)
    intent_dir = stage / "intents/chapter-0001"
    (intent_dir / "precard.md").write_text("接续侧门检查；事件尚未结束。\n", encoding="utf-8")
    commit(project, stage)

    prepare_stage(project, stage, 2)
    carried_contract = read_json(project / "contracts/chapter-0001.json")
    carried_contract["chapter"] = 2
    write_json(stage / "contracts/chapter-0002.json", carried_contract)
    for source in (project / "intents/chapter-0001").iterdir():
        shutil.copy2(source, stage / "intents/chapter-0002" / source.name)
    protagonist = read_json(project / "project.json")["ensemble"]["protagonistId"]
    intent_path = stage / "intents/chapter-0002" / f"{protagonist}.json"
    rejected = commit(project, stage, expect=1)
    assert "intent chapter must match" in rejected["error"]
    assert read_json(project / "project.json")["lastCommittedChapter"] == 1

    carried_intent = read_json(intent_path)
    carried_intent["chapter"] = 2
    write_json(intent_path, carried_intent)
    (stage / "sessions/test-chapter-0002.md").write_text(
        "沿用第1章的前卡、意图与裁定，当前检查行动和合法性条件未变。\n", encoding="utf-8"
    )
    commit(project, stage)
    carried_intent.pop("chapter")
    original_intent = read_json(project / "intents/chapter-0001" / f"{protagonist}.json")
    original_intent.pop("chapter")
    assert carried_intent == original_intent
    assert (project / "intents/chapter-0002/ruling.json").read_bytes() == (project / "intents/chapter-0001/ruling.json").read_bytes()
    assert read_json(project / "contracts/chapter-0002.json")["arcStatus"] == "open"


def test_persistent_tail_across_commit_and_restore(base: Path) -> None:
    project, stage = base / "draft-recovery", base / "draft-recovery-stage"
    initialize(project, "持久尾稿恢复")
    prepare_stage(project, stage, 1)
    head = stage / "chapters/第0001章-测试章.md"
    tail = base / "recovery-tail.md"
    source = base / "recovery-source.md"
    tail_raw = "未提交的尾稿仍在追查另一条线索。\r\n".encode("utf-8")
    tail.write_bytes(tail_raw)
    source.write_bytes(head.read_bytes() + tail_raw)
    checkpoint_script = str(SCRIPTS / "draft_checkpoint.py")
    saved = json.loads(run(
        sys.executable, checkpoint_script, "save", "--project", str(project),
        "--after-chapter", "1", "--source", str(source), "--head", str(head), "--tail", str(tail),
    ).stdout)
    checkpoint = Path(saved["checkpoint"])
    check = [sys.executable, checkpoint_script, "check", "--project", str(project)]
    assert json.loads(run(*check, expect=1).stdout)["status"] == "awaiting-commit"
    first = commit(project, stage)
    assert json.loads(run(*check).stdout)["status"] == "ready"
    assert all(not path.startswith("drafts/") for path in first["files"])
    assert read_json(project / "project.json")["totalContentChars"] == content_chars(head.read_text())
    assert not any("未提交的尾稿" in path.read_text() for path in (project / "state").glob("*.json"))
    source.unlink()
    tail.unlink()
    prepare_stage(project, stage, 2)
    second = commit(project, stage)
    assert json.loads(run(*check).stdout)["status"] == "no-checkpoint"
    assert (checkpoint / "tail-working.md").read_bytes() == tail_raw
    run(sys.executable, str(SCRIPTS / "commit_chapter.py"), "--project", str(project), "--restore", second["backup"])
    assert json.loads(run(*check).stdout)["status"] == "ready"
    assert (checkpoint / "tail-working.md").read_bytes() == tail_raw


def test_chapter_metrics_cuts_by_length_without_padding() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        short = Path(temporary) / "short.md"
        short.write_text("# 第一章\n\n他放下笔。\n", encoding="utf-8")
        short_report = json.loads(
            run(
                sys.executable,
                str(SCRIPTS / "chapter_metrics.py"),
                str(short),
                "--target",
                "2500",
            ).stdout
        )
        ready = Path(temporary) / "ready.md"
        ready.write_text("# 第一章\n\n" + ("他推开门，把欠条放到桌上。\n\n" * 230), encoding="utf-8")
        ready_report = json.loads(
            run(
                sys.executable,
                str(SCRIPTS / "chapter_metrics.py"),
                str(ready),
                "--target",
                "2500",
            ).stdout
        )
        long = Path(temporary) / "long.md"
        long.write_text("# 第一章\n\n" + ("他推开门，把欠条放到桌上。\n\n" * 320), encoding="utf-8")
        long_report = json.loads(
            run(
                sys.executable,
                str(SCRIPTS / "chapter_metrics.py"),
                str(long),
                "--target",
                "2500",
            ).stdout
        )
    assert short_report["lengthSignal"] == "continue"
    assert short_report["lengthAction"] == "write-the-event"
    assert ready_report["lengthSignal"] == "cut"
    assert ready_report["lengthAction"] == "next-chapter"
    assert long_report["lengthSignal"] == "overflow"
    assert long_report["lengthAction"] == "move-excess"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="longform-webnovel-v2-") as temporary:
        base = Path(temporary)
        test_initialization_and_cadence(base)
        test_short_story_mode(base)
        test_novella_mode(base)
        test_committed_project_guards(base)
        test_style_profiles(base)
        test_publishing_package(base)
        test_drafting_with_unconfirmed_package(base)
        test_market_research(base)
        test_short_story_market_boundary(base)
        test_story_overlap(base)
        test_reference_guard(base)
        test_performance_feedback(base)
        test_opening_audit(base)
        test_prose_lint(base)
        test_review_gate(base)
        test_migration(base)
        test_cast_arcs(base)
        test_commit_validation_and_restore(base)
        test_event_context_carry_forward(base)
        test_persistent_tail_across_commit_and_restore(base)
    test_chapter_metrics_cuts_by_length_without_padding()
    print("longform-webnovel v8 integration checks passed")


if __name__ == "__main__":
    main()

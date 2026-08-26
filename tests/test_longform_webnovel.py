#!/usr/bin/env python3
"""Integration checks for the staged longform-webnovel v5 skill."""

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


def initialize(path: Path, title: str) -> None:
    run("python3", str(SCRIPTS / "init_project.py"), "--path", str(path), "--title", title, "--style", "fanqie-clean")
    for relative in (
        "canon/story-contract.md",
        "canon/characters.md",
        "canon/world.md",
        "planning/current-volume.md",
        "planning/rolling-outline.md",
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
        "python3",
        str(SCRIPTS / "prose_lint.py"),
        str(chapter_path),
        "--output",
        str(review_dir / f"第{chapter:04d}章-lint.json"),
    )
    digest = hashlib.sha256(chapter_text.encode("utf-8")).hexdigest()
    write_json(
        review_dir / f"第{chapter:04d}章-review.json",
        {
            "schemaVersion": 1,
            "chapter": chapter,
            "reviewedTextSha256": digest,
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
            "resolution": {"action": "accepted", "notes": "独立审阅未发现阻断问题。"},
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


def commit(project: Path, stage: Path, *, dry_run: bool = False, expect: int = 0) -> dict:
    args = ["python3", str(SCRIPTS / "commit_chapter.py"), "--project", str(project), "--staging", str(stage)]
    if dry_run:
        args.append("--dry-run")
    completed = run(*args, expect=expect)
    stream = completed.stdout if expect == 0 else completed.stderr
    return json.loads(stream)


def test_initialization_and_cadence(base: Path) -> None:
    project = base / "initial"
    initialize(project, "初始化测试")
    result = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert result["ok"]
    dry = json.loads(run("python3", str(SCRIPTS / "plan_cadence.py"), str(project), "--count", "15", "--json").stdout)
    assert [row["chapter"] for row in dry["chapters"] if row["reward"]] == [3, 5, 6, 9, 10, 12, 15]
    assert dry["chapters"][14]["reward"] == "major"
    written = json.loads(
        run("python3", str(SCRIPTS / "plan_cadence.py"), str(project), "--count", "15", "--write", "--json").stdout
    )
    assert written["added"] == 7
    assert len(read_json(project / "state/rewards.json")["beats"]) == 7


def test_short_story_mode(base: Path) -> None:
    project = base / "short-story"
    run(
        "python3",
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

    planned = json.loads(run("python3", str(SCRIPTS / "plan_cadence.py"), str(project), "--json").stdout)
    assert planned["mode"] == "fanqie-short-story"
    assert planned["count"] == 5
    assert max(row["chapter"] for row in planned["chapters"]) == 5
    assert "结局收束" in planned["chapters"][-1]["role"]
    assert planned["chapters"][-1]["reward"] == "major"
    single = json.loads(
        run("python3", str(SCRIPTS / "plan_cadence.py"), str(project), "--count", "1", "--json").stdout
    )
    assert len(single["chapters"]) == 1
    assert "开局扰动" in single["chapters"][0]["role"] and "结局收束" in single["chapters"][0]["role"]
    assert single["chapters"][0]["reward"] == "major"
    written = json.loads(run("python3", str(SCRIPTS / "plan_cadence.py"), str(project), "--write", "--json").stdout)
    assert written["added"] >= 2
    validation = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert validation["ok"]
    assert not any("chapter 15" in warning.lower() for warning in validation["warnings"])

    index = read_json(project / "project.json")
    index["shortStory"]["status"] = "complete"
    write_json(project / "project.json", index)
    incomplete = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("must commit exactly" in error for error in incomplete["errors"])
    index["shortStory"]["status"] = "planning"
    write_json(project / "project.json", index)

    index.pop("storyMode")
    index.pop("shortStory")
    write_json(project / "project.json", index)
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

    index["storyMode"] = "unknown-mode"
    write_json(project / "project.json", index)
    invalid = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    assert any("storyMode is invalid" in error for error in invalid["errors"])


def test_committed_project_guards(base: Path) -> None:
    project = base / "guard-errors"
    run("python3", str(SCRIPTS / "init_project.py"), "--path", str(project), "--title", "错误防线")
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
    failed = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
    joined = "\n".join(failed["errors"])
    assert "totalContentChars" in joined
    assert "unresolved marker" in joined
    assert "invalid dueWindow" in joined
    assert "handoff record" in joined


def test_style_profiles(base: Path) -> None:
    unselected = base / "style-unselected"
    run("python3", str(SCRIPTS / "init_project.py"), "--path", str(unselected), "--title", "待选风格")
    assert read_json(unselected / "project.json")["schemaVersion"] == 5
    assert read_json(unselected / "project.json")["styleProfile"]["status"] == "unconfirmed"
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(unselected)).stdout)["ok"]

    listed = json.loads(run("python3", str(SCRIPTS / "style_profile.py"), "--list").stdout)
    assert len(listed) == 8 and listed["fanqie-clean"] == "清晰推进"
    shown = run("python3", str(SCRIPTS / "style_profile.py"), "--show", "suspense-tight").stdout
    assert "冷峻悬疑" in shown and "公平可见" in shown

    before = (unselected / "project.json").read_text(encoding="utf-8")
    preview = json.loads(
        run(
            "python3",
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
            "python3",
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
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(unselected)).stdout)["ok"]

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
            "python3",
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
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(unselected)).stdout)["ok"]

    index = read_json(unselected / "project.json")
    index["lastCommittedChapter"] = 1
    write_json(unselected / "project.json", index)
    refused = run(
        "python3",
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
            "python3",
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
    run("python3", str(SCRIPTS / "init_project.py"), "--path", str(project), "--title", "暂定书名", "--style", "suspense-tight")
    generic = json.loads(run("python3", str(SCRIPTS / "publishing_package.py"), "--check-title", "重生归来").stdout)
    assert not generic["ok"] and generic["requiresPublicExactSearch"]
    distinctive = json.loads(run("python3", str(SCRIPTS / "publishing_package.py"), "--check-title", "雾城收件人").stdout)
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
        "python3",
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
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

    (project / "canon/publishing-package.md").write_text(
        package_text.replace("## 书名排版与字体说明", "## 排版说明"), encoding="utf-8"
    )
    invalid_layout = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)
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
    args = ("python3", str(SCRIPTS / "market_brief.py"), "--project", str(project), "--snapshot", str(snapshot_path))
    preview = json.loads(run(*args, "--dry-run").stdout)
    assert preview["dryRun"] and read_json(project / "project.json")["marketResearch"]["status"] == "unrequested"
    applied = json.loads(run(*args).stdout)
    assert applied["sourceCount"] == 2 and applied["sampleCount"] == 5
    assert "观察事实" in (project / "canon/market-brief.md").read_text(encoding="utf-8")
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

    invalid = dict(snapshot)
    invalid["sources"] = snapshot["sources"][:1]
    invalid["samples"] = snapshot["samples"][:4]
    invalid["hypotheses"] = [
        {"claim": "证据不足", "confidence": "certain", "evidenceTitles": ["不存在"]},
        {"claim": "仍然不足", "confidence": "certain", "evidenceTitles": ["观察样本1"]},
    ]
    invalid_path = base / "invalid-market.json"
    write_json(invalid_path, invalid)
    failed = json.loads(run("python3", str(SCRIPTS / "market_brief.py"), "--project", str(project), "--snapshot", str(invalid_path), expect=1).stdout)
    joined = "\n".join(failed["errors"])
    assert "at least 2 public sources" in joined and "at least 5 observed works" in joined and "confidence" in joined


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
        run("python3", str(SCRIPTS / "prose_lint.py"), str(risky), "--baseline", str(baseline)).stdout
    )
    codes = {finding["code"] for finding in result["findings"]}
    assert result["claim"] == "editorial-risk-signals-not-authorship-detection"
    assert "repeated-micro-actions" in codes and "summary-ending" in codes
    assert any(code.startswith("baseline-drift-") for code in codes)


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
    preview = json.loads(run("python3", str(SCRIPTS / "migrate_project.py"), str(project), "--dry-run").stdout)
    assert preview["changed"] and preview["dryRun"]
    assert (project / "project.json").read_text(encoding="utf-8") == before

    migrated = json.loads(run("python3", str(SCRIPTS / "migrate_project.py"), str(project)).stdout)
    assert migrated["changed"] and Path(migrated["backup"]).is_dir()
    assert read_json(project / "project.json")["rewardCadence"]["enforceFromChapter"] == 4
    rewards = read_json(project / "state/rewards.json")
    assert rewards["legacyUnauditedThrough"] == 3
    assert read_json(project / "state/cast-arcs.json")["legacyUnauditedThrough"] == 3
    assert rewards["beats"][0]["status"] == "needs-review"
    assert rewards["beats"][0]["rewardType"] == "other"
    validation = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert validation["ok"] and any("Legacy chapters through 3" in warning for warning in validation["warnings"])

    backups_before = list((project / ".webnovel" / "backups").iterdir())
    repeated = json.loads(run("python3", str(SCRIPTS / "migrate_project.py"), str(project)).stdout)
    backups_after = list((project / ".webnovel" / "backups").iterdir())
    assert not repeated["changed"]
    assert len(backups_before) == len(backups_after)

    hybrid = base / "hybrid-schema"
    create_legacy_project(hybrid)
    hybrid_index = read_json(hybrid / "project.json")
    hybrid_index["schemaVersion"] = 2
    hybrid_index["rewardCadence"].update({"supercycle": 15, "enforceFromChapter": 1})
    write_json(hybrid / "project.json", hybrid_index)
    mixed = json.loads(run("python3", str(SCRIPTS / "migrate_project.py"), str(hybrid)).stdout)
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
    upgraded = json.loads(run("python3", str(SCRIPTS / "migrate_project.py"), str(previous_v2)).stdout)
    assert upgraded["fromVersion"] == 2 and upgraded["rewardsFromVersion"] == 2
    assert upgraded["legacyUnauditedThrough"] == 0
    upgraded_index = read_json(previous_v2 / "project.json")
    assert upgraded_index["schemaVersion"] == 5
    assert upgraded_index["rewardCadence"]["enforceFromChapter"] == 1
    assert upgraded_index["styleProfile"]["status"] == "unconfirmed"
    assert upgraded_index["publishingPackage"]["status"] == "unconfirmed"
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(previous_v2)).stdout)["ok"]

    previous_v3 = base / "previous-v3"
    initialize(previous_v3, "旧版配角迁移")
    previous_v3_index = read_json(previous_v3 / "project.json")
    previous_v3_index["schemaVersion"] = 3
    write_json(previous_v3 / "project.json", previous_v3_index)
    (previous_v3 / "state/cast-arcs.json").unlink()
    upgraded_v3 = json.loads(run("python3", str(SCRIPTS / "migrate_project.py"), str(previous_v3)).stdout)
    assert upgraded_v3["fromVersion"] == 3 and upgraded_v3["castLegacyUnauditedThrough"] == 0
    assert read_json(previous_v3 / "project.json")["schemaVersion"] == 5
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(previous_v3)).stdout)["ok"]

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
    upgraded_v4 = json.loads(run("python3", str(SCRIPTS / "migrate_project.py"), str(previous_v4)).stdout)
    assert upgraded_v4["fromVersion"] == 4
    assert read_json(previous_v4 / "project.json")["reviewGate"]["enforceFromChapter"] == 2
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(previous_v4)).stdout)["ok"]


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
            "relationships": [],
        },
    ]
    write_json(cast_path, cast_doc)
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]

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
    assert json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)["ok"]
    write_json(cast_path, cast_doc)

    unknown = read_json(cast_path)
    unknown["characters"][0]["relationships"][0]["targetId"] = "missing-person"
    write_json(cast_path, unknown)
    errors = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("unknown targetId" in error for error in errors)

    missing_love_fields = read_json(cast_path)
    missing_love_fields["characters"][0]["relationships"][0].update({"targetId": "warden", "basis": "", "cost": ""})
    write_json(cast_path, missing_love_fields)
    errors = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("concrete basis" in error for error in errors) and any("concrete cost" in error for error in errors)

    missing_goal = read_json(cast_path)
    missing_goal["characters"][0]["relationships"][0].update(
        {"basis": "共同救过人", "cost": "公开真相会失去对方"}
    )
    missing_goal["characters"][0]["independentGoal"] = ""
    write_json(cast_path, missing_goal)
    errors = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("concrete independentGoal" in error for error in errors)

    missing_love_evidence = read_json(cast_path)
    missing_love_evidence["asOfChapter"] = 1
    missing_love_evidence["characters"][0]["independentGoal"] = "查清旧令来源"
    missing_love_evidence["characters"][0]["relationships"][0]["sinceChapter"] = 1
    write_json(cast_path, missing_love_evidence)
    errors = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("needs evidenceChapters for love" in error for error in errors)

    missing_history = read_json(cast_path)
    missing_history["asOfChapter"] = 1
    missing_history["characters"][0]["independentGoal"] = "查清旧令来源"
    missing_history["characters"][0]["lastAdvancedChapter"] = 1
    missing_history["characters"][0]["relationships"][0]["evidenceChapters"] = [1]
    write_json(cast_path, missing_history)
    errors = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("matching choice/delta history evidence" in error for error in errors)

    no_anchor = read_json(cast_path)
    no_anchor["asOfChapter"] = 5
    no_anchor["characters"] = []
    write_json(cast_path, no_anchor)
    index = read_json(project / "project.json")
    index["lastCommittedChapter"] = 5
    index["latestDraftChapter"] = 5
    write_json(project / "project.json", index)
    errors = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("needs at least one anchor supporting character" in error for error in errors)

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
    errors = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project), expect=1).stdout)["errors"]
    assert any("must advance by choice/consequence" in error for error in errors)


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
            "python3",
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
    rollback_validation = json.loads(run("python3", str(SCRIPTS / "validate_project.py"), str(project)).stdout)
    assert rollback_validation["ok"]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="longform-webnovel-v2-") as temporary:
        base = Path(temporary)
        test_initialization_and_cadence(base)
        test_short_story_mode(base)
        test_committed_project_guards(base)
        test_style_profiles(base)
        test_publishing_package(base)
        test_market_research(base)
        test_prose_lint(base)
        test_review_gate(base)
        test_migration(base)
        test_cast_arcs(base)
        test_commit_validation_and_restore(base)
    print("longform-webnovel v5 integration checks passed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Migrate an older longform-webnovel project to the current schema."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from webnovel_io import (
    CURRENT_CAST_SCHEMA,
    CURRENT_PROJECT_SCHEMA,
    CURRENT_REWARD_SCHEMA,
    backup_files,
    chapter_role,
    content_char_count,
    load_json,
    restore_backup,
    utc_now,
    write_json_atomic,
    write_text_atomic,
)
from webnovel_style import PRESETS, render_legacy_profile, render_profile, render_unselected_profile


CHAPTER_RE = re.compile(r"^第(\d{4,})章-.+\.md$")


def render_legacy_package(title: str) -> str:
    return f"""# 书名与封面包装

## 状态

- 包装状态：`legacy`
- 定名状态：`legacy`
- 唯一性检查：`legacy-unverified`
- 封面提示词状态：`legacy-existing`
- 小说名：{title}

这是迁移项目。保留原书名和既有封面；作者要求改名或换封面时，再执行公开检索、提供封面提示词并记录重大决策。
"""


def render_unconfirmed_package() -> str:
    return """# 书名与封面包装

## 状态

- 包装状态：`unconfirmed`
- 定名状态：待确认
- 唯一性检查：待确认
- 封面提示词状态：待确认

在第一章正文前确认书名、公开检索记录和封面提示词。
"""


def render_unrequested_market_brief() -> str:
    return """# 市场观察

## 状态

- 研究状态：`unrequested`

这是迁移项目。市场研究保持可选；需要时再保存带日期、来源和样本的公开市场快照，不追溯伪造历史研究。
"""


def upgrade_beat(beat: dict, legacy: bool) -> dict:
    upgraded = dict(beat)
    chapter = upgraded.get("chapter", 0)
    if legacy and upgraded.get("status") == "delivered":
        upgraded["status"] = "needs-review"
    upgraded.setdefault("role", chapter_role(chapter) if isinstance(chapter, int) and chapter > 0 else "待复核")
    default_type = "unassigned" if upgraded.get("status") == "planned" else "other"
    upgraded.setdefault("rewardType", default_type)
    if upgraded.get("status") != "planned" and upgraded.get("rewardType") == "unassigned":
        upgraded["rewardType"] = "other"
    upgraded.setdefault("setupChapters", [])
    upgraded.setdefault("evidence", [])
    upgraded.setdefault("cost", "")
    upgraded.setdefault("stateDeltas", [])
    upgraded.setdefault("sourceThreadIds", [])
    upgraded.setdefault("conflictType", "")
    upgraded.setdefault("solutionType", "")
    return upgraded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.project.expanduser().resolve()
    project_path = root / "project.json"
    rewards_path = root / "state" / "rewards.json"
    cast_path = root / "state" / "cast-arcs.json"
    market_path = root / "canon" / "market-brief.md"
    project = load_json(project_path)
    old_version = project.get("schemaVersion", 1)
    if not isinstance(old_version, int) or old_version <= 0:
        raise SystemExit("Invalid project schemaVersion")
    if old_version > CURRENT_PROJECT_SCHEMA:
        raise SystemExit(f"Project schema {old_version} is newer than supported schema {CURRENT_PROJECT_SCHEMA}")

    committed = project.get("lastCommittedChapter", 0)
    if not isinstance(committed, int) or committed < 0:
        raise SystemExit("Invalid lastCommittedChapter")

    original_project = json.dumps(project, ensure_ascii=False, sort_keys=True)

    if rewards_path.is_file():
        rewards = load_json(rewards_path)
        original_rewards = json.dumps(rewards, ensure_ascii=False, sort_keys=True)
        old_reward_version = rewards.get("schemaVersion", 1)
        if not isinstance(old_reward_version, int) or old_reward_version <= 0:
            raise SystemExit("Invalid rewards schemaVersion")
        if old_reward_version > CURRENT_REWARD_SCHEMA:
            raise SystemExit(f"Rewards schema {old_reward_version} is newer than supported schema {CURRENT_REWARD_SCHEMA}")
        beats = rewards.get("beats", [])
        if not isinstance(beats, list):
            raise SystemExit("Invalid rewards beats")
    else:
        rewards = {"beats": []}
        original_rewards = None
        old_reward_version = 0

    reward_legacy = old_version < 2 or old_reward_version < CURRENT_REWARD_SCHEMA
    rewards["beats"] = [upgrade_beat(beat, reward_legacy) if isinstance(beat, dict) else beat for beat in rewards["beats"]]

    if cast_path.is_file():
        cast_doc = load_json(cast_path)
        original_cast = json.dumps(cast_doc, ensure_ascii=False, sort_keys=True)
        old_cast_version = cast_doc.get("schemaVersion", 1)
        if not isinstance(old_cast_version, int) or old_cast_version <= 0:
            raise SystemExit("Invalid cast-arcs schemaVersion")
        if old_cast_version > CURRENT_CAST_SCHEMA:
            raise SystemExit(f"Cast schema {old_cast_version} is newer than supported schema {CURRENT_CAST_SCHEMA}")
    else:
        cast_doc = {"characters": []}
        original_cast = None
        old_cast_version = 0
    cast_doc["schemaVersion"] = CURRENT_CAST_SCHEMA
    if old_version < 4 or original_cast is None:
        cast_doc["asOfChapter"] = committed
        cast_doc["legacyUnauditedThrough"] = max(
            int(cast_doc.get("legacyUnauditedThrough", 0) or 0),
            committed,
        )
    else:
        cast_doc.setdefault("asOfChapter", committed)
        cast_doc.setdefault("legacyUnauditedThrough", 0)
    cast_doc.setdefault("characters", [])

    cadence = project.get("rewardCadence") if isinstance(project.get("rewardCadence"), dict) else {}
    cadence.setdefault("smallEvery", 3)
    cadence.setdefault("majorEvery", 5)
    cadence.setdefault("supercycle", 15)
    cadence.setdefault("overlapPolicy", "major-absorbs-small")
    if reward_legacy:
        existing_enforce = cadence.get("enforceFromChapter", 1)
        if not isinstance(existing_enforce, int) or isinstance(existing_enforce, bool) or existing_enforce <= 0:
            existing_enforce = 1
        cadence["enforceFromChapter"] = max(committed + 1, existing_enforce)
    else:
        cadence.setdefault("enforceFromChapter", 1)
    project["rewardCadence"] = cadence
    project.setdefault("storyMode", "serial")
    review_gate = project.get("reviewGate") if isinstance(project.get("reviewGate"), dict) else {}
    review_gate.setdefault("enforceFromChapter", committed + 1 if old_version < 5 else 1)
    review_gate.setdefault("editorRequired", True)
    review_gate.setdefault("readerRequired", True)
    review_gate.setdefault("lintRequired", True)
    project["reviewGate"] = review_gate
    market_research = project.get("marketResearch")
    if not isinstance(market_research, dict):
        market_research = {
            "status": "unrequested",
            "asOfDate": None,
            "sourceCount": 0,
            "sampleCount": 0,
            "updatedAt": utc_now(),
        }
        project["marketResearch"] = market_research
    else:
        market_research.setdefault("status", "unrequested")
        market_research.setdefault("asOfDate", None)
        market_research.setdefault("sourceCount", 0)
        market_research.setdefault("sampleCount", 0)
        market_research.setdefault("updatedAt", utc_now())
    market_needs_write = not market_path.is_file()
    project["schemaVersion"] = CURRENT_PROJECT_SCHEMA
    style_path = root / "canon" / "style-profile.md"
    style_needs_write = not style_path.is_file()
    style = project.get("styleProfile")
    if not isinstance(style, dict):
        style_needs_write = True
        style = {
            "primary": "legacy-observed" if committed else "unselected",
            "secondary": None,
            "status": "observed" if committed else "unconfirmed",
            "updatedAt": utc_now(),
        }
        project["styleProfile"] = style
    else:
        style.setdefault("secondary", None)
        style.setdefault("status", "observed" if committed else "unconfirmed")
        style.setdefault("updatedAt", utc_now())
    if committed and old_version < CURRENT_PROJECT_SCHEMA and style.get("status") == "unconfirmed":
        style_needs_write = True
        style.update(
            {
                "primary": "legacy-observed",
                "secondary": None,
                "status": "observed",
                "updatedAt": utc_now(),
            }
        )
    if style_needs_write and style.get("primary") not in PRESETS:
        style.update(
            {
                "primary": "legacy-observed" if committed else "unselected",
                "secondary": None,
                "status": "observed" if committed else "unconfirmed",
                "updatedAt": utc_now(),
            }
        )
    package_path = root / "canon" / "publishing-package.md"
    package_needs_write = not package_path.is_file()
    package = project.get("publishingPackage")
    if not isinstance(package, dict):
        package_needs_write = True
        package = {
            "status": "legacy" if committed else "unconfirmed",
            "titleStatus": "legacy" if committed else "unconfirmed",
            "uniquenessStatus": "legacy-unverified" if committed else "unconfirmed",
            "coverPromptStatus": "legacy-existing" if committed else "unconfirmed",
            "updatedAt": utc_now(),
        }
        project["publishingPackage"] = package
    else:
        package.setdefault("status", "legacy" if committed else "unconfirmed")
        package.setdefault("titleStatus", "legacy" if committed else "unconfirmed")
        package.setdefault("uniquenessStatus", "legacy-unverified" if committed else "unconfirmed")
        package.setdefault("coverPromptStatus", "legacy-existing" if committed else "unconfirmed")
        package.setdefault("updatedAt", utc_now())
    if package_needs_write or (committed and old_version < CURRENT_PROJECT_SCHEMA and package.get("status") == "unconfirmed"):
        package_needs_write = True
        package.update(
            {
                "status": "legacy" if committed else "unconfirmed",
                "titleStatus": "legacy" if committed else "unconfirmed",
                "uniquenessStatus": "legacy-unverified" if committed else "unconfirmed",
                "coverPromptStatus": "legacy-existing" if committed else "unconfirmed",
                "updatedAt": utc_now(),
            }
        )
    total_content_chars = 0
    for chapter_path in (root / "chapters").glob("*.md"):
        match = CHAPTER_RE.match(chapter_path.name)
        if match and int(match.group(1)) <= committed:
            total_content_chars += content_char_count(chapter_path.read_text(encoding="utf-8"))
    project["totalContentChars"] = total_content_chars

    rewards["schemaVersion"] = CURRENT_REWARD_SCHEMA
    rewards["asOfChapter"] = committed
    rewards["legacyUnauditedThrough"] = max(int(rewards.get("legacyUnauditedThrough", 0) or 0), committed if reward_legacy else 0)

    changed = (
        style_needs_write
        or package_needs_write
        or market_needs_write
        or original_rewards is None
        or original_cast is None
        or json.dumps(project, ensure_ascii=False, sort_keys=True) != original_project
        or json.dumps(rewards, ensure_ascii=False, sort_keys=True) != original_rewards
        or json.dumps(cast_doc, ensure_ascii=False, sort_keys=True) != original_cast
    )
    result = {
        "fromVersion": old_version,
        "rewardsFromVersion": old_reward_version,
        "toVersion": CURRENT_PROJECT_SCHEMA,
        "legacyUnauditedThrough": rewards["legacyUnauditedThrough"],
        "castLegacyUnauditedThrough": cast_doc["legacyUnauditedThrough"],
        "changed": changed,
        "dryRun": args.dry_run,
    }
    if not args.dry_run and changed:
        paths = [Path("project.json"), Path("state/rewards.json"), Path("state/cast-arcs.json")]
        if style_needs_write:
            paths.append(Path("canon/style-profile.md"))
        if package_needs_write:
            paths.append(Path("canon/publishing-package.md"))
        if market_needs_write:
            paths.append(Path("canon/market-brief.md"))
        backup = backup_files(root, paths, f"migration-v{old_version}-to-v{CURRENT_PROJECT_SCHEMA}")
        try:
            write_json_atomic(project_path, project)
            write_json_atomic(rewards_path, rewards)
            write_json_atomic(cast_path, cast_doc)
            if style_needs_write:
                primary = style.get("primary")
                secondary = style.get("secondary")
                if primary in PRESETS and (secondary is None or secondary in PRESETS):
                    style_content = render_profile(primary, secondary, status=style.get("status", "active"))
                else:
                    style_content = render_legacy_profile() if committed else render_unselected_profile()
                write_text_atomic(style_path, style_content)
            if package_needs_write:
                package_content = render_legacy_package(str(project.get("title", "原书名"))) if committed else render_unconfirmed_package()
                write_text_atomic(package_path, package_content)
            if market_needs_write:
                write_text_atomic(market_path, render_unrequested_market_brief())
        except Exception:
            restore_backup(root, backup)
            raise
        result["backup"] = str(backup)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

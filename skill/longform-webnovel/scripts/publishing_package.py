#!/usr/bin/env python3
"""Check a title or apply a confirmed title and cover-prompt package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from webnovel_io import CURRENT_PROJECT_SCHEMA, backup_files, load_json, restore_backup, utc_now, write_json_atomic, write_text_atomic


GENERIC_EXACT = {
    "重生归来",
    "逆天改命",
    "都市修仙",
    "绝世武神",
    "无敌战神",
    "最强赘婿",
    "末世求生",
    "巅峰人生",
}
FORMULAIC_PATTERNS = (
    (re.compile(r"^(开局|重生|穿越|觉醒).{0,4}(系统|签到|无敌|逆袭)"), "常见开局/系统公式"),
    (re.compile(r"^(最强|绝世|无敌|极品).{0,6}(神|王|帝|婿|高手|战神)$"), "常见最强身份公式"),
    (re.compile(r"^我在.{1,8}(当|做|成了|修仙|种田)$"), "常见‘我在某处’公式"),
)


def analyze_title(title: str) -> dict:
    normalized = re.sub(r"[\s《》〈〉【】]", "", title)
    errors = []
    warnings = []
    if len(normalized) < 4:
        errors.append("书名少于 4 个字符，辨识度通常不足")
    if len(normalized) > 30:
        warnings.append("书名超过 30 个字符，封面排版和口头传播成本较高")
    if normalized in GENERIC_EXACT:
        errors.append("书名属于高频泛化标题")
    for pattern, message in FORMULAIC_PATTERNS:
        if pattern.search(normalized):
            warnings.append(message)
    return {
        "title": title.strip(),
        "normalized": normalized,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "requiresPublicExactSearch": True,
    }


def read_bounded(path: Path, label: str, minimum: int, maximum: int) -> str:
    content = path.expanduser().read_text(encoding="utf-8").strip()
    if not minimum <= len(content) <= maximum:
        raise ValueError(f"{label} must contain {minimum}-{maximum} characters")
    return content


def render_package(title: str, positioning: str, cover_prompt: str, negative_prompt: str, research: str, checked_at: str) -> str:
    return f"""# 书名与封面包装

## 状态

- 包装状态：`active`
- 定名状态：`confirmed`
- 唯一性检查：`completed`
- 封面提示词状态：`ready`
- 小说名：{title}
- 检查时间：{checked_at}

## 定位

{positioning}

## 公开检索记录

{research}

精确检索只能降低撞名和俗套风险，不构成商标、版权或全网唯一性保证。

## 封面主提示词

{cover_prompt}

## 负面提示词

{negative_prompt or "低清晰度，错误文字，乱码标题，水印，平台标识，过度拥挤，主体被裁切，廉价素材拼贴，模仿具体艺术家风格"}

## 排版说明

优先生成无文字封面底图，为中文书名、作者名和平台角标保留明确安全区；文字在后期排版，不依赖图像模型生成汉字。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-title", help="Analyze one title without changing a project")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--positioning-file", type=Path)
    parser.add_argument("--cover-prompt-file", type=Path)
    parser.add_argument("--negative-prompt-file", type=Path)
    parser.add_argument("--research-notes-file", type=Path)
    parser.add_argument("--confirmed", action="store_true", help="Confirm changing a title after chapters have been committed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.check_title:
        print(json.dumps(analyze_title(args.check_title), ensure_ascii=False, indent=2))
        return 0
    required = (args.project, args.title, args.positioning_file, args.cover_prompt_file, args.research_notes_file)
    if not all(required):
        parser.error("use --check-title or provide --project, --title, --positioning-file, --cover-prompt-file, and --research-notes-file")

    title_result = analyze_title(args.title)
    if not title_result["ok"]:
        raise SystemExit("; ".join(title_result["errors"]))
    positioning = read_bounded(args.positioning_file, "positioning", 20, 800)
    cover_prompt = read_bounded(args.cover_prompt_file, "cover prompt", 80, 3000)
    research = read_bounded(args.research_notes_file, "research notes", 30, 3000)
    negative = read_bounded(args.negative_prompt_file, "negative prompt", 10, 1000) if args.negative_prompt_file else ""

    root = args.project.expanduser().resolve()
    project_path = root / "project.json"
    package_path = root / "canon" / "publishing-package.md"
    project = load_json(project_path)
    if project.get("schemaVersion") != CURRENT_PROJECT_SCHEMA:
        raise SystemExit("Project schema is old; run migrate_project.py first")
    committed = project.get("lastCommittedChapter", 0)
    if not isinstance(committed, int) or isinstance(committed, bool) or committed < 0:
        raise SystemExit("Invalid lastCommittedChapter")
    title_changed = project.get("title") != args.title.strip()
    if committed > 0 and title_changed and not args.confirmed:
        raise SystemExit("Changing the title after committed chapters is a major decision; pass --confirmed after author approval")

    checked_at = utc_now()
    content = render_package(args.title.strip(), positioning, cover_prompt, negative, research, checked_at)
    proposed = dict(project)
    proposed["title"] = args.title.strip()
    proposed["publishingPackage"] = {
        "status": "active",
        "titleStatus": "confirmed",
        "uniquenessStatus": "completed",
        "coverPromptStatus": "ready",
        "updatedAt": checked_at,
    }
    proposed["updatedAt"] = checked_at
    result = {
        "ok": True,
        "dryRun": args.dry_run,
        "title": args.title.strip(),
        "titleWarnings": title_result["warnings"],
        "project": str(root),
    }
    if not args.dry_run:
        backup = backup_files(root, [Path("project.json"), Path("canon/publishing-package.md")], "publishing-package")
        try:
            write_text_atomic(package_path, content)
            write_json_atomic(project_path, proposed)
        except Exception:
            restore_backup(root, backup)
            raise
        result["backup"] = str(backup)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

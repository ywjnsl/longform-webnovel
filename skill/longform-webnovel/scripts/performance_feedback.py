#!/usr/bin/env python3
"""Save a publication snapshot and diagnose the earliest measurable funnel bottleneck."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from webnovel_io import (
    CURRENT_PROJECT_SCHEMA,
    backup_files,
    load_json,
    restore_backup,
    utc_now,
    write_json_atomic,
    write_text_atomic,
)


STATUSES = {"unknown", "initial", "initial-complete", "normal", "limited"}
COUNT_FIELDS = ("impressions", "reads", "completedReads", "unlocks", "likes", "comments", "bookshelves")


def validate(data: dict) -> list[str]:
    errors = []
    if data.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if not isinstance(data.get("platform"), str) or not data["platform"].strip():
        errors.append("platform must be a non-empty string")
    for field in ("windowStart", "windowEnd"):
        try:
            date.fromisoformat(data.get(field))
        except (TypeError, ValueError):
            errors.append(f"{field} must be YYYY-MM-DD")
    try:
        if date.fromisoformat(data.get("windowStart")) > date.fromisoformat(data.get("windowEnd")):
            errors.append("windowStart cannot be after windowEnd")
    except (TypeError, ValueError):
        pass
    if data.get("recommendationStatus") not in STATUSES:
        errors.append("recommendationStatus must be unknown, initial, initial-complete, normal, or limited")
    for field in COUNT_FIELDS:
        value = data.get(field)
        if field in {"impressions", "reads"} and value is None:
            errors.append(f"{field} is required")
        elif value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            errors.append(f"{field} must be a non-negative integer or null")
    impressions = data.get("impressions")
    reads = data.get("reads")
    if isinstance(impressions, int) and isinstance(reads, int) and reads > impressions:
        errors.append("reads cannot exceed impressions")
    completed = data.get("completedReads")
    if isinstance(completed, int) and isinstance(reads, int) and completed > reads:
        errors.append("completedReads cannot exceed reads")
    return errors


def percentage(part: int | None, whole: int | None) -> float | None:
    if part is None or whole in (None, 0):
        return None
    return round(part / whole, 4)


def diagnose(data: dict, min_impressions: int, min_reads: int, click_rate: float, completion_rate: float) -> dict:
    impressions = data["impressions"]
    reads = data["reads"]
    completed = data.get("completedReads")
    read_rate = percentage(reads, impressions)
    finish_rate = percentage(completed, reads)
    if impressions < min_impressions:
        stage = "insufficient-exposure"
        action = "核对签约和初期推荐状态、分类标签及数据更新时间；样本不足，不据此改正文或判断包装成败。"
    elif read_rate is not None and read_rate < click_rate:
        stage = "entry-conversion"
        action = "优先检查书名、封面、简介和推荐标题是否承诺同一件事；一次只改一个入口变量。"
    elif reads < min_reads:
        stage = "insufficient-reading-sample"
        action = "入口已有阅读但样本仍不足，继续积累可比窗口，不用互动为零判断结局质量。"
    elif finish_rate is not None and finish_rate < completion_rate:
        stage = "reading-retention"
        action = "先审前300字、第一次回报与试读节点，再定位读者流失段落。"
    elif completed is not None and sum(data.get(field) or 0 for field in ("likes", "comments", "bookshelves")) == 0:
        stage = "payoff-expression"
        action = "检查结局回报和情绪表达是否清楚，保留自然可表态的位置，不添加求互动文案。"
    else:
        stage = "no-demonstrated-bottleneck"
        action = "当前字段没有显示明确瓶颈；继续收集相同推荐状态下的可比窗口。"
    return {"stage": stage, "readRate": read_rate, "completionRate": finish_rate, "recommendedAction": action}


def render(data: dict, result: dict, thresholds: dict) -> str:
    def show_rate(value: float | None) -> str:
        return "未提供" if value is None else f"{value * 100:.2f}%"

    return f"""# 发布后数据诊断

- 平台：{data['platform']}
- 统计窗口：{data['windowStart']} 至 {data['windowEnd']}
- 推荐状态：`{data['recommendationStatus']}`
- 展现：{data['impressions']}
- 阅读：{data['reads']}
- 阅读率：{show_rate(result['readRate'])}
- 完读率：{show_rate(result['completionRate'])}
- 当前诊断：`{result['stage']}`

## 下一步

{result['recommendedAction']}

## 口径

诊断线为展现 {thresholds['minImpressions']}、阅读 {thresholds['minReads']}、阅读率 {thresholds['clickRate'] * 100:.2f}%、完读率 {thresholds['completionRate'] * 100:.2f}%。这些是本地编辑诊断参数，不是番茄官方流量标准；平台不保证持续给量，单日小样本不能证明永久限流。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--min-impressions", type=int, default=100)
    parser.add_argument("--min-reads", type=int, default=30)
    parser.add_argument("--click-rate", type=float, default=0.05)
    parser.add_argument("--completion-rate", type=float, default=0.50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.min_impressions <= 0 or args.min_reads <= 0 or not 0 <= args.click_rate <= 1 or not 0 <= args.completion_rate <= 1:
        raise SystemExit("Thresholds must be positive counts and rates between 0 and 1")

    root = args.project.expanduser().resolve()
    project_path = root / "project.json"
    project = load_json(project_path)
    if project.get("schemaVersion") != CURRENT_PROJECT_SCHEMA:
        raise SystemExit("Project schema is not current; run migrate_project.py first")
    data = load_json(args.input.expanduser().resolve())
    errors = validate(data)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    thresholds = {
        "minImpressions": args.min_impressions,
        "minReads": args.min_reads,
        "clickRate": args.click_rate,
        "completionRate": args.completion_rate,
    }
    result = diagnose(data, args.min_impressions, args.min_reads, args.click_rate, args.completion_rate)
    relative = Path("performance/snapshots") / f"{data['windowStart']}-to-{data['windowEnd']}.json"
    diagnosis_path = Path("performance/latest-diagnosis.md")
    now = utc_now()
    proposed = dict(project)
    previous_feedback = project.get("performanceFeedback")
    if not isinstance(previous_feedback, dict):
        previous_feedback = {}
    proposed["performanceFeedback"] = {
        "status": "active",
        "latestWindowEnd": data["windowEnd"],
        "latestStage": result["stage"],
        "snapshotCount": previous_feedback.get("snapshotCount", 0) + (0 if (root / relative).exists() else 1),
        "updatedAt": now,
    }
    proposed["updatedAt"] = now
    output = {"ok": True, "dryRun": args.dry_run, **result, "snapshot": relative.as_posix()}
    if not args.dry_run:
        backup = backup_files(root, [Path("project.json"), relative, diagnosis_path], "performance-feedback")
        try:
            write_json_atomic(project_path, proposed)
            write_json_atomic(root / relative, data)
            write_text_atomic(root / diagnosis_path, render(data, result, thresholds))
        except Exception:
            restore_backup(root, backup)
            raise
        output["backup"] = str(backup)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

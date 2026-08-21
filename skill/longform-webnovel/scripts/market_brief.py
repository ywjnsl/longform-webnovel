#!/usr/bin/env python3
"""Validate and save an evidence-backed public-market snapshot for a webnovel project."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from webnovel_io import CURRENT_PROJECT_SCHEMA, backup_files, load_json, utc_now, write_json_atomic, write_text_atomic


VALID_CONFIDENCE = {"low", "medium", "high"}
SAFE_NAME_RE = re.compile(r"[^a-z0-9-]+")


def concrete(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: object, label: str, minimum: int, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        errors.append(f"{label} needs at least {minimum} item(s)")
        return []
    result = []
    for index, item in enumerate(value):
        if not concrete(item):
            errors.append(f"{label} item #{index + 1} must be a non-empty string")
        else:
            result.append(item.strip())
    return result


def validate_snapshot(snapshot: dict) -> list[str]:
    errors: list[str] = []
    if snapshot.get("schemaVersion") != 1:
        errors.append("snapshot schemaVersion must be 1")
    as_of = snapshot.get("asOfDate")
    try:
        date.fromisoformat(as_of)
    except (TypeError, ValueError):
        errors.append("asOfDate must be YYYY-MM-DD")
    if not concrete(snapshot.get("platform")):
        errors.append("platform must be a non-empty string")

    scope = snapshot.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        for field in ("audience", "genre", "ranking", "sampleWindow"):
            if not concrete(scope.get(field)):
                errors.append(f"scope.{field} must be a non-empty string")

    sources = snapshot.get("sources")
    source_urls: set[str] = set()
    if not isinstance(sources, list) or len(sources) < 2:
        errors.append("sources needs at least 2 public sources")
    else:
        for index, source in enumerate(sources):
            label = f"source #{index + 1}"
            if not isinstance(source, dict):
                errors.append(f"{label} must be an object")
                continue
            if not concrete(source.get("title")):
                errors.append(f"{label} needs a title")
            try:
                date.fromisoformat(source.get("accessedAt"))
            except (TypeError, ValueError):
                errors.append(f"{label} accessedAt must be YYYY-MM-DD")
            url = source.get("url")
            parsed = urlparse(url) if isinstance(url, str) else None
            if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{label} needs a valid public http(s) URL")
            elif url in source_urls:
                errors.append(f"Duplicate source URL: {url}")
            else:
                source_urls.add(url)

    samples = snapshot.get("samples")
    sample_titles: set[str] = set()
    if not isinstance(samples, list) or len(samples) < 5:
        errors.append("samples needs at least 5 observed works")
    else:
        for index, sample in enumerate(samples):
            label = f"sample #{index + 1}"
            if not isinstance(sample, dict):
                errors.append(f"{label} must be an object")
                continue
            title = sample.get("title")
            if not concrete(title):
                errors.append(f"{label} needs a title")
            elif title in sample_titles:
                errors.append(f"Duplicate sample title: {title}")
            else:
                sample_titles.add(title.strip())
            if sample.get("sourceUrl") not in source_urls:
                errors.append(f"{label} sourceUrl must reference sources")
            string_list(sample.get("tags"), f"{label}.tags", 1, errors)
            string_list(sample.get("observedSignals"), f"{label}.observedSignals", 1, errors)

    string_list(snapshot.get("observations"), "observations", 3, errors)
    string_list(snapshot.get("opportunities"), "opportunities", 2, errors)
    string_list(snapshot.get("avoidCopying"), "avoidCopying", 2, errors)
    hypotheses = snapshot.get("hypotheses")
    if not isinstance(hypotheses, list) or len(hypotheses) < 2:
        errors.append("hypotheses needs at least 2 item(s)")
    else:
        for index, hypothesis in enumerate(hypotheses):
            label = f"hypothesis #{index + 1}"
            if not isinstance(hypothesis, dict):
                errors.append(f"{label} must be an object")
                continue
            if not concrete(hypothesis.get("claim")):
                errors.append(f"{label} needs a concrete claim")
            if hypothesis.get("confidence") not in VALID_CONFIDENCE:
                errors.append(f"{label} confidence must be low, medium, or high")
            evidence_titles = string_list(hypothesis.get("evidenceTitles"), f"{label}.evidenceTitles", 1, errors)
            for title in evidence_titles:
                if title not in sample_titles:
                    errors.append(f"{label} references unknown sample title: {title}")
    return errors


def render(snapshot: dict) -> str:
    scope = snapshot["scope"]
    lines = [
        "# 市场观察",
        "",
        "## 状态",
        "",
        "- 研究状态：`completed`",
        f"- 截止日期：{snapshot['asOfDate']}",
        f"- 平台：{snapshot['platform']}",
        f"- 受众：{scope['audience']}",
        f"- 题材范围：{scope['genre']}",
        f"- 榜单范围：{scope['ranking']}",
        f"- 样本窗口：{scope['sampleWindow']}",
        "",
        "市场数据只用于判断读者需求、竞争密度和差异化空间，不授权复制样本作品的书名、人设、表达或情节组合。",
        "",
        "## 来源",
        "",
    ]
    for source in snapshot["sources"]:
        lines.append(f"- [{source['title']}]({source['url']})，访问于 {source['accessedAt']}")
    lines.extend(["", "## 样本", "", "| 作品 | 标签 | 可观察信号 |", "|---|---|---|"])
    for sample in snapshot["samples"]:
        title = sample["title"].replace("|", "｜")
        tags = "、".join(sample["tags"]).replace("|", "｜")
        signals = "；".join(sample["observedSignals"]).replace("|", "｜")
        lines.append(f"| [{title}]({sample['sourceUrl']}) | {tags} | {signals} |")
    lines.extend(["", "## 观察事实", ""])
    lines.extend(f"- {item}" for item in snapshot["observations"])
    lines.extend(["", "## 推断", ""])
    for hypothesis in snapshot["hypotheses"]:
        evidence = "、".join(hypothesis["evidenceTitles"])
        lines.append(f"- **{hypothesis['confidence']}**：{hypothesis['claim']}（样本：{evidence}）")
    lines.extend(["", "## 可利用空位", ""])
    lines.extend(f"- {item}" for item in snapshot["opportunities"])
    lines.extend(["", "## 创作隔离线", ""])
    lines.extend(f"- {item}" for item in snapshot["avoidCopying"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.project.expanduser().resolve()
    project_path = root / "project.json"
    project = load_json(project_path)
    if project.get("schemaVersion") != CURRENT_PROJECT_SCHEMA:
        raise SystemExit("Project schema is not current; run migrate_project.py first")
    snapshot = load_json(args.snapshot.expanduser().resolve())
    errors = validate_snapshot(snapshot)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    platform_name = snapshot["platform"].strip()
    platform_slug = SAFE_NAME_RE.sub("-", platform_name.lower()).strip("-")
    if not platform_slug:
        platform_slug = f"market-{hashlib.sha256(platform_name.encode('utf-8')).hexdigest()[:8]}"
    relative_snapshot = Path("research/market-snapshots") / f"{snapshot['asOfDate']}-{platform_slug}.json"
    brief_path = root / "canon/market-brief.md"
    now = utc_now()
    project["marketResearch"] = {
        "status": "completed",
        "asOfDate": snapshot["asOfDate"],
        "sourceCount": len(snapshot["sources"]),
        "sampleCount": len(snapshot["samples"]),
        "updatedAt": now,
    }
    result = {
        "ok": True,
        "dryRun": args.dry_run,
        "snapshot": relative_snapshot.as_posix(),
        "sourceCount": len(snapshot["sources"]),
        "sampleCount": len(snapshot["samples"]),
    }
    if not args.dry_run:
        backup = backup_files(root, [Path("project.json"), Path("canon/market-brief.md"), relative_snapshot], "market-brief")
        write_json_atomic(project_path, project)
        write_json_atomic(root / relative_snapshot, snapshot)
        write_text_atomic(brief_path, render(snapshot))
        result["backup"] = str(backup)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

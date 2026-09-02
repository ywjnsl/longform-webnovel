#!/usr/bin/env python3
"""Shared safe file operations for longform-webnovel scripts."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import uuid
import math
from datetime import datetime, timezone
from pathlib import Path


CURRENT_PROJECT_SCHEMA = 5
CURRENT_REWARD_SCHEMA = 2
CURRENT_CAST_SCHEMA = 1
VALID_STORY_MODES = {"serial", "fanqie-short-story"}
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
ASCII_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_markdown(text: str) -> str:
    lines = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line.lstrip().startswith("#"):
            continue
        lines.append(re.sub(r"!?(?:\[([^]]*)\])\([^)]*\)", r"\1", line))
    return "\n".join(lines)


def content_char_count(text: str) -> int:
    body = strip_markdown(text)
    return len(CJK_RE.findall(body)) + len(ASCII_WORD_RE.findall(body))


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def copy_file_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    temp_path = Path(temporary)
    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)


def write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def backup_files(root: Path, relative_paths: list[Path], label: str) -> Path:
    backup_root = root / ".webnovel" / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_root / f"{label}-{stamp}-{uuid.uuid4().hex[:8]}"
    files_root = backup / "files"
    files_root.mkdir(parents=True)

    records = []
    for relative in sorted(set(relative_paths), key=lambda item: item.as_posix()):
        source = root / relative
        existed = source.is_file()
        records.append({"path": relative.as_posix(), "existed": existed})
        if existed:
            destination = files_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    write_json_atomic(
        backup / "manifest.json",
        {"schemaVersion": 1, "createdAt": utc_now(), "label": label, "files": records},
    )
    return backup


def restore_backup(root: Path, backup: Path) -> None:
    backup = backup.resolve()
    allowed = (root / ".webnovel" / "backups").resolve()
    try:
        backup.relative_to(allowed)
    except ValueError as exc:
        raise ValueError("Backup must be inside the project's .webnovel/backups directory") from exc

    manifest = load_json(backup / "manifest.json")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("Invalid backup manifest")

    for record in records:
        relative = Path(record["path"])
        destination = root / relative
        if record.get("existed"):
            copy_file_atomic(backup / "files" / relative, destination)
        else:
            destination.unlink(missing_ok=True)


def chapter_role(chapter: int) -> str:
    roles = {
        1: "起势，建立当轮目标",
        2: "加压，制造明确缺口",
        3: "第一次小兑现",
        4: "扩大代价，为大兑现蓄力",
        5: "第一次阶段大兑现",
        6: "承接胜利余波，交付新筹码或关系收益",
        7: "打开由旧后果导致的新局面",
        8: "二次加压",
        9: "第二次小兑现",
        10: "第二次阶段大兑现",
        11: "承担胜利后果",
        12: "第三次小兑现",
        13: "多线汇合",
        14: "高潮蓄力，锁定不可回避的选择",
        15: "超级循环高潮，同时吸收小爽点职责",
    }
    return roles[(chapter - 1) % 15 + 1]


def story_mode(project: dict) -> str:
    """Treat pre-mode projects as serial projects for backward compatibility."""
    return project.get("storyMode", "serial")


def short_story_anchors(total_sections: int) -> dict[int, dict]:
    """Map percentage-based short-story turns onto a finite section count."""
    markers = (
        (0.10, "开局扰动：尽快让核心异常、欲望或压力发生", None),
        (0.25, "不可逆选择：主角主动进入主要冲突", "small"),
        (0.50, "中点翻转：认知、关系或目标发生实质改写", "small"),
        (0.80, "决定性对抗：主要矛盾进入不可回避的解决", "major"),
        (1.00, "结局收束：兑现主承诺并交代关键后果", "major"),
    )
    anchors: dict[int, dict] = {}
    for ratio, role, reward in markers:
        section = max(1, min(total_sections, math.ceil(total_sections * ratio)))
        anchor = anchors.setdefault(section, {"roles": [], "reward": None})
        anchor["roles"].append(role)
        if reward == "major" or (reward == "small" and anchor["reward"] is None):
            anchor["reward"] = reward
    return anchors


def required_reward(chapter: int, cadence: dict) -> str | None:
    small = cadence["smallEvery"]
    major = cadence["majorEvery"]
    if chapter % major == 0:
        return "major"
    if chapter % small == 0:
        return "small"
    return None


def blank_beat(chapter: int, level: str, role: str | None = None) -> dict:
    return {
        "chapter": chapter,
        "level": level,
        "status": "planned",
        "role": role or chapter_role(chapter),
        "rewardType": "unassigned",
        "payoff": "待规划",
        "setupChapters": [],
        "evidence": [],
        "cost": "",
        "stateDeltas": [],
        "sourceThreadIds": [],
        "conflictType": "",
        "solutionType": "",
    }

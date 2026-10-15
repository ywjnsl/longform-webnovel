#!/usr/bin/env python3
"""Generate or persist serial reward beats or short-story structural anchors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from webnovel_io import (
    CURRENT_PROJECT_SCHEMA,
    backup_files,
    blank_beat,
    load_json,
    VALID_STORY_MODES,
    finite_story_settings,
    novella_stages,
    short_story_anchors,
    story_mode,
    write_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--from-chapter", type=int, dest="start")
    parser.add_argument("--count", type=int, help="Serial horizon or total short-story section count")
    parser.add_argument("--write", action="store_true", help="Add missing reward anchors to state/rewards.json")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = args.project.expanduser().resolve()
    project = load_json(root / "project.json")
    rewards_path = root / "state" / "rewards.json"
    rewards = load_json(rewards_path)
    if project.get("schemaVersion", 1) < CURRENT_PROJECT_SCHEMA:
        raise SystemExit("Project schema is old; run migrate_project.py first")
    mode = story_mode(project)
    if mode not in VALID_STORY_MODES:
        raise SystemExit(f"Unsupported storyMode: {mode}")
    if mode == "novella":
        if args.count is not None or args.start is not None:
            raise SystemExit("Novella stages do not accept --count or --from-chapter chapter assignments")
        settings = finite_story_settings(project)
        payload = {
            "mode": mode,
            "targetTotalChars": settings.get("targetTotalChars"),
            "stages": novella_stages(),
            "chapters": [],
            "added": 0,
            "backup": None,
        }
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("短中篇全书阶段（不绑定章号或平均字数）：")
            for stage in payload["stages"]:
                print(f"- {stage['role']}")
            print("在 planning/current-volume.md 填写阶段选择、代价和副线回收；兑现记在实际发生的章节。")
            if args.write:
                print("Added 0 reward anchor(s). No chapter numbers were preassigned.")
        return 0
    default_count = 15 if mode == "serial" else project.get("shortStory", {}).get("plannedSections", 5)
    count = args.count if args.count is not None else default_count
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0 or count > 300:
        raise SystemExit("--count must be between 1 and 300")

    committed = project.get("lastCommittedChapter", 0)
    start = args.start if args.start is not None else (committed + 1 if mode == "serial" else 1)
    if start <= 0:
        raise SystemExit("--from-chapter must be positive")
    if mode == "serial" and args.write and start <= committed:
        raise SystemExit("Refusing to write planned beats into already committed chapters")

    cadence = project.get("rewardCadence", {})
    spine_cadence = {
        "smallEverySpineSegments": cadence.get("smallEvery", 3),
        "majorEverySpineSegments": cadence.get("majorEvery", 5),
        "sideExcludedUnlessPaysSpine": True,
    }
    rows = []
    if mode != "serial":
        anchors = short_story_anchors(count)
        for chapter in range(start, count + 1):
            anchor = anchors.get(chapter)
            rows.append(
                {
                    "chapter": chapter,
                    "role": "；".join(anchor["roles"]) if anchor else "因果推进：冲突、选择、揭示或兑现至少推进一项",
                    "reward": anchor["reward"] if anchor else None,
                }
            )

    added = 0
    backup = None
    if args.write:
        beats = rewards.get("beats")
        if not isinstance(beats, list):
            raise SystemExit("state/rewards.json field 'beats' must be an array")
        existing = {beat.get("chapter") for beat in beats if isinstance(beat, dict)}
        for row in rows:
            if row["reward"] and row["chapter"] > committed and row["chapter"] not in existing:
                beats.append(blank_beat(row["chapter"], row["reward"], row["role"]))
                added += 1
        beats.sort(key=lambda beat: beat.get("chapter", 0))
        if added:
            backup = backup_files(root, [Path("state/rewards.json")], "cadence-plan")
            write_json_atomic(rewards_path, rewards)

    if args.as_json:
        payload = {
            "mode": mode,
            "start": start,
            "count": count,
            "added": added,
            "backup": str(backup) if backup else None,
            "chapters": rows,
        }
        if mode == "serial":
            payload["spineCadence"] = spine_cadence
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif mode == "serial":
        small = spine_cadence["smallEverySpineSegments"]
        major = spine_cadence["majorEverySpineSegments"]
        print(f"贯穿线段序：大约每 {small} 段一次小兑现，每 {major} 段一次大兑现。")
        print("支流不计入段序，除非该段付的是贯穿线的账。不按章号预排情节或兑现。")
        if args.write:
            print("\nAdded 0 reward anchor(s). Future chapter numbers were left unassigned.")
    else:
        phase_label = "全文结构位置"
        print(f"| 章号/分节 | {phase_label} | 节拍 |")
        print("|---:|---|---|")
        for row in rows:
            print(f"| {row['chapter']} | {row['role']} | {row['reward'] or '普通章'} |")
        if args.write:
            print(f"\nAdded {added} reward anchor(s).")
            if backup:
                print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

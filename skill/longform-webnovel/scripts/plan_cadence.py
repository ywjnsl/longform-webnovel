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
    chapter_role,
    load_json,
    required_reward,
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
    if mode not in {"serial", "fanqie-short-story"}:
        raise SystemExit(f"Unsupported storyMode: {mode}")
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
    rows = []
    if mode == "serial":
        for chapter in range(start, start + count):
            rows.append({"chapter": chapter, "role": chapter_role(chapter), "reward": required_reward(chapter, cadence)})
    else:
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
        print(json.dumps({"mode": mode, "start": start, "count": count, "added": added, "backup": str(backup) if backup else None, "chapters": rows}, ensure_ascii=False, indent=2))
    else:
        phase_label = "15章相位" if mode == "serial" else "全文结构位置"
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

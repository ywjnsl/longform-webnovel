#!/usr/bin/env python3
"""Create an original, durable project skeleton for a serialized webnovel."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from webnovel_io import CURRENT_CAST_SCHEMA, CURRENT_PROJECT_SCHEMA, CURRENT_REWARD_SCHEMA
from webnovel_style import PRESETS, render_profile, render_unselected_profile


TEXT_FILES = {
    "canon/story-contract.md": """# 故事合同

## 一句话承诺

待填写。

## 核心阅读体验

- 主要回报：待填写
- 情绪基调：待填写
- 目标读者：待填写

## 主角发动机

- 当下欲望：待填写
- 长期欲望：待填写
- 核心缺陷：待填写
- 不能轻易跨越的边界：待填写

## 核心矛盾与独特机制

待填写。

## 内容边界

待填写。
""",
    "canon/characters.md": """# 人物正史

只记录相对稳定的人设与已经发生的变化。重要事实标注来源章号。

## 主角

待填写。

## 核心角色

待填写。
""",
    "canon/world.md": """# 世界正史

记录会约束剧情的规则、制度和已展示后果，不写无用百科。

待填写。
""",
    "canon/timeline.md": """# 正史时间线

| 故事时间 | 章号 | 事件 | 影响 |
|---|---:|---|---|
""",
    "planning/series-map.md": """# 长线地图

## 当前可收束路径

待填写：核心矛盾如何在有限卷数内结束。

## 可选远期阶段

只保留 2–4 个由既有后果触发的方向，不写死。
""",
    "planning/current-volume.md": """# 当前卷

## 本卷承诺

待确认。

## 卷初与卷末的状态差

待确认。

## 主要对抗与代价

待确认。

## 小篇章

待规划。

## 卷末重大决策

待确认。
""",
    "planning/rolling-outline.md": """# 滚动章纲

保持未来 5–10 章。每章写明：目的、阻碍、至少两项状态变化、兑现内容、结尾推动力。

先标记节拍锚点：第 3 章倍数为 `small`，第 5 章倍数为 `major`；重合章只标 `major`。

待规划。
""",
}

PUBLISHING_TEMPLATE = """# 书名与封面包装

## 状态

- 包装状态：`unconfirmed`
- 定名状态：待确认
- 唯一性检查：待确认
- 封面提示词状态：待确认

在第一章正文前按 `references/publishing-package.md` 确认书名、公开检索记录和封面提示词。
"""

MARKET_BRIEF_TEMPLATE = """# 市场观察

## 状态

- 研究状态：`unrequested`

市场研究是可选输入，不是正文许可。需要研究时按 `references/market-research.md` 保存带日期、来源和样本的快照；不从榜单作品复制书名、人设或情节。
"""


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Project directory to create")
    parser.add_argument("--title", required=True, help="Novel title")
    parser.add_argument("--style", choices=sorted(PRESETS), help="Optional initial language style preset")
    parser.add_argument("--force-empty", action="store_true", help="Allow an existing empty directory")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if root.exists():
        if any(root.iterdir()):
            raise SystemExit(f"Refusing to initialize non-empty directory: {root}")
        if not args.force_empty:
            raise SystemExit("Directory already exists; pass --force-empty only if it is intentionally empty")

    for name in (
        "canon",
        "planning",
        "state",
        "chapters",
        "reviews",
        "research/market-snapshots",
        "sessions",
        ".webnovel/backups",
        ".webnovel/staging",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    project = {
        "schemaVersion": CURRENT_PROJECT_SCHEMA,
        "title": args.title,
        "platformStyle": "fanqie",
        "targetChapterChars": 2500,
        "rewardCadence": {
            "smallEvery": 3,
            "majorEvery": 5,
            "supercycle": 15,
            "overlapPolicy": "major-absorbs-small",
            "enforceFromChapter": 1,
        },
        "styleProfile": {
            "primary": args.style or "unselected",
            "secondary": None,
            "status": "active" if args.style else "unconfirmed",
            "updatedAt": now,
        },
        "publishingPackage": {
            "status": "unconfirmed",
            "titleStatus": "unconfirmed",
            "uniquenessStatus": "unconfirmed",
            "coverPromptStatus": "unconfirmed",
            "updatedAt": now,
        },
        "marketResearch": {
            "status": "unrequested",
            "asOfDate": None,
            "sourceCount": 0,
            "sampleCount": 0,
            "updatedAt": now,
        },
        "reviewGate": {
            "enforceFromChapter": 1,
            "editorRequired": True,
            "readerRequired": True,
            "lintRequired": True,
        },
        "currentVolume": 1,
        "latestDraftChapter": 0,
        "lastCommittedChapter": 0,
        "totalContentChars": 0,
        "createdAt": now,
        "updatedAt": now,
    }
    state = {
        "schemaVersion": 1,
        "asOfChapter": 0,
        "storyTime": "待填写",
        "location": "待填写",
        "protagonist": {"goal": "待填写", "condition": "待填写", "resources": [], "constraints": []},
        "characters": [],
        "relationships": [],
        "worldChanges": [],
        "readerKnowledge": [],
        "recentDeltas": [],
    }
    threads = {"schemaVersion": 1, "asOfChapter": 0, "threads": []}
    rewards = {"schemaVersion": CURRENT_REWARD_SCHEMA, "asOfChapter": 0, "legacyUnauditedThrough": 0, "beats": []}
    cast_arcs = {"schemaVersion": CURRENT_CAST_SCHEMA, "asOfChapter": 0, "legacyUnauditedThrough": 0, "characters": []}
    decisions = {"schemaVersion": 1, "decisions": []}

    write_json(root / "project.json", project)
    write_json(root / "state/story-state.json", state)
    write_json(root / "state/threads.json", threads)
    write_json(root / "state/rewards.json", rewards)
    write_json(root / "state/cast-arcs.json", cast_arcs)
    write_json(root / "state/decisions.json", decisions)
    for relative, content in TEXT_FILES.items():
        (root / relative).write_text(content, encoding="utf-8")
    style_content = render_profile(args.style) if args.style else render_unselected_profile()
    (root / "canon/style-profile.md").write_text(style_content, encoding="utf-8")
    (root / "canon/publishing-package.md").write_text(PUBLISHING_TEMPLATE, encoding="utf-8")
    (root / "canon/market-brief.md").write_text(MARKET_BRIEF_TEMPLATE, encoding="utf-8")

    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

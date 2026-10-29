#!/usr/bin/env python3
"""Create an original, durable project skeleton for a webnovel or short story."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from webnovel_io import CURRENT_CAST_SCHEMA, CURRENT_PROJECT_SCHEMA, CURRENT_REWARD_SCHEMA, novella_stages
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
    "canon/laws.md": """# 法则

法则裁判只认本文。写手和角色不得另造例外。新增规则必须随正文实例化后再写入。

## 力量

待填写。

## 信息

- 谁能知道机密：待填写
- 侦查/感知边界：待填写
- 角色不得因读者知道而知道

## 冲突裁定

意图互斥时：先看谁在场、谁的信息更真、谁愿意付的代价更高；再看法则谁先被违反。被否决的意图记为试图失败，不得改写成成功。
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

## 本卷贯穿线

一卷只有一条。用一句话写这条线，并写卷末谁的状态不可逆地变了。卷末结果只由这条线兑现。

待确认。

## 支流与伏笔

支流用来完善这条贯穿线，也可以为以后的主线留伏笔。每一段标明「贯穿」或「支流」。支流按一件事写，到约 2500 字切章，完结后才开下一段。伏笔记下埋下处、读者能看见的事实、回收卷（本卷或后卷）。

待确认。

## 卷初与卷末的状态差

先写卷末谁的状态不可逆地变了，再倒推必须先发生的选择。升级、调查、经营是做法，不是主线。

待确认。

## 主要对抗与代价

待确认。

## 小篇章

这里写贯穿线上的转折，不预占章号。支流写在「支流与伏笔」里，开的时候再生。

待规划。

## 卷末重大决策

待确认。
""",
    "planning/rolling-outline.md": """# 滚动章纲

保持贯穿线接下来的转折可见。每一段先用一句话写它让哪件已有的事变得更难，或付清哪一笔旧账，并标明这一段是贯穿还是支流。支流不占章号；开写时写明它服务贯穿线的哪一处，或给哪条后卷主线留什么，以及当前卷的代价、信息或人选变了什么。动笔时不把这一句拆成场景拍，也不分配成每章约2500字的剧情；按 `references/chapter-outline.md` 沿同一事件连续写并实测字数，接近 `targetChapterChars` 阈值就在完整句子或段落间切片，直到这段事完结。切章后沿用未完事件，不重设本章结局，标题按实际切片内容后定。支流完结后回到本卷贯穿线。卷的最后一段是贯穿线落地。滚动章纲不写台词，也不把未来每一章的情节填满。

兑现按贯穿线段序走：大约每三段一次小兑现，每五段一次大兑现。支流不占段序，除非这段付的是贯穿线的账。

待规划。
""",
    "planning/current-arc.md": """# 当前弧

- id: 待填写
- 目标: 待填写
- 状态: open
- 估计章窗: 待填写
- 成功长什么样: 待填写
- 失败长什么样: 待填写
- 本章之前已发生:
- 还差什么: 待填写
- 由什么后果开启: 待填写
""",
}

SHORT_STORY_PLANNING_FILES = {
    "planning/series-map.md": """# 短故事收束地图

## 单一主承诺

待填写。

## 主要矛盾的终点

待确认。

## 开放结尾边界

默认完整收束；若作者明确选择开放结尾，在此记录保留什么余韵、必须回答什么。
""",
    "planning/current-volume.md": """# 短故事全文结构

## 开局扰动

待确认。

## 不可逆选择与主要对抗

待确认。

## 中点翻转

待规划。

## 决定性对抗与结局

待确认。
""",
    "planning/rolling-outline.md": """# 短故事分节纲

覆盖全部剩余分节。每一节先用一句话写它如何逼近结局，再写事件线 ID 与阶段（`single`/`opening`/`middle`/`turn`/`closing`）、阻碍、状态变化、阶段性揭示或兑现和结尾收束类型。短故事不按长篇的 2500 字切章。分节纲不写台词。

按全文比例标记开局扰动、不可逆选择、中点翻转、决定性对抗和结局收束；分节较少时允许同节承担多个结构职责。

待规划。
""",
}

NOVELLA_PLANNING_FILES = {
    "planning/series-map.md": """# 短中篇全书终点

## 主承诺与主要矛盾

待确认。

## 最终选择、代价与人物归宿

先锁定结局，再倒推必须发生的选择。开放结尾也要完成主行动。

待确认。

## 必要副线与回收

每条副线写明如何改变主线选择、信息或代价，以及在哪里闭合；不为续作留坑。

待规划。
""",
    "planning/current-volume.md": "# 短中篇全书阶段\n\n阶段不绑定章号，可跨章；不要求每章反转或结案。\n\n"
    + "\n".join(f"## {stage['role']}\n\n待确认。\n" for stage in novella_stages()),
    "planning/rolling-outline.md": """# 短中篇滚动事件纲

保留全书结局和剩余阶段，只细化接下来这件事：从哪里接起、发生什么、怎样才算结束、服务哪个阶段或副线。阶段不平均分配字数，不预排每章事件。

正文顺着因果连续写并实测字数；`targetChapterChars`（默认2500）是文本切分阈值，不是单章创作目标。接近阈值就在完整句子或段落间切开，不等事件或动作结束；标题按切出的内容后定，下一章从断处直接承接。事情未完不为章末收尾；事情已完可以短章。阶段完成后，在任务范围内继续其后果，不自动把阶段边界当成任务结束。全书终点落地才完结。

待规划。
""",
}

PUBLISHING_TEMPLATE = """# 书名与封面包装

## 状态

- 包装状态：`unconfirmed`
- 定名状态：待确认
- 唯一性检查：待确认
- 封面提示词状态：待确认

## 书名排版与字体说明

待确认：书名位置、断行、字体家族与字重、字号层级、字色、描边/阴影，以及作者名和平台角标的避让规则。

可先使用暂定书名创作。发布前按 `references/publishing-package.md` 确认书名、公开检索记录、封面提示词和书名排版说明；未完成时保留 `unconfirmed`，不阻断正文入库。
"""

MARKET_BRIEF_TEMPLATE = """# 市场观察

## 状态

- 研究状态：`unrequested`

市场研究是可选输入，不是正文许可。需要研究时按 `references/market-research.md` 保存带日期、来源和样本的快照；不从榜单作品复制书名、人设或情节。
"""


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


SKILL_ROOT = Path(__file__).resolve().parent.parent


def write_character(root: Path, character_id: str, name: str) -> None:
    """写入项目内角色 skill；情绪与记忆走 state.json，不写进 SKILL.md。"""
    dest = root / "cast" / character_id
    dest.mkdir(parents=True, exist_ok=True)
    skill = (SKILL_ROOT / "templates" / "character" / "SKILL.md").read_text(encoding="utf-8")
    skill = skill.replace("character-{id}", f"character-{character_id}")
    skill = skill.replace("{id}", character_id)
    skill = skill.replace("{姓名}", name)
    (dest / "SKILL.md").write_text(skill, encoding="utf-8")
    state = json.loads((SKILL_ROOT / "templates" / "character" / "state.json").read_text(encoding="utf-8"))
    state["id"] = character_id
    write_json(dest / "state.json", state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Project directory to create")
    parser.add_argument("--title", required=True, help="Novel title")
    parser.add_argument("--style", choices=sorted(PRESETS), help="Optional initial language style preset")
    parser.add_argument("--mode", choices=("serial", "fanqie-short-story", "novella"), default="serial")
    parser.add_argument("--target-total-chars", type=int, help="Finite-work target; novella defaults to 50000")
    parser.add_argument("--min-total-chars", type=int, help="Explicit novella minimum, enforced at completion")
    parser.add_argument("--sections", type=int, help="Planned short-story sections (default: 5); not a novella chapter quota")
    parser.add_argument("--force-empty", action="store_true", help="Allow an existing empty directory")
    parser.add_argument("--protagonist-id", default="main", help="Protagonist cast id (not the reserved cast-arcs id protagonist)")
    parser.add_argument("--protagonist-name", default="主角")
    args = parser.parse_args()
    if args.protagonist_id.strip() in {"", "protagonist"}:
        raise SystemExit("--protagonist-id cannot be empty or 'protagonist'")

    if args.mode == "serial" and args.target_total_chars is not None:
        raise SystemExit("--target-total-chars is only valid with a finite-work mode")
    if args.target_total_chars is not None and args.target_total_chars <= 0:
        raise SystemExit("--target-total-chars must be positive")
    if args.sections is not None and not 1 <= args.sections <= 300:
        raise SystemExit("--sections must be between 1 and 300")
    if args.mode == "novella" and args.sections is not None:
        raise SystemExit("--sections is not valid for novella; chapters emerge from continuous writing")
    if args.min_total_chars is not None:
        if args.mode != "novella" or args.min_total_chars <= 0:
            raise SystemExit("--min-total-chars requires novella and a positive value")
        if args.min_total_chars > (args.target_total_chars or 50000):
            raise SystemExit("--min-total-chars cannot exceed --target-total-chars")

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
        "research/reference-adaptations",
        "performance/snapshots",
        "sessions",
        "cast",
        "contracts",
        "intents",
        ".webnovel/backups",
        ".webnovel/staging",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    project = {
        "schemaVersion": CURRENT_PROJECT_SCHEMA,
        "title": args.title,
        "platformStyle": "fanqie",
        "storyMode": args.mode,
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
        "performanceFeedback": {
            "status": "unrequested",
            "latestWindowEnd": None,
            "latestStage": None,
            "snapshotCount": 0,
            "updatedAt": now,
        },
        "reviewGate": {
            "enforceFromChapter": 1,
            "editorRequired": True,
            "readerRequired": True,
            "lintRequired": True,
            "naturalnessRequired": True,
            "naturalnessEnforceFromChapter": 1,
            "repetitionRequired": True,
            "repetitionEnforceFromChapter": 1,
        },
        "ensemble": {
            "enabled": True,
            "protagonistId": args.protagonist_id.strip(),
            "explorationBeatsDefault": 3,
            "maxOnStage": 4,
            "enforceFromChapter": 1,
        },
        "currentVolume": 1,
        "latestDraftChapter": 0,
        "lastCommittedChapter": 0,
        "totalContentChars": 0,
        "createdAt": now,
        "updatedAt": now,
    }
    if args.mode == "fanqie-short-story":
        project["shortStory"] = {
            "targetTotalChars": args.target_total_chars,
            "plannedSections": args.sections or 5,
            "status": "planning",
            "endingType": "closed",
        }
    elif args.mode == "novella":
        project["finiteStory"] = {
            "targetTotalChars": args.target_total_chars or 50000,
            "minTotalChars": args.min_total_chars,
            "status": "planning",
            "endingType": "closed",
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
    text_files = dict(TEXT_FILES)
    if args.mode == "fanqie-short-story":
        text_files.update(SHORT_STORY_PLANNING_FILES)
    elif args.mode == "novella":
        text_files.update(NOVELLA_PLANNING_FILES)
    for relative, content in text_files.items():
        (root / relative).write_text(content, encoding="utf-8")
    style_content = render_profile(args.style) if args.style else render_unselected_profile()
    (root / "canon/style-profile.md").write_text(style_content, encoding="utf-8")
    (root / "canon/publishing-package.md").write_text(PUBLISHING_TEMPLATE, encoding="utf-8")
    (root / "canon/market-brief.md").write_text(MARKET_BRIEF_TEMPLATE, encoding="utf-8")
    write_character(root, args.protagonist_id.strip(), args.protagonist_name.strip() or "主角")
    characters_path = root / "canon/characters.md"
    characters_text = characters_path.read_text(encoding="utf-8")
    characters_path.write_text(
        characters_text.replace(
            "## 主角\n\n待填写。",
            f"## 主角\n\n- id: `{args.protagonist_id.strip()}`\n- 姓名: {args.protagonist_name.strip() or '主角'}\n- 人设: 待填写。",
        ),
        encoding="utf-8",
    )

    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

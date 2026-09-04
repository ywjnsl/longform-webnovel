# 群像仿真（与连载同一套正史）

长篇网文仍是一份项目：合同、卷纲、爽点、审稿、提交事务不变。群像仿真只改**章是怎么长出来的**：角色先隔离给出意图，法则裁判否决非法，写手再成章。

沙盒决定这一拍发生什么；网文决定这一章凭什么结束。**章不是收束单位，弧才是。** 失败、改路、暴露都算交付；空转非法。

角色 skill 活在 `cast/{id}/`，不要注册成全局 Cursor skill。`cast-arcs.json` 仍是配角弧光账本；`cast/*/state.json` 是情绪与信息隔离层。主角不要写入 `cast-arcs.json`（id `protagonist` 已保留给关系目标）。

## 何时读

写下一章、发合同、扮演角色、按需生成配角时读本文和 [ensemble-character.md](ensemble-character.md)。不要因此跳过 [chapter-craft.md](chapter-craft.md)、[reward-system.md](reward-system.md)、[review-system.md](review-system.md)。

## 三层

| 层 | 管什么 | 多长 |
|---|---|---|
| 拍 | 意图、情绪、一次行动 | 章内 2–4 拍 |
| 章 | 至少两个状态维度变化；可失败、留钩子 | 1 章 |
| 弧 | `planning/current-arc.md` 的目标兑现或彻底失败 | 多章 |

合法章结局：`progress` / `setback` / `reroute` / `expose` / `pause-with-scar`。`pause-with-scar` 必须留下不可撤销痕迹。非法：`status-quo`。弧默认保持 `open`。

## 未完成合同

每章写入 `contracts/chapter-NNNN.json`：

```json
{
  "chapter": 4,
  "arcId": "steal-fragment",
  "arcGoal": "拿到残卷",
  "arcStatus": "open",
  "estimatedChapters": [4, 9],
  "thisChapterMust": "推进或加压一格",
  "legalOutcomes": ["progress", "setback", "reroute", "expose", "pause-with-scar"],
  "illegalOutcomes": ["status-quo"],
  "explorationBeats": 3,
  "onStage": ["main", "lin-qiao"],
  "payoffLevel": "none",
  "publicFactsForCast": ["夜雨", "侧门两人巡逻"]
}
```

`payoffLevel` 仍服从 3/5 章账本：`none` | `small` | `major`。`small`/`major` 可以是失败。`onStage` 人数 ≤ `project.json.ensemble.maxOnStage`。普通章探索拍默认 `explorationBeatsDefault`；`small` 减 1；`major` 只留 1–2 拍。配额用完仍无合法结局时，导演给出两个不可回避选项。

## 写章循环

在「继续连载」读完正史、通过校验、确认无阻断决策之后：

1. 读 `canon/laws.md`、`planning/current-arc.md`、上场角色的 `cast/{id}/SKILL.md` 与 `state.json`。
2. 写本章合同。弧默认 `open`。
3. 主角先自由提案。每拍为上场角色启动隔离上下文，只喂公开事实、此人会知道的法则、自己的 skill/state、合同里的 `publicFactsForCast`。角色只输出意图 JSON，写入 `intents/chapter-NNNN/{id}.json`。
4. 法则裁判只认 `canon/laws.md`，写入 `ruling.json`。被否决的意图记为试图失败，不得改写成成功。
5. 写手只根据裁定后的意图按 [chapter-craft.md](chapter-craft.md) 和 [scene-craft.md](scene-craft.md) 写正文。先把空间、身体、动作过程写出来，再写对白。对打、追逐、破境抢关按打斗规则大幅度加厚，不准一句收胜负。不发明角色没打算做的关键选择。被否决的意图写成试图失败。
6. 再走原有审稿与章节提交事务。提交时同步合同、意图、ruling、上场角色 `state.json`、`planning/current-arc.md`。正文没发生的事不能进正史。

## 信息隔离

扮演某角色时禁止给：其他角色私密状态、完整卷纲、作者备注、读者才知道的信息。不知道的事写成 `misread`。

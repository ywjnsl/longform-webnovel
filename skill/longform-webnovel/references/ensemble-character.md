# 角色 skill、意图与按需生成

从 `templates/character/` 复制到 `cast/{id}/`。SKILL.md 只放稳定人设；本章情绪、记忆、此刻打算只放 `state.json`。

## 意图 JSON

写入 `intents/chapter-NNNN/{id}.json`（多拍用数组）。同一事件跨章可按 [ensemble.md](ensemble.md) 复制仍有效的意图快照并更新 `chapter`；章号变化本身不触发新的欲望、情绪或行动提案。必须含 `emotion.trigger`、`wantNow`、`wouldDo`、`wouldSay`、`wouldNeverSay`。

```json
{
  "characterId": "lin-qiao",
  "chapter": 4,
  "beat": 1,
  "emotion": {
    "from": "戒备",
    "to": "忌妒里夹着不安",
    "trigger": "看见主角靠近藏经阁侧门",
    "shown": "冷淡",
    "hidden": true
  },
  "wantNow": "抢先确认残卷是否还在三层",
  "wouldDo": "假装巡夜从侧翼跟上",
  "wouldSay": ["这么晚还练剑？"],
  "wouldNeverSay": ["我也在找残卷"],
  "misread": "以为主角来偷自己的钥匙",
  "offstageIfAbsent": "独自收买守阁弟子",
  "costWilling": "被记过一次",
  "costUnwilling": "养母身份曝光"
}
```

写手不得让角色说出 `wouldNeverSay`。配角按自己的欲望反对、利用或离开，不默认帮主角。主角可以绕路、失败，但不能空转。番茄短故事写节时，关键选择还要按 [fanqie-character-craft.md](fanqie-character-craft.md) 能从经历、性格、欲望、当场处境解释；赢了要把代价写进 `cost` / `state.json`，不能只口头说付出。

## state.json

章末更新上场或刚离开的角色：`emotion`、`wantNow`、`knownFacts`、`memory`、`relationships`、`presence`。`secrets` 仅自己与作者可见。`memory` 可只保留最近 8 条。`presence` 用 `onstage`，或 `offline` 并写明之后还会回到哪条线、哪一卷，或这条线已经结束。见 [supporting-cast.md](supporting-cast.md) 的「在场状态」。

`memory` 若做压缩，保留仍影响当前关系、目标或选择的重要前因，不把最近 8 条当作删除旧转折的硬上限。`relationships` 沿用既有结构，描述已成立的信任、戒备或依赖及其依据；正式加入、受到照顾和被信任不必同时成立。一次情绪不写成稳定人设，角色自述和他人评价不写成已证实事实。具体取舍见 [narrative-continuity.md](narrative-continuity.md)，不增加字段或逐章关系变化配额。

`cast-arcs.json` 仍按 [supporting-cast.md](supporting-cast.md) 记录选择与后果。两边都要有的是 `anchor`/`recurring`：账本记弧光和在场状态，这里记此刻知道什么、情绪是什么。同一角色的 `presence` 两边保持一致。

## 按需生成

默认不预写路人百科。闸门：

1. 本章合同或已有意图需要一个尚不存在的人；
2. 此人由已发生后果或公开世界结构长出来；
3. `onStage` 仍不超过上限。

| 层 | 何时 | 最低要求 |
|---|---|---|
| `cameo` | 一次性功能 | 短 skill、当场合理行为 |
| `recurring` | 第二次上场或留下跨章把柄 | 独立诉求 + state.json + `cast-arcs.json` |
| `anchor` | 其选择会改变主弧 | 完整欲望/约束；尽量问作者 |

同一章最多新建 1 个 `recurring`，不要当场新建 `anchor`。场外 `anchor`/`recurring` 每章最多扫一次：若 `offstageIfAbsent` 会影响下一章，写入 `ruling.offstage`，不必写成场面。

# 角色 skill、意图与按需生成

从 `templates/character/` 复制到 `cast/{id}/`。SKILL.md 只放稳定人设；本章情绪、记忆、此刻打算只放 `state.json`。

## 意图 JSON

写入 `intents/chapter-NNNN/{id}.json`（多拍用数组）。必须含 `emotion.trigger`、`wantNow`、`wouldDo`、`wouldSay`、`wouldNeverSay`。

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

写手不得让角色说出 `wouldNeverSay`。配角按自己的欲望反对、利用或离开，不默认帮主角。主角可以绕路、失败，但不能空转。

## state.json

章末更新上场角色：`emotion`、`wantNow`、`knownFacts`、`memory`、`relationships`。`secrets` 仅自己与作者可见。`memory` 可只保留最近 8 条。

`cast-arcs.json` 仍按 [supporting-cast.md](supporting-cast.md) 记录选择与后果。两边都要有的是 `anchor`/`recurring`：账本记弧光，这里记此刻知道什么、情绪是什么。

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

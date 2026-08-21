# 爽点账本与 15 章节拍

## 15 章超级循环

| 相位 | 作用 | 最低回报 |
|---:|---|---|
| 1 | 起势，建立当轮目标 | 普通章回报 |
| 2 | 加压，制造明确缺口 | 普通章回报 |
| 3 | 第一次小兑现 | `small` |
| 4 | 扩大代价，为大兑现蓄力 | 普通章回报 |
| 5 | 第一次阶段大兑现 | `major` |
| 6 | 承接胜利余波，交付新筹码或关系收益 | `small` |
| 7 | 打开由旧后果导致的新局面 | 普通章回报 |
| 8 | 二次加压 | 普通章回报 |
| 9 | 第二次小兑现 | `small` |
| 10 | 第二次阶段大兑现 | `major` |
| 11 | 让角色承担胜利后果 | 普通章回报 |
| 12 | 第三次小兑现 | `small` |
| 13 | 多线汇合 | 普通章回报 |
| 14 | 高潮蓄力，锁定不可回避的选择 | 普通章回报 |
| 15 | 超级循环高潮，同时吸收小爽点职责 | `major` |

循环按全书章号继续。第 6 章这类紧跟大爽点的 `small` 优先交付战利品、认可、关系主动权或新情报，不连续安排同类战斗高潮。

## Beat 结构

`state/rewards.json` 中的 `beats` 使用以下字段：

```json
{
  "chapter": 5,
  "level": "major",
  "status": "delivered",
  "role": "第一次阶段大兑现",
  "rewardType": "truth",
  "payoff": "主角公开证据，洗清嫌疑并锁定幕后组织",
  "setupChapters": [1, 2, 4],
  "evidence": ["投影幕布上，转账记录与录音时间严丝合缝。"],
  "cost": "幕后组织转而威胁主角家人",
  "stateDeltas": ["主角恢复公开身份", "对手从观察转为追杀"],
  "sourceThreadIds": ["main-framed"],
  "conflictType": "public-accusation",
  "solutionType": "evidence-exposure"
}
```

## 字段规则

- `status` 使用 `planned`、`delivered` 或迁移专用的 `needs-review`。
- `rewardType` 使用 `power`、`status`、`relationship`、`truth`、`resource`、`revenge`、`emotional`、`escape`、`achievement`、`other`；未完成计划可暂用 `unassigned`。
- `setupChapters` 只列当前章之前真正承担铺垫功能的章节。
- `evidence` 在兑现后保存正文中 6–120 字的原文片段；校验器会确认片段确实存在于对应章节。
- `cost` 说明回报带来的代价、新责任或新约束。`major` 必须有具体代价。
- `stateDeltas` 写结果，不写感受；`small` 至少一项，`major` 至少两项。
- `sourceThreadIds` 关联被推进、兑现或转化的剧情线。大爽点通常至少关联一条。
- `conflictType` 与 `solutionType` 使用稳定、简短的描述，用于检测重复模式。

## 计划与兑现

规划时先用 `plan_cadence.py --write` 创建锚点，再把 `unassigned` 和“待规划”替换成具体方案。普通章也必须有回报，但不写入节拍账本，除非它承担额外爽点。

兑现后必须从最终正文提取证据，再把状态改成 `delivered`。不得先把账本写成已兑现，再去凑正文。

连续两个同级爽点不得复用完全相同的 `conflictType + solutionType + rewardType`。连续三个同级爽点使用相同 `rewardType` 会触发疲劳警告。

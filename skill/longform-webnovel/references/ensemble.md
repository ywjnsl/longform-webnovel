# 群像仿真（与连载同一套正史）

长篇网文仍是一份项目：合同、卷纲、爽点、审稿、提交事务不变。群像仿真只改**章是怎么长出来的**：角色先隔离给出意图，法则裁判否决非法，写手再成章。

角色意图与法则决定接下来发生什么；`serial`、`novella` 的章由连续正文的实测字数决定切点。**章不是收束单位，弧才是。** 失败、改路、暴露和正在进行的尝试都能推进事件，不为给一章结局强制制造变化。短故事另按分节职责处理。

角色 skill 活在 `cast/{id}/`，不要注册成全局 Cursor skill。`cast-arcs.json` 仍是配角弧光账本；`cast/*/state.json` 是情绪与信息隔离层。主角不要写入 `cast-arcs.json`（id `protagonist` 已保留给关系目标）。

## 何时读

筹备下一章、发合同、扮演角色、按需生成配角时读本文和 [ensemble-character.md](ensemble-character.md)。兑现设计按需读 [reward-system.md](reward-system.md)，正式审稿读 [review-system.md](review-system.md)；正文阶段改用 [writer-context.md](writer-context.md)，写法有具体问题才补读 [chapter-craft.md](chapter-craft.md)。番茄短故事的筹备与编辑按 [fanqie-character-craft.md](fanqie-character-craft.md) 核对选择、代价和声音。法则裁判按 [fanqie-consistency.md](fanqie-consistency.md) 核对战力、金钱与规则，不得对主角免费豁免。

## 三层

| 层 | 管什么 | 多长 |
|---|---|---|
| 拍 | 意图、情绪、一次行动 | 随行动发生，不按章预分数量 |
| 章/节 | 长篇与短中篇是连续文本的切片和提交单位；短故事是全文结构中的分节 | 长篇约2500有效字切片，事件可跨片 |
| 弧 | `planning/current-arc.md` 的目标兑现或彻底失败 | 多章 |

合同用 `progress` / `setback` / `reroute` / `expose` / `pause-with-scar` 描述实际推进，不预先当作每章必须演出的结局。行动仍在进行、尚未产生最终结果时可记为 `progress`，不必在切点新增转折。短故事另记录 `eventStage`（`single` / `opening` / `middle` / `turn` / `closing`）和 `endingType`。`pause-with-scar` 必须已有不可撤销痕迹；`status-quo` 指无效空转，不指场面尚未结束。弧默认保持 `open`。

## 未完成合同

每章写入 `contracts/chapter-NNNN.json`：

```json
{
  "chapter": 4,
  "arcId": "steal-fragment",
  "arcGoal": "拿到残卷",
  "arcStatus": "open",
  "eventId": "theft-at-dock",
  "estimatedChapters": [4, 9],
  "thisChapterMust": "接续侧门行动，按实测字数切片，不要求本片拿到残卷",
  "legalOutcomes": ["progress", "setback", "reroute", "expose", "pause-with-scar"],
  "illegalOutcomes": ["status-quo"],
  "explorationBeats": 3,
  "onStage": ["main", "lin-qiao"],
  "payoffLevel": "none",
  "publicFactsForCast": ["夜雨", "侧门两人巡逻"]
}
```

`payoffLevel` 按贯穿线实际兑现填写：`none` | `small` | `major`。支流默认不占用 small/major 位置，除非它付的是贯穿线的账。`small`/`major` 可以是失败。`onStage` 人数 ≤ `project.json.ensemble.maxOnStage`。`explorationBeats` 与 `explorationBeatsDefault` 保留兼容旧数据，不能用作正文拍数、章长或强制转折的配额；不要因达到这个数而结束章节或制造二选一。`estimatedChapters` 也只是排程参考，不绑定情节与切点。上例为长篇合同；`sectionDelivery`、`eventStage`、`endingType` 是短故事分节规划所用，长篇不为填字段预设本片结果，旧合同有这些字段时按已写正文理解。

## 写章循环

在「继续连载」读完正史、通过校验、确认无阻断决策之后：

1. 读 `canon/laws.md`、`planning/current-arc.md`、上场角色的 `cast/{id}/SKILL.md` 与 `state.json`。
2. 新事件写合同，弧默认 `open`；同一事件跨章复用上一片仍有效的合同、前卡、角色意图与裁定快照，先核对已提交正文中的新情况。`thisChapterMust` 写正在接续的行动，不预定本章结局；跨章沿用该事件，阶段与回报在切片后按正文核实；短故事的 `sectionDelivery` 沿用已确认分节职责，再据正文核对。
3. 新事件或影响选择的新情况才重新收取意图，主角先自由提案。为相关上场角色提供隔离上下文，只喂公开事实、此人会知道的法则、自己的 skill/state、合同里的 `publicFactsForCast`。角色只输出意图 JSON，写入 `intents/chapter-NNNN/{id}.json`；新情况改变选择时再取意图，不按预设拍数反复发起。
4. 行动合法性或相关规则条件变化时重做裁定；条件未变沿用有效裁定。法则裁判只认 `canon/laws.md`，写入 `ruling.json`。被否决的意图记为试图失败，不得改写成成功。
5. 将裁定后的意图、当前事实、相关正文与声音依据按 [writer-context.md](writer-context.md) 交给写手。不传整份筹备教程，不发明角色没打算做的关键选择；被否决的意图写成试图失败。空间、动作、对白和心理按人物注意组织，不固定先后。对打、追逐或破境需让人看懂决定结果的过程；确有空间或动作缺失时再查 [scene-craft.md](scene-craft.md)，不按回合加厚。
6. 达到切分阈值时先切文本，再走原有审稿与章节提交事务。提交时同步合同、意图、ruling、上场角色 `state.json`、`planning/current-arc.md`。正文没发生的事不能进正史；提交完成后从断处接着未完事件，不因章号改变重置意图或补造新高潮。

## 同一事件跨章归档

每章仍提交合同、意图和裁定，作为该片的审计快照。复用时将上一章仍有效的 `precard.md`、各角色意图及 `ruling.json` 复制到 staging 的本章目录；合同与意图中的 `chapter` 更新为当前章号，角色诉求、知情边界和裁定理由保持原意。`onStage` 按当前片实际出场核对，阶段、回报与正史只按该片正文更新；不能把上一片的结果当作这一片再次发生。

在已有 `sessions/` 记录中说明沿用哪一章的材料及其仍有效的依据，不将复制说成新提案或新裁定。新伤势、公开信息、资源或人物反应会改变当前选择或合法性时，只更新相关角色与裁定；事件结束、转入新事件时重新筹备。无需新增必填卡片或数据字段。

## 信息隔离

扮演某角色时禁止给：其他角色私密状态、完整卷纲、作者备注、读者才知道的信息。不知道的事写成 `misread`。

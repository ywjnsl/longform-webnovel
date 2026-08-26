# 章节独立审稿系统

## 目的

每章在正式提交前完成三种互补检查：确定性语言风险扫描、编辑诊断、目标读者体验模拟。扫描只发现值得复核的模式，不能判断作者身份，也不能输出“AI 概率”。项目已确认正文和 `canon/style-profile.md` 始终是声音基线。

## 角色隔离

有可用子代理时，让编辑与读者模拟分别读取本章、必要正史和风格档案，避免互相锚定。没有子代理时，在同一代理内依次执行两个上下文隔离的角色通道：先让读者只报告在哪里产生了什么体验，再让编辑诊断原因和修订方向。读者不替作者改稿，编辑不伪装成目标读者投票。

- 编辑检查：读者承诺、因果、结构、人物、声音、连续性、行文执行。
- 读者模拟：以具体目标读者 persona 记录逐点反应、继续阅读意愿、好奇与卡顿位置。
- 两者可以意见不同。保留分歧，不用平均分消解它。

## 执行顺序

1. 运行 `chapter_metrics.py`。
2. 用最近 2–5 章已确认正文作为可选基线，运行：

```bash
python3 <skill-dir>/scripts/prose_lint.py <章节文件> \
  --baseline <已确认章节> \
  --output <staging>/reviews/第NNNN章-lint.json
```

3. 独立完成读者模拟与编辑诊断，写 `第NNNN章-review.json`。
4. 优先修因果、人物和结构，再处理行文。普通警告不要求机械修改。
5. 最多自动修订一次；正文变化后必须重跑扫描和两类审稿，因为旧哈希与证据已经失效。
6. 编辑 `blocked`、未解决的 `high` 问题、读者 `drop-risk` 或 `stop` 会阻断提交。若作者明确接受风险，先把确认写入 `state/decisions.json`，再使用 `author-approved` 和对应 `decisionId`。

番茄短故事的最后一节还要执行全文终审：核对单一主承诺是否兑现、主要线索是否闭合、关键铺垫是否回收、配角选择是否产生后果、结局是否同时具备因果必然性与初读意外感。开放结尾只允许保留作者已确认的余韵，不能遗漏主要矛盾的处理。

## 审稿文件

`reviews/第NNNN章-review.json` 使用以下结构：

```json
{
  "schemaVersion": 1,
  "chapter": 16,
  "reviewedTextSha256": "正文 UTF-8 字节的 SHA-256",
  "editor": {
    "status": "pass-with-notes",
    "diagnosis": "本章的主要判断",
    "strengths": ["已经有效的部分"],
    "findings": [
      {
        "priority": "medium",
        "dimension": "causality",
        "evidence": "正文中的逐字片段",
        "readerCost": "对读者造成的具体代价",
        "direction": "修订方向，不代写整段",
        "resolved": true
      }
    ]
  },
  "reader": {
    "status": "engaged",
    "persona": "本次模拟的具体目标读者",
    "completionIntent": "continue",
    "moments": [
      {
        "evidence": "正文中的逐字片段",
        "reaction": "此处实际产生的反应",
        "channel": "curiosity",
        "valence": "positive"
      }
    ],
    "openQuestions": ["读者自然带走的问题"]
  },
  "resolution": {
    "action": "revised",
    "notes": "如何处理审稿结果"
  }
}
```

枚举值：

- 编辑状态：`pass`、`pass-with-notes`、`blocked`。
- 优先级：`high`、`medium`、`low`。
- 编辑维度：`promise`、`causality`、`structure`、`character`、`voice`、`continuity`、`line`。
- 读者状态：`engaged`、`mixed`、`drop-risk`；完成意愿：`continue`、`uncertain`、`stop`。
- 体验通道：`transportation`、`aesthetic`、`social`、`curiosity`、`flow`；倾向：`positive`、`negative`、`mixed`。
- 处理结果：`accepted`、`revised`、`author-approved`。最后一种还需 `decisionId`。

所有 `evidence` 必须是当前章原文的逐字子串。不要把概括、推测或改写后的句子伪装成证据。

## 语言风险解释

`prose_lint.py` 检查高频通用微动作、解释连接词、比喻密度、总结式收尾、过于整齐的句段节奏、长短语重复和相对项目基线的漂移。命中只表示“值得编辑检查”：悬疑复沓、刻意排比、角色口癖和场景节奏都可能是合理原因。

不得单凭词表、句长或扫描结果删除项目声音。不得把结果表述为抄袭、机器生成或作者身份鉴定。

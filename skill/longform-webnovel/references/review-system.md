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

3. 独立完成读者模拟与编辑诊断，写 `第NNNN章-review.json`。编辑对自然化风险按“替读者下结论、纠正式骨架过密、对白工具化、能力过度整齐、程序展示过满、人物同声、主题封口”检查是否形成模式簇；判据见 [prose-naturalization.md](prose-naturalization.md)。涉及证据缺口、人物记错或后置揭示时，另查前文旁白与正史是否已把该事实提前写死，并确认早期争议与后期兑现之间存在可追溯的因果。
4. 优先修因果、人物和结构，再处理行文。普通警告不要求机械修改；自然化修订只改有逐字证据的段落，不能把全文重新生成成另一套统一腔调。
5. 每轮最多自动修订一次；正文变化后必须重跑扫描和两类审稿，因为旧哈希与证据已经失效。审稿无阻断项且作者确认当前版本达标后停止自然化循环，不因主观分数仍可降低而继续改稿。
6. 编辑 `blocked`、未解决的 `high` 问题、读者 `drop-risk` 或 `stop` 会阻断提交。若作者明确接受风险，先把确认写入 `state/decisions.json`，再使用 `author-approved` 和对应 `decisionId`。

番茄短故事第一节在第 2 步后另运行 `opening_audit.py --window 300`。目标读者先只看脚本截出的前 300 字，复述人物关系、当前事件、主角选择、具体风险与下一问；编辑再检查这些信息是否形成因果链。复述需要作者补充背景、主角到 300 字仍无主动选择、风险只有抽象情绪，或下一问无法由后文回答时，至少记为 `high` 入口问题并阻断提交，修订后重新生成窗口。脚本指标本身不形成通过或阻断结论。

番茄短故事的最后一节还要执行全文终审：核对单一主承诺是否兑现、主要线索是否闭合、关键铺垫是否回收、配角选择是否产生后果、结局是否同时具备因果必然性与初读意外感，并检查结尾是否在矛盾解决后继续替读者概括主题。对于后文保留未知或纠正主角判断的事实，从揭示点回查首次陈述：前文只能确认当时可知的路径和结果，不能由叙述者提前给出与后文疑点冲突的确定答案。这里的外部读者视角不是把正文改成第三人称，而是暂时放下作者身份，按普通读者顺序通读全文。开放结尾只允许保留作者已确认的余韵，不能遗漏主要矛盾的处理；去除总结句也不能牺牲结局因果。

终审必须写入 `reviews/final-review.json`，并绑定按章节顺序计算的全文 SHA-256。最小结构如下：

```json
{
  "schemaVersion": 1,
  "storyMode": "fanqie-short-story",
  "reviewedThroughChapter": 5,
  "reviewedTextSha256": "章节文件名和正文按章顺序计算的 SHA-256",
  "perspective": "external-reader",
  "editorStatus": "pass",
  "readerStatus": "engaged",
  "completionIntent": "complete",
  "checks": {
    "promise": "pass",
    "causality": "pass",
    "continuity": "pass",
    "setupPayoff": "pass",
    "characterConsequences": "pass",
    "titleResonance": "pass",
    "endingBoundary": "pass"
  },
  "resolution": "具体说明通读后如何处理问题"
}
```

只有全部 `checks` 为 `pass`、哈希覆盖所有已提交章节且 `completionIntent` 为 `complete` 时，才可把 `shortStory.status` 改为 `complete`。

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

纠正式句型或重复句首只有成组出现才报告。编辑必须回到上下文判断它们是在塑造人物、制造节奏，还是反复替读者校正结论。人物对白中的自然口癖、法庭质询和刻意复沓可以保留。

不得单凭词表、句长或扫描结果删除项目声音。不得把结果表述为抄袭、机器生成或作者身份鉴定。

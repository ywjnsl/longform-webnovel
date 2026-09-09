# 章节独立审稿系统

## 目的

每章在正式提交前完成五种互补检查：确定性重复审计、语言风险扫描、网文自然度审稿、编辑诊断、目标读者体验模拟。扫描只发现值得复核的模式，不能判断作者身份，也不能输出“AI 概率”。项目已确认正文和 `canon/style-profile.md` 始终是声音基线。

网文自然度审稿按 [webnovel-naturalness-review.md](webnovel-naturalness-review.md) 执行。它对所有新写或修改过的章节强制生效，不因 lint 无 finding、普通审稿已通过、作者要求停止润色或正文只改一句而省略。

## 角色隔离

有可用子代理时，让自然度审稿、编辑与读者模拟分别读取本章、必要正史和风格档案，避免互相锚定。没有子代理时，在同一代理内依次执行三个上下文隔离的角色通道：先让自然度审稿定位模式簇，再让编辑诊断因果、结构和修订方向，最后让读者只报告在哪里产生了什么体验。读者不替作者改稿，编辑不伪装成目标读者投票。

- 编辑检查：读者承诺、因果、结构、人物、声音、连续性、行文执行。番茄短故事的 `character` 还要覆盖人设漂移、无代价胜利、情绪硬喊、新人难认；细则见 [fanqie-character-craft.md](fanqie-character-craft.md)。
- 自然度审稿：回声重复、副词过密、工整修辞、机械节拍、解释过满、纠正式骨架、对白播设定、人物同声、因果过度装配、通用反应和主题封口。
- 读者模拟：以具体目标读者 persona 记录逐点反应、继续阅读意愿、好奇与卡顿位置。
- 三者可以意见不同。保留分歧，不用平均分消解它。

## 执行顺序

1. 运行 `chapter_metrics.py`。
2. 对每个新写或修改过的章节运行确定性重复审计。番茄短故事比较全部较早已提交分节；长篇默认比较最近 5 章：

```bash
python3 <skill-dir>/scripts/repetition_audit.py <章节文件> \
  --project <项目目录> \
  --output <staging>/reviews/第NNNN章-repetition.json
```

3. 用最近 2–5 章已确认正文作为可选基线，运行：

```bash
python3 <skill-dir>/scripts/prose_lint.py <章节文件> \
  --baseline <已确认章节> \
  --output <staging>/reviews/第NNNN章-lint.json
```

4. 按 [webnovel-naturalness-review.md](webnovel-naturalness-review.md) 独立完成自然度审稿，再依次完成编辑诊断与读者模拟，统一写入 `第NNNN章-review.json`。涉及证据缺口、人物记错或后置揭示时，另查前文旁白与正史是否已把该事实提前写死，并确认早期争议与后期兑现之间存在可追溯的因果。
5. 优先修因果、人物和结构，再处理行文。普通警告不要求机械修改；自然度修订只改有逐字证据的段落，不能把全文重新生成成另一套统一腔调。
6. 每轮最多自动修订一次；正文变化后必须重跑指标、重复审计、语言扫描、自然度审稿、编辑诊断和读者模拟，因为旧哈希、finding ID、例外和证据已经失效。执行过自然度修改时，在最终报告保存修改前哈希和处理类别；最终 finding 只引用修改后正文仍存在的逐字证据。
7. 重复报告中每个仍保留的 exact/near finding 都必须在 `naturalness.repetitionExceptions` 中按 finding ID 和最终正文哈希记录具体编辑理由，否则阻断提交。自然度 `needs-revision`、自然度或编辑未解决的 `high` 问题、编辑 `blocked`、读者 `drop-risk` 或 `stop` 也会阻断提交。若作者明确接受自然度风险，先把确认写入 `state/decisions.json`，其中 `kind` 为 `naturalness-exception`，并绑定具体 `chapter` 与最终正文 `reviewedTextSha256`；再使用 `author-approved` 和对应 `decisionId`。

番茄短故事第一节在第 2 步后另运行 `opening_audit.py --window 300`。目标读者先只看脚本截出的前 300 字，复述人物关系、当前事件、主角选择、具体风险与下一问；编辑再检查这些信息是否形成因果链。复述需要作者补充背景、主角到 300 字仍无主动选择、风险只有抽象情绪，或下一问无法由后文回答时，至少记为 `high` 入口问题并阻断提交，修订后重新生成窗口。脚本指标本身不形成通过或阻断结论。

番茄短故事的写节审稿与最后一节全文终审，还要按 [fanqie-signing-quality.md](fanqie-signing-quality.md) 与 [fanqie-character-craft.md](fanqie-character-craft.md) 检查：不套用他人结构与核心剧情、不靠机械扩写拉长、大段必须推动情节、人物行为对得上角色卡、重要胜利有真实代价、情绪落到身体而非旁白硬喊、新人出场能认、对白能区分，以及收口完整。最后一节终审：核对单一主承诺是否兑现、主要线索是否闭合、关键铺垫是否回收、配角选择是否产生后果、结局是否同时具备因果必然性与初读意外感；结尾既不能在矛盾解决后继续替读者概括主题，也不能把最后一场已起手的动作切成半句。对于后文保留未知或纠正主角判断的事实，从揭示点回查首次陈述：前文只能确认当时可知的路径和结果，不能由叙述者提前给出与后文疑点冲突的确定答案。这里的外部读者视角不是把正文改成第三人称，而是暂时放下作者身份，按普通读者顺序通读全文。开放结尾只允许保留作者已确认的余韵，不能遗漏主要矛盾的处理；去除总结句也不能牺牲结局因果。

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
  "naturalness": {
    "status": "pass",
    "diagnosis": "未发现影响沉浸的自然度问题簇。",
    "reviewedTextSha256": "正文 UTF-8 字节的 SHA-256",
    "findings": [],
    "repetitionExceptions": [],
    "revision": {
      "action": "not-needed",
      "notes": "没有证据支持额外修改。"
    }
  },
  "externalNaturalness": {
    "provider": "zhuque",
    "checkedAt": "送检时间",
    "reviewedTextSha256": "送检正文 SHA-256",
    "overallSignal": "原报告总体信号",
    "sourceArtifacts": ["reviews/evidence/截图.png"],
    "flaggedPassages": []
  },
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

- 自然度状态：`pass`、`pass-with-notes`、`needs-revision`。
- 自然度类别：`echo-repetition`、`modifier-overuse`、`rhetorical-symmetry`、`cadence-packaging`、`over-explanation`、`corrective-syntax`、`expository-dialogue`、`same-voice`、`over-engineered-causality`、`generic-reaction`、`theme-closure`、`padding-expansion`、`truncated-ending`。
- 自然度处理：`not-needed`、`revised`、`author-approved`。`revised` 必须记录与最终哈希不同的 `beforeTextSha256` 和非空 `changedCategories`；`author-approved` 必须关联已确认的 `naturalness-exception` 决策，该决策的 `chapter` 和 `reviewedTextSha256` 必须与本次最终正文一致。
- 编辑状态：`pass`、`pass-with-notes`、`blocked`。
- 优先级：`high`、`medium`、`low`。
- 编辑维度：`promise`、`causality`、`structure`、`character`、`voice`、`continuity`、`line`、`originality`、`padding`、`ending`。`character` 在番茄短故事中至少覆盖：选择能否从角色卡解释、重要胜利有无真实代价、情绪是否落到身体、对白能否辨认说话人。
- 读者状态：`engaged`、`mixed`、`drop-risk`；完成意愿：`continue`、`uncertain`、`stop`。
- 体验通道：`transportation`、`aesthetic`、`social`、`curiosity`、`flow`；倾向：`positive`、`negative`、`mixed`。
- 处理结果：`accepted`、`revised`、`author-approved`。最后一种还需 `decisionId`。

所有 `evidence` 必须是当前最终章节正文的逐字子串。不要把概括、推测、修改前已删除的句子或改写后的句子伪装成证据。`externalNaturalness` 是作者提供朱雀逐段报告时的可选顶层对象；过期哈希、缺失截图和无法对应正文的标红只告警，不替代内部审稿，也不按总体百分比自动触发修订。逐段 `action` 只允许 `kept`、`revised`、`deleted`、`rejected`：`revised` 指就地改写，`deleted` 指删段，禁止理解成扩写。

## 语言风险解释

`repetition_audit.py` 对长句逐字重复和高相似复述提供哈希绑定证据。`prose_lint.py` 检查高频通用微动作、解释连接词、比喻密度、总结式收尾、副词簇、工整修辞、机械三拍、过于整齐的句段节奏、长短语重复和相对项目基线的漂移。命中只表示“值得编辑检查”：悬疑复沓、刻意排比、角色口癖和场景节奏都可能是合理原因。

纠正式句型或重复句首只有成组出现才报告。编辑必须回到上下文判断它们是在塑造人物、制造节奏，还是反复替读者校正结论。人物对白中的自然口癖、法庭质询和刻意复沓可以保留。

不得单凭词表、句长或扫描结果删除项目声音，也不得一刀切删除副词、强加迟疑或无功能细节、追求更大的句长方差。不得把结果表述为抄袭、机器生成或作者身份鉴定。

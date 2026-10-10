# 章节独立审稿系统

## 目的

每章在正式提交前完成五种互补检查：确定性重复审计、语言风险扫描、网文自然度审稿、编辑诊断、目标读者体验模拟。扫描只发现值得复核的模式，不能判断作者身份，也不能输出“AI 概率”。项目已确认正文和 `canon/style-profile.md` 始终是声音基线。

网文自然度审稿按 [webnovel-naturalness-review.md](webnovel-naturalness-review.md) 执行。它对所有新写或修改过的章节强制生效，不因 lint 无 finding、普通审稿已通过、作者要求停止润色或正文只改一句而省略。

## 角色隔离

有可用子代理时，让自然度审稿、编辑与读者模拟分别读取本章、必要正史和风格档案，避免互相锚定。没有子代理时，在同一代理内依次执行三个上下文隔离的角色通道：先让自然度审稿定位模式簇，再让编辑诊断因果、结构和修订方向，最后让读者只报告在哪里产生了什么体验。读者不替作者改稿，编辑不伪装成目标读者投票。

- 编辑检查：读者承诺、因果、结构、人物、声音、连续性、行文执行。番茄短故事的 `character` 还要覆盖人设漂移、无代价胜利、情绪硬喊、新人难认；细则见 [fanqie-character-craft.md](fanqie-character-craft.md)。
- 自然度审稿：回声重复、副词过密、工整修辞、机械节拍、解释过满、纠正式骨架、对白播设定、人物同声、因果过度装配、通用反应和主题封口。
- 读者模拟：以具体目标读者 persona 记录逐点反应、继续阅读意愿、好奇与卡顿位置。作者看不出章节问题时，冷读者至少能回答：他叫什么、他想干什么、他正在做什么；答不上来记入入口或本章目标问题。细则见 [fanqie-revision.md](fanqie-revision.md)。
- 三者可以意见不同。保留分歧，不用平均分消解它。

## 执行顺序

进入下列正式审稿前，必须完成 [prose-naturalization.md](prose-naturalization.md) 的“正文后的真人感改写阶段”：保存原稿、冻结事实、定位证据簇、做一轮局部改写、核验事实与阅读连贯性，并保存过程记录。无问题时允许不改；不得为了留下修改痕迹强行改句。该前置阶段适用于新写正文，也适用于作者授权修改的正文；作者明确停止润色时不再改写，但仍执行正式审稿。审稿只读取最终正文，过程记录不代替审稿结论。

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

番茄短故事第一节在第 2 步后另运行 `opening_audit.py --window 300`。目标读者先只看脚本截出的前 300 字，复述人物关系、当前事件、主角选择、具体风险与下一问；并指出前三行有没有看点、哪句想滑走。编辑再检查这些信息是否形成因果链，以及开篇花活是否进入主线。复述需要作者补充背景、主角到 300 字仍无主动选择、风险只有抽象情绪，或下一问无法由后文回答时，至少记为 `high` 入口问题并阻断提交，修订后重新生成窗口。脚本指标本身不形成通过或阻断结论。细则见 [fanqie-new-book.md](fanqie-new-book.md)。

番茄短故事的写节审稿与最后一节全文终审，还要按 [fanqie-signing-quality.md](fanqie-signing-quality.md)、[fanqie-character-craft.md](fanqie-character-craft.md) 与 [length-modes.md](length-modes.md) 的“情绪曲线”检查：不套用他人结构与核心剧情、不靠机械扩写拉长、大段必须推动情节、人物行为对得上角色卡、重要胜利有真实代价、情绪落到身体而非旁白硬喊、新人出场能认、对白能区分，以及收口完整。 编辑必须指出每节情绪的触发动作、方向变化、代价和离场余波；若连续三节没有情绪方向变化，或希望、损失、释放都只靠旁白宣布，标记 `needs-revision`。第一节与长篇前三章另按 [fanqie-new-book.md](fanqie-new-book.md) 检查设定微创新、首屏看点和无效开篇花活。写章还要按 [fanqie-consistency.md](fanqie-consistency.md) 检查战力/金钱/规则前后一致、时空不瞬移、不为爽点降智。最后一节终审：核对单一主承诺是否兑现、主要线索是否闭合、关键铺垫是否回收、配角选择是否产生后果、结局是否同时具备因果必然性与初读意外感；结尾既不能在矛盾解决后继续替读者概括主题，也不能把最后一场已起手的动作切成半句。对于后文保留未知或纠正主角判断的事实，从揭示点回查首次陈述：前文只能确认当时可知的路径和结果，不能由叙述者提前给出与后文疑点冲突的确定答案。这里的外部读者视角不是把正文改成第三人称，而是暂时放下作者身份，按普通读者顺序通读全文。开放结尾只允许保留作者已确认的余韵，不能遗漏主要矛盾的处理；去除总结句也不能牺牲结局因果。

若采用规则反噬型现实爽文，编辑还要核对让步、反咬、合法退出和依赖链是否逐步出现；对方的最终损失必须由其先前享受的资源、客户、租户、信誉或便利传导而来，不能只靠作者宣判或凭空降罚。


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
- 编辑维度：`promise`、`causality`、`structure`、`character`、`voice`、`continuity`、`line`、`originality`、`padding`、`ending`。`character` 在番茄短故事中至少覆盖：选择能否从角色卡解释、重要胜利有无真实代价、情绪是否落到身体、对白能否辨认说话人。`continuity` 至少覆盖战力/金钱/规则是否对上法则库、时间地点是否接上时间线、有没有为爽点降智；细则见 [fanqie-consistency.md](fanqie-consistency.md)。
- 读者状态：`engaged`、`mixed`、`drop-risk`；完成意愿：`continue`、`uncertain`、`stop`。
- 体验通道：`transportation`、`aesthetic`、`social`、`curiosity`、`flow`；倾向：`positive`、`negative`、`mixed`。
- 处理结果：`accepted`、`revised`、`author-approved`。最后一种还需 `decisionId`。

所有 `evidence` 必须是当前最终章节正文的逐字子串。不要把概括、推测、修改前已删除的句子或改写后的句子伪装成证据。`externalNaturalness` 是作者提供朱雀逐段报告时的可选顶层对象；过期哈希、缺失截图和无法对应正文的标红只告警，不替代内部审稿，也不按总体百分比自动触发修订。逐段 `action` 只允许 `kept`、`revised`、`deleted`、`rejected`：`revised` 指就地改写，`deleted` 指删段，禁止理解成扩写。

### 外部报告与最终审稿的版本边界

导入和复测流程见 [prose-naturalization.md](prose-naturalization.md) 的“朱雀分段报告的使用”。PDF 可以替代截图作为 `sourceArtifacts`，路径仍须在 `reviews/evidence/`。`checkedAt` 记录可核实的检测时间；仅有打印时间时明确标注“报告显示时间，检测时间未知”。`overallSignal` 保留原报告的指标名与值，不由本地扫描生成。

`externalNaturalness.reviewedTextSha256` 始终属于实际送检版本，不改成新正文哈希来消除告警。正文已改而尚未复测时，保留旧哈希及其版本不一致告警，并在过程记录注明未复测；找不到送检原稿时只保存外部过程记录，不编造该对象。`flaggedPassages[].text` 仍需是最终正文逐字子串；被删除的原句、旧版摘文与跨版映射放到过程记录，不能为填 `deleted` 动作把旧句塞进最终证据。

过程记录最少包含：

| 项目 | 记录要求 |
|---|---|
| 报告来源 | 原始文件相对路径、SHA-256、报告编号、显示时间及时间类型 |
| 送检版本 | 原稿路径、SHA-256、核对方式；无法核实则写未知 |
| 分段索引 | 原片段编号、页码、原标签与 AIGC 值、首尾锚点、原稿段落范围 |
| 编辑决定 | 逐字原句、具体阅读代价、保留/就地改写/删除及理由；没有问题也记录保留 |
| 改后核验 | 新正文 SHA-256、改前/改后有效字数与变化比例、90% 字数护栏结果、因果与事实核对、情绪回报 |
| 复测对照 | 新报告与送检版本、片段对齐依据、可比范围、原始结果、阅读结论；无报告写未复测 |

过程记录用于人工复核，目前项目校验器只检查既有 `externalNaturalness` 字段、路径和版本告警，不校验分段值、报告哈希或跨版对齐。不要声称这些扩展记录已被脚本验证。

## 语言风险解释

`repetition_audit.py` 对长句逐字重复和高相似复述提供哈希绑定证据。`prose_lint.py` 检查高频通用微动作、解释连接词、上帝预告、对白标签密度、经典三段式、破折号揭晓链、比喻密度、总结式收尾、副词簇、工整修辞、机械三拍、过于整齐的句段节奏、长短语重复和相对项目基线的漂移。命中只表示“值得编辑检查”：悬疑复沓、刻意排比、角色口癖、古风里偶尔的「道」和场景节奏都可能是合理原因。外壳清单与保留边界见 [prose-naturalization.md](prose-naturalization.md)。

纠正式句型或重复句首只有成组出现才报告。编辑必须回到上下文判断它们是在塑造人物、制造节奏，还是反复替读者校正结论。人物对白中的自然口癖、法庭质询和刻意复沓可以保留。

不得单凭词表、句长或扫描结果删除项目声音，也不得一刀切删除副词、强加迟疑或无功能细节、追求更大的句长方差。不得把结果表述为抄袭、机器生成或作者身份鉴定。

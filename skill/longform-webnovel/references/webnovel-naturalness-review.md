# 网文自然度强制审稿

## 目的

每次新写或修改章节正文后，都用本模块做一次独立的网文自然度审稿。它检查影响沉浸、人物可信度和阅读余韵的可观察文本模式，不判断作者身份，不输出 AI 概率，也不以“像不像人工”为无限优化目标。

**这是章节门禁，不是按需润色。** 哪怕只改一句、`prose_lint.py` 没有 finding、编辑与读者模拟已经通过，正文哈希变化后仍必须重做本审稿。作者要求“直接交稿”可以阻止无证据润色，不能跳过审稿。

需要建立个人声音或执行定向修改时，同时读取 [prose-naturalization.md](prose-naturalization.md)。

## 输入与视角

审稿者读取当前完整章节、`canon/style-profile.md`、必要正史和最近 2–5 章已确认正文。先以目标网文读者身份顺读，记录哪里产生“作者在安排我怎么理解”“角色在播设定”“每一步都过于刚好”等体验；再回到编辑视角定位逐字证据。

不要先看 `prose_lint.py` 的结论再决定读者感受。扫描结果只能用于复核遗漏，不能替代语义审稿。

## 七类模式

| 类别 | 形成问题簇的证据 | 常见读者代价 | 定向方向 |
|---|---|---|---|
| `over-explanation` | 动作、对白或场景已证明后，旁白再次解释人物判断、关系意义或事件结论 | 情绪被预先说明，读者没有参与理解 | 删除重复判词，或让必要信息落到动作与后果 |
| `corrective-syntax` | “不是……而是……”“没有……只是……”等纠正式骨架连续承担金句或总结功能 | 叙述者持续校正读者，声音显得统一而用力 | 保留真正的认知转折，改写重复骨架 |
| `expository-dialogue` | 角色向本来知情的人完整讲规则、背景、证据或标准反驳 | 人物像设定播报器，对话失去利益和回避 | 缩到角色此刻愿意说的部分，让信息从反应中露出 |
| `same-voice` | 多名角色共享相同的冷静程度、词汇、句长、机锋和总结能力 | 人物只能靠名字区分 | 从各自利益、恐惧和回避方式重做命中对白 |
| `over-engineered-causality` | 多个物件、回忆、规则与巧合都立即服务同一钩子，人物没有独立选择造成的摩擦或余波 | 场景像预先装配的提纲，世界只为主角让路 | 不拖慢主线；让一项信息延迟、失败或产生真实选择代价 |
| `generic-reaction` | “眼前一黑、眯起眼、嘴角一勾、深吸一口气”等通用反应或电影式转场成组替代身体过程 | 人物身体与场景失去具体性 | 改为会改变动作、距离或判断的身体反应 |
| `theme-closure` | 可见后果或情绪已经落地，结尾又概括主题、成长或真正意义 | 余韵被封口，读者被告知应该怎样感受 | 停在行动、物件、关系变化或未回答的问题上 |

商业网文的快节奏、短段落、倒计时、章尾钩子和常用句式本身不是问题。只有同类证据形成模式簇，并造成具体读者代价时才写 finding。孤立单句只进入复核，不为了填报告强行修改。

## 审稿与修改

1. 记录初审正文 SHA-256。
2. 顺读后按七类模式列证据簇；每项必须说明 `readerCost` 和只影响命中段的 `direction`。
3. 无成立问题簇时标记 `pass`，`revision.action` 为 `not-needed`，不得继续寻找理由润色。
4. 只有轻微、可保留的风险时标记 `pass-with-notes`。未解决的高优先级问题不得放在此状态蒙混通过。
5. 影响沉浸、人物或收尾且需要修改时标记 `needs-revision`，按 [prose-naturalization.md](prose-naturalization.md) 最多自动定向修改一次。不得整章重新生成。
6. 修改后重新运行章节指标、语言扫描、本审稿、编辑审稿和读者模拟。最终报告只引用修改后仍存在的逐字证据；已经删除的问题写入 `revision.changedCategories`，并用 `beforeTextSha256` 记录修改前版本。
7. 复审仍为 `needs-revision` 或仍有未解决的 `high` finding 时阻断提交。作者明确接受风险时，使用 `author-approved` 并关联 `state/decisions.json` 中已确认的 `naturalness-exception` 决策；该决策必须绑定本章章号与最终正文 SHA-256，不能复用无关决策。

## 报告结构

将结果写入 `reviews/第NNNN章-review.json` 的 `naturalness` 对象：

```json
{
  "status": "pass",
  "diagnosis": "未发现影响沉浸的自然度问题簇。",
  "reviewedTextSha256": "最终章节正文 SHA-256",
  "findings": [],
  "revision": {
    "action": "not-needed",
    "notes": "没有证据支持额外修改。"
  }
}
```

执行过修改时使用：

```json
{
  "status": "pass",
  "diagnosis": "解释过满问题已处理，复审未见残留问题簇。",
  "reviewedTextSha256": "修改后章节正文 SHA-256",
  "findings": [],
  "revision": {
    "action": "revised",
    "beforeTextSha256": "修改前章节正文 SHA-256",
    "changedCategories": ["over-explanation"],
    "notes": "删除重复结论，以人物动作保留必要因果。"
  }
}
```

仍保留的 finding 使用：

```json
{
  "priority": "low",
  "category": "corrective-syntax",
  "evidence": ["当前最终正文中的逐字片段"],
  "readerCost": "具体说明读者体验损失",
  "direction": "只针对证据段的修改方向",
  "resolved": false
}
```

`evidence` 只能引用最终正文中的逐字子串。修改前已删除的句子不得伪装成最终证据，也不把审稿意见本身写进正文。

自然度风险例外的决策至少包含：

```json
{
  "id": "accept-naturalness-risk-0016",
  "status": "confirmed",
  "kind": "naturalness-exception",
  "chapter": 16,
  "reviewedTextSha256": "最终章节正文 SHA-256"
}
```

## 禁止事项

- 不用错别字、病句、随机断句、方言或无功能闲聊制造人味。
- 不把任何单词、句长指标、短段数量或扫描命中当成作者身份证据。
- 不为自然度牺牲因果清晰、类型回报、世界规则或已确认的个人声音。
- 不因作者要求停稿而跳过审稿；若无成立问题，审稿结论就是 `pass`，无需修改。
- 不做第二轮无证据润色。一次定向修改后仍有阻断问题，报告并停止提交。

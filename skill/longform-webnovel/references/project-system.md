# 项目系统

## 目录

```text
作品目录/
├── project.json
├── canon/
│   ├── story-contract.md
│   ├── characters.md
│   ├── world.md
│   ├── style-profile.md
│   ├── publishing-package.md
│   ├── market-brief.md
│   └── timeline.md
├── planning/
│   ├── series-map.md
│   ├── current-volume.md
│   └── rolling-outline.md
├── state/
│   ├── story-state.json
│   ├── threads.json
│   ├── rewards.json
│   ├── cast-arcs.json
│   └── decisions.json
├── chapters/
├── reviews/
├── research/
│   └── market-snapshots/
└── sessions/
```

## 信息所有权

- `story-contract.md`：作品不能轻易改变的承诺、边界和核心体验。
- `characters.md`：相对稳定的人设、欲望、恐惧、能力边界、语言特征。
- `world.md`：世界规则和已证实的规则后果；不要堆百科。
- `style-profile.md`：已确认的语言风格参数、作者手法转译、项目定制和禁用倾向。
- `publishing-package.md`：确认书名、公开检索记录、封面提示词、负面提示词和排版说明。
- `market-brief.md`：可选的公开市场观察、事实、推断、置信度和创作隔离线。
- `timeline.md`：已发生事件的时间顺序，只记录正史。
- `series-map.md`：长篇保存可收束主线与远期选择；短故事保存单一主承诺和结局边界。
- `current-volume.md`：长篇保存当前卷；短故事保存全文有限结构。
- `rolling-outline.md`：长篇保持未来 5–10 章；短故事覆盖全部剩余分节。
- `story-state.json`：当前章结束时的机器可读快照。
- `threads.json`：主线、支线、悬念、伏笔和承诺的生命周期。
- `rewards.json`：未来爽点计划与已经兑现的 3/5 章节拍账本。
- `cast-arcs.json`：核心/常驻配角的独立目标、弧光阶段、选择证据、转折窗口与关系网络。
- `decisions.json`：重大决策的待确认、已确认和否决记录。
- `reviews/`：每章绑定正文哈希的语言风险扫描、编辑诊断和目标读者模拟。
- `research/market-snapshots/`：带日期、来源 URL 和样本窗口的公开市场快照。
- `sessions/`：跨会话交接，不替代正史文件。

每个正式提交章必须新增包含 `chapter-NNNN` 的 Markdown 交接文件，例如 `sessions/2026-08-21-chapter-0016.md`。它记录本章已同步的状态和下一会话入口，不保存尚未发生的计划为正史。

## 状态规则

`project.json` 是提交索引。`storyMode` 使用 `serial` 或 `fanqie-short-story`；旧项目缺失时按 `serial`。短故事另以 `shortStory` 保存目标总字符数、预计分节数、创作状态和结尾类型，详见 [length-modes.md](length-modes.md)。`lastCommittedChapter` 只能指向正文和状态都已完成的章。`latestDraftChapter` 可以领先，表示存在未提交正文。

`totalContentChars` 必须等于全部已提交正文的有效字符总数，口径与 `chapter_metrics.py` 一致：忽略 Markdown 标题和代码块，中文按字、连续英文或数字按词计数。正式提交后，故事合同、人物、世界、语言风格、当前卷和滚动章纲不得仍残留初始化模板中的“待填写”“待确认”“待规划”。

`project.json.styleProfile` 保存主风格、辅风格、状态和更新时间；它必须与 `canon/style-profile.md` 的选择区一致。预设、自定义手法卡和换风格规则见 [style-system.md](style-system.md)。

`project.json.publishingPackage` 保存定名、唯一性检查和封面提示词状态。新书第一章提交前必须为 `active`；旧项目迁移可为 `legacy`。完整流程见 [publishing-package.md](publishing-package.md)。

`project.json.marketResearch` 保存可选研究状态、截止日期和来源/样本数，必须与 `canon/market-brief.md` 和对应快照一致。`unrequested` 不阻止创作。格式与边界见 [market-research.md](market-research.md)。

`project.json.reviewGate` 保存开始强制执行的章号，以及编辑、读者模拟和语言扫描开关。新项目从第 1 章执行；旧项目迁移只从下一章开始，不伪造历史审稿。完整格式见 [review-system.md](review-system.md)。

`story-state.json` 只保存当前有效状态和最近变化，不复制整部小说。每项重要事实包含来源章号；推测必须标成 `uncertain`，不能伪装成正史。

长篇用 `project.json.rewardCadence` 保存节拍：`smallEvery: 3`、`majorEvery: 5`、`supercycle: 15`、`overlapPolicy: "major-absorbs-small"` 和开始强制执行的章号。短故事保留该字段以兼容项目工具，但不执行章号周期，改用全文比例结构锚点。改变模式或节拍属于故事合同级决定，必须由作者确认。

`rewards.json` 的完整结构和证据规则见 [reward-system.md](reward-system.md)。长篇每 3 章需要 `small` 以上兑现、每 5 章需要 `major`；短故事只在不可逆选择、中点翻转、决定性对抗和结局等有限结构位置记录兑现。

`cast-arcs.json` 不复制人物正史。稳定人设放在 `characters.md`；当前弧光与关系变化按 [supporting-cast.md](supporting-cast.md) 记录。迁移前旧章可标记为未审计，新章必须随章节快照同步。

`threads.json` 中每条线索至少包含：

- `id`：稳定且唯一；
- `kind`：`main`、`subplot`、`promise`、`foreshadow`；
- `status`：`open`、`advanced`、`deferred`、`resolved`、`transformed`；
- `openedChapter`、`lastAdvancedChapter`；
- `dueWindow`：建议兑现或推进的章号区间；
- `question`：读者等待什么答案；
- `payoff`：预计如何形成回报，可留空但不能永久含糊；
- `history`：重要推进记录。

## 导入旧稿

1. 不直接猜测完整正史。按章节顺序读取已有正文。
2. 先抽取明确事实，再标记矛盾、未知和可能设定。
3. 建立故事合同草案、人物卡、时间线和开放剧情线。
4. 把无法从正文确定且会影响续写的问题交给作者确认。
5. 生成近景滚动章纲后再续写。

导入旧格式项目或发现缺失 v5 文件时，不手工猜测字段；按 [operations.md](operations.md) 运行迁移脚本。

## 会话恢复

新会话先读稳定层和当前层，不通读全书：故事合同、语言风格档案、当前卷、滚动章纲、五个状态 JSON、最近会话记录、最近 1–2 章。只有遇到具体矛盾时，才按来源章号回读旧章。

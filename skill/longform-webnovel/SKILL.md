---
name: longform-webnovel
description: 创建、规划、连载、续写和修订中文长篇网文或番茄短故事项目；也可把参考短故事拆成可迁移的结构、情绪与叙事机制，生成非换名复述的新故事并检查原文复用风险。支持追妻追夫火葬场等情感题材、公开市场样本、书名与封面提示词、语言风格、个人声音建模、自然化改稿、配角弧光、跨会话正史、编辑审稿和目标读者模拟。也适用于多Agent小说、角色skill、沙盒连载、跨章弧、修炼法则世界观，以及每个角色隔离情绪与意图后再写章。适用于开新网文、创作或仿写短故事、处理 AI 味或模板腔、市场定位、起书名、制作封面提示词、挑选文风、参考作者手法、继续连载、修订诊断、扩展新卷或完成有限篇幅小说；不用于洗稿、逐段同义改写或规避内容检测。
---

# 长期网文连载

把小说视为持续演化的状态，而不是一串互不相干的章节。默认 `serial` 面向中文长篇网文，每章以约 2500 字作为起始估算和节奏信号，不是硬性配额；`fanqie-short-story` 面向一次完整收束的番茄短故事，也按场景职责保留篇幅弹性。两种模式都采用快进入、强推进和清晰回报，题材不固定；先从故事承诺推导写法，不套用固定类型模板。

## 基本原则

1. 让故事长期扩展，但不给故事注水。每次扩展必须来自已有行动的后果。
2. 长篇保持三层规划：当前章具体、未来 5–10 章清楚、当前卷稳定；更远内容只保留方向和选择。短故事让当前节具体、全部剩余分节可见、结局稳定。
3. 每章至少改变两个状态维度：目标、关系、认知、资源/能力、世界局势、道德位置。
4. 章节目标字数是节奏参考，不是硬性配额。正文不足时先补充能推进因果、揭示信息、迫使选择或交付回报的场景；若继续扩写会注水，就拆分或增加章节/分节，并同步更新章纲、爽点账本、状态快照和篇幅合同。
5. 长篇每 3 章兑现一次小爽点或小高潮，每 5 章兑现一次大爽点或大高潮；短故事改用全文比例结构锚点，不机械补齐 3/5 章。所有兑现都必须造成真实状态变化。
6. 不用单纯提高战力、扩大地图或复制反派来续命。升级必须同时增加代价、责任、限制或新的对抗方式。
7. 重大决策询问作者，其余内容自主完成。按 [approval-policy.md](references/approval-policy.md) 判断。
8. 正文完成后再抽取事实并更新状态。不能把计划中的内容提前写成既定事实。
9. 把语言风格保存为可描述参数。可以参考作者手法，不复刻标志性表达；人物声音和故事清晰度优先于表面仿写。自然化依靠作者确认样本、人物利益和定向修订，不靠随机句长、故意病句或“去 AI 词表”。作者确认当前版本已达目标后停止自然化循环，后续只由明确的节奏、重复、连续性、完读问题或新的可比发布数据触发正常编辑。
10. 第一章正文前先确认有辨识度的书名和封面提示词；公开检索降低撞名风险，但不承诺绝对唯一。
11. 让少量核心配角拥有独立欲望、选择和后果。弧光可由事业、信仰、责任、亲情、友情、师徒、竞争、债务、复仇、求生、归属或爱情驱动；爱情只是可选项，不把配角弧光默认写成感情线，也不把所有关系写成主角奖励。
12. 每次写成或修改章节正文后，强制执行网文自然度审稿、编辑审稿与目标读者模拟；模板化语言扫描只提示编辑风险，不判断文本是否由 AI 创作。正文哈希变化会让全部旧审稿失效。
13. 角色是项目内 skill（`cast/{id}/`），不是全局 Cursor skill。写章前先隔离收意图，再由法则裁判否决，最后写手成章；角色不得写正文。
14. 章不是收束单位，弧才是。每章必须改变状态，但开篇目标可以跨多章才兑现或彻底失败。失败、改路、暴露都算交付；空转非法。

## 识别任务

- **新建项目**：用户只有灵感、题材、梗或一句话设想。
- **番茄短故事**：用户要写可一次完结或少量分节的短故事。
- **参考短故事再创作**：用户提供样稿并要求仿写、借结构、换题材重写或生成相似阅读体验。
- **继续连载**：项目结构存在，用户要求下一章、若干章或继续写。
- **规划扩展**：用户要求卷纲、章纲、新地图、新阶段或长期方向。
- **修订诊断**：用户指出注水、崩设定、节奏慢、人物失真或战力失控。
- **发布后诊断**：用户提供展现、阅读、完读、解锁或互动数据，要求判断低展现或低完读原因。
- **导入旧稿**：用户已有正文，但没有本 Skill 的项目状态。
- **增配角 / 群像仿真**：需要独立角色 skill、按需生成配角，或主角在未完成弧里自由探索。

先读取 [project-system.md](references/project-system.md)，并按 [length-modes.md](references/length-modes.md) 确定篇幅模式。用户要求仿写、借鉴样稿或换题材重写时读 [reference-adaptation.md](references/reference-adaptation.md)；需要公开市场研究时读 [market-research.md](references/market-research.md)；新书定名或准备封面时读 [publishing-package.md](references/publishing-package.md)；设计配角、群像、人物弧或关系网络时读 [supporting-cast.md](references/supporting-cast.md) 与 [ensemble-character.md](references/ensemble-character.md)；写下一章或跑角色意图时读 [ensemble.md](references/ensemble.md)；涉及新卷或长期扩展时再读 [continuation-engine.md](references/continuation-engine.md)；规划爽点时读 [reward-system.md](references/reward-system.md)；选择、组合或更换文风以及参考作者手法时读 [style-system.md](references/style-system.md)；写正文时读 [chapter-craft.md](references/chapter-craft.md) 与 [scene-craft.md](references/scene-craft.md)。每次写成或修改任何章节正文后，必须读取 [webnovel-naturalness-review.md](references/webnovel-naturalness-review.md) 与 [review-system.md](references/review-system.md)，先执行自然度门禁再提交；迁移、提交或恢复项目时读 [operations.md](references/operations.md)；判断题材写法时读 [genre-routing.md](references/genre-routing.md)。故事以追妻、追夫、火葬场、破镜重圆、旧爱追悔或“追而不得”为主要承诺时，还要读取 [relationship-regret.md](references/relationship-regret.md)；纯离婚清算、资产追偿或复仇故事不因存在前任自动套用。用户指出“AI 味”、机械、模板腔、对白太正确、解释过满，要求建立个人声音，或自然度审稿需要定向修改时，必须读取 [prose-naturalization.md](references/prose-naturalization.md)。不要无差别加载全部参考资料。

番茄短故事或 `serial` 长篇开篇做信息流标题、前 300 字、黄金三章、试读节点或入口审稿时，读取 [short-story-information-flow.md](references/short-story-information-flow.md)。用户提供发布数据时读取 [performance-feedback.md](references/performance-feedback.md)，用 `performance_feedback.py` 保存原始统计并按漏斗定位；需要按统一口径截取首屏时运行 `scripts/opening_audit.py`。不要无差别加载全部参考资料。

## 新建项目

1. 若用户未指定项目路径，在当前工作目录下使用安全的作品名创建项目文件夹。
2. 只询问无法合理推断且会改变作品方向的信息。通常一次收集：故事种子、希望避免的内容、主角初始困境。题材可以由故事种子推导，也可以给出 3 个差异明显的方案让作者选择。
3. 确认 `serial` 或 `fanqie-short-story`，提出简短的故事合同，并按 [style-system.md](references/style-system.md) 给出 2–4 个适配的语言风格选项。用户指定作者时先做手法转译卡；用户提供亲手改稿或原创样本时，按 [prose-naturalization.md](references/prose-naturalization.md) 提取有逐字证据的个人声音规则。短故事还需确认目标总长度、预计分节和结尾类型。
4. 用户要求市场定位或题材竞争不明时，按 [market-research.md](references/market-research.md) 研究公开来源；正式建项前先把快照保存在项目外的临时工作目录，不能成为迟迟不写的借口。短故事必须以短故事专属样本为主要证据，长篇榜只能作为旁证，不能据此宣称短故事热门。
5. 按 [publishing-package.md](references/publishing-package.md) 生成 8–12 个非公式化书名，筛出 3 个做公开精确检索；为推荐书名提供封面主提示词、负面提示词，并按 [cover-typography.md](references/cover-typography.md) 给出 3 个结构明显不同的书名字效方向，推荐其中 1 个，写清断行、字形骨架、笔画性格、材质、描边层、投影/立体深度、占比、安全区和主体遮挡关系。将候选合同或项目运行 `story_overlap.py`，与作者同一作品库中的历史项目比较；高风险时重做人物、关系、核心危机或解决机制，除非作者确认是同世界观续作。
6. 将故事合同、第一卷重大设计、语言风格、终选书名和封面提示词一起交给作者确认。不要在确认前批量写正文。
7. 运行：

```bash
python3 <skill-dir>/scripts/init_project.py --path <项目目录> --title <书名> --style <风格标识> --mode <模式> --protagonist-id <id> --protagonist-name <姓名>
```

8. 用 `publishing_package.py` 保存公开检索记录与封面提示词；若第 4 步生成了市场快照，用 `market_brief.py` 归档到项目。将确认内容和已作出的重大选择写入故事合同及决策记录，建立主要人物、分层配角、世界规则与 `canon/laws.md`，填主角 `cast/{id}/SKILL.md` 和 `planning/current-arc.md`。长篇规划当前卷和未来 5–10 章；短故事按 [length-modes.md](references/length-modes.md) 规划全文剩余分节。
9. 运行 `plan_cadence.py --write`。长篇建立未来 15 章节拍；短故事按预计总分节建立全文比例结构锚点。补全每个锚点的回报类型、铺垫和代价。
10. 运行 `validate_project.py`。只有 `publishingPackage.status` 和 `styleProfile.status` 均已确认后才开始正文；市场研究不是许可条件。

## 参考短故事再创作

把“仿写”解释为复用阅读机制，不解释为换名复述。先从参考稿提取抽象机制卡和必须替换清单，再只依据机制卡设计新故事合同；人物专名、独特物件、事件链、证据链、关键场面、结局揭示和标志性表达不得沿用。参考稿属于作者本人或公版且作者明确要求改编时，才按其确认的授权范围保留具体元素。

写正文时不要逐段对照参考稿。每节完成后运行 `reference_guard.py` 检查连续原文复用与禁用词，再运行 `story_overlap.py` 检查作者作品库内的同质化；任一高风险都先重写，不能把脚本结论称为抄袭认定或法律判断。

### 番茄短故事差异

- 一个短故事是一个有终点的作品，不是缩短版无限连载。只保留一个主承诺、一个主要矛盾和能在结局前闭合的少量副线。
- 正文可以是一个完整文本或少量连续分节；每节仍执行指标、语言扫描、编辑审稿、读者模拟和状态提交。
- 短故事动笔前建立入口合同；标题、前 300 字、主情绪、主动选择和试读节点按 [short-story-information-flow.md](references/short-story-information-flow.md) 联动检查。前 300 字必须让冷读者说清“谁遇到什么、做了什么、会失去什么、接下来等哪个答案”，但不按固定句数或反转次数机械写作。
- 把 `shortStory.status` 从 `planning` 更新为 `drafting` 后再提交第一节。全文终审通过、主要线索闭合且结局回报已交付后改为 `complete`。
- 标记 `complete` 后停止自动续写。改成长篇、增加续作或重开结局都必须询问作者。
- 短故事进入 `complete` 前必须完成全文外部读者终审，写入 `reviews/final-review.json`；这里的“第三视角”指作者退场的普通读者审读，不改变正文既定人称。
- 发布后不要从一次小流量测试反推永久结论。保存推荐状态和完整漏斗数据；下一个故事的选题与包装可以吸收数据，但不能把无样本的猜测写成平台规则。

## 继续连载

按以下顺序执行，不要依赖聊天记忆代替项目文件：

1. 定位包含 `project.json` 的项目根目录。
2. 若 `schemaVersion` 旧于当前版本，缺少 v6 群像文件，或缺少 v7 自然度门禁，先按 [operations.md](references/operations.md) 运行 `migrate_project.py`。
3. 读取 `canon/story-contract.md`、`canon/style-profile.md`、`canon/publishing-package.md`、`canon/laws.md`、`planning/current-volume.md`、`planning/rolling-outline.md`、`planning/current-arc.md`。
4. 读取 `state/story-state.json`、`state/threads.json`、`state/rewards.json`、`state/cast-arcs.json`、`state/decisions.json`，以及上场角色的 `cast/{id}/state.json`。
5. 读取最近 1–2 章正文、对应审稿报告和最新 `sessions/` 记录；只在需要时查询更早章节。
6. 运行 `validate_project.py`。先处理错误；把警告纳入本章计划。
7. 若存在会阻断本章或当前写作范围的未决重大决策，先给出 2–4 个明确选项及影响，等待作者选择；未来章的判断点不提前阻断当前章。
8. 若无阻断，按 [ensemble.md](references/ensemble.md) 写未完成合同、隔离收意图、法则裁判，再按 [chapter-craft.md](references/chapter-craft.md) 与 [scene-craft.md](references/scene-craft.md) 写正文。先写空间、身体和动作过程，再写对白。长篇按章号判断普通章、小爽点章或大爽点章；短故事按全文结构位置判断本节职责。本章只推进或加压一格，不要求把弧写完。确认目的、状态变化、兑现内容、结尾推动力和五个风格锚点。
9. 按 [review-system.md](references/review-system.md) 运行语言风险扫描、[网文自然度强制审稿](references/webnovel-naturalness-review.md)、独立编辑审稿和目标读者模拟。自然度审稿对每个新写或修改过的章节都必须执行，不以 lint 通过、普通审稿通过、改动很小或作者催交为跳过理由；命中问题簇时按 [prose-naturalization.md](references/prose-naturalization.md) 只定向修改证据段，最多自动修改一次，并基于最终正文重新执行全部审稿。
10. 按“章节提交事务”更新全部状态文件，再向作者报告。

## 章节提交事务

把正文和状态更新视为同一次提交。不得先直接修改正式项目再补状态：

1. 按 [operations.md](references/operations.md) 创建 staging 目录，把新正文和所有拟更新文件按项目相对路径写入 staging。
2. 在 staging 中写 `chapters/第NNNN章-标题.md`，不要覆盖现有章节，除非用户明确要求修订。
3. 运行章节指标；短故事先用“目标总字符数 ÷ 预计分节数”得到本节起始估算，单篇不分节时使用全文目标替换 `2500`。这个 `--target` 只用于发现节奏异常，不得阻断自然短章、长章或合理增节：

```bash
python3 <skill-dir>/scripts/chapter_metrics.py <章节文件> --target 2500
```

   `fanqie-short-story` 的第一节还要运行 `opening_audit.py <章节文件> --window 300`，并按 [short-story-information-flow.md](references/short-story-information-flow.md) 完成冷读者复述与编辑因果检查。正文变化后重新运行，不能沿用旧窗口判断。

4. 运行 `prose_lint.py`，将结果写入 `reviews/第NNNN章-lint.json`；再按 [review-system.md](references/review-system.md) 分离执行网文自然度审稿、编辑审稿和目标读者模拟，写入 `reviews/第NNNN章-review.json`。自然度 finding 必须引用问题簇的逐字证据并说明读者代价，不能根据单个词命中机械重写。自然度对象、审稿报告和 lint 都必须绑定当前正文 SHA-256。
5. 若自然度审稿或其他审稿存在阻断项，自动定向修改一次并重新运行指标、扫描、自然度审稿、编辑审稿和读者模拟。仍有高优先级问题、`needs-revision` 或弃读风险时停止提交；只有作者通过重大决策记录明确接受风险时才可例外。
6. 从已经通过审查的正文抽取新增事实：人物状态、关系变化、时间地点、资源变化、公开信息、秘密揭示、世界规则实例。
7. 在 staging 中更新 `state/story-state.json`，不得删除仍然有效的旧事实。
8. 在 staging 中更新 `state/threads.json`：推进、兑现、转化或延期剧情线；延期必须记录原因和新的兑现窗口。
9. 在 staging 中更新 `state/rewards.json`。按 [reward-system.md](references/reward-system.md) 填写回报类型、铺垫章、正文证据、代价、状态变化和冲突/解法模式。
10. 在 staging 中更新 `state/cast-arcs.json`：只为本章真实发生的配角选择、人生状态或关系变化追加证据；普通露面不算弧光推进。同步更新上场角色的 `cast/{id}/state.json`、`contracts/chapter-NNNN.json`、`intents/chapter-NNNN/` 与 `planning/current-arc.md`。弧未闭环则保持 `open`。
11. 在 staging 中更新 `planning/rolling-outline.md`：长篇删除已完成章并保持 5–10 章窗口，用 `plan_cadence.py` 补齐 15 章节拍；短故事删除已完成分节并保持全部剩余结构可见，不向结局之后补新锚点。
12. 在 staging 中更新 `project.json` 的章号、总字数和当前卷；新增 `sessions/` 交接记录。短故事最后一节若要标记 `complete`，同时暂存 `reviews/final-review.json`。
13. 运行 `commit_chapter.py --project <项目> --staging <staging>`。它会构造预览项目、校验、备份并提交；不要绕过此步骤。

提交失败时正式项目保持原状态，修复 staging 后重试。若异常中断造成部分写入，使用脚本报告的备份目录执行 `commit_chapter.py --restore`，不得假装提交成功。

## 连续创作多章或多节

- 默认顺序写作；下一章必须基于上一章真正发生的内容重新规划。
- 每写完一章都执行完整提交事务，不能等整批结束后才补状态。
- 长篇每 3 章完成一个小兑现，每 5 章完成一个能改变后续局势的大兑现；大爽点章同时执行阶段审查。短故事按结构锚点审查，不为凑章数增写场景。
- 长篇每 5 章检查核心配角能动性，每 15 章至少推进一名核心配角的选择或后果。短故事只保留影响主要矛盾或结局代价的配角选择，不强迫完整副线。
- 到达小篇章或卷末时停止自动跨越边界。若下一步属于重大决策，先询问作者。
- 不并行撰写相邻正文；相邻章节存在强因果依赖，批量并行容易破坏连续性。

## 长期扩展

使用 [continuation-engine.md](references/continuation-engine.md) 的扩展闸门。只有同时满足以下条件才开启新篇章或新卷：

- 已兑现至少一个旧承诺；
- 新目标是此前选择或后果导致的，而非凭空降临；
- 规则、关系或代价至少有一项发生结构性变化；
- 至少关闭或转化一条旧剧情线；
- 新冲突的解决方式不能复刻最近两个篇章。

长期连载不等于拒绝结局。始终保留“可收束路径”：当前主线在若干卷内能够结束；如果继续，是开启有因果联系的新阶段，而不是无限拖延同一问题。

## 修订与诊断

先从高层到低层检查：故事承诺 → 卷结构 → 人物弧 → 章节因果 → 场景 → 句子。不要用润色掩盖结构问题。

修改既有正史前：

1. 列出改动会影响的角色、时间线、伏笔、后续章节和世界规则。
2. 若改动属于重大决策，等待作者确认。
3. 修改正文与所有受影响状态，记录到 `state/decisions.json`。
4. 运行项目校验，并抽查受影响章节的前后衔接。

用户只指出“AI 味重”“不自然”时，不直接全篇改写。先按 [prose-naturalization.md](references/prose-naturalization.md) 区分结构问题、人物同声、对白工具化、解释过密、程序展示过满和主题封口，列出逐字证据与修订范围；保留故事事实和已经成立的个人声音，只对有证据的问题做一次定向修订。

结构级自然化优先检查四件事：主角的非最优选择是否真正改变后续价格、信任、机会或关系；证据缺口是否改变结论边界，而非最后仍证明主角全面正确；人物声音是否来自不同利益与回避方式；流程删减是否保留了会造成延迟、失败或代价的必要手续。修订后还要对照前后章节和正史，检查叙述者是否在前文把后文仍未知的事实提前说死。

“AI 味分数”只能记录作者或读者的主观感知，不能当作检测结果或持续优化指标。作者明确表示停在当前版本时，把停止条件写入 `canon/style-profile.md` 和 `state/decisions.json`；不得为了继续降分人为增加错误、含混、口语、断句、闲聊或随机障碍。以后只有正常编辑问题或新数据支持的具体假设才重开修订。

## 面向作者的输出

保持简洁，不展示原始 JSON 或内部长清单。

- 写章后报告：章节、约略字数、自然度门禁状态、爽点级别、合法结局类型、弧还差什么、本章实际变化、谁的情绪变了、兑现/新增的线索、下一章方向。
- 配角弧光推进时：报告是谁主动做了什么、付出什么代价，以及其目标、能力、身份、信念、关系或立场如何改变。
- 有重大决策时：先说明为什么现在必须决定，再给 2–4 个差异明确的选项和影响。
- 开新书时：正文之前展示终选书名的检索结论、3 个差异明显的书名字效方向及推荐项、适配目标生成器的一次成图提示词、纯底图提示词、标题区域重绘提示词和负面提示词。不能只交付“书法、大气、金色描边”之类抽象形容。
- 有校验问题时：区分阻断错误和可继续的警告。
- 不用“无限生成”承诺掩盖上下文限制；依靠项目文件实现跨会话延续。

## 脚本

- `scripts/init_project.py`：创建原创的长篇连载或番茄短故事项目骨架和初始状态。
- `scripts/migrate_project.py`：将旧项目安全迁移到当前 schema，并保留迁移备份。
- `scripts/plan_cadence.py`：生成或写入长篇 15 章节拍，或短故事全文比例结构锚点。
- `scripts/style_profile.py`：列出、预览或安全应用预设/自定义语言风格档案。
- `scripts/publishing_package.py`：检查书名公式化风险，保存确认书名、公开检索记录和封面提示词。
- `scripts/market_brief.py`：校验并保存带日期、公开来源、样本和置信度的市场观察。
- `scripts/story_overlap.py`：比较候选与历史项目的人名、设定和故事发动机文本信号，提示高同质化风险，不判断抄袭或平台处罚。
- `scripts/reference_guard.py`：比较参考稿与候选正文的连续复用片段和禁用专名，提示编辑风险，不作抄袭或法律认定。
- `scripts/performance_feedback.py`：保存发布后统计窗口，计算阅读/完读漏斗并生成带样本限制的诊断。
- `scripts/commit_chapter.py`：在隔离预览中校验后原子替换文件；失败时自动回滚。
- `scripts/chapter_metrics.py`：统计正文有效字数、段落、对话比例和重复段落信号。
- `scripts/opening_audit.py`：按有效字符口径截取短故事前 100/200/300 字窗口，输出入口审稿所需的文本与基础指标；不代替语义判断。
- `scripts/merge_chapters.py`：将已提交章节按顺序合并为单一 Markdown，可移除章节 H1，并验证有效字数不变。
- `scripts/prose_lint.py`：扫描模板化语言和项目基线漂移，只输出编辑风险信号。
- `scripts/validate_project.py`：校验项目结构、JSON 状态、剧情线窗口、爽点正文证据、模式重复、群像合同/意图和提交一致性。

---
name: longform-webnovel
description: 创建、规划、续写和修订中文长篇网文、短中篇及番茄短故事；支持参考故事机制提炼与原创再创作、人物与群像、语言风格和个人声音、自然化改稿、跨会话正史、编辑审稿、市场定位及书名封面。适用于开新书、继续连载、修订诊断和提炼小说写法；不用于洗稿、逐段同义改写或规避内容检测。
---

# 长期网文连载

按当前任务和阶段加载资料。故事是持续演化的状态，正文顺着具体人物正在经历的事写。教程中的机制用于帮助选择与诊断，不是每场必须展示的内容。

## 写作底线

- 尊重作者确认的故事合同、篇幅模式、人物选择、叙述权限与个人声音。参考作品只提炼可迁移手法，不搬专名、剧情链或标志性表达。
- `serial` 与 `novella` 以事件为写作单位：先明确接下去发生的这一件事，连续写并实测字数，到约2500个有效字在已写文本中切下一章。2500是切分阈值，不是“写一章约2500字”的创作目标；不预分每章的剧情、拍数或收尾。切点可以在同一场面中途，下一章从断处接续；标题按切出的内容后定。不把细纲逐条扩写成段落。
- `serial` 每卷一条贯穿线，可有支流；卷末状态差落地后不自动写下一卷。兑现按贯穿线段序，不锁在第 3、5、15 章；`novella` 按全书阶段，`fanqie-short-story` 按全文与分节职责处理。
- 角色是项目内 `cast/{id}/` skill。筹备先对齐正史、角色意图与法则裁定；正文之后才抽取事实更新状态，计划与推断不能提前写成正史。
- 允许人物没想明白、感受矛盾、关系暂不变化。推进可以跨章落定，不为每场补成长、误判、损失、回报或主题总结。
- 重大方向与既有正史修订按 [approval-policy.md](references/approval-policy.md) 判断，其余在已授权范围自主完成。

## 按阶段使用

| 阶段 | 读取与产出 | 交接边界 |
| --- | --- | --- |
| 筹备 | 对齐项目状态、当前事件与角色；按任务选下面的参考；写明接续点及事件完成条件 | 把抽象机制转成当前事实、人物诉求与具体限制；沿用现有合同和四句前卡，不增加必填卡片 |
| 正文 | **先读 [writer-context.md](references/writer-context.md)**，再读其中要求的相关正文和声音依据 | 写手使用当前事件需要的材料；不接收整份教程、评分表或长篇修订记录，不把意图JSON逐句翻译成台词 |
| 编辑与提交 | 读取 [prose-naturalization.md](references/prose-naturalization.md)、[webnovel-naturalness-review.md](references/webnovel-naturalness-review.md)、[review-system.md](references/review-system.md)；按 [task-workflows.md](references/task-workflows.md) 提交 | 必须检查新写或修改的正文；只因具体问题改文，保留有效原段，再从最终正文更新正史 |

这些是工作阶段，不要求增加代理或更换模型。有独立写作上下文时只传递精简材料；同一会话无法清除已读规则时，避免重复加载，转入正文后以短指南和已确认事实为当前依据。精简上下文不能删掉关键限制、未决冲突或角色必须知道的前因。

## 按任务读取

详细操作见 [task-workflows.md](references/task-workflows.md) 的对应小节，常用脚本也在该文件末尾。只读当前任务需要的部分。

| 任务 | 参考入口 |
| --- | --- |
| 新建、恢复或导入项目 | [project-system.md](references/project-system.md)、[length-modes.md](references/length-modes.md)；迁移与提交读 [operations.md](references/operations.md) |
| 短中篇完整小说 | [novella.md](references/novella.md)，其阶段、篇幅和完结规则优先 |
| 继续连载、角色意图与裁定 | task-workflows的“继续连载”、[ensemble.md](references/ensemble.md)、[chapter-outline.md](references/chapter-outline.md)；随后切换正文阶段 |
| 卷纲、扩展、兑现设计 | [continuation-engine.md](references/continuation-engine.md)、[reward-system.md](references/reward-system.md)；写手只接收当前已选定的事实与限制 |
| 人物、群像、关系设计 | [supporting-cast.md](references/supporting-cast.md)、[ensemble-character.md](references/ensemble-character.md)；关系转折或连续性问题再读 [narrative-continuity.md](references/narrative-continuity.md) |
| 战力、合作、利益与误判诊断 | [conflict-and-inference.md](references/conflict-and-inference.md)、[fanqie-consistency.md](references/fanqie-consistency.md) |
| 正文出现具体写法问题 | [chapter-craft.md](references/chapter-craft.md)按问题选节；对白同声读 [dialogue-craft.md](references/dialogue-craft.md)，空间或动作难懂读 [scene-craft.md](references/scene-craft.md)；问题明确后才补读 |
| 选文风、参考作者、提炼写法 | [style-system.md](references/style-system.md)；建立个人声音或诊断AI味读prose-naturalization，不以检测分数决定文笔 |
| 仿写、参考故事再创作 | [reference-adaptation.md](references/reference-adaptation.md)，使用 `reference_guard.py` 与 `story_overlap.py` 核查复用风险 |
| 修订旧稿、自检或改乱了 | [fanqie-revision.md](references/fanqie-revision.md)，先定问题与范围，再选择不改、小改或请示大改 |
| 市场、书名、封面 | [market-research.md](references/market-research.md)、[publishing-package.md](references/publishing-package.md)、[cover-typography.md](references/cover-typography.md) |
| 发布数据与入口诊断 | [performance-feedback.md](references/performance-feedback.md)、[short-story-information-flow.md](references/short-story-information-flow.md) |

题材判断按需读 [genre-routing.md](references/genre-routing.md)。追妻追夫、火葬场或旧爱追悔为主承诺时读 [relationship-regret.md](references/relationship-regret.md)，不因出现前任就套用。

番茄短故事的筹备与编辑还须按 [fanqie-signing-quality.md](references/fanqie-signing-quality.md)、[fanqie-character-craft.md](references/fanqie-character-craft.md) 核对职责；长篇按番茄投稿时同样使用。新建、定名、短故事第一节和长篇前三章读 [fanqie-new-book.md](references/fanqie-new-book.md)；入口设计再读short-story-information-flow。将选定的近期目标与必要条件交给写手，不把整份课堂检查表放进正文任务。

## 编辑与交付边界

自然化只修有原文证据和读者代价的问题。保留必要心理、背景与叙述口气；允许原稿检查通过。语言改写记录前后字数，低于改前90%时复核有效内容是否损失；比例不决定采用或恢复，误删才从原稿恢复。朱雀逐段标红时冻结未标红段；作者确认当前版本后停止自然化循环。

每次新写或修改正文后，仍须执行 `repetition_audit.py`、语言扫描、自然度审稿、编辑与读者模拟；正式报告绑定最终正文哈希。局部修改只给修订者相关原段、必要前后文、具体问题和范围，最多一次自动定向修订后重审，仍有阻断则报告。按task-workflows执行staging与 `commit_chapter.py`，不绕过正史、备份和提交校验。

面向作者以正文为主，简报篇幅、必要的实际变化和未解决事项。没有发生的成长、收益或情绪转折无需逐项报告；校验问题区分阻断与警告，不展示内部长清单。

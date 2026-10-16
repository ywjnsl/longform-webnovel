# 项目迁移、暂存、提交与恢复

`novella` 短中篇复用同一套暂存、校验、提交和恢复流程；建项与全书阶段见 [novella.md](novella.md)。原有 v8 项目无需为此改模式或迁移字段。短中篇第一次提交前更新 `finiteStory.status = drafting`；完结时一并暂存 `reviews/final-review.json`，以全文终审和实际字数下限收口，不要求固定章数。重复审计与长篇相同，默认最近 5 章。

## 迁移旧项目

先运行：

```bash
python3 <skill-dir>/scripts/migrate_project.py <项目目录>
```

迁移脚本会在 `.webnovel/backups/` 保存迁移前文件，升级项目到 v8，补充语言风格档案、节拍配置、爽点账本、配角弧光账本、可选市场研究状态、章节审稿门禁、网文自然度门禁、确定性重复门禁，以及群像仿真所需的 `canon/laws.md`、`planning/current-arc.md`、主角 `cast/` 和 `ensemble` 配置。旧连载的合同/意图与重复门禁从迁移后的下一章开始强制；已发布旧章节不会被伪装成已跑过角色意图、重复审计或自然度审稿。旧连载默认沿用最近正文的可观察语言特征，不会被强行套用新预设；自然度与重复门禁从各自迁移起始章生效。

迁移后运行 `validate_project.py`。`needs-review` 或历史未审计提示不是新正文的写作许可；有时间时回读旧节拍章并补证据。

## 准备章节 staging

在项目外或项目的 `.webnovel/staging/` 下创建唯一临时目录。按正式项目相对路径写入所有拟提交文件，例如：

```text
staging/
├── project.json
├── chapters/第0016章-新的代价.md
├── reviews/第0016章-repetition.json
├── reviews/第0016章-lint.json
├── reviews/第0016章-review.json
├── reviews/evidence/朱雀-第0016章.png
├── planning/rolling-outline.md
├── planning/current-arc.md
├── contracts/chapter-0016.json
├── intents/chapter-0016/ruling.json
├── cast/{id}/state.json
├── state/story-state.json
├── state/threads.json
├── state/rewards.json
├── state/cast-arcs.json
└── sessions/2026-08-21-chapter-0016.md
```

必须暂存 `project.json`、四个章节快照状态文件、新章节正文、确定性重复报告、语言风险扫描和独立审稿报告。四个快照为 `story-state.json`、`threads.json`、`rewards.json` 和 `cast-arcs.json`；群像强制章还要暂存合同、ruling、`planning/current-arc.md` 和上场角色 `cast/{id}/state.json`。朱雀截图及 `externalNaturalness` 仅在作者提供逐段证据时暂存。提交脚本会从正式项目构造隔离预览，其他未变化文件可以省略。

三个审稿 JSON 必须绑定最终正文的 SHA-256；`第NNNN章-review.json` 内的 `naturalness.reviewedTextSha256` 也必须匹配。正文发生任何修改后，重跑 `repetition_audit.py`、`prose_lint.py`、网文自然度审稿、编辑审稿和读者模拟，不能沿用旧报告、finding ID 或重复例外。番茄短故事的重复报告必须列入全部较早已提交分节，长篇默认列入最近 5 章；每个保留的 exact/near finding 都要在 `naturalness.repetitionExceptions` 中按最终哈希记录具体编辑理由。执行过自然度定向修改时，最终报告另存修改前哈希与处理类别。结构和阻断规则见 [review-system.md](review-system.md)。

每章同时暂存 `sessions/*chapter-NNNN*.md` 交接记录。`project.json.totalContentChars` 使用 `chapter_metrics.py` 的 `contentChars` 口径累加；修订旧章时用新旧正文有效字符差更新。

`serial`、`novella` 的 `targetChapterChars` 是连续正文的切分阈值，不是必须填满的章节配额。达到约2500有效字，在完整句子或段落间切出下一章是正常分章；不要求新章先有独立的因果职责、入口、转折或自然收束。切点处事情未完就保留未完，尾后文字留给下一片，不改写、不丢失，也不在前片补结局。逐片审稿和提交，只把该片已发生的事实写入状态；滚动事件纲保留尚未完成的同一事件。

`fanqie-short-story` 增加分节仍按全文结构说明职责与前后关系，并更新 `shortStory.plannedSections`；不要只添标题伪造新内容。三种模式均同步实际章号、爽点账本和状态；只有改动主承诺、结局或主要矛盾才按重大决策流程处理，正常字数切章不因此要求重新规划情节。

## 尾稿保存与跨会话恢复

`serial`、`novella` 切出一片后、编辑该片之前，用 `draft_checkpoint.py` 把连续原稿、切出的前片和尾稿保存在项目内。`--after-chapter` 是刚切出、即将审稿提交的章号；三个输入应为添加标题之前的原文切片，必须逐字节拼回原稿：

```bash
python3 <skill-dir>/scripts/draft_checkpoint.py save --project <项目目录> \
  --after-chapter 16 --source <连续原稿> --head <切出前片> --tail <尾稿>
```

工具创建 `drafts/continuations/after-0016/`，保存 `source.md`、`head.md`、`tail.md` 原始快照，以及可编辑的 `tail-working.md` 和版本记录 `checkpoint.json`。这些是未提交正文的恢复材料，不加入章节 staging，不更新正史，也不计入已完成字数；备份项目时一并保存 `drafts/`。目录已有时拒绝覆盖，不能通过删掉恢复点重跑来消除版本差异。

每次恢复写作，以及前片正式提交后开始下一片之前，运行：

```bash
python3 <skill-dir>/scripts/draft_checkpoint.py check --project <项目目录>
```

- `ready`：找到与最后已提交章对应的尾稿；先读该章实际结尾与 `workingTail` 指向的全文，再从工作尾稿末尾继续，不从前章末尾重新生成已有内容。`emptyTail` 为真时没有余文可接，从已提交章末继续当前事件或进入已确认的新事件。
- `review-required`：前章正文或工作尾稿有变化，先核对接续再动笔。只忽略第一行章标题、换行格式和文件首尾空白的差异；其他修改都会提示检查，即使发生在章中也不自动判定无关。
- `awaiting-commit`：发现下一章的保存点，但该章尚未提交；优先从session指向的 staging 恢复该片的编辑与提交事务，并核对其与当前已提交章的接续。不能返回旧尾稿重新生成这一片，也不能把新尾稿当作已发生事实续写。staging 已丢失时，保存点的 `head.md` 仅用于恢复候选原稿，须重新核对并完成正式审稿。
- `no-checkpoint`：当前已提交章没有尾稿保存点。回查最新 session 的交接记录及工作目录；确认没有已写余文后再新写，不把旧章保存点自动当成本章尾稿。每次交接在现有 session 记录本次保存点路径、工作稿位置和实际接续处；在任务中途暂停时保存正在写的工作稿，不只保留临时文件或聊天内容。

接续核对以最终已提交章为准：读前章相关改动和结尾，以及受影响的尾稿原段，检查人物位置、在手物件、动作起止、已知信息、时间与资源。前片语言调整没有影响接续时保留尾稿；改变了事实或动作时，仅在 `tail-working.md` 修正受影响的接续，保留三个原始快照。不为衔接重写整段事件、重新切前章或填补章长。改动触及作者未授权的既有正史时，按原修订权限处理。

完成实际核对后，记录核对范围、是否修改及原因，再绑定这次前章与工作尾稿的版本：

```bash
python3 <skill-dir>/scripts/draft_checkpoint.py confirm --project <项目目录> \
  --note "前章改为把灯放桌上；尾稿仅改为从桌上取灯，后续位置与照明方向一致。"
```

`confirm` 由执行者在核对后记录，不是脚本语义审稿；不能只为清除提示运行。之后任一正文版本再次变化，原确认失效。工作稿成为下一片的一部分时，仍执行正常的后处理与正式审稿。新一章提交后，恢复入口只匹配新的已提交章号，旧保存点留档，不自动重复接入尾稿；提交失败或回滚时保留原保存点以供恢复。该工具不替代正式项目校验，无需迁移项目 schema。

## 校验并提交

```bash
python3 <skill-dir>/scripts/commit_chapter.py \
  --project <项目目录> \
  --staging <staging目录>
```

脚本执行以下操作：获取项目锁、验证路径、构造隔离预览（包括 `research/` 快照）、运行完整校验、备份将被替换的文件、用原子文件替换提交。普通提交只允许从最后已提交章前进一章。

先检查而不写入：

```bash
python3 <skill-dir>/scripts/commit_chapter.py --project <项目目录> --staging <staging目录> --dry-run
```

明确修订旧章时增加 `--allow-revision`。仍需保持所有状态快照与 `lastCommittedChapter` 一致。

## 恢复备份

捕获到的提交错误会自动回滚。进程被强制中断时，根据脚本输出或 `.webnovel/backups/` 中最新提交备份恢复：

```bash
python3 <skill-dir>/scripts/commit_chapter.py \
  --project <项目目录> \
  --restore <备份目录>
```

恢复会按备份清单还原旧文件，并删除该次提交新建的文件。恢复后立即运行项目校验。

## 合并完稿

短故事标记 `complete` 且项目校验通过后，用以下命令生成单一发布 Markdown：

```bash
python3 <skill-dir>/scripts/merge_chapters.py \
  --project <项目目录> \
  --output <输出文件> \
  --strip-headings
```

脚本按已提交章号排序，`--strip-headings` 只移除章节 H1，不改正文段落，并验证合并稿有效字符总数与章节总和一致。输出文件不得写入 `chapters/`。

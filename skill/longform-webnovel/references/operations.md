# 项目迁移、暂存、提交与恢复

## 迁移旧项目

先运行：

```bash
python3 <skill-dir>/scripts/migrate_project.py <项目目录>
```

迁移脚本会在 `.webnovel/backups/` 保存迁移前文件，升级项目到 v7，补充语言风格档案、节拍配置、爽点账本、配角弧光账本、可选市场研究状态、章节审稿门禁、v7 网文自然度门禁，以及群像仿真所需的 `canon/laws.md`、`planning/current-arc.md`、主角 `cast/` 和 `ensemble` 配置。旧连载的合同/意图从迁移后的下一章开始强制；已发布旧章节不会被伪装成已跑过角色意图或自然度审稿。旧连载默认沿用最近正文的可观察语言特征，不会被强行套用新预设；自然度门禁从迁移后的下一未提交章开始。

迁移后运行 `validate_project.py`。`needs-review` 或历史未审计提示不是新正文的写作许可；有时间时回读旧节拍章并补证据。

## 准备章节 staging

在项目外或项目的 `.webnovel/staging/` 下创建唯一临时目录。按正式项目相对路径写入所有拟提交文件，例如：

```text
staging/
├── project.json
├── chapters/第0016章-新的代价.md
├── reviews/第0016章-lint.json
├── reviews/第0016章-review.json
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

必须暂存 `project.json`、四个章节快照状态文件、新章节正文、语言风险扫描和独立审稿报告。四个快照为 `story-state.json`、`threads.json`、`rewards.json` 和 `cast-arcs.json`；群像强制章还要暂存合同、ruling、`planning/current-arc.md` 和上场角色 `cast/{id}/state.json`。提交脚本会从正式项目构造隔离预览，其他未变化文件可以省略。

两个审稿 JSON 必须绑定最终正文的 SHA-256；`第NNNN章-review.json` 内的 `naturalness.reviewedTextSha256` 也必须匹配。正文发生任何修改后，重跑 `prose_lint.py`、网文自然度审稿、编辑审稿和读者模拟，不能沿用旧报告。执行过自然度定向修改时，最终报告另存修改前哈希与处理类别。结构和阻断规则见 [review-system.md](review-system.md)。

每章同时暂存 `sessions/*chapter-NNNN*.md` 交接记录。`project.json.totalContentChars` 使用 `chapter_metrics.py` 的 `contentChars` 口径累加；修订旧章时用新旧正文有效字符差更新。

章节长度只作为审稿信号，不是必须填满的指标。若正文偏短，先检查是否缺少推进因果、有效信息、人物选择或回报；禁止用重复对白、重复解释、无后果反转或把同一正文机械拆成多个标题来达标。需要新增长篇章节或短故事分节时，先在 `planning/rolling-outline.md` 写清新增分节的因果职责、入口、结尾推动力及其与前后章的关系，再同步更新 `project.json` 的章号字段或 `shortStory.plannedSections`、爽点账本和四个状态快照。若增章改变主承诺、结局类型或主要矛盾，按重大决策流程等待作者确认。

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

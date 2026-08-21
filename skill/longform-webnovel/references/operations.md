# 项目迁移、暂存、提交与恢复

## 迁移旧项目

先运行：

```bash
python3 <skill-dir>/scripts/migrate_project.py <项目目录>
```

迁移脚本会在 `.webnovel/backups/` 保存迁移前文件，升级项目到 v5，补充语言风格档案、节拍配置、爽点账本、配角弧光账本、可选市场研究状态和章节审稿门禁。旧连载默认沿用最近正文的可观察语言特征，不会被强行套用新预设；已发布旧章节也不会被伪装成已验证，审稿门禁从迁移后的下一章开始。

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
├── state/story-state.json
├── state/threads.json
├── state/rewards.json
├── state/cast-arcs.json
└── sessions/2026-08-21-chapter-0016.md
```

必须暂存 `project.json`、四个章节快照状态文件、新章节正文、语言风险扫描和独立审稿报告。四个快照为 `story-state.json`、`threads.json`、`rewards.json` 和 `cast-arcs.json`；提交脚本会从正式项目构造隔离预览，其他未变化文件可以省略。

两个审稿 JSON 必须绑定最终正文的 SHA-256。正文修改后重跑 `prose_lint.py` 并重做编辑/读者审稿，不能沿用旧报告。结构和阻断规则见 [review-system.md](review-system.md)。

每章同时暂存 `sessions/*chapter-NNNN*.md` 交接记录。`project.json.totalContentChars` 使用 `chapter_metrics.py` 的 `contentChars` 口径累加；修订旧章时用新旧正文有效字符差更新。

## 校验并提交

```bash
python3 <skill-dir>/scripts/commit_chapter.py \
  --project <项目目录> \
  --staging <staging目录>
```

脚本执行以下操作：获取项目锁、验证路径、构造隔离预览、运行完整校验、备份将被替换的文件、用原子文件替换提交。普通提交只允许从最后已提交章前进一章。

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

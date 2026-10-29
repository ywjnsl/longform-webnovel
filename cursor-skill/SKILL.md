---
name: longform-webnovel
description: 创建、规划、续写和修订中文长篇网文、短中篇及番茄短故事；支持参考故事机制提炼与原创再创作、人物与群像、语言风格和个人声音、自然化改稿、跨会话正史、编辑审稿、市场定位及书名封面。适用于开新书、继续连载、修订诊断和提炼小说写法；不用于洗稿、逐段同义改写或规避内容检测。
---

# 入口

本文件只供 Cursor 发现。完整 skill、脚本与参考资料在 `~/.codex/skills/longform-webnovel/`。

先读取该目录的 `SKILL.md`，按当前任务与筹备、正文、编辑阶段加载材料。正文使用 `references/writer-context.md`；操作与提交使用 `references/task-workflows.md`，不要把全部参考教程作为写作提示。当前项目 schema 为 v8。先区分试写/审读/修改候选、正式入库和发布准备：轻流程不先建项目或要求包装，采用入库才执行完整审稿与提交；未完成包装可保留 `unconfirmed`。

`serial` 与 `novella` 连续写当前事件，实测到约2500有效字后切开已有文本，从断处继续；标题切出后再定，不预分每章剧情或收尾。`fanqie-short-story` 沿用全文和分节职责。审稿、正史与提交校验按完整 skill 执行。群像、角色 skill 和跨章弧使用同一项目，不另走 `sandbox-serial-novel` 流程。

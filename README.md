# Longform Webnovel

一个面向中文长期网文连载的 Codex Skill。它把小说作为持续演化的项目来管理，而不是一组彼此独立的提示词或章节。

默认适配番茄式移动端阅读节奏，每章约 2500 个有效字符；题材不固定，支持新书策划、长期续写、旧稿导入、卷纲扩展和结构修订。

## 主要能力

- 使用故事合同、滚动章纲和状态账本维持跨会话连续性。
- 每 3 章交付小爽点或小高潮，每 5 章交付大爽点或大高潮；重合章由大爽点吸收两级职责。
- 在重大方向变化前询问作者，其余章节级选择自主完成。
- 第一章前筛选有辨识度的书名，保存公开检索记录并生成封面提示词。
- 支持语言风格档案和知名作者公开写作手法的参数化转译，不复刻标志性表达。
- 为核心配角维护独立目标、选择、后果和非主角中心关系。
- 可选保存带日期、URL、样本和置信度的公开市场观察。
- 每章执行模板化语言风险扫描、编辑审稿和目标读者模拟。
- 使用正文 SHA-256、隔离预览、备份与回滚保证章节和状态原子提交。

语言风险扫描只提供编辑调查信号，不判断文本是否由 AI 创作，也不输出作者身份概率。

## 安装

克隆仓库后，将 Skill 目录复制到 Codex 默认 Skill 位置：

```bash
git clone https://github.com/ywjnsl/longform-webnovel.git
cp -R longform-webnovel/skill/longform-webnovel ~/.codex/skills/
```

重新打开 Codex 任务后，可直接调用：

```text
$longform-webnovel 帮我策划一部可以长期连载但不注水的中文网文。
```

## 仓库结构

```text
skill/longform-webnovel/   可安装的 Skill
tests/                     集成与结构测试
.github/workflows/         GitHub Actions
```

运行测试：

```bash
python3 tests/check_skill.py
python3 tests/test_longform_webnovel.py
```

运行时只依赖 Python 标准库。

## 创作边界

- 公开市场研究用于理解读者需求和差异化空间，不授权复制样本作品。
- 可以借鉴公开可描述的叙事手法，但不直接模仿在世作者的标志性措辞。
- “长期扩展”依靠正史和状态文件实现，不承诺脱离上下文限制的无限生成。
- 自动审稿不能替代作者判断；严重风险只能由作者通过明确决策记录接受。

## 致谢

设计过程中研究了以下公开项目的市场扫描、审稿角色分离和文本风险检查思路：

- [worldwonderer/oh-story-claudecode](https://github.com/worldwonderer/oh-story-claudecode)
- [haowjy/creative-writing-skills](https://github.com/haowjy/creative-writing-skills)

本仓库的代码、数据结构和说明为独立实现；未复制上述项目的代码或文案。

## 许可证

[MIT](LICENSE)

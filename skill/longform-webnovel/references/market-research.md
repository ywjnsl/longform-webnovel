# 公开市场研究

## 边界

市场研究是可选的定位输入，不是写正文、定书名或提交章节的前置许可。仅研究公开可访问页面，记录访问日期和 URL。观察读者承诺、品类密度、包装方式与差异化空间，不复制样本作品的书名、人设、专有机制、表达或情节组合。

研究结果有时效性。只写当前样本能支持的结论，严格分开可观察事实与推断；每条推断标记 `low`、`medium` 或 `high` 置信度。无法访问实时页面时明确说明，不凭记忆伪造榜单。

## 最小样本

- 至少 2 个公开来源，可以是平台公开榜单、分类页或可靠的公开行业材料。
- 至少 5 部可核查作品；记录样本标题、来源 URL、标签与可观察信号。
- 保存受众、题材、榜单范围和抽样窗口。
- 至少 3 条事实观察、2 条推断、2 个差异化机会和 2 条创作隔离线。

样本量只保证基本可追溯性，不代表统计显著。不要把一个时间切片写成长期定律。

### 短故事样本边界

`fanqie-short-story` 项目必须使用短故事专属页面、短故事频道、短故事活动或作者明确提供的后台“热门故事”观察作为主要选题证据。长篇原创榜、长篇阅读榜和长篇在读人数只能作为邻近题材旁证，不能据此声称“这是当前短故事热门题材”。

快照的 `scope.contentForm` 必须标明 `short-story`、`longform` 或 `mixed`。短故事项目归档时必须为 `short-story`；每个样本所引用来源也必须标明 `contentForm: short-story`。无法获得至少 5 个可核查短故事样本时，明确报告证据不足，先给探索性候选，不制造“热门”结论。

## 快照结构

准备 JSON 输入。若正式项目尚未初始化，先将它放在项目外的临时工作目录；书名、风格和第一卷方向确认并初始化项目后，再用脚本归档，不把候选方案提前写成正史：

```json
{
  "schemaVersion": 1,
  "asOfDate": "2026-08-21",
  "platform": "番茄小说",
  "scope": {
    "audience": "目标读者",
    "genre": "题材范围",
    "ranking": "公开榜单或页面范围",
    "sampleWindow": "抽样方式",
    "contentForm": "short-story"
  },
  "sources": [
    {"title": "来源名", "url": "https://...", "accessedAt": "2026-08-21", "contentForm": "short-story"}
  ],
  "samples": [
    {
      "title": "样本作品",
      "sourceUrl": "https://...",
      "tags": ["公开标签"],
      "observedSignals": ["页面上可直接观察的事实"]
    }
  ],
  "observations": ["不掺推断的观察事实"],
  "hypotheses": [
    {"claim": "有限推断", "confidence": "medium", "evidenceTitles": ["样本作品"]}
  ],
  "opportunities": ["与故事合同相容的差异化机会"],
  "avoidCopying": ["明确不复制的边界"]
}
```

实际数组数量必须满足最小样本要求。保存前可预检：

```bash
python3 <skill-dir>/scripts/market_brief.py \
  --project <项目目录> \
  --snapshot <快照.json> \
  --dry-run
```

确认后移除 `--dry-run`。脚本会原子更新 `project.json.marketResearch`、`canon/market-brief.md` 和 `research/market-snapshots/YYYY-MM-DD-platform.json`，并先创建备份。

## 如何使用

把机会翻译为本项目自己的故事承诺、冲突发动机和包装选择。若市场信号与已经确认的作品方向冲突，把是否转向作为重大决策交给作者；不能用“市场如此”擅自改写故事合同。章节审稿优先判断本书对自身承诺是否兑现，不要求追逐每次榜单波动。

短故事生成候选后，运行 `story_overlap.py` 对同一作品库中的历史项目做相似度检查。重复人名、关系结构、核心危机、关键物件和解决机制不能只靠换标题掩盖；高风险候选应重做故事发动机，除非作者明确要求同世界观续作。

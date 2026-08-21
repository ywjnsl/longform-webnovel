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
    "sampleWindow": "抽样方式"
  },
  "sources": [
    {"title": "来源名", "url": "https://...", "accessedAt": "2026-08-21"}
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

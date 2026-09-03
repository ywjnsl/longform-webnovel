# 发布后数据反馈

## 目的与边界

发布后诊断按“展现 → 阅读/点击 → 完读/解锁 → 互动”定位最早出现证据的环节。平台没有公开保证持续给量；脚本阈值是可调整的编辑诊断线，不是番茄官方流量标准，也不能从单日小样本推断作品被永久限流。

短故事发布后，保存后台可见的统计窗口、推荐状态和原始数字。不要把截图里的“17”读成“17万”，不要把点击率高但只有数十次展现写成包装已验证成功。

## 数据文件

准备 JSON：

```json
{
  "schemaVersion": 1,
  "platform": "番茄小说",
  "windowStart": "2026-08-29",
  "windowEnd": "2026-08-31",
  "recommendationStatus": "initial",
  "impressions": 17,
  "reads": 4,
  "completedReads": null,
  "unlocks": null,
  "likes": 0,
  "comments": 0,
  "bookshelves": 0,
  "notes": "后台显示已签约；数据每天12点更新"
}
```

`recommendationStatus` 使用 `unknown`、`initial`、`initial-complete`、`normal` 或 `limited`。未知数据填 `null`，不能用零冒充未提供。

保存并诊断：

```bash
python3 <skill-dir>/scripts/performance_feedback.py \
  --project <项目目录> \
  --input <数据.json>
```

脚本把原始快照保存到 `performance/snapshots/`，把最新诊断写入 `performance/latest-diagnosis.md`，同时更新 `project.json.performanceFeedback`。默认以 100 次展现作为“可开始判断入口”的编辑样本线，可用 `--min-impressions` 调整；它不是平台标准。

## 诊断与动作

- 展现低于样本线：只标记 `insufficient-exposure`。先核对签约、初期推荐是否结束、分类/标签和数据更新时间，不因点击率波动重写正文。
- 展现足够但阅读率低于诊断线：标记 `entry-conversion`，一次只测试书名、封面、简介或推荐标题中的一项，保留修改日期和旧版本。
- 阅读样本足够但完读率低：标记 `reading-retention`，先审前 300 字、第一次回报和试读节点。
- 完读有基础但互动稀少：标记 `payoff-expression`，检查结局回报是否清楚、是否留下自然可表态的位置，不插入求互动文案。

每次修改后等待新的可比统计窗口。不同题材、发布时间、账号和推荐状态的数据不能直接混为一组。发布数据用于修正下一个候选和包装策略，不追溯改写已确认故事合同，除非作者明确要求修订。

# 配角弧光与关系网络

## 分层管理

不是每个出场人物都需要完整弧光。按叙事投入分三层：

| 层级 | 用途 | 最低要求 |
|---|---|---|
| `anchor` | 2–5 名真正影响主线的核心配角 | 独立目标、私人约束、关键选择、后果和可见变化 |
| `recurring` | 反复出现的同伴、对手、家人、同事 | 自己的诉求、独立行动、下一次转折窗口 |
| `cameo` | 一次性证人、顾客、守卫、邻居等 | 功能清楚、行为合理，不强开支线 |

`anchor` 不等于永远站主角一边。核心配角可以帮助、利用、背叛、误解或超越主角；其选择由自己的欲望、信息和代价驱动。

## 弧光最小闭环

配角弧光使用五步：

1. **欲望**：他不依附主角也想得到什么？
2. **压力**：主线事件如何逼迫他在两种代价之间选择？
3. **选择**：他主动做了什么，而不是被主角安排做什么？
4. **后果**：选择改变了关系、资源、身份、认知或道德位置中的什么？
5. **变化**：他坚持、修正、放弃还是扭曲了原来的信念？

弧光不必都向善。配角可以变坚定、变冷酷、认清自我、承担责任、走向反派，或带着代价离开。重要的是变化由选择挣得。

每个 5 章区间至少检查一次核心配角能动性；每个 15 章循环至少让一名 `anchor` 完成“选择”或“后果”推进。不要为满足检查硬插独立番外，优先让配角的决定改变主线局势。

## 感情关系

`relationships` 从当前配角指向其关系目标。`targetId: "protagonist"` 表示主角；反派和其他配角使用各自在 `cast-arcs.json` 中的稳定 ID。因此配角可以爱主角、爱反派、爱另一名配角，也可以没有爱情线。

- 爱情不是奖品。被爱不证明主角或反派正确，也不自动带来回应。
- 爱反派不等于替反派洗白。保留伤害、立场冲突和知情后的选择后果。
- 爱主角的配角仍需拥有恋爱以外的目标、关系和退出权。
- 单恋、旧情、隐瞒、拒绝、互相利用和关系转化都可以成立，但必须有行为证据。
- 不用突发强吻、嫉妒降智或牺牲女性角色作为廉价推进器；关系变化服从人物边界和作品内容约定。

`kind: "love"` 至少记录：为何产生感情的 `basis`、这段关系要求角色承担什么 `cost`、发生或变化的证据章号。若互相爱，可在双方各记一条，或在状态中标记 `reciprocated`；不要默认单向记录代表双向成立。

## 状态结构

`state/cast-arcs.json` 中的核心配角示例：

- `tier`：`anchor`、`recurring`、`cameo`
- `narrativeRole`：`ally`、`rival`、`antagonist`、`foil`、`mentor`、`family`、`romantic`、`civilian`、`other`
- `status`：`active`、`deferred`、`resolved`、`departed`、`dead`
- `arcPhase`：`none`、`setup`、`pressure`、`choice`、`consequence`、`changed`、`closed`；非 `cameo` 不使用 `none`
- `relationships[].kind`：`love`、`loyalty`、`rivalry`、`debt`、`family`、`friendship`、`fear`、`interest`、`other`
- `relationships[].status`：`hidden`、`expressed`、`reciprocated`、`rejected`、`complicated`、`ended`、`transformed`

枚举只负责机器校验，不要求牺牲人物细度。无法精确归类时使用 `other`，把具体含义写入目标、约束、关系依据和历史事件，不自行创造校验器未知标签。

```json
{
  "id": "lin-qiao",
  "name": "林乔",
  "tier": "anchor",
  "narrativeRole": "rival",
  "status": "active",
  "introducedChapter": 1,
  "lastAdvancedChapter": 6,
  "ownWant": "查清父亲被定罪的原始证据",
  "independentGoal": "抢在主角之前进入封存档案室",
  "privateConstraint": "公开翻案会让养母失去现有身份",
  "arcPhase": "choice",
  "nextTurnWindow": [8, 10],
  "history": [
    {
      "chapter": 6,
      "choice": "隐瞒主角需要的钥匙，独自与档案官交易",
      "delta": "从竞争盟友转为拥有独立筹码的潜在对手"
    }
  ],
  "relationships": [
    {
      "targetId": "director-xu",
      "kind": "love",
      "status": "hidden",
      "sinceChapter": 4,
      "basis": "对方曾在所有人放弃她父亲时保留复查记录",
      "cost": "她必须面对对方正是当前主线反派的事实",
      "evidenceChapters": [4, 6]
    }
  ]
}
```

`history` 只记录真正推进弧光的选择与结果，不记录每次露面。`lastAdvancedChapter` 必须有同章 `history` 证据；普通出场不算弧光推进。

## 写章检查

涉及配角的场景至少回答三个问题：他进场前想完成什么；如果主角不在，他会怎么做；离场时他的可选项发生了什么变化。若答案始终只是“帮助主角、夸主角、向主角解释”，该角色仍是工具人。

配角高光不能靠临时夺走主角智商。让不同角色凭各自职业、关系、风险承受能力和信息位置解决不同问题。

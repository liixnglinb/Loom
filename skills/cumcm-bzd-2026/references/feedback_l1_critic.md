# L1 Critic 评分规范

> 本文件、`rubrics.md` 与 `scripts/score_artifact.py` 三处的 verdict 定义必须**完全一致**。
> 修改任一处，必须同步另两处。

## 职责分工

| 角色 | 职责 |
|---|---|
| 模型 | 分析、比较、生成，输出评分与问题 |
| 脚本 | 校验评分 JSON、重算 verdict、聚合 per-Qi、写入 decision_log |

**verdict 不是模型说了算，由脚本重算。** 这避免模型自报"通过"却实际不达标。

## 评分维度

每阶段 5 维，每维 1–10 分。维度定义见各 `stage_0N_*.md` 的「5 维评分」小节。

维度键命名规则：`<序号>_<语义名>`，如 `1_resource_fit`。键名必须命中白名单，或 `config/dim_weights.json` 中定义的特化维度。

## Critic 输出格式

强制 JSON，约 500 token：

```json
{
  "stage": 5,
  "iteration": 0,
  "qi_id": "Q2",
  "scores": {
    "1_subproblem_completeness": 8,
    "2_model_rigor": 7,
    "3_result_interpretation": 9,
    "4_figure_quality": 8,
    "5_cross_reference_chain": 6
  },
  "issues": [
    {
      "severity": "high",
      "pattern": "E1",
      "desc": "表 4 的达标概率未在正文定义，无法回指目标函数符号",
      "fix": "在 6.3 节补一行定义式"
    }
  ],
  "verdict_suggestion": "refine"
}
```

`verdict_suggestion` 仅供参考，**实际 verdict 由脚本按下列规则重算**。

## verdict 计算规则

设 `raw_min` = 各维最低分，`weighted_mean` = Σ(s_i × w_i) / Σ(w_i)。

权重来自 `config/dim_weights.json[<task_type>][<stage>]`，未列出则默认 1.0，clamp [0.7, 1.5]。

按优先级从高到低判定：

| 优先级 | verdict | 触发条件 | 行为 |
|---|---|---|---|
| 1 | `block` | issues 含 ≥1 个 severity=high | 暂停，团队介入 |
| 2 | `pass_early` | raw_min ≥ 9 且 weighted_mean ≥ 9 | iteration-1 早退 |
| 3 | `pass` | raw_min ≥ 7 且 weighted_mean ≥ 8 | 进下一阶段 |
| 4 | `pass_with_review` | stage 5 且任一 Qi mark_for_review，但加权阈值满足 | 进 stage 6，L2 必读 review_qis |
| 5 | `refine` | 其他情况 | section-patch 精修，iter += 1（cap 3） |
| 6 | `refine_partial` | stage 5 且某 Qi.min < 7，其他 Qi 已 pass | 仅重跑该 Qi |
| 7 | `carryover` | iter == 3 仍为 refine | 进下一阶段，标记由 L2 处理 |

**双门槛的意义**：`weighted_mean` 用于排序，`raw_min` 防止致命短板被平均数掩盖。某一维得 3 分但均分 8.5 的情况，仍应 refine。

## Stage 9 的 block 特判

Stage 9 的合规 block **不是暂停交付**，而是触发"不合规 → 回退重改 → 重审"闭环：

1. 按问题归属退回 Stage 3 / 5 / 6 / 8，或修复渲染器
2. 改完重进 Stage 9，**只重跑受影响的检查**
3. 循环至 `submission_ready = true` 且无致命违规

此闭环只在 Stage 9 内执行，不改变其他阶段 `block` = 暂停的语义。

## severity 判定

| severity | 判定标准 | 例 |
|---|---|---|
| `high` | 影响结论正确性，或违反竞赛规则 | 结果与数据矛盾；匿名信息未清除；跨问口径漂移 |
| `medium` | 影响论证完整性，但不推翻结论 | 缺少基线对比；灵敏度仅 OAT |
| `low` | 表述、格式、可读性 | 图题字号偏小；中英文缺空格 |

**high-severity 不能被平均数掩盖，也不能以"时间不够"为由降级。** 若确实无法修复，需在 decision_log 中写明风险接受理由与影响范围。

## 调用

```bash
python <wf>/scripts/score_artifact.py \
  --stage 5 \
  --critique <cwd>/state/critique_v0.json \
  --decision-log <cwd>/state/decision_log.json
```

per-Qi 聚合：

```bash
python <wf>/scripts/score_artifact.py \
  --mode aggregate_qi \
  --qi-results <cwd>/state/qi_results.json \
  --decision-log <cwd>/state/decision_log.json
```

## 上下文纪律

- Critic 输出强制 JSON，~500 token/次
- 精修用 section-level patch，优先只传相关章节
- references/ 文件懒加载
- 阶段完成后，产物摘要 + 关键数据 + 路径写入 decision_log，不在上下文保留全文
- 只有当前 harness/API 提供可靠 usage 时才记录 token 消耗；不可观测时保留 `null`，**不得估算成已用额度**
- 上下文压力或剩余时间不足时，向团队建议 championship → standard → fast 降级，确认后写入 events；不要声称已自动计量或静默切换

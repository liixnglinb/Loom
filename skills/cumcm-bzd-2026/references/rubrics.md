# 评分维度总表

各阶段 5 维评分的集中定义。供交叉核对与 `config/dim_weights.json` 的键名校验使用。

> **一致性要求**：本文件的维度键名、`config/dim_weights.json` 的权重键名、
> `scripts/score_artifact.py` 的处理逻辑三者必须一致。
> 修改任一处，必须同步另两处。

---

## Stage 1 · 启动与选题

| 键 | 维度 | 判据 |
|---|---|---|
| `1_resource_fit` | 资源匹配 | 数据与工具能否支撑，缺什么、能否补 |
| `2_capability_fit` | 能力匹配 | 是否落在队伍擅长区间 |
| `3_risk_identified` | 风险识别 | 是否识别真实风险（非"时间紧"这类无效条目） |
| `4_rule_baseline` | 规则基线 | 当届规则是否核对、有据可查 |
| `5_decision_quality` | 决策质量 | 选题与放弃项是否有可核验的论证 |

## Stage 2 · 赛题解析与任务拆解

| 键 | 维度 | 判据 |
|---|---|---|
| `1_completeness` | 完整性 | 题面每句是否处理，有无漏问漏条件 |
| `2_hidden_conditions` | 隐藏条件 | 是否识别非字面条件并说明依据 |
| `3_linkage_clarity` | 联动清晰 | 跨问关系是否真实、传递方式是否明确 |
| `4_data_inventory` | 数据清单 | 是否覆盖字段、单位、缺失率、异常 |
| `5_task_actionability` | 可执行性 | 任务卡能否直接指导建模 |

## Stage 3 · 模型选型

| 键 | 维度 | 判据 |
|---|---|---|
| `1_candidate_diversity` | 候选多样性 | 候选是否跨族、有无真实权衡 |
| `2_selection_rationale` | 选型论证 | 是否针对本题（删背景后是否通用） |
| `3_data_fit` | 数据适配 | 模型数据要求与现有数据是否匹配 |
| `4_solver_feasibility` | 求解可行性 | 是否做过最小可运行验证、有无失败条件 |
| `5_literature_support` | 依据支撑 | 是否有可核验的依据 |

## Stage 4 · 基础构建

| 键 | 维度 | 判据 |
|---|---|---|
| `1_assumption_support` | 假设支撑 | 每条假设是否有依据与影响说明 |
| `2_assumption_coverage` | 假设覆盖 | 是否覆盖所有实际前提，无冗余 |
| `3_symbol_integrity` | 符号完整 | 一符一义、单位完整、无冲突 |
| `4_terminology_uniformity` | 术语统一 | 缩写全称、概念统一、与代码可对应 |
| `5_consistency_precheck` | 一致性预检 | 是否做了与模型/公式/代码的交叉预检 |

## Stage 5 · 递归求解（per-Qi）

| 键 | 维度 | 判据 |
|---|---|---|
| `1_subproblem_completeness` | 子问完整 | 任务卡要求的输出是否全部交付 |
| `2_model_rigor` | 模型严谨 | 变量/目标/约束是否完整，约束是否数学化 |
| `3_result_interpretation` | 结果解读 | 是否解读含义并与基线对比 |
| `4_figure_quality` | 图表质量 | 图型是否匹配、数值是否真实、可读性 |
| `5_cross_reference_chain` | 引用链 | 是否正确引用上游结果，口径是否一致 |

## Stage 6 · 检验与稳健性

| 键 | 维度 | 判据 |
|---|---|---|
| `1_multivariate_perturbation` | 联合扰动 | 是否做了联合扰动（非仅 OAT） |
| `2_perturbation_realism` | 扰动现实性 | 幅度是否有数据/文献/业务依据 |
| `3_robust_interval_quantitative` | 稳健区间 | 是否报告数值区间而非定性断言 |
| `4_failure_boundary` | 失败边界 | 是否写明结论失效的条件 |
| `5_cross_check` | 交叉核对 | 输出-正文-图表-摘要是否一致 |

## Stage 7 · 模型评价

| 键 | 维度 | 判据 |
|---|---|---|
| `1_strength_evidence` | 优点依据 | 每条优点是否有真实内容与量化证据 |
| `2_limitation_boundary` | 缺点边界 | 是否说明来源、影响与适用范围 |
| `3_improvement_mapping` | 改进对应 | 改进是否逐项对应缺点 |
| `4_generalization_concreteness` | 推广具体 | 是否说明场景、条件与修改方式 |
| `5_fulltext_consistency` | 全文一致 | 评价是否与摘要、结果、检验一致 |

## Stage 8 · 论文装配

| 键 | 维度 | 判据 |
|---|---|---|
| `1_structure_completeness` | 结构完整 | 章节是否齐全、编号是否连续 |
| `2_cross_stage_consistency` | 跨阶段一致 | 摘要/正文/图表/结果是否自洽 |
| `3_format_compliance` | 格式合规 | 页边距、页码、匿名、篇幅是否符合当届要求 |
| `4_ai_disclosure` | AI 披露 | 声明与详情是否完整、是否写明人工核验 |
| `5_abstract_quality` | 摘要质量 | 结构、人称、量化结果、禁用项 |

## Stage 9 · 终审与提交

| 键 | 维度 | 判据 |
|---|---|---|
| `1_compliance_gate` | 合规门 | 合规检查是否全部通过 |
| `2_quality_score` | 质量得分 | 论文质量得分与扣分明细 |
| `3_issue_closure` | 问题闭环 | 问题是否全部闭环（非"已知悉"） |
| `4_consistency_final` | 终检一致 | 跨章节一致性终检 |
| `5_submission_integrity` | 提交完整 | 提交包是否完整、命名与格式是否符合要求 |

---

## verdict 计算规则

设 `raw_min` = 各维最低分，`weighted_mean` = Σ(s_i × w_i) / Σ(w_i)，
权重来自 `config/dim_weights.json[<task_type>][<stage>]`，clamp [0.7, 1.5]。

| 优先级 | verdict | 触发 | 行为 |
|---|---|---|---|
| 1 | `block` | issues 含 ≥1 high-severity | 暂停，团队介入 |
| 2 | `pass_early` | raw_min ≥ 9 且 weighted_mean ≥ 9 | iteration-1 早退 |
| 3 | `pass` | raw_min ≥ 7 且 weighted_mean ≥ 8 | 进下一阶段 |
| 4 | `pass_with_review` | stage 5 且任一 Qi mark_for_review，加权阈值满足 | 进 stage 6，L2 必读 |
| 5 | `refine` | 其他 | 精修，iter += 1（cap 3） |
| 6 | `refine_partial` | stage 5 且某 Qi.min < 7，其他已 pass | 仅重跑该 Qi |
| 7 | `carryover` | iter == 3 仍 refine | 进下一阶段，标记由 L2 处理 |

**Stage 9 的 block 特判**：触发"不合规 → 回退重改 → 重审"闭环，非暂停交付。详见 `stage_09_final_review.md` 步骤 4。

**双门槛的意义**：`weighted_mean` 用于排序，`raw_min` 防止致命短板被平均数掩盖。

---

## severity 判定

| severity | 标准 | 例 |
|---|---|---|
| `high` | 影响结论正确性，或违反竞赛规则 | 结果与数据矛盾；匿名信息未清除；跨问口径漂移 |
| `medium` | 影响论证完整性，不推翻结论 | 缺少基线对比；灵敏度仅 OAT |
| `low` | 表述、格式、可读性 | 图题字号偏小；中英文缺空格 |

high-severity 不能被平均数掩盖，也不能以"时间不够"为由降级。确实无法修复时，需在 decision_log 中写明风险接受理由与影响范围。

# 竞赛·逻辑对抗复核（独立视角，专挑自查盲区）

**为什么需要这一步**：建模/编程用的是同一个"心智模型"，如果它在建模阶段就把某个方向想反了（如把上界当下界）、或把某项算了两次，**自查时用的还是那个反的脑子，永远看不见**。这一步换一个独立视角，只干一件事——挑那五类"数值合法但逻辑错"的硬伤。

## ⚡ 开关说明 + FAST_MODE 二级保险（开头先跑）

⛔ **本步默认「关」**：后端 `_resolve_template` 默认把 comp-review 从步骤链里移除，**只有用户显式 `enable_comp_review=true` 时本步才会出现并执行**（这才是真省额度——不出现在链里就不启动进程）。所以你现在能读到这段，说明用户已选择开启。

```bash
# 二级保险：即便被开启，FAST_MODE 下仍跳过（速度优先场景），产占位不阻塞。
if grep -q 'MH_FAST_MODE=1' CLAUDE.md 2>/dev/null; then
  echo "⏭ FAST_MODE：逻辑对抗复核跳过。确定性闸(logic_audit/cross_problem_check)已在 comp-code 兜底。"
  printf '# 逻辑对抗复核\n\nFAST_MODE 跳过（省额度）。确定性逻辑闸仍在 comp-code 阶段跑过。\n' > COMP_REVIEW.md
  exit 0
fi
```
> ⛔ 本步是**唯一多花一次 AI 调用**的环节。默认关(后端移除)、开启后 FAST_MODE 仍可跳。跳过时确定性闸(logic_audit/cross_problem_check)已在上一步兜底，不影响主流程。

## 输入（只读摘要，禁整读大 JSON）

- `PROBLEM_ANALYSIS.md`（题面/逐句表/硬约束）、`DATA_FACTS.json`（数据事实台账）
- `MODELING_REPORT.md`（假设/`LOGIC_CONTRACT_MACHINE`/`CROSS_PROBLEM_LEDGER`）
- `RESULTS.md` + `AUDIT_REPORT.md`（前面各闸的结论）
- `figures/*_results.json` 用 `_utils` 下的 summarize 或 `Grep`/`Read` 局部看，**⛔ 禁 `cat` 整包大 JSON**（吃光 context）

## Step 1: 先看确定性闸的既有结论（不重复劳动）

```bash
# logic_audit / cross_problem_check 已在 comp-code 阶段跑过，先复用它们的裁定作锚点
[ -f AUDIT_REPORT.md ] && grep -nE "外推|特征完整性|重复计量|跨问|矛盾|❌|⚠" AUDIT_REPORT.md | head -30
```

## Step 2: 逐条对撞五类缺口（核心，用证据说话）

对每一类，找**具体代码行/具体数值**当证据，不泛泛而谈：

1. **方向/界反没反**：核对 `LOGIC_CONTRACT_MACHINE.bounds` 声明的上/下界与代码实现是否一致。凡有删失/封顶/反解，代入观测值验证不等号方向。（这是确定性闸抓不到、最需要独立视角的一类）
2. **重复计量**：任何"总量=A+B"，查 A 的拟合/标定是否已吸收 B（如截距用含某分项的总量拟合、又显式加该分项）。
3. **外推口吻过硬**：预测点落在 `DATA_FACTS` 观测区间外的，正文是否用了确定性口吻当"数据结论"（应标"情景模拟、需现场标定"）。
4. **漏真实变量**：`DATA_FACTS` 里 `role=observed` 的关键变量，是否都进了模型；被当"不重要"丢掉的要质疑。
5. **跨问矛盾**：某问算出的关键结论（如峰值/边界）是否与另一问的优化约束/结论冲突。
6. **任务理解 vs 题目原文（⛔ 最该由你独立视角兜的一类）**：拿 `PROBLEM_ANALYSIS.md` 的**关键概念对齐表**和 `MODELING_REPORT.md` 的**目标/约束原文溯源**，逐条核对——建的目标函数/约束/关键量，和题目**原句**要的是不是同一件事？重点抓：求 A 做成了求 B（如覆盖宽度→面积）、最优化方向反（min↔max）、约束理解反、关键量物理含义错、漏做某个明确要求。⛔ **这是"赛题读歪"唯一的独立防线**——下游所有确定性闸都只核"是否忠于建模者的理解"，核不了"理解本身对不对"，只有你带着题目原文重看才可能发现。发现"任务读歪/目标搞错"属 **fatal**（方向全错，回炉重来）。

⛔ **诚实认知（天花板）**：本复核 AI 与答题同源，有共同盲区，**显著降漏网率但非万无一失**（尤其"任务理解"这类：你也可能和答题时一样误读同一句话）。机器可判的部分已由 logic_audit/cross_problem_check 确定性拦截，本步只兜"确定性查不了的语义残余"。发现存疑处要给出"哪行代码/哪个数/哪句原文"支撑，不做无证据的断言。机器可判的部分已由 logic_audit/cross_problem_check 确定性拦截，本步只兜"确定性查不了的语义残余"。发现存疑处要给出"哪行代码/哪个数"支撑，不做无证据的断言。

## Step 3: 产出裁定（人读 + 机器读）

```bash
# 人读报告
cat > COMP_REVIEW.md <<'EOF'
# 逻辑对抗复核报告
（逐条：问题描述 / 严重性(fatal|major|minor) / 定位(文件:行或数值) / 证据 / 建议）
EOF
```

机器可读裁定 `COMP_REVIEW_VERDICT.json`：
```json
{"findings":[
  {"category":"bound_direction|double_count|extrapolation|missing_feature|cross_problem",
   "severity":"fatal|major|minor","where":"calibrate.py:L692 或 Q1峰值","evidence":"...","fix":"..."}
],"fatal_count":0}
```

## Step 4: 硬门禁（⛔ 有 fatal 不许放行）

```bash
FATAL=$(python3 -c "import json;d=json.load(open('COMP_REVIEW_VERDICT.json'));print(d.get('fatal_count',0))" 2>/dev/null || echo 0)
if [ "$FATAL" -gt 0 ]; then
  echo "❌ 逻辑对抗复核发现 $FATAL 处致命逻辑错 — 必须回 comp-modeling/comp-code 修正后重跑，不许进论文撰写。"
  echo "   (fatal 类：方向反、同一项算两次、跨问硬矛盾——这些会系统性歪曲结论)"
else
  echo "✅ 逻辑对抗复核通过（无 fatal；major/minor 见 COMP_REVIEW.md，写论文时注意）。"
fi
```
> - `fatal`（方向反/重复计量/跨问硬矛盾）= 退出前必修，回炉重跑。
> - `major/minor`（外推口吻、可疑假设）= 不硬拦，但必须在论文里如实标注为"情景模拟/假设"，禁确定性口吻。

## Additional Parameters
- skip_improvement_loop: False
- data_fig_vision: True
- ai_disclosure: none
- competition: cumcm
- language: zh
- max_pages: 20
- output_format: pdf
- flowchart_engine: html
- problem_id: B
- tools: python
- min_figures: auto
- min_tables: auto
- min_models: auto
- enable_comp_review: True
- model_preset_id: 6bed4bf1e5ab
- diagram_style: mono
- step_models: {'comp-prob-analysis': '216e85e672aa', 'comp-modeling': '216e85e672aa', 'comp-code': '216e85e672aa', 'paper-figure': '216e85e672aa', 'paper-figure-html': '216e85e672aa', 'comp-review': '216e85e672aa', 'comp-paper-zh': '216e85e672aa', 'comp-compile-zh': '216e85e672aa', 'auto-paper-improvement-loop': '216e85e672aa'}

## Workspace Context
The following files already exist in the workspace from previous steps:
- _tmp_recipe.txt
- AUDIT_REPORT.md
- CAPABILITY_CHECKLIST.json
- code/constraint_audit.py
- code/data_check.py
- code/main.py
- code/problem1.py
- code/problem2.py
- code/problem3.py
- code/problem4.py
- code/problem5.py
- code/requirements.txt
- code/utils.py
- DATA_FACTS.json
- DATA_PROFILE.json
- DELIVERABLES.json
- FIGURE_WORK_REPORT.md
- figures/all_results.json
- figures/fig_pipeline.html
- figures/fig_q1_balance_before_after.pdf
- figures/fig_q1_influence_rank.pdf
- figures/fig_q1_loss_distribution.pdf
- figures/fig_q1_source_reliability.pdf
- figures/fig_q2_carbon_flow.pdf
- figures/fig_q2_intensity_monthly.pdf
- figures/fig_q2_mixed_weight.pdf
- figures/fig_q2_responsibility_compare.pdf
- figures/fig_q3_budget_heatmap.pdf
- figures/fig_q3_pareto.pdf
- figures/fig_q3_priority.pdf
- figures/fig_q3_project_schedule.pdf
- figures/fig_q3_sensitivity.pdf
- figures/fig_q4_convergence.pdf
- figures/fig_q4_parameter_surface.pdf
- figures/fig_q4_robust_cost.pdf
- figures/fig_q4_scenario_distribution.pdf
- figures/fig_roadmap.html
- figures/gen_fig_q1_balance_before_after.py
- figures/gen_fig_q1_influence_rank.py
- figures/gen_fig_q1_loss_distribution.py
- figures/gen_fig_q1_source_reliability.py
- figures/gen_fig_q2_carbon_flow.py
- figures/gen_fig_q2_intensity_monthly.py
- figures/gen_fig_q2_mixed_weight.py
- figures/gen_fig_q2_responsibility_compare.py
- figures/gen_fig_q3_budget_heatmap.py
- figures/gen_fig_q3_pareto.py
- figures/gen_fig_q3_priority.py
- figures/gen_fig_q3_project_schedule.py
- figures/gen_fig_q3_sensitivity.py
- figures/gen_fig_q4_convergence.py
- figures/gen_fig_q4_parameter_surface.py
- figures/gen_fig_q4_robust_cost.py
- figures/gen_fig_q4_scenario_distribution.py
- figures/generate_all_figures.py
- figures/latex_includes.tex
- figures/problem_1_results.json
- figures/problem_2_results.json
- figures/problem_3_results.json
- figures/problem_4_results.json
- figures/problem_5_results.json
- figures/tikz_carbon_network.aux
- figures/tikz_carbon_network.log
- figures/tikz_carbon_network.pdf
- figures/tikz_carbon_network.tex
- figures/tikz_robust_structure.aux
- figures/tikz_robust_structure.log
- figures/tikz_robust_structure.pdf
- figures/tikz_robust_structure.tex
- MODELING_REPORT.md
- PARAMS_RAW.md
- PROBLEM_ANALYSIS.md
- PROBLEM_FACTS.json
- results/problem1_corrected.json
- results/problem2_carbon_flow.json
- results/problem3_project_plan.json
- results/problem4_robust_adjustment.json
- results/problem5_consultation.json
- RESULTS.md
- user_data/_problem_file.txt
- user_data/B题.pdf
- user_data/B题_extracted.txt
- user_data/附件1.xlsx
- user_data/附件2.xlsx
- user_data/附件3.xlsx
- user_data/附件4.xlsx
- user_data/附件5.xlsx
- user_data/附件6.xlsx
Please read and build upon these files as needed using the Read tool.

## Previous Steps Output Summary
工作区中已有文件（请用 Read/Bash 工具按需读取具体内容）:
- _tmp_recipe.txt
- AUDIT_REPORT.md
- CAPABILITY_CHECKLIST.json
- code/constraint_audit.py
- code/data_check.py
- code/main.py
- code/problem1.py
- code/problem2.py
- code/problem3.py
- code/problem4.py
- code/problem5.py
- code/requirements.txt
- code/utils.py
- DATA_FACTS.json
- DATA_PROFILE.json
- DELIVERABLES.json
- FIGURE_WORK_REPORT.md
- figures/all_results.json
- figures/fig_pipeline.html
- figures/fig_q1_balance_before_after.pdf
- figures/fig_q1_influence_rank.pdf
- figures/fig_q1_loss_distribution.pdf
- figures/fig_q1_source_reliability.pdf
- figures/fig_q2_carbon_flow.pdf
- figures/fig_q2_intensity_monthly.pdf
- figures/fig_q2_mixed_weight.pdf
- figures/fig_q2_responsibility_compare.pdf
- figures/fig_q3_budget_heatmap.pdf
- figures/fig_q3_pareto.pdf
- figures/fig_q3_priority.pdf
- figures/fig_q3_project_schedule.pdf
- figures/fig_q3_sensitivity.pdf
- figures/fig_q4_convergence.pdf
- figures/fig_q4_parameter_surface.pdf
- figures/fig_q4_robust_cost.pdf
- figures/fig_q4_scenario_distribution.pdf
- figures/fig_roadmap.html
- figures/gen_fig_q1_balance_before_after.py
- figures/gen_fig_q1_influence_rank.py
- figures/gen_fig_q1_loss_distribution.py
- figures/gen_fig_q1_source_reliability.py
- figures/gen_fig_q2_carbon_flow.py
- figures/gen_fig_q2_intensity_monthly.py
- figures/gen_fig_q2_mixed_weight.py
- figures/gen_fig_q2_responsibility_compare.py
- figures/gen_fig_q3_budget_heatmap.py
- figures/gen_fig_q3_pareto.py
- figures/gen_fig_q3_priority.py
- figures/gen_fig_q3_project_schedule.py
- figures/gen_fig_q3_sensitivity.py
- figures/gen_fig_q4_convergence.py
- figures/gen_fig_q4_parameter_surface.py
- figures/gen_fig_q4_robust_cost.py
- figures/gen_fig_q4_scenario_distribution.py
- figures/generate_all_figures.py
- figures/latex_includes.tex
- figures/problem_1_results.json
- figures/problem_2_results.json
- figures/problem_3_results.json
- figures/problem_4_results.json
- figures/problem_5_results.json
- figures/tikz_carbon_network.aux
- figures/tikz_carbon_network.log
- figures/tikz_carbon_network.pdf
- figures/tikz_carbon_network.tex
- figures/tikz_robust_structure.aux
- figures/tikz_robust_structure.log
- figures/tikz_robust_structure.pdf
- figures/tikz_robust_structure.tex
- MODELING_REPORT.md
- PARAMS_RAW.md
- PROBLEM_ANALYSIS.md
- PROBLEM_FACTS.json
- results/problem1_corrected.json
- results/problem2_carbon_flow.json
- results/problem3_project_plan.json
- results/problem4_robust_adjustment.json
- results/problem5_consultation.json
- RESULTS.md
- user_data/_problem_file.txt
- user_data/B题.pdf
- user_data/B题_extracted.txt
- user_data/附件1.xlsx
- user_data/附件2.xlsx
- user_data/附件3.xlsx
- user_data/附件4.xlsx
- user_data/附件5.xlsx
- user_data/附件6.xlsx


## Pipeline Context
当前步骤: 逻辑对抗复核 (comp-review) — 第 6/9 步
已完成步骤: 赛题分析
剩余步骤: 竞赛论文撰写, 编译与合规检查, 论文改进循环

该步骤必须产出的文件（至少）:
- COMP_REVIEW.md

## IMPORTANT: 前步骤的关键文件
以下文件是前面步骤的产出，内容在摘要中可能被截断。请在开始工作前使用 Read 工具完整读取这些文件。
- PROBLEM_ANALYSIS.md
- AUDIT_REPORT.md
- CAPABILITY_CHECKLIST.json
- DATA_FACTS.json
- PARAMS_RAW.md
- PROBLEM_FACTS.json

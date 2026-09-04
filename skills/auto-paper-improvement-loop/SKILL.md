# Auto Paper Improvement Loop: Review → Fix → Recompile

Autonomously improve the paper at: **当前工作区中的 main.tex / 论文文件**

## Context

Runs after `/paper-write` + `/paper-compile`. Iterates on writing quality (not research).

## Constants

- **MAX_ROUNDS = 2** — Round 1 catches structural issues, Round 2 catches presentation issues.
- **REVIEWER_SCRIPT** — External reviewer script. Thread via `_reviewer_thread.json`.
- **HUMAN_CHECKPOINT = false** — When true, pause after each review for user input.
- **LATEX_ENGINE** — Auto-detect: ctex/xelatex in main.tex → xelatex, otherwise pdflatex.
- **CUSTOM_REQUIREMENTS** — Highest priority.

## State Persistence

Writes `PAPER_IMPROVEMENT_STATE.json` after each round for crash recovery:
```json
{"current_round": 1, "last_score": 6, "status": "in_progress", "timestamp": "..."}
```
On startup: if exists + in_progress + <24h → resume. Otherwise start fresh.

## Workflow

### Step 0: Preserve Original
```bash
mkdir -p paper/_improvement_rounds
cp paper/main.pdf paper/_improvement_rounds/round0_original.pdf
```

### Step 1: Collect Paper Text
Concatenate all `paper/sections/*.tex` for review.

### Step 2: Round 1 Review

Send the full paper text to the external reviewer via `reviewer_client.py`:

```bash
mkdir -p _tmp
cat << 'REVIEW_EOF' > _tmp/_review_prompt.txt
You are reviewing an academic paper. Please provide a detailed, structured review.

## Full Paper Text:
REVIEW_EOF
cat _tmp/_paper_full_text.tex >> _tmp/_review_prompt.txt
cat << 'REVIEW_EOF' >> _tmp/_review_prompt.txt

## Review Instructions
Please act as a senior reviewer. Provide:
1. **Overall Score** (1-10, where 6 = weak accept, 7 = accept)
2. **Summary** (2-3 sentences)
3. **Strengths** (3-5 bullet points)
4. **Weaknesses** (categorized as CRITICAL / MAJOR / MINOR, each with specific location and actionable fix)
   - Check for "figure-as-subject" AI pattern: paragraphs starting with "图X展示了"/"As shown in Figure X" — flag as MAJOR if ≥3 occurrences
5. **Verdict**: "Accept" / "Almost" / "Reject"
6. **Actionable Fixes** (ordered by priority, each with exact section and what to change)
REVIEW_EOF
PYTHON=""; for _c in "$MH_PYTHON" python python3; do [ -z "$_c" ] && continue; if $_c -c "import sys" >/dev/null 2>&1; then PYTHON="$_c"; break; fi; done; [ -z "$PYTHON" ] && PYTHON=python
$PYTHON "$REVIEWER_SCRIPT" --prompt-file _tmp/_review_prompt.txt --thread-file _tmp/_reviewer_thread.json 2>&1 | tee _tmp/_round1_review.txt
```

If the reviewer script fails (API key not configured or network error), perform the review using self-analysis — act as a senior reviewer, score honestly, and proceed to Step 3. Cross-model review is preferred for objectivity but not required.

### Step 2b: Human Checkpoint (if enabled)
Present score + weaknesses. Wait for "go" / custom instructions / "skip N" / "stop".
Non-interactive mode: auto-proceed.

### Step 3: Implement Round 1 Fixes

Priority: CRITICAL → MAJOR → MINOR.

Common fix patterns:
| Issue | Fix |
|-------|-----|
| Assumption-model mismatch | Rewrite assumption, add bridging proposition |
| Overclaims | Soften: "validate"→"demonstrate relevance" |
| Missing metrics | Add quantitative table with caveats |
| Notation confusion | Rename globally, add Notation paragraph |
| Figure-as-subject writing | Rewrite: move figure ref to parenthetical, lead with analysis point |
| Missing references | Add to bib, cite appropriately |

### Step 4: Recompile Round 1

Auto-detect engine. Manual 4-step: engine→bibtex→engine→engine. Then snapshot to subdir:
```bash
cp paper/main.pdf paper/_improvement_rounds/round1.pdf
```

### Step 5-6: Round 2 Review + Fixes

Same process. Use same `_tmp/_reviewer_thread.json` for context continuity (multi-turn dialogue is automatic):

```bash
cat << 'REVIEW_EOF' > _tmp/_review_prompt.txt
Since your last review, we have implemented the following fixes:
[list the fixes from Step 3]

Please re-review the updated paper. Focus on:
1. Were the CRITICAL/MAJOR issues adequately addressed?
2. Any new issues introduced by the fixes?
3. Updated score and verdict.

## Updated Paper Text:
REVIEW_EOF
cat _tmp/_paper_full_text.tex >> _tmp/_review_prompt.txt
PYTHON=""; for _c in "$MH_PYTHON" python python3; do [ -z "$_c" ] && continue; if $_c -c "import sys" >/dev/null 2>&1; then PYTHON="$_c"; break; fi; done; [ -z "$PYTHON" ] && PYTHON=python
$PYTHON "$REVIEWER_SCRIPT" --prompt-file _tmp/_review_prompt.txt --thread-file _tmp/_reviewer_thread.json 2>&1 | tee _tmp/_round2_review.txt
```

If reviewer unavailable, use self-analysis for Round 2 as well.

### Step 7: Recompile Round 2

Snapshot to subdir:
```bash
cp paper/main.pdf paper/_improvement_rounds/round2.pdf
```
`paper/main.pdf` itself stays as the final deliverable (= round2).

### Step 8: Format Check

Check overfull hbox (>10pt → fix), page count vs limit, underfull warnings.

### Step 9: Document Results

Create `paper/PAPER_IMPROVEMENT_LOG.md`：

```markdown
# Paper Improvement Log

## Score Progression

| Round | Score | Verdict | Key Changes |
|-------|-------|---------|-------------|
| Round 0 (original) | X/10 | No/Almost/Yes | Baseline |
| Round 1 | Y/10 | No/Almost/Yes | [summary of fixes] |
| Round 2 | Z/10 | No/Almost/Yes | [summary of fixes] |

## Round 1 Review & Fixes

### Review (full text)
[Complete raw review text, verbatim]

### Fixes Implemented
1. [Fix description + which files changed]
2. [Fix description]

## Round 2 Review & Fixes

### Review (full text)
[Complete raw review text, verbatim]

### Fixes Implemented
1. [Fix description]
2. [Fix description]

## PDFs
| File | Size | Description |
|------|------|-------------|
| main.pdf | X KB | **最终成品（= round2），编辑/下载只认这个** |
| _improvement_rounds/round0_original.pdf | X KB | Before improvement (历史留痕) |
| _improvement_rounds/round1.pdf | X KB | After round 1 (历史留痕) |
| _improvement_rounds/round2.pdf | X KB | After round 2 (历史留痕) |
```

## Output

```
paper/
├── main.pdf                       # 最终成品(= round2)，编辑/下载只认这个
├── PAPER_IMPROVEMENT_LOG.md
└── _improvement_rounds/           # 历史快照(只读留痕，不参与后续编辑)
    ├── round0_original.pdf
    ├── round1.pdf
    └── round2.pdf
```

## Key Rules

⛔ **File writing strategy (prevent both failure modes):**
- For short content (<150 lines): use the **Write tool** directly (atomic, reliable)
- For long content (>150 lines): use **Write** for the first section (ensures file exists on disk), then append remaining sections with `cat << 'EOF' >> paper/PAPER_IMPROVEMENT_LOG.md`
- **NEVER `end_turn` without producing the improved `paper/main.pdf`** — even if some rounds had issues, keep the best compiled PDF

⛔ **MUST run output verification before ending**:
```bash
PASS=true
# 主产出: 改进后的 paper/main.pdf (引擎按此判定成败)
[ -f paper/main.pdf ] && SZ=$(wc -c < paper/main.pdf) || SZ=0
if [ "$SZ" -ge 100000 ]; then
    echo "✅ paper/main.pdf ($SZ bytes)"
else
    echo "❌ paper/main.pdf missing or too small ($SZ bytes) — must keep a compiled PDF before ending"
    PASS=false
fi
# 改进日志
if [ -f paper/PAPER_IMPROVEMENT_LOG.md ]; then
    echo "✅ paper/PAPER_IMPROVEMENT_LOG.md"
else
    echo "❌ paper/PAPER_IMPROVEMENT_LOG.md missing — write the improvement log before ending"
    PASS=false
fi
[ "$PASS" != true ] && echo "⛔ Verification failed — must produce output before ending step"
```

- Preserve all PDF snapshots under `paper/_improvement_rounds/` — keep `paper/` root clean (only `main.pdf` there, so the editor / download never points at a stale round snapshot)
- Save full raw review text (don't truncate)
- Same thread file for Round 2 (context continuity)
- Always recompile after fixes
- Don't fabricate experimental results
- Soften overclaims rather than adding unsupported claims
- Global consistency when renaming notation (all files)
- ⛔ Main output: `paper/main.pdf` + `paper/PAPER_IMPROVEMENT_LOG.md`. Don't write extra reports (e.g. AUTO_PAPER_IMPROVEMENT_REPORT.md, AUTO_PAPER_IMPROVEMENT_FINAL_REPORT.md) to root
- ⛔ Temp files (`_review_prompt.txt`, `_paper_full_text.tex`, `_round1_review.txt` etc.) go to `_tmp/`
- Large files: Bash heredoc

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
- _tmp/_cited_keys.txt
- _tmp/_labels.txt
- _tmp/_refs.txt
- _tmp/compile_check_final.log
- _tmp/compile_check_final2.log
- _tmp/paper_bibtex.log
- _tmp/paper_bibtex_final.log
- _tmp/paper_compile.log
- _tmp/paper_compile_final.log
- _tmp/paper_compile_final_pass1.log
- _tmp/paper_compile_final_pass2.log
- _tmp/paper_compile_final_pass3.log
- _tmp/paper_compile_pass1.log
- _tmp/paper_compile_pass2.log
- _tmp/paper_compile_pass3.log
- _tmp/paper_compile_second.log
- _tmp/writing_check_final.log
- _tmp/writing_check_final2.log
- _tmp/writing_check_final3.log
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
- COMP_REVIEW.md
- COMP_REVIEW_VERDICT.json
- COMPILE_COMPLIANCE_REPORT.md
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
- paper/cumcmthesis.cls
- paper/main.aux
- paper/main.bbl
- paper/main.blg
- paper/main.log
- paper/main.out
- paper/main.pdf
- paper/main.tex
- paper/main.tex.tmp
- paper/main.toc
- paper/references.bib
- paper/sections/1_restatement.tex
- paper/sections/2_analysis.tex
- paper/sections/3_assumptions.tex
- paper/sections/4_symbols.tex
- paper/sections/5_problem1.tex
- paper/sections/6_problem2.tex
- paper/sections/7_problem3.tex
- paper/sections/8_sensitivity.tex
- paper/sections/9_evaluation.tex
- paper/sections/A_code.tex
- paper/simkai.ttf
- paper/simsun.ttc
- PAPER_BLOCKED_REPORT.md
- PAPER_DATA_CHECK_REPORT.md
- PAPER_DATA_CHECKLIST.md
- PARAMS_RAW.md
- PROBLEM_ANALYSIS.md
- PROBLEM_FACTS.json
- results/problem1_corrected.json
- results/problem2_carbon_flow.json
- results/problem3_project_plan.json
- results/problem4_robust_adjustment.json
- results/problem5_consultation.json
- RESULTS.md
- texput.log
- user_data/_problem_file.txt
- user_data/B题.pdf
- user_data/B题_extracted.txt
- user_data/附件1.xlsx
- user_data/附件2.xlsx
- user_data/附件3.xlsx
- user_data/附件4.xlsx
- user_data/附件5.xlsx
- user_data/附件6.xlsx
- WORK_REPORT.md
Please read and build upon these files as needed using the Read tool.

## Previous Steps Output Summary
工作区中已有文件（请用 Read/Bash 工具按需读取具体内容）:
- _tmp/_cited_keys.txt
- _tmp/_labels.txt
- _tmp/_refs.txt
- _tmp/compile_check_final.log
- _tmp/compile_check_final2.log
- _tmp/paper_bibtex.log
- _tmp/paper_bibtex_final.log
- _tmp/paper_compile.log
- _tmp/paper_compile_final.log
- _tmp/paper_compile_final_pass1.log
- _tmp/paper_compile_final_pass2.log
- _tmp/paper_compile_final_pass3.log
- _tmp/paper_compile_pass1.log
- _tmp/paper_compile_pass2.log
- _tmp/paper_compile_pass3.log
- _tmp/paper_compile_second.log
- _tmp/writing_check_final.log
- _tmp/writing_check_final2.log
- _tmp/writing_check_final3.log
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
- COMP_REVIEW.md
- COMP_REVIEW_VERDICT.json
- COMPILE_COMPLIANCE_REPORT.md
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
- paper/cumcmthesis.cls
- paper/main.aux
- paper/main.bbl
- paper/main.blg
- paper/main.log
- paper/main.out
- paper/main.pdf
- paper/main.tex
- paper/main.tex.tmp
- paper/main.toc
- paper/references.bib
- paper/sections/1_restatement.tex
- paper/sections/2_analysis.tex
- paper/sections/3_assumptions.tex
- paper/sections/4_symbols.tex
- paper/sections/5_problem1.tex
- paper/sections/6_problem2.tex
- paper/sections/7_problem3.tex
- paper/sections/8_sensitivity.tex
- paper/sections/9_evaluation.tex
- paper/sections/A_code.tex
- paper/simkai.ttf
- paper/simsun.ttc
- PAPER_BLOCKED_REPORT.md
- PAPER_DATA_CHECK_REPORT.md
- PAPER_DATA_CHECKLIST.md
- PARAMS_RAW.md
- PROBLEM_ANALYSIS.md
- PROBLEM_FACTS.json
- results/problem1_corrected.json
- results/problem2_carbon_flow.json
- results/problem3_project_plan.json
- results/problem4_robust_adjustment.json
- results/problem5_consultation.json
- RESULTS.md
- texput.log
- user_data/_problem_file.txt
- user_data/B题.pdf
- user_data/B题_extracted.txt
- user_data/附件1.xlsx
- user_data/附件2.xlsx
- user_data/附件3.xlsx
- user_data/附件4.xlsx
- user_data/附件5.xlsx
- user_data/附件6.xlsx
- WORK_REPORT.md


## Pipeline Context
当前步骤: 论文改进循环 (auto-paper-improvement-loop) — 第 9/9 步
已完成步骤: 赛题分析

该步骤必须产出的文件（至少）:
- paper/main.pdf
- paper/PAPER_IMPROVEMENT_LOG.md

## IMPORTANT: 前步骤的关键文件
以下文件是前面步骤的产出，内容在摘要中可能被截断。请在开始工作前使用 Read 工具完整读取这些文件。
- PROBLEM_ANALYSIS.md
- AUDIT_REPORT.md
- CAPABILITY_CHECKLIST.json
- DATA_FACTS.json
- PARAMS_RAW.md
- PROBLEM_FACTS.json

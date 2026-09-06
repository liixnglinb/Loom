---
stage: 9
name: review
duration_h: 2-6
inputs: ["paper.tex", "paper.pdf", "decision_log_full", "decision_log.competition"]
outputs:
  - "stage.9.{anti_patterns_check, compliance_checks, ai_compliance_check, redo_log, panel_scores, weakest_section, red_team_record, final_pdf_path, submission_ready}"
loads_reference:
  - "competitions/<comp>/current_rules.md"
  - "competitions/<comp>/anti_patterns.md"
  - "competitions/<comp>/ai_compliance_checklist.md"
  - "competitions/<comp>/rubric_overlay.json"
  - "references/feedback_layer3_panel.md"
loads_template: ["templates/latex/<comp>/"]
feedback: ["L1", "L3_panel", "red_team_in_championship"]
next: SUBMIT
---

# Stage 9 — Submission review

The final gate is compliance first, content consistency second, presentation third. A polished paper that violates the current rules is not submission-ready.

## 1. Re-open the official rules

Read `competitions/<comp>/current_rules.md`, open its official links, and compare the final artifacts against the current contest year. Record the check in `decision_log.stages.9.compliance_checks`.

Minimum branches:

### CUMCM

- electronic paper starts with the abstract page;
- no commitment form, numbering page, table of contents, or identity information;
- main text and file size meet the current limits;
- appendix lists the supporting-material files;
- support ZIP/RAR contains runnable code and required evidence, is within the size limit, and excludes secrets;
- AI-assisted content is marked and cited;
- if AI was used, support materials contain `AI工具使用详情.pdf`; otherwise the required no-AI declaration is present.

Any unresolved rule violation sets `submission_ready=false` and yields `block`.

## 2. Run the active anti-pattern checklist

Read `competitions/<comp>/anti_patterns.md` and derive the count from the active file rather than copying a remembered or example count.

These are maintainer heuristics, not official scoring weights. Fix high-severity hits; record accepted medium-risk items with an explicit rationale.

## 3. Verify the evidence chain

Cross-check the final paper against `decision_log.json` and the saved artifacts:

- no abandoned model remains in the abstract or conclusion;
- no symbol changes meaning between sections;
- all headline values reproduce from stored results;
- every figure/table path resolves and its caption matches the content;
- every external claim has a verified source;
- AI-generated citations have been opened and checked manually.

## 4. Review presentation

- labels, units, legends, equations, and captions remain readable at final PDF size;
- fonts and colors are consistent and accessible;
- tables use consistent units and precision;
- there are no unresolved `??` references, missing glyphs, clipped figures, or large overfull boxes;
- all required sections are present in the compiled PDF, not merely on disk as detached `.tex` files;
- single figures are about 70% of the text width and undistorted;
- English abbreviations carry full names at first occurrence, and inline citations appear only in the problem analysis or at first method introduction;
- no stray spaces follow Chinese punctuation;
- section hierarchy 一、→ 1.1 → bullet is consistent; level-1 titles are centered with fonts larger than the body, level-2 titles are left-aligned, and 1.2 问题提出 has an intro paragraph before the bulleted subproblems.

## 5. Run the five-view panel

Use `references/feedback_layer3_panel.md` as the single source for panel roles and aggregation. Prefer independent parallel views when the harness supports them; otherwise run the views separately to reduce cross-contamination.

Map every high-severity concern back to one source section and apply a targeted patch. Re-run only the affected checks and panel views. Do not ask the panel to predict an award; use `ready`, `refine`, or `block` against the repository rubric.

## 6. Generate AI disclosure artifacts

For CUMCM, run from the user project root:

```bash
python <skill>/scripts/render_ai_usage.py \
  --competition <competition> \
  --decision-log state/decision_log.json \
  --paper-workspace paper_workspace/ \
  --support-dir support_materials/
```

For CUMCM with AI use, verify `support_materials/AI工具使用详情.pdf` is in the supporting archive and that inline marks and AI-tool references are present. For an explicit empty CUMCM ledger, the helper instead creates `paper_workspace/AI工具未使用声明.md`; rerender and verify that the declaration appears immediately after the references, with no details PDF.

## 6a. Run the 26-item AI compliance checklist

Read `competitions/<comp>/ai_compliance_checklist.md` (CUMCM) — the full 2026 National-CUMCM AI self-check: 6 dimensions × 26 sub-items, transcribed item-by-item from the official standard checklist table without omission. For CUMCM, walk every one of the 26 items and mark each `合格 / 存在问题 / 待核实`, recording the problem location and a fix suggestion.

The 26 items span:
- **2026 AI 新规合规 (4)**: core-modeling AI-led trace, core-writing AI-trace, AI-declaration truthfulness, AI-content human-verification;
- **AI hallucination & data truthfulness (4)**: raw-data authenticity, literature/conclusion truthfulness, figure-value matching, logic/causation truthfulness;
- **Modeling logic & problem fit (5)**: problem-understanding, logic self-consistency, all-subproblems closed-loop, model-selection fit, constraint inclusion;
- **Solving & result plausibility (3)**: common-sense plausibility, solver-fit, parameter-justification;
- **Official writing rules (6)**: abstract compliance, full-structure completeness, core validation completeness, content resonance, assumption count/quality, anti-similarity;
- **Layout & page count (4)**: body page range 20–32, format consistency, figure/table/formula typesetting, anonymity.

Persist to `decision_log.stages.9.ai_compliance_check` with `total_items=26`, per-item status/where/problem/fix, and a `critical_violations` count. Any fatal item (AI-led core modeling, fabricated data/literature, or AI-usage non-disclosure that contradicts the declaration) sets `submission_ready=false` and yields `block`, regardless of panel scores. No item may be left blank.

## 6b. Non-conformance → revise-and-recheck loop

If any compliance or 26-item checklist result is not fully green, the paper is **not** released: it must be revised and re-checked until every item is `合格` (or accepted `待核实` with explicit rationale) with no fatal violation. The loop is mandatory — do not hand a non-conforming paper to the team.

1. **Classify the defect** by the non-conforming item and route it to the smallest responsible artifact:

| Non-conforming scope | Revise target |
|---|---|
| AI-led core modeling / fabricated data-literature / AI-declaration mismatch | Stage 5 model & code, Stage 8 rebuttal, regenerate disclosure (§6) |
| hallucination, figure-value mismatch, logic/causation break | Stage 5 results / Stage 9 §3 evidence chain |
| modeling logic, problem fit, subproblem closure, solver fit, parameter basis | Stage 5 (per-question) / Stage 3 selection |
| assumption count/quality, abstract, structure, resonance, similarity | Stage 8 writing (§2 anti-patterns) |
| page count, format, typesetting, anonymity, AI disclosure artifact | renderer + template + §6/§7 |

2. **Apply the targeted fix** on that artifact and recompute any downstream numbers it changes. Do not paper over a wrong result with prose.
3. **Re-enter Stage 9** and re-run only the checks affected by the change (§1 rules if touched, §2 anti-patterns, §3 evidence, §6a checklist items that changed). If the fix touched modeling or results, add a focused L3 panel re-run on the affected personas (§5) rather than a full restart.
4. **Loop to green**: repeat until §1-§6 all pass with `submission_ready=true`. Each iteration records a `redo_log` entry with the routed target, the fix, the re-run scope, and the before/after status. Bound the loop by time — but running out of time does **not** convert a known fatal violation into `ready`.
5. Track via `decision_log.stages.9.redo_log`; keep `submission_ready=false` until the loop converges green.

## 7. Compile and inspect the final PDF

Use `<skill>/scripts/render_paper.py` or the selected LaTeX engine. Compilation succeeds only when the PDF exists, includes all intended sections, and has no unresolved high-severity warnings. Visually inspect the first page, dense equations, wide tables, figure-heavy pages, references, appendices, and the AI report.

## 8. Persist the final gate

Write actual runtime-derived counts and paths. The schema is:

```json
{
  "anti_patterns_check": {
    "total": null,
    "passed": null,
    "fixed": null,
    "deferred": null
  },
  "compliance_checks": {
    "rules_verified": null,
    "anonymity_passed": null,
    "page_limit_passed": null,
    "ai_disclosure_passed": null
  },
  "final_pdf_path": "paper_output/paper.pdf",
  "submission_ready": null
}
```

The `null` values above are schema placeholders only. Replace every one with an observed count or verified boolean before persisting Stage 9; never copy a sample result into the final gate.

## Exit conditions

- current official rules verified with no unresolved violation;
- anti-pattern and consistency checks completed;
- **the 26-item AI compliance checklist (§6a) is fully filled with no blank items and no fatal violations;**
- all high-severity panel findings resolved;
- PDF compiled and visually inspected;
- AI disclosure and supporting materials complete when required;
- `decision_log.stages.9.submission_ready == true`.

Only then hand the final submission package back to the team.

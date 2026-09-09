***

name: bzd-2026-stage-01
description: BZD 双审精制流 · 阶段1 启动与题面解析。Use when 执行 cumcm-bzd-2026 全流程第 1 阶段。
--------------------------------------------------------------------------

# 阶段 1 · 启动与题面解析（BZD 双审精制流）

完整规则见主 Skill `cumcm-bzd-2026`（references/stage\_01、stage\_02），本文件为阶段入口指令。

## 本阶段任务（一次会话内完成）

1. 环境与选题：`doctor.py` 预检、角色分工、规则基线（重开当届官方链接核对页数/匿名/AI披露，写 `state/decision_log.json` 的 compliance.ruleset + verified\_at——规则三重门 #1）。
2. **题面翻译台账**（本阶段核心）：从题标题起读，一句完整原句一个编号单元（B01/Q2-04）→ **十类角色标注**（context/entity/definition/mechanism/given/constraint/task/objective/validation/deliverable）→ **8 列覆盖台账**（编号|题干原句|通俗翻译|明示条件数据|隐含建模信号|与前后联动|漏读后果|后文证据）→ 翻译六问 → 量词保真（不考虑/仅/至多/至少/必须/不得 强度原样保留）→ 最易漏读句 5-12 条 → 术语口径表（区分题面事实与模型假设）→ 逐问输入-任务-输出表。
3. 数据交接包（有附件时）：实际读取生成数据集说明，单独输出可发给其他 AI 的描述。
4. 状态：初始化 `<cwd>/state/decision_log.json`（模板见随包 `$MH_BZD_DIR/templates/shared/decision_log.json`），写入 5 个启动字段与 task\_type；`sub_status` 视题面是否公布置位。

## 产物（必须落盘）

- `PROBLEM_TRANSLATION.md`：题面翻译台账全文（覆盖台账核心表 + 术语表 + 逐问I/O + 联动链）

- `state/decision_log.json` 更新（stages.1 / compliance.ruleset / task\_type）

## 质量门

- 覆盖审计 100%（实质单元数 = 台账行数）；漏读后果列无空行；联动链完整；无虚构"官方解读"。

- 风险定级 P0-P3，任一 P0（虚构/身份泄露/复现失败）不进入下一阶段。

## 引用

- 翻译台账格式细节：主 Skill `$MH_BZD_DIR/references/stage_02_problem_decomposition.md`（步骤 1b）

- 规则基线：主 Skill `$MH_BZD_DIR/references/rules_baseline.md`

- 状态模板：随包 `$MH_BZD_DIR/templates/shared/decision_log.json`（复制到 `<cwd>/state/`）


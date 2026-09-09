---
name: bzd-2026-stage-02
description: BZD 双审精制流 · 阶段2 建模策略与模型选型。Use when 执行 cumcm-bzd-2026 第 2 阶段。
---

# 阶段 2 · 建模策略与模型选型（BZD 双审精制流）

完整规则见主 Skill `cumcm-bzd-2026`（references/stage_03、model_fit_rubric），本文件为阶段入口指令。

## 本阶段任务

1. 任务角色分类：每问标 foundation/estimation/explanation/prediction/extension/optimization/decision/validation；对照六种跨问架构预判联动。
2. 数据盘点：结构/类型/样本量/缺失异常口径；预处理方法必须对应实际数据问题，禁止无依据罗列方法。
3. 模型选型：每问候选 ≥2 真不同（求解器名不算模型）；查数模字典（随包 `$MH_BZD_DIR/scripts/query_model_dict.py`，只读引用）得到适用场景/数据要求/关键假设/输入输出/禁忌/检验；四级判定（合适/有条件合适/不合适/证据不足待人工复核）。
4. 比较与推荐：比较表逐列可执行；说明契合/数据/假设代价/输出/可解释/计算成本/与后续问题兼容性；给出备选切换时机。
5. 全文统一口径表 v1：共享符号/指标/变量/参数/单位/坐标/预处理规则/目标/约束/评价指标——一次定义全文复用。
6. 创新方向：每条 = 改动组件+实现步骤+可测对照+风险备选；"使用遗传算法/模型融合/更多可视化"不算创新。
7. toy demo：每问主模型最小可行示例验证可行性（失败原因必须登记）。
8. 断链检查：参数/坐标/单位/目标跨问兼容；防特征泄漏与重复计数；确定 `task_type` 写入状态。

## 产物

- `TECH_ROUTE.md`：任务角色表 + 候选/比较/推荐表 + 统一口径表 v1 + 技术路线（含通过选型更新的跨问联动链）
- `state/decision_log.json` 更新（stages.2 / task_type / toy 结论）

## 质量门

- 每问候选 ≥2 且接口列非空；断链清单为空或逐条登记处置；toy 全过或失败原因已登记；无 P0/P1 残留。

## 引用

- 六维判定细则：主 Skill `$MH_BZD_DIR/references/model_fit_rubric.md`
- 提示词（可选）：主 Skill `$MH_BZD_DIR/references/prompt_library.md`（第二章/第五章板块）
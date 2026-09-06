---
name: bzd-2026-stage-03
description: BZD 双审精制流 · 阶段3 建模执行。Use when 执行 cumcm-bzd-2026 第 3 阶段。
---

# 阶段 3 · 建模执行（BZD 双审精制流）

完整规则见主 Skill `cumcm-bzd-2026`（references/stage_05、template_library/chapter05_model_solving.md），本文件为阶段入口指令。

## 本阶段任务（对每个子问题跑 mini-pipeline）

1. 篇幅规划：正文 ≤30 页——前置 3-4 页、公共数据 2-3 页（多问共用才集中设章）、每问 6-9 页、收尾 2-3 页。
2. 数据预处理（位置按共用关系判定）：七要素——来源/样本量字段时间范围/缺失异常重复的量化/处理方法与理由/处理数量/前后统计对比/标准化编码划分；禁止"对数据进行了处理"式空话。
3. **逐问六步**：
   - A 建模思路与选型（目标/已知/输出/数学类型四件套；"删除赛题背景仍通用"=未针对本题，重写）
   - B 模型建立（变量参数含单位取值；公式前依据后释意；参数来源四类；每条约束写现实含义；**优化模型集中表达**"综上建立如下模型"+目标+约束+变量一个公式组）
   - C 模型求解（算法名称/思想/理由；输入输出关键步骤；初值/参数/停止条件/软件版本；智能算法附编码/适应度/算子/种群/收敛曲线/种子；完整代码进附录正文留伪代码）
   - D 结果呈现（逐项回答不漏；数值方案排名预测标单位口径时间样本范围；解释现实规律；异常归因）
   - E 模型检验（指标匹配模型类型并量化：预测→MAE/RMSE/MAPE/R²+残差；分类→混淆矩阵/准确率/召回/F1/AUC；聚类→轮廓/CH/DB；优化→约束满足率/最优性差距/重复运行；评价→排名一致性/权重扰动。给出指标数值+判定标准+对照；**训练集拟合不算验证**）
   - F 灵敏度分析（只对决定结论/参数依赖强/来源不确定的主模型：选参→基准范围步长→固定其余逐次重解→参数-结果图→敏感参数与稳定区间→结论是否改变；S=(ΔY/Y)/(ΔX/X)；多因素用正交/响应面/网格/蒙特卡洛/Sobol；禁止全部参数机械 ±10%）
4. 跨问联动：递进问显式写出前问输出→后问接口→单位时间转换→误差传播；"只写基于问题一而实际重算"=假联动（P1）。
5. 图表纪律：表承数值图承趋势；同一组结果只留一种主表达；图表三有（前引/中引用/后解释）；正文表格 ≤15 行；单图约 70% 文本宽。
6. ⛔ **图的生产规范（论文级，必读必执行）**：`cat _utils/figure_production_rules.md` 并按 A–D 节执行——
   - **数据图**：风格基线 `_utils/plot_utils.py`（setup_style）+ 图型选型 `_utils/chart_library.md` + 配方 `_utils/figure_recipes_*.md` / `_utils/get_recipe.py` → 写 `figures/gen_fig_<key>.py` → 出矢量 PDF → `$PYTHON _utils/figure_check.py figures/fig_<key>.pdf` 质检（FAIL 必修，最多 3 轮）。
   - **流程图/架构图/技术路线图**：手写 HTML+CSS（flex/grid 自动布局、公式 `\(...\)`、黑白基调低饱和）→ **3 候选择优**（结构不同 3 版 → `$PYTHON _utils/screenshot_capture.py --geom-check` 几何自检 → 四维打分：逻辑忠实 40%/信息 20%/对齐 20%/融合 20% → 选 1）→ 选中版 `$PYTHON _utils/screenshot_capture.py --file figures/fig_<name>.html --out figures/fig_<name>.pdf --format pdf [--render-math]` 转单页矢量 PDF；落败候选清理、打分留痕 `_tmp/fig_choice_notes.md`（⛔ 不进论文）。
   - 每张图通过后，在 `SOLVING_RESULTS.md` 图索引区追加 `- fig_<name>.pdf — 建议 caption：<≤20字>`，供 stage05 直接 `\includegraphics`。
7. 写作落地素材：代码转正文（函数名替换为中文语义名/数学符号）与结果分析段（180-220 字连续段落）写入素材文件。

## 产物

- `SOLVING_RESULTS.md`：逐问建模/代码/结果/检验/灵敏度摘要 + 结果文件索引（results/、figures/、code/）
- `results/`、`figures/`、`code/` 真实文件 + 可运行代码与随机种子记录

## 质量门

- 每问六步齐备；检验匹配表量化；无假联动；无 P0（虚构结果/复现黑洞）；关键产物路径写入 stages.3。

## 引用

- 六步细节与图表纪律：主 Skill `$MH_BZD_DIR/references/stage_05_solving_loop.md`
- 成稿模板：主 Skill `$MH_BZD_DIR/references/template_library/chapter05_model_solving.md`
- 提示词：主 Skill `$MH_BZD_DIR/references/prompt_library.md`（第五章板块）
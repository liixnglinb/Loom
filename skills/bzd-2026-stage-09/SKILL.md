---
name: bzd-2026-stage-09
description: BZD 双审精制流 · 阶段9 终稿装配与合规出库。Use when 执行 cumcm-bzd-2026 第 9 阶段。
---

# 阶段 9 · 终稿装配与合规出库（BZD 双审精制流）

完整规则见主 Skill `cumcm-bzd-2026`（references/template_library/chapter07_ai_reference_appendix.md、support_ai_usage_detail.md），本文件为阶段入口指令。

## 本阶段任务

1. **全文组装**（顺序固定）：承诺书 → 编号专用页 → 摘要专用页（第一页起编页码、页脚居中）→ 正文（重述→分析→假设→符号→各问建立求解→模型评价）→ **AI 工具使用声明** → 参考文献 → 附录（A 文件列表/B 软件环境与求解工具/C 完整源程序与补充材料）。**正文不设目录**。
2. **合规门（fail-closed，逐项布尔）**：
   - 摘要（含标题关键词）≤1 页；正文 ≤30 页（附录不计入）；A4、四边距 ≥2.5cm
   - **全文无身份信息**：摘要/正文/附录/页眉页脚/文档属性/代码/截图/文件名逐项扫描
   - AI 声明位置正确且与详情一致；使用了的→支撑材料含《AI工具使用详情.pdf》（四要素）
   - **附录与复现终检 10 项**：输入文件存在且字段一致 / 无绝对路径 / 关键参数与正文一致 / 目标函数约束与正文一致 / 随机算法固定种子或说明重复运行 / 无缺失自定义函数与依赖 / 程序能产出正文主要数值图表 / 代码有注释无无关测试 / 无账号密码密钥 / 支撑材料代码与附录展示一致（无程序则写"本论文没有用到程序"）
3. **参考文献终检**：GB/T 7714 体系内格式统一；逐条真实可检索；正文引用与文末一一对应；AI 工具未列入。
4. **26 项 AI 合规清单终过一遍**：任何死亡项（AI 主导核心建模/虚构数据文献/声明与实际矛盾）→ block。
5. **支撑材料包**：ZIP ≤20MB，含文件清单、可运行源程序、自主数据、《AI工具使用详情.pdf》（用 support_ai_usage_detail.md 的 A-01~A-04 记录模板 + 采纳/人工核验表）；不含赛题原始数据、承诺书、密钥与身份信息。
6. **最终 PDF 目检**：首页/公式密集页/宽表/图密集页/参考文献/附录逐页过；无 `??` 引用、无越界。
7. **规则核对三重门 #3**：出库前最后核对当届官方通知，更新 `compliance.ruleset.verified_at`；写 `submission_ready=true`。

## 产物

- `SUBMISSION.md`：交付清单（最终 PDF 路径 / 支撑材料包路径 / 合规门逐项结果 / 复现终检结果 / submission_ready）
- 最终 `paper_output/main.pdf` + `support_materials/`（含 AI 工具使用详情）
- `state/decision_log.json` 更新（stages.9）

## 质量门

- 合规门全绿；26 项无空项无死亡项；PDF 存在且目检通过；支撑包完整匿名；`submission_ready=true`。

## 引用

- 合规/参考文献/附录完整模板：主 Skill `$MH_BZD_DIR/references/template_library/chapter07_ai_reference_appendix.md`
- AI 使用详情记录模板：主 Skill `$MH_BZD_DIR/references/template_library/support_ai_usage_detail.md`
- 生成详情脚本（可选）：随包 `$MH_BZD_DIR/scripts/`（doctor.py --check-paper 等）
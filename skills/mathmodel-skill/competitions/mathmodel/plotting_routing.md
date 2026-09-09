# 绘图路由（plotting_routing）

> 论文需要图表时，先按图类型路由到对应的绘图 skill，不要混用。本文件是 Stage 5/6/8/9 图表环节的路由依据；对应的绘图 skill 位于项目根目录，命名以 `技能_` 开头。
>
> **图表放在论文什么内容后面、配什么类型**，先参考同目录 `plotting_placement.md`（50 篇获奖论文观察总结，属于参考基线而非硬规则）；类型确定后再按本文件路由到对应 skill。

## 路由总原则

- **按图类型选择对应 skill**（见下表），不要在单一 skill 里硬凑所有图。
- 数据结果图走 `技能_scientific-agent-drawing`（matplotlib/seaborn 子技能）；流程/结构/示意/技术路线图走 `技能_diagram-design` 或 `技能_drawio-skill`。
- 三个绘图 skill 的优先级关系见项目根 `技能_图表路由规则.md`：重叠类型优先 `diagram-design`，需可编辑矢量/多格式导出用 `drawio-skill`，需数据统计图用 `scientific-agent-drawing`。
- 模板库没有的定制图（利用率图、迁移热力图、SOC 轨迹、总体框架图等）由 agent 直接写 matplotlib 绘制，风格遵循 `scientific-agent-drawing/scientific-visualization` 规范（一致配色、图宽约 70%、图题在下、期刊线条）。

## 图类型 → skill 映射

| 图类型 | 具体图 | 用哪个 skill |
|---|---|---|
| 统计可视化类 | 折线、散点、箱线、热图、柱状、直方、堆叠、饼图、雷达、ROC、相关热图、误差棒 | **scientific-agent-drawing**（matplotlib/seaborn） |
| 对比/排名/综合评价 | 多方案对比、排名、雷达、帕累托、多面板报告 | **scientific-agent-drawing** |
| 预测评估类 | 回归/分类指标、学习曲线、ROC、残差、时序拟合 | **scientific-agent-drawing** |
| 灵敏度/稳健性类 | SHAP、偏依赖（PDP）、箱线区间、参数扰动曲线 | **scientific-agent-drawing**（SHAP/PDP 自写 matplotlib）；参数扰动折线/表可手画 |
| 数据结果类 | 区域利用率、迁移热力图、SOC 轨迹、逐时负荷曲线 | **scientific-agent-drawing**（matplotlib 自绘） |
| 流程框架类 | 总体技术路线图、算法流程图、模型结构框图、决策流程 | **diagram-design**（优先）或 **drawio-skill** |
| 甘特图 | 任务调度甘特图、项目排期 | **drawio-skill** 或 matplotlib `broken_barh` 自绘 |
| 时序/交互图 | 时序图、API 调用、消息传递 | **diagram-design**（sequence）或 **drawio-skill**（UML sequence） |
| 架构/拓扑/ER/UML | 系统架构、网络拓扑、ER 图、类图、C4 | **drawio-skill**（可编辑 .drawio）或 **diagram-design** |
| 思维导图/知识结构 | 脑图、层级关系、概念关系 | **diagram-design**（nested/tree）或 mermaid 转 drawio |
| 原理示意图/场景图 | 坐标系示意、物理过程、场景图 | 无模板 → agent 自绘 matplotlib 或 SVG |

## 渲染依赖

- **scientific-agent-drawing**：Python（matplotlib/seaborn/pandas），读 CSV/XLSX 数据，纯本地零 API Key。
- **diagram-design**：输出自包含 HTML/SVG/PNG，浏览器打开即可；纯本地零 API Key。
- **drawio-skill**：需 draw.io 桌面 CLI（Windows 已装 `draw.io.exe` 并在 PATH，`draw.io --version` ≥30），导出 PNG/SVG/PDF。
- 输出统一放 `figures/`（论文装配目录），矢量 PDF 优先，图宽约 70%、图题在下。
- 位图（PNG）统一 `dpi≥300`（`savefig(..., dpi=300)`），避免打印/放大发虚；能矢量导出时优先 PDF/SVG。

## 绘图前置约束：可读性自检与整改（硬规则）

**每张图绘制完成后，必须自动做一次可读性自检。只要命中下列任意一条，就判定为"图表杂乱"，禁止直接输出原图，必须按下方优先级整改后再输出。** 这是 Stage 5/6 出图前的必检项，不是可选建议。

### 杂乱判定（满足任意一条即判定杂乱）

1. **点/柱过密**：数据点、柱子数量过多，密密麻麻出现毛刺、堆叠拥挤。
2. **线过多缠绕**：线条数量太多，多条线缠绕重叠，看不清趋势。
3. **类别过多/图例拥挤**：类别过多，图例拥挤，标签文字互相重叠。
4. **多维信息爆炸**：信息全部堆在一张图，一张图同时塞太多维度，信息爆炸，人眼难以读取。

### 整改优先级（按顺序，先用低优先级无法解决再上高优先级）

1. **优先级 1：降采样 / 聚合数据**。时序时间步太多时先聚合，如小时聚合为 4 小时 / 6 小时均值，减少绘图点数，保留整体变化趋势，不丢失关键峰谷特征。
2. **优先级 2：拆分多子图（分面）**。把多组数据拆到多个子图，不要全部挤在同一坐标轴；例如 6 个区域拆成 2 行 3 列子图，每个子图画一个对象。
3. **优先级 3：更换图表类型**。
   - 时序多组分堆叠、杂乱柱状图 → 换成 **堆叠面积图**；
   - 多序列曲线缠绕、多条折线 → **分面子图**；
   - 二维大量矩阵数据、密密麻麻曲线 → 替换为 **热力图**；
   - 类别数量巨大的柱状图 → 只保留 **Top-N 关键项**，其余合并为“其他”。
4. **优先级 4：简化图表元素**。精简图例、坐标轴刻度，避免标签重叠；配色选择区分度高的颜色，避免相近色。

### 输出规则

1. 整改完成后输出**优化后的图表**。
2. 附带简短说明：原来是什么问题、做了什么优化、为什么这么改。
3. 禁止只输出原图，必须解决可读性问题。
4. 图表严格符合数学建模论文规范：带标题、坐标轴名称、图例，适合 PDF 导出。

### 兜底

聚合/分面/换型/简化仍放不下时，用**表格替代图**，或用“代表性样本 + 文字说明全貌”；判定没有固定数量阈值，以“读者能否一眼看清趋势和关键结论”为准，看不清就整改。
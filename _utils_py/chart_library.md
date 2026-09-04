# 图表模板库目录（Chart Library）

> **给 AI 的出图前选型索引。写数据图脚本之前，先读本目录，不要一上来就翻 recipe 原文。**
> 本目录只承担「选型」：每一类图一行，含 图名 / 场景 / 适配判定 / 画法出处。
> 确定 1 个最终图型后，再按「画法出处」打开对应 recipe（或 plot\_utils 函数）抄代码、填真实数据。
> 与「查看所有图表」弹窗的 52 类一一对应（示例图见前端弹窗）。

## 画法出处文件名映射（recipe 编号 → 文件）

- `basic#N` → `_utils/figure_recipes_basic.md`

- `competition#N` → `_utils/figure_recipes_competition.md`

- `advanced#N` → `_utils/figure_recipes_advanced.md`

- `empirical#N` → `_utils/figure_recipes_empirical.md`

- `academic#N` → `_utils/figure_recipes_academic.md`

> ⛔ 抄 recipe 代码时：`figsize` 不要照抄原文占位值，按 `_utils/figure_check.sh` / `fig_include_size.py` 的「长宽比档位」换算（单 panel 横图约 6.0in、2×2 近方图约 5.0in，详见 figure\_recipes\_competition.md 开头）。

## 使用方式（强制流程）

1. **Step 1 · 数据判定**：根据手上数据的形态 + 论文要回答的问题，先定「类别」（比较/趋势/分布/相关/组成/专业/示意），见 chart\_select\_guide.md。
2. **Step 2 · 候选 3 个**：只读下面表格中「适配判定」列，从对应类别里选出 3 个图名（不要打开 recipe 原文，节省上下文）。
3. **Step 3 · 终选 1 个**：按 适配度 > 可读性 > 高级感 排序，写一句选择理由，再打开 recipe 出图。

***

## 比较类（多组/多方法数值对比）

| 图名    | 适配判定                    | 画法出处                                      |
| ----- | ----------------------- | ----------------------------------------- |
| 分组柱状图 | 2-5 组方法 × 多指标，要精确数值+误差棒 | recipe basic#1 / plot\_utils.bar\_compare |
| 堆叠柱状图 | 构成占比随时间/条件堆叠，总量+分项      | recipe basic#2                            |
| 发散条形图 | 双向差异（正负两侧对称展示，如盈亏/偏差）   | recipe advanced#20                        |
| 水平条形图 | 类别名长/类目多（≥6 项）排序展示      | plot\_utils（barh）或 basic 风格               |
| 棒棒糖图  | 单指标排名，类别多，要简洁高级感        | recipe advanced#1                         |
| 哑铃图   | 两时点/两方案的前后差异对比          | recipe advanced#2                         |
| 背靠背图  | 两群体同指标镜像对比（如男女/AB）      | recipe advanced#21                        |
| 点误差图  | 多组均值+置信区间，组少（≤6）数据点精确   | recipe advanced#13                        |
| 配对点图  | 同一对象前后配对变化（个体连线）        | recipe advanced#22                        |

## 趋势类（随指标连续变化）

| 图名         | 适配判定                      | 画法出处                               |
| ---------- | ------------------------- | ---------------------------------- |
| 折线图·置信带    | 时间/迭代序列，多序列对比+误差带         | recipe basic#3                     |
| 面积图        | 单/少数序列累积量或总量变化            | recipe basic#8                     |
| 双轴图        | 两组量纲不同但相关的指标（如成本×收益）      | recipe basic#10                    |
| 斜率图        | 两时点排序变化，强调"谁升谁降"          | recipe advanced#3                  |
| 瀑布图        | 增量分解（基数→各贡献→终值）           | recipe advanced#6 / competition#20 |
| 帕累托图       | 找"少数关键"（累计 80% 分界）        | recipe basic#9                     |
| 扇形预测图      | 历史+未来预测带（多层 CI 扇面）        | recipe advanced#27                 |
| 排名轨迹图      | 多对象排名随时间的变化（排名轴）          | recipe advanced#4                  |
| 流图         | 多类别占比随时间堆叠流动              | recipe advanced#33                 |
| CUSUM 累积和图 | 过程是否发生漂移/突变点（累计偏差监测）      | recipe advanced#37                 |
| 分位数趋势带     | 多次运行均值±Q1/Q3 平滑带（复现性/鲁棒性） | recipe advanced#38                 |

## 分布类（数值分布的形态对比）

| 图名     | 适配判定              | 画法出处                           |
| ------ | ----------------- | ------------------------------ |
| 箱线图    | 多组分布对比+异常点，样本量大   | recipe basic#7（含箱线组件）          |
| 小提琴图   | 多组分布形状+m（看密度形态）   | recipe basic#11                |
| 分组小提琴图 | 双因素分组分布（2 组×多个条件） | recipe advanced#24             |
| 直方图    | 单变量分布，观察偏态/峰态     | plot\_utils.distribution\_plot |
| 密度曲线   | 连续分布对比，平滑形态       | plot\_utils（kdeplot）           |
| 山脊图    | 多组分布沿轴堆叠，类目多      | recipe advanced#23             |
| 雨云图    | 分布+散点+箱线三合一，信息最全  | recipe basic#7 / basic#11      |
| 后验轨迹图  | 贝叶斯 MCMC 链+后验密度   | recipe advanced#32             |

## 相关 / 回归类（两两关系）

| 图名           | 适配判定             | 画法出处                                       |
| ------------ | ---------------- | ------------------------------------------ |
| 散点图·回归       | 两连续变量关系+拟合线+r²   | recipe basic#4 / plot\_utils.scatter\_plot |
| 散点矩阵         | 多变量两两关系总览（≤6 变量） | recipe advanced#30                         |
| 二维密度图        | 散点过密遮挡时用密度着色     | recipe advanced#34 / competition#25        |
| Bland-Altman | 两测量方法一致性检验       | recipe advanced#8                          |
| 校准图          | 预测概率 vs 实际频率可靠性  | recipe advanced#11                         |
| 热力图·相关矩阵     | 多变量相关矩阵，数值标注+下三角 | recipe basic#5 / competition#12            |
| 聚类热力图        | 变量/样本聚类+热力（行序重排） | recipe advanced#14                         |
| 网络图          | 节点-边关系/图论问题      | recipe advanced#15                         |

## 组成 / 多维类

| 图名      | 适配判定                   | 画法出处                  |
| ------- | ---------------------- | --------------------- |
| 环形饼图    | 部分占整体，类别 ≤6            | recipe basic#6        |
| 雷达图     | 多维度综合评估（性能/能力画像）       | recipe competition#5  |
| 平行坐标    | 多维特征对比（高维数据寻找 pattern） | recipe advanced#17    |
| 等高线图    | 双参数搜索/目标函数地形           | recipe competition#14 |
| 三维曲面图   | 三维地形展示（投影型优先，防遮挡）      | recipe competition#6  |
| 桑基图     | 能量/流量转移分配（用量要克制）       | recipe advanced#5     |
| 泰勒图     | 多模型多指标综合评估（相关系数+标准差）   | recipe advanced#19    |
| PCA 双标图 | 降维后样本+载荷（机器学习赛题）       | recipe advanced#18    |

## 专业 / 高级类

| 图名           | 适配判定                    | 画法出处                                        |
| ------------ | ----------------------- | ------------------------------------------- |
| 生存曲线         | 医学/可靠性：生存概率随时间          | recipe advanced#9                           |
| 漏斗图          | Meta 分析出版偏倚             | recipe advanced#12                          |
| 日历热力图        | 时间密度（每日/每周活动量）          | recipe advanced#28                          |
| 性能剖面图        | 优化算法多问题性能对比（Dolan-Moré） | recipe advanced#25                          |
| 火山图          | 生物差异表达（fold-change×p 值） | recipe advanced#10                          |
| Hovmöller 图  | 时空二维（时间×空间）             | recipe advanced#29                          |
| ICE/PDP 图    | 机器学习特征效应分析              | recipe advanced#26                          |
| 组合子图         | 多 panel 统一叙事（2×2 等）     | recipe basic#12 / plot\_utils.subplot\_grid |
| Tornado 灵敏度图 | 参数扰动对结果影响的排序条形（±%）      | recipe advanced#44                          |
| 甘特图          | 调度/排产/任务时间线（含关键路径高亮）    | recipe advanced#45                          |
| 相平面图         | 微分方程动力学：相轨迹/等倾线/平衡点     | recipe advanced#46                          |
| 参数扫描热力图      | 双参数网格下结果值着色（灵敏度扫描）      | recipe advanced#47                          |
| 轨迹/OD 流向图    | 空间轨迹/起讫流向（经纬度连线+箭头）     | recipe advanced#48                          |

## 流程 / 架构图（示意，非数据图）

| 图名        | 适配判定                       | 画法出处                                     |
| --------- | -------------------------- | ---------------------------------------- |
| 流程图（HTML） | 技术路线/流程/架构示意（默认引擎，自动布局防重叠） | skills/paper-figure-html                 |
| 时序图       | 系统/协议交互（消息往来按时间轴）          | skills/paper-figure-html（模板 advanced#49） |
| 状态机图      | 状态转移/生命周期（状态+事件+转移条件）      | skills/paper-figure-html（模板 advanced#50） |
| 泳道图       | 跨部门/跨角色流程（职责分泳道）           | skills/paper-figure-html（模板 advanced#51） |
| 指标体系树     | AHP 层次/指标体系/组织树（自上而下的树）    | skills/paper-figure-html（模板 advanced#52） |

***

## 兜底规则

- 上表没有覆盖的图型 → 用 raw matplotlib/seaborn 直接画（SKILL 已允许），但每个脚本仍必须 `setup_style()` + 数据来自产物 JSON。

- plot\_utils 现成函数优先：`bar_compare / heatmap / forest_plot / trend_plot / scatter_plot / distribution_plot / multi_line_plot / box_plot / radar_plot / subplot_grid`。

- 同一类数据只画 1 张，不要把「候选 3 个」全部画出来。

<br />

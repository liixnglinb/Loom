# 数学模型目录 (model_catalog)

> 常用数学建模方法的候选目录，按问题类型组织。它用于扩大候选集，不根据题目关键词自动选型。每个候选仍需检查输出形式、数据条件、假设、约束、计算预算和验证方法。

---

## 模型选择规则

1. 在达到题目求解目标、满足精度与约束条件的前提下，优先选用原理简单、易于解释的模型，拒绝无意义堆砌复杂高级算法。
2. 若问题本身属于高复杂度场景（多目标优化、非线性预测、多维时序等），允许使用复杂度更高的模型；必须写明为什么简单模型不适用，说明选用复杂模型的理由。
3. 输出时，至少对比 2 套候选模型：简单方案 + 最终选用方案，简要对比两者优缺点，解释最终取舍原因。

> 补充：处理大规模问题、大量子问题或高维决策空间时，优先采用精确求解器、高效启发式、分解或降维等计算代价可控的方法，避免硬上重型分布式模拟（如大规模 ABM）；任何方法都要在比赛时间预算内可完成求解。

## 0. 问题类型 → 候选模型族（stage 3 生成候选时参考）

| 题目特征 | 可检查的候选模型族 |
|---------|----------|
| "求最优..." / "如何分配..." / "在约束下使...最大" | **优化类** (LP/IP/NLP/启发式) |
| "预测..." / "未来..." / "时间序列" | **预测类** (回归/ARIMA/灰色/LSTM) |
| "评价..." / "排名..." / "综合得分" | **评价类** (AHP/TOPSIS/熵权/CRITIC/DEA/灰色关联/VIKOR/模糊) |
| "判断..." / "归类..." / "识别..." / "推荐..." | **分类类** (Logistic/SVM/决策树/NN/判别分析/DBSCAN/关联规则) |
| "模拟..." / "如果...会怎样" / "随机..." / "排队..." | **仿真类** (蒙特卡罗/系统动力学/ABM/排队论) |
| "网络中..." / "路径..." / "流量..." | **图论类** (最短路/最大流/最小生成树) |
| "概率..." / "分布..." / "假设检验" / "插值..." | **统计类** (描述统计/检验/方差分析/插值与拟合) |
| "动态..." / "随时间..." | **动力系统类** (ODE/PDE/差分方程) |

---

## 1. 优化类 (Optimization)

> **代码**: `templates/shared/code_starter/optimization.py`（LP/MILP/凸优化/多目标/GA/贪心基线）；MATLAB: `templates/shared/code_starter/matlab_optimization.m`

### 1.1 线性规划 LP
- **适用**: 目标 + 约束都线性
- **Python**: `scipy.optimize.linprog`, `cvxpy`, `pulp`
- **变体名**: "考虑动态权重的多目标线性规划", "鲁棒线性规划"
- **示例场景**: 调度、配送、资源分配；是否适用取决于线性关系与约束表达

### 1.2 整数规划 IP / 0-1 规划
- **适用**: 决策变量取整数 / 0-1
- **Python**: `cvxpy + GUROBI/CBC`, `pulp`
- **变体名**: "基于分支定界的混合整数规划", "Lagrangian 松弛 IP"
- **示例场景**: 选址、路径、组合；需核对整数变量规模与可用求解器

### 1.3 非线性规划 NLP
- **适用**: 目标或约束含非线性
- **Python**: `scipy.optimize.minimize` (SLSQP, trust-constr), `cvxpy` (DCP)
- **变体名**: "凸近似 NLP", "二阶锥规划 SOCP"

### 1.4 多目标规划
- **适用**: 多个相互冲突目标
- **方法**: 加权法 / ε-约束法 / NSGA-II
- **Python**: `pymoo`, `deap`
- **变体名**: "基于熵权的多目标规划", "Pareto-NSGA-II"
- **选型提醒**: 目标之间需存在真实权衡，并说明权重或 Pareto 方案的决策依据

### 1.5 动态规划 DP
- **适用**: 阶段决策、最优子结构
- **Python**: 自实现 (numpy + memoization)
- **变体名**: "状态压缩动态规划", "近似动态规划 ADP"

### 1.6 启发式算法
- **遗传算法 GA**: `deap`, `pygad` — "自适应交叉率 GA"
- **粒子群 PSO**: `pyswarms` — "改进惯性权重 PSO"
- **模拟退火 SA**: 自实现 — "自适应温度 SA"
- **蚁群 ACO**: 自实现 — "信息素改进 ACO"
- **示例场景**: 大规模组合优化、多峰目标；需报告停止条件、随机种子和与可解释基线的比较

### 1.7 鲁棒优化 / 随机规划
- **适用**: 参数不确定
- **Python**: `cvxpy` (robust constraints), `Pyomo`
- **变体名**: "基于场景的随机规划", "Wasserstein 鲁棒优化"
- **选型提醒**: 只有不确定性集合、概率或场景来源有依据时，才使用鲁棒优化或随机规划

---

## 2. 预测类 (Prediction)

> **代码**: `templates/shared/code_starter/prediction.py`（回归/ARIMA/灰色/组合预测）

### 2.1 回归
- 线性: `sklearn.linear_model.LinearRegression`
- 多项式: `PolynomialFeatures + LinearRegression`
- 岭回归 / Lasso: `Ridge`, `Lasso`
- **变体名**: "弹性网回归", "贝叶斯线性回归"

### 2.2 时间序列经典
- ARIMA: `statsmodels.tsa.arima.model.ARIMA`
- SARIMA: 季节性 ARIMA
- 指数平滑 (Holt-Winters): `statsmodels.tsa.holtwinters`
- **变体名**: "差分整合移动平均自回归模型 (ARIMA)", "Holt-Winters 三参数指数平滑"

### 2.3 灰色预测
- GM(1,1): 自实现；可作为小样本、近指数趋势数据的候选，需先检验适用条件并做留出验证
- **变体名**: "残差修正 GM(1,1)", "GM(1,N) 多变量灰色模型"
- **验证提醒**: 用滚动或留出验证与合适基线比较，不因组合方法名称而默认更优

### 2.4 机器学习预测
- 随机森林: `sklearn.ensemble.RandomForestRegressor`
- XGBoost: `xgboost`
- LSTM: `tensorflow.keras` / `torch`
- **变体名**: "改进 LSTM-Attention 时序预测", "XGBoost-LightGBM Stacking"

### 2.5 组合预测
- **核心思想**: 多模型加权 (权重由误差倒数 / 熵权 / AHP 给出)
- **变体名**: "基于熵权的 ARIMA-LSTM 组合预测"
- **选型提醒**: 组合模型只在子模型误差具有互补性且留出集结果支持时采用，并报告权重与消融结果

### 2.6 Prophet
- **核心**: Facebook 开源的加性模型，自动处理趋势、季节性与节假日效应
- **Python**: `prophet`
- **变体名**: "多季节 Prophet", "Prophet 外生回归"
- **选型提醒**: 适合强季节性 + 节假日 + 较长历史的时序；小样本/无明显季节时未必优于 ARIMA，需留出验证比较

---

## 3. 评价类 (Evaluation)

> **代码**: `templates/shared/code_starter/evaluation.py`（AHP/熵权/TOPSIS/模糊/组合评价）

### 3.1 层次分析 AHP
- **核心**: 主观赋权,构造判断矩阵
- **Python**: 自实现 (numpy: 几何平均 + 一致性检验)
- **变体名**: "群决策 AHP", "动态权重 AHP"
- **选型提醒**: AHP 适合有明确层级与可解释判断来源的场景；主观判断矩阵需做一致性和敏感性检查，不要求与其他方法拼接

### 3.2 熵权法
- **核心**: 客观赋权,基于指标方差
- **Python**: 自实现 (numpy)
- **变体名**: "改进熵权法 (考虑指标相关性)"

### 3.3 TOPSIS
- **核心**: 与正负理想解的距离
- **Python**: 自实现
- **变体名**: "灰色关联 TOPSIS", "熵权 TOPSIS"
- **组合提醒**: 若与 AHP 或熵权组合，需解释各权重来源、冲突处理和组合相对单一方法的实际作用

### 3.4 模糊综合评价
- **适用**: 评价对象边界模糊
- **Python**: 自实现 (隶属函数 + 模糊矩阵)
- **变体名**: "二级模糊综合评价"

### 3.5 数据包络分析 DEA
- **核心**: 多投入多产出相对效率评价 (CCR/BCC 模型)
- **Python**: 自实现 (线性规划对偶，`scipy.optimize.linprog`) 或 `pydea`
- **变体名**: "超效率 DEA", "三阶段 DEA", "SBM 模型"
- **选型提醒**: 评价对象为"决策单元 DMU"，指标为投入/产出；需注意 DMU 数量与指标数量比、规模报酬假设，避免与 AHP/TOPSIS 拼凑无实际作用

### 3.6 CRITIC 权重法
- **核心**: 客观赋权，综合指标变异性与冲突性
- **Python**: 自实现 (numpy: 标准差 + 相关系数)
- **变体名**: "改进 CRITIC (考虑指标间相关性)"
- **选型提醒**: 与熵权法一样属客观赋权，但基于对比强度与冲突性；与熵权/ AHP 组合时需说明各权重作用

### 3.7 灰色关联分析 (GRA)
- **核心**: 序列间几何接近程度 (关联系数)
- **Python**: 自实现 (numpy)
- **变体名**: "加权灰色关联分析", "动态灰色关联"
- **选型提醒**: 区别于灰色预测 GM(1,1)；用于因素分析/评价排序，常与熵权或 AHP 组合，需说明分辨系数 ρ 与序列初值化方式

### 3.8 VIKOR
- **核心**: 与正负理想解距离 + 群体效用/个体遗憾折中
- **Python**: 自实现 (numpy)
- **变体名**: "改进 VIKOR", "直觉模糊 VIKOR"
- **选型提醒**: 与 TOPSIS 同属"理想解距离"族但引入折中系数 v；需说明 v 的取值依据并与 TOPSIS 结果对比验证

### 3.9 主成分分析 PCA
- **Python**: `sklearn.decomposition.PCA`
- **作用**: 降维 / 因子提取
- **变体名**: "鲁棒 PCA", "稀疏 PCA"

### 3.10 因子分析 / 聚类评价
- **Python**: `sklearn.cluster.KMeans`, `factor_analyzer`
- **变体名**: "基于 K-Means++ 的聚类评价"

---

## 4. 分类类 (Classification)

> **代码**: `templates/shared/code_starter/classification.py`（Logistic/SVM/树/集成/Stacking/不平衡处理）

### 4.1 Logistic 回归
- **Python**: `sklearn.linear_model.LogisticRegression`
- **变体名**: "L1 正则化 Logistic", "多项 Logit"

### 4.2 支持向量机 SVM
- **Python**: `sklearn.svm.SVC`
- **变体名**: "RBF 核 SVM", "多分类 OVR-SVM"

### 4.3 决策树 / 随机森林 / GBDT
- **Python**: `sklearn.tree`, `sklearn.ensemble`, `xgboost`, `lightgbm`
- **变体名**: "代价敏感随机森林"

### 4.4 神经网络
- **Python**: `tensorflow.keras`, `torch`
- **变体名**: "ResNet 改进结构", "BP-Adam 反向传播"

### 4.5 朴素贝叶斯 / KNN
- **Python**: `sklearn.naive_bayes`, `sklearn.neighbors`
- 简单但 sanity check 用得上

### 4.6 判别分析
- **核心**: Fisher 线性判别 LDA / 二次判别 QDA，用投影最大类间距离分类
- **Python**: `sklearn.discriminant_analysis`
- **变体名**: "Fisher 判别", "逐步判别分析"
- **选型提醒**: 经典统计判别，可与 SVM/随机森林并列做多分类器对比；对高维光谱/指标数据常先 PCA 再判别

### 4.7 密度聚类 DBSCAN / 层次聚类
- **核心**: DBSCAN 基于密度邻域聚类、可识别噪声；层次聚类生成树状层级
- **Python**: `sklearn.cluster.DBSCAN`, `sklearn.cluster.AgglomerativeClustering`
- **变体名**: "自适应邻域 DBSCAN", "Ward 层次聚类"
- **选型提醒**: 与 K-means 对比选优；DBSCAN 需调 eps/min_samples，层次聚类需确定截断层级；同用于异常识别与形状不规则簇

### 4.8 关联规则
- **核心**: Apriori / FP-Growth 挖掘频繁项集与关联规则
- **Python**: `mlxtend.frequent_patterns`
- **变体名**: "FP-Growth 关联规则", "加权关联规则"
- **选型提醒**: 面向事务/共现数据；关注支持度、置信度、提升度；与相关性分析互补用于变量共现规律挖掘

---

## 5. 仿真类 (Simulation)

> **代码**: `templates/shared/code_starter/simulation.py`（蒙特卡罗/LHS/Sobol/ODE-SEIR/灵敏度）

### 5.1 蒙特卡罗 MC
- **核心**: 大量随机采样估计
- **Python**: `numpy.random` + `scipy.stats`
- **变体名**: "拉丁超立方蒙特卡罗", "马尔可夫链 MCMC"
- **选型提醒**: 可用于不确定性传播或仿真估计；采样分布、样本量和收敛诊断需要依据

### 5.2 系统动力学 SD
- **适用**: 反馈、库存、流速
- **Python**: 自实现 (ODE) 或 Vensim
- **变体名**: "因果回路图 + 库存流图 SD 模型"

### 5.3 元胞自动机 CA
- **适用**: 空间扩散、交通流
- **Python**: 自实现 (numpy 数组迭代)
- **变体名**: "Nagel-Schreckenberg 交通流 CA"

### 5.4 Agent-Based Modeling ABM
- **Python**: `mesa`
- **变体名**: "基于学习智能体的 ABM"
- **适用范围**: 仅用于涌现/个体交互类问题且规模可控（通常千级以内）时；大规模问题优先用优化/解析/分解方法，避免硬上 ABM 分布式模拟（见"选型总原则"）

### 5.5 离散事件仿真 DES
- **Python**: `simpy`
- **变体名**: "基于排队论的 DES"

### 5.6 排队论 (Queuing)
- **核心**: M/M/1、M/M/c 等到达-服务过程稳态指标
- **Python**: 自实现 (出生-死亡过程) 或 `queueing-tool`
- **变体名**: "多服务台排队 M/M/c", "有限队长 M/M/1/K"
- **选型提醒**: 面向顾客到达/服务/等待场景（挂号、窗口、调度）；需说明到达与服务分布假设；可与 DES 仿真互证稳态公式

---

## 6. 图论类 (Graph)

> **代码**: `templates/shared/code_starter/graph.py`（最短路/最大流/最小费用流/MST/中心性/TSP）

### 6.1 最短路
- Dijkstra / Floyd / A*
- **Python**: `networkx.shortest_path`

### 6.2 最大流 / 最小费用流
- **Python**: `networkx.maximum_flow`, `networkx.min_cost_flow`

### 6.3 最小生成树 MST
- Kruskal / Prim
- **Python**: `networkx.minimum_spanning_tree`

### 6.4 网络中心性 / 社团检测
- PageRank / Betweenness
- **Python**: `networkx.pagerank`, `community-louvain`

### 6.5 旅行商 TSP / VRP
- **Python**: `networkx.approximation.traveling_salesman`, `OR-Tools`
- **变体名**: "考虑时间窗的 VRPTW", "蚁群 VRP"

---

## 7. 统计类 (Statistics)

> **代码**: `templates/shared/code_starter/stats_analysis.py`（描述统计/检验/ANOVA/相关/分布拟合/插值拟合）

### 7.1 描述性统计
- 均值、方差、偏度、峰度、相关性
- **Python**: `pandas.describe`, `scipy.stats`

### 7.2 假设检验
- t 检验 / χ² / F 检验 / 秩和
- **Python**: `scipy.stats.ttest_*`, `chisquare`

### 7.3 方差分析 ANOVA
- 单因素 / 双因素 / 协方差
- **Python**: `scipy.stats.f_oneway`, `statsmodels.stats.anova`

### 7.4 相关与回归
- Pearson / Spearman / Kendall
- **Python**: `scipy.stats.pearsonr`

### 7.5 分布拟合
- 用 KS 检验拟合优度
- **Python**: `scipy.stats.kstest`, `fitter`

### 7.6 插值与拟合
- **插值**: 拉格朗日 / 牛顿 / 三次样条 — `scipy.interpolate`, `scipy.interpolate.CubicSpline`
- **拟合**: 多项式 / 最小二乘 / 曲线拟合 — `numpy.polyfit`, `scipy.optimize.curve_fit`
- **变体名**: "三次样条插值", "最小二乘多项式拟合", "分段线性插值"
- **选型提醒**: 插值过数据点、拟合逼近趋势；噪声大用拟合、要求精确过点用插值；需说明光滑度与过拟合取舍

---

## 8. 动力系统类

> **代码**: `templates/shared/code_starter/dynamical.py`（ODE 求解/解析数值互证/参数优化/差分方程）；MATLAB: `templates/shared/code_starter/matlab_ode.m`

### 8.1 常微分方程 ODE
- **Python**: `scipy.integrate.solve_ivp`
- 经典: SIR/SEIR (传染病)、Lotka-Volterra (生态)
- **变体名**: "改进 SEIR 含潜伏期与隔离", "随机 SDE"

### 8.2 偏微分方程 PDE
- **Python**: `fipy`, `fenics`, 自实现有限差分
- **选型提醒**: 热扩散、流体等机理问题可能需要 PDE；应先确认边界条件、离散误差和计算资源

### 8.3 差分方程
- 自实现迭代

---

## 9. 信号处理 / 时频分析

> **代码**: `templates/shared/code_starter/signal_analysis.py`（FFT/小波去噪/压缩感知）

### 9.1 傅里叶变换 FFT
- **Python**: `numpy.fft`, `scipy.fft`

### 9.2 小波分析
- **Python**: `pywt`

### 9.3 压缩感知 (Compressed Sensing)
- **核心**: 欠采样下利用稀疏性重构信号 (OMP / LASSO / 基追踪)
- **Python**: `sklearn.linear_model.OrthogonalMatchingPursuit`, `numpy.linalg.lstsq`, `picos` (基追踪)
- **变体名**: "OMP 稀疏重构", "LASSO 压缩感知"
- **选型提醒**: 面向高维/欠采样信号恢复与超分辨定位类问题；需满足稀疏性与不相干条件，并报告重构误差与观测数-稀疏度比

---

## 10. 决策类

> **代码**: `templates/shared/code_starter/decision.py`（纳什均衡/期望效用/MDP 值迭代/Stackelberg）

### 10.1 博弈论
- 纳什均衡: `nashpy`
- 多人合作博弈
- **变体名**: "Stackelberg 博弈"

### 10.2 决策树 (决策分析,非 ML)
- 期望效用 / 风险敏感

### 10.3 马尔可夫决策过程 MDP
- **Python**: `mdptoolbox`
- 强化学习: `stable-baselines3`

---

## 模型组合候选（仅在机制互补且验证支持时使用）

下面的组合不是加分公式。每个连接号都意味着额外假设、接口和验证成本；组合模型是否选用，应按「模型选择规则」对比简单方案与组合方案的优缺点，并写明取舍理由。

```
评价类: AHP + 熵权 + TOPSIS = "AHP-熵权-TOPSIS 综合评价"
预测类: ARIMA + 灰色 + LSTM = "ARIMA-GM-LSTM 组合预测"
优化类: 启发式 + 鲁棒 = "鲁棒-NSGA-II 多目标优化"
分类类: Stacking 集成 = "RF-XGBoost-LightGBM Stacking 分类"
仿真类: 蒙特卡罗 + 灵敏度 = "LHS-蒙特卡罗稳健性仿真"
```

---

## stage 3 选型 checklist

对进入决策矩阵的候选记录:
- [ ] 来自哪个族 (1-10)
- [ ] 与题目输出、数据、约束和评价指标的对应关系
- [ ] 关键假设及其证据或可检验方式
- [ ] Python 实现路径 (库/自实现)
- [ ] 规模、复杂度、求解器与比赛时间预算
- [ ] 验证计划、基线和失败条件
- [ ] 不选候选及不选理由

候选数量和差异程度由实际决策不确定性决定。存在方法权衡时，应比较假设或求解机制不同的候选；没有合理替代方案时，不为凑数引入不适用模型。

---

## §11 历年类比的使用边界

仓库曾收集 91 份来源文档，但当前不随仓库分发 PDF；分位统计只来自 59 份可提取文本，且以 2023 年样本为主、另含 1 份 2025 年文本，没有可用于统计的 2024 年文本。因而不能从这批材料推出“某年份某题应使用某模型”的稳定映射。

使用历年题时应遵循以下证据链:

1. 先读取当届题面，写明输出、数据、约束和评价指标。
2. 若引用历年题作类比，保存可访问来源并指出相同与不同条件。
3. 从本目录生成候选族后，用当前数据做最小可运行验证和基线比较。
4. 只有模型机制、输入条件和验证结果都支持时，才保留该类比；题目动词相似本身不是选型证据。

# 代码书写规范（CODE_STYLE）

> 本规范约束 mathmodel-skill 生成的所有求解代码，直接映射 50 篇获奖论文的代码书写习惯：正文不贴源码、程序放附录、结果外置文件、求解按 Step 组织。所有 code_starter 与自动生成的求解脚本必须遵循本规范。

## 1. 通用规范（所有代码）

### 1.1 文件头
每个脚本以中文 docstring 开头，说明：适用场景、对应论文章节、国赛常见模型、命名变体建议。示例：

```python
"""
优化类 code starter — 对应论文 §5.x 求解算法
适用: 线性规划 (LP) / 整数规划 (IP/MILP) / 二次规划 (QP) / 凸优化

库依赖:
- cvxpy (DSL, 自动选择 solver)
- scipy.optimize (轻量级)
- pulp (MILP 备选)

国赛常见用法: 调度、配比、选址、组合优化
"""
```

### 1.2 固定骨架（每个脚本必须包含，顺序一致）
```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ---- 全局可复现性 ----
np.random.seed(42)

# ---- 中文字体（避免论文图中文乱码）----
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ---- 输出目录自动创建 ----
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)
```

### 1.3 函数组织
- 每个模型一个独立函数，函数名小写下划线；
- **docstring 克制**：只给复杂接口函数写 `Args/Returns`，简单小函数写一行 `# 说明` 即可（见 §5.7，避免 AI 味）；
- **区分两类函数**：纯计算/库函数（如 `ahp_weights`、`gm11`）内部不 `print`、只 `return` 结构化结果（含 status / 关键指标 / 结果数组）；流程函数与主流程按 §5.4 的进度契约 `print` 开始/完成；
- 按 `# ==== 区块标题 ====` 分隔功能区块；
- 主流程放 `if __name__ == "__main__":` 中，模拟示例数据（注明"实际从附件读"），跑通并打印结果、保存图。

### 1.4 结果与图表落盘
- 数值结果保存到 `results/`（npy / csv / xlsx）；
- 图表保存到 `figures/`（dpi=300）；
- 对应论文"结果外置附件 result*.xlsx"的习惯：可运行脚本支持 `--out result1.xlsx` 类输出。

### 1.5 语言与注释
- 注释、docstring、输出提示**一律中文**；
- 英文缩写首次出现给出完整形式（对应 winning_patterns §11）；
- 只在逻辑不自明处加注释，不逐行注释。

### 1.6 检验与稳健
- 防御性校验**克制**：只在真正由外部输入触发、且会静默产生错误结果的边界做校验（除零、空集、外部数据缺失、量纲不一致），不要满屏 `raise ValueError`（见 §5.5 的"AI 味"说明）；
- 每个模型至少提供 sanity check 或与基线对比（对应论文"多方法交叉验证"）；
- 随机算法报告停止条件、随机种子、与可解释基线的比较。

## 2. 按题型/模型类别的代码规范

### 2.1 机理仿真类（A 题）→ MATLAB 优先
- 用 `matlab -batch "run('xxx.m')"` 自动调用（matlab 需在 PATH；或用环境变量 `MATLAB` 指定完整路径）
- 脚本结构：`%% 参数定义 → %% 机理方程（ode45/solve_ivp）→ %% 数值求解 → %% 结果可视化`；
- 优先 MATLAB：`ode45`（微分方程）、`fmincon`（非线性优化）、`linprog/intlinprog`（LP/IP）、`trapz`（数值积分）、`fit/polyfit`（拟合）；
- 结果用 `writematrix / writetable` 输出到 `result*.xlsx`，图用 `saveas/figure` 存 PNG；
- 提供解析解 + 数值解互证（对应获奖论文"解析+数值双轮驱动"）。

### 2.2 优化调度类（B 题及部分 C 题）→ Python 优先
- 精确求解（小规模）：`cvxpy`（LP/QP/SOCP）、`pulp`（MILP）、`scipy.optimize`（NLP/全局）；
- 启发式（大规模）：`deap`/`pygad`（GA）、`pyswarms`（PSO）、自实现模拟退火、贪心基线；
- 必须报告：决策变量定义 → 目标函数 → 约束 → 模型汇总（对应论文三段式）；
- 必备：与贪心/精确小例基线对比 + 收敛性（历史曲线）。

### 2.3 数据统计类（C/E 题）→ Python 优先
- 处理：`pandas`（清洗/聚合/透视）、`scipy.stats`（检验/分布/相关）；
- 时序：`statsmodels`（ARIMA/SARIMA/平稳性）、自实现灰色 GM(1,1)、`prophet`（季节）；
- ML：`sklearn`（回归/分类/聚类/降维）、`xgboost/lightgbm`、`tensorflow/torch`（LSTM）；
- 必备：交叉验证 + 指标（R²/MAE/RMSE/AUC/F1）+ 显著性检验（p 值）；
- 数据预处理必须独立成函数（缺失/异常/标准化/编码）。

### 2.4 综合评价类（D/F 题）→ Python 优先
- 全部自实现 numpy：AHP（一致性检验）、熵权、CRITIC、TOPSIS、VIKOR、灰色关联、DEA（linprog 对偶）、模糊综合评价；
- 必备：指标正负向性处理、权重来源说明、排序稳定性检验（扰动权重看排序是否变）。

### 2.5 仿真/灵敏度（跨题型）→ Python 优先
- 蒙特卡罗 / LHS / Sobol：`numpy` + `scipy.stats.qmc` + `SALib`；
- ODE 系统：`scipy.integrate.solve_ivp`；
- 必备：扰动方式 → 结果趋势 → 稳健结论三段式（对应论文灵敏度写法）。

### 2.6 图论/网络（网络流、路径）→ Python 优先
- `networkx`：最短路（Dijkstra/Floyd）、最大流/最小费用流、MST、中心性、社团检测；
- TSP/VRP：`OR-Tools` 或 `networkx.approximation`；
- 必备：图可视化 + 路径/流结果表。

### 2.7 决策类 → Python 优先
- 博弈：`nashpy`；MDP：`mdptoolbox`；决策树分析：自实现期望效用；
- 强化学习：`stable-baselines3`（仅高维策略问题）；
- 必备：策略结果表 + 参数敏感性。

## 3. 自动调用协议

### 3.1 Python
```powershell
# 运行 code_starter 或生成的求解脚本（推荐用 run_starter.py 统一调度, 或直接当前解释器）
python <script>.py [--in <data>] [--out <result>]
```

### 3.2 MATLAB
```powershell
# 批处理调用（matlab 需在 PATH, 或用环境变量 MATLAB 指定完整路径）
matlab -batch "run('<script>.m')"
```

### 3.3 命名与索引
- code_starter 按模型族命名：`optimization.py / prediction.py / evaluation.py / classification.py / simulation.py / graph.py / stats_analysis.py / dynamical.py / signal_analysis.py / decision.py`；
- 注意：文件名**不得**与 Python 标准库同名（`statistics.py`、`signal.py` 会遮蔽标准库，导致 seaborn/matplotlib 导入失败），已分别命名为 `stats_analysis.py`、`signal_analysis.py`；
- MATLAB 脚本：`matlab_ode.m / matlab_optimization.m / matlab_prediction.m / matlab_evaluation.m / matlab_classification.m / matlab_simulation.m / matlab_graph.m / matlab_stats.m / matlab_signal.m / matlab_decision.m`；
- 每个模型族在 `model_catalog.md` 的条目中用 `**代码**: <code_starter 路径>` 索引，供 stage 3/5 自动定位与调用。

## 4. 论文公式撰写规范（纯 LaTeX 精细排版）

> 采用纯 LaTeX 精细排版（`.tex` 直接写公式，弃用 Markdown `$$`）。国赛获奖论文约 90%、美赛几乎 100% 用 LaTeX 排版。本 skill 直接用 `templates/latex/<comp>/main.tex` 与各 `sections/*.tex`，公式写成标准 LaTeX 源码，用 `equation`/`align` 环境 + `\label`/`\eqref` 交叉引用，实现编号、对齐、引用全自动。

### 4.1 公式环境选择（按语义选，精细排版铁律）

| 场景 | 环境 | 是否编号 | 写法示例 |
|---|---|---|---|
| 行内公式 | `$...$` | 否 | `设 $x_i$ 为第 $i$ 个变量` |
| 单行非编号公式 | `\[...\]` | 否 | `\[ x^2 \]` |
| 单行编号公式 | `equation` | 是 | `\begin{equation} E=mc^2 \end{equation}` |
| 多行对齐公式（推荐） | `align`（`&` 放等号前，`\\` 分行） | 是 | `\begin{align} a^2+b^2 &= c^2 \\ x+y &= z \end{align}` |
| 多行居中 | `gather` | 是 | `\begin{gather} ... \end{gather}` |
| 长公式换行（整体一个编号） | `multline` 或 `split` 外包 `equation` | 是 | `equation` 内嵌 `split` |
| 分段函数/方程组 | `cases` | 否 | `\begin{cases} ... \end{cases}` |
| 矩阵/行列式 | `matrix`/`bmatrix` | 否 | 嵌在 `equation`/`align` 内 |

### 4.2 铁律（精细排版必须遵守）
1. **必须加载 `amsmath,amssymb,amsthm`**（`align`/`gather`/`cases`/`split` 都在 amsmath；模板 main.tex 已预载）。
2. **非编号公式用 `\[...\]`**，禁止 `$$...$$`（在 amsmath 下编号与间距会出错）。
3. **多行用 `align` 而非 `eqnarray`**（老环境间距差、已被淘汰）。
4. **对齐点 `&` 放关系符前**：写 `x &= y`，不写 `x =& y`。
5. **环境内不空行**（`align`/`gather` 内部空行会报 `Paragraph ended` 错误）。
6. **多行环境末行不加 `\\`**（会多出垂直空隙）。
7. **每个需引用的公式加 `\label{eq:xxx}`**，正文用 `\eqref{eq:xxx}` 交叉引用（自动编号，不手写 (1)(2)）。
8. **编号控制**：某行不需编号用 `\notag`/`\nonumber`；自制标签用 `\tag{...}`。
9. **建议加 `cleveref`/`\cref`**（可选）生成"式 (3)""图 2"等智能引用，减少手写措辞。
10. 中文公式语境：主公式用 `equation`/`align`，推导步骤用 `align`，定义符号用行内 `$ $`。

### 4.3 编号、对齐与引用（精细排版收益点）
- **编号**：全自动，`\begin{equation}` 每环境一个号；`align` 每行一号，用 `\notag` 去多余号；
- **对齐**：`align` 的 `&` 让等号列对齐，长公式用 `split` 断行不对齐；
- **引用**：`\label{eq:xxx}` + `\eqref{eq:xxx}`，改公式顺序后编号自动更新，正文引用不失效；
- **交叉制度**：公式/图/表统一 `\ref`/`\eqref`，全文一致。

### 4.4 工具分工（结论）
- **LaTeX**：终稿唯一排版方式（国赛得奖主流程），公式编号/对齐/交叉引用全自动；
- **Word/WPS + MathType/AxMath**：仅当最终必须交 Word 版时，用 Word 内置 `Alt+=` 或 MathType 粘贴 LaTeX 转换；
- **在线 LaTeX 辅助**：CodeCogs（latex 转图片预览）、Mathpix Snip（截图转 LaTeX）。
- 写作流程：`paper_workspace/*.md` 仍用于组织文字，但**公式一律以 LaTeX 源码嵌入**（pandoc 可识别 `$$\begin{aligned}...\end{aligned}$$`）；追求最精细排版时，公式直接写进 `sections/*.tex`，由 main.tex 汇编。

---

## 5. 代码「去 AI 感」规范（获奖论文实证）

> 来源：对获奖论文（C 题 NIPT 检测，附录 B 提供 problem1.do / problem2.py / problem3.py / problem4.py 完整求解代码）的代码逐行精读。本节的唯一目标是让生成的代码读起来像**参赛队员自己写的**，而不是模板库生成的、过于工整的"机器味"。生成任何一个求解脚本前，先过一遍本节的对照表。

### 5.1 核心判断：AI 味 vs 真人味

| 维度 | AI 味（要避免） | 真人味（要模仿） |
|---|---|---|
| 文件拆分 | 一个"全能"文件装下所有模型 | **按子问题拆文件**：problem1.do / problem2.py / problem3.py / problem4.py，文件名 = 问题号 |
| 文件头注释 | 英文三引号 + 大段 Args/Returns | 一段中文，交代"这文件做什么 + 对应论文哪节 + 怎么跑" |
| 分段方式 | 整齐的 `1.` `2.` 编号标题 | `# 第一步：数据准备`、`# 模块二：遗传算法策略优化`、`# 主执行流程` 这类口语化中文块注释 |
| 打印 | 几乎不打印，或只打印最终值 | `print("第二步：开始执行遗传算法策略优化")`、`print("策略优化完成")`、`print(f"结果已保存至：{path}")` |
| 常量 | 魔法数字散落各处 | 路径、超参数**集中成常量**：`BASE_DIR = Path(__file__).resolve().parent`、`GA_PARAMS = {...}` |
| 变量命名 | `x1` `x2` `m1` `m2` | 贴合题目术语：`t_attain`、`person_id`、`Initial_BMI`、`recommended_nipt_week`、`min_group_size`、`p_target` |
| 错误处理 | 大段裸 `raise` 或干脆没有 | `try/except` + 中文报错：`print(f"错误：找不到原始数据文件：{e}")` |
| 落盘 | 直接 `to_csv(...)` | 带中文编码：`to_csv(..., index=False, encoding='utf-8-sig')` |
| 中文字体 | 中文图乱码 | 开头统一设 `plt.rcParams['font.sans-serif'] = ['SimHei', ...]` + `axes.unicode_minus=False` |
| 重复运行 | 每次全量重算 | **缓存幂等**：`if os.path.exists(路径): print("检测到已存在的文件，直接加载")` |

### 5.2 统一文件骨架（Python，求解脚本必须照此）

```python
"""
问题二：求解 BMI 分组和最佳 NIPT 时点的 Python 代码 (problem2.py)
对应论文 §6.2；入口：python problem2.py；依赖：pandas/numpy/scikit-learn/deap/plotly
"""

# ---- 全局可复现 ----
import numpy as np
import pandas as pd
np.random.seed(42)

# ---- 中文字体（无头环境下可保留，绘图时生效） ----
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ---- 路径与超参数集中定义（换了机器只改这里）----
BASE_DIR = ...
RAW_DATA_PATH = BASE_DIR / "附件1.xlsx"
OUTPUT_PATH = BASE_DIR / "result1.csv"
GA_PARAMS = {"num_splits": 2, "min_group_size": 50, "pop_size": 100}

# ---------- 第一步：数据准备 ----------
...

# ---------- 第二步：建模与求解 ----------
print("第二步：开始求解")
...
print("第二步：已完成")

# ---------- 第三步：结果落盘 ----------
...
print(f"结果已保存至：{OUTPUT_PATH}")

# ---------- 主执行流程 ----------
if __name__ == "__main__":
    ...
```

### 5.3 统一文件骨架（MATLAB，求解脚本必须照此）

```matlab
%% problem1.m — 问题一求解（对应论文 §5.1）
% 入口：matlab -batch "run('problem1.m')"
clear; clc; rng(42);

%% 第一步：读入数据
% ...

%% 第二步：建模求解
fprintf('第二步：开始求解\n');
% ...
fprintf('最优值 = %.4f\n', obj);

%% 第三步：结果可视化与落盘
if ~exist('figures', 'dir'), mkdir('figures'); end
if ~exist('results', 'dir'), mkdir('results'); end
saveas(gcf, 'figures/problem1_result.png');
```

### 5.4 硬性规则（生成的每一份求解代码都要满足）

1. **中文注释**：注释、`print`/`fprintf` 提示、报错信息一律中文；英文缩写首次出现给全称。
2. **文件头写明三件事**：对应正文小节号、入口命令（`python xxx.py` / `matlab -batch "run('xxx.m')"`）、主要依赖和随机种子。
3. **按问题拆文件**：提交版本里每个子问题一个文件（`problem1`/`Q1_solve`）；code_starter 是"模板家族"，实际交付时按题目子问题落地命名。
4. **print 进度契约**：每个相对较慢的阶段（读数据 / 建模 / 训练 / 优化 / 落盘 / 画图）开头打一句 `开始…`，结束打一句 `…完成`；保存结果打一句 `已保存至：<路径>`。
5. **常量/参数集中**：文件路径、超参数、阈值都提到文件顶部集中定义，正文逻辑里不出现魔法数字。
6. **区分"库函数"与"流程函数"**：纯计算函数（如 `ahp_weights`、`gm11`）仍不 `print`、只 `return` 结果（保留 §1.3）；但"流程函数/主流程"必须 `print` 进度。两层不冲突。
7. **禁止过度 docstring**：只在一眼看不明白处加一行 `# 说明`；不要给每个函数都套 `Args/Returns` 三引号文档。参赛队员手写代码不会这么"标准"。

### 5.5 禁用写法（AI 味重灾区）

- 给每个 5 行小函数都写满中文 docstring 的 `Args:`/`Returns:` 段落——只在复杂接口函数保留。
- 变量名用 `data`、`result`、`tmp1`、`x1`、`m1` 这种无业务含义的占位名（仅限**交付态**；模板态 code_starter 允许抽象变量，见 §5.6）。
- 满屏 `raise ValueError` 的"防御性编程"——只在真正由外部输入触发、且会静默产生错误结果的边界做校验（如除零、空集），其余交给题目数据的既定约束。
- 英文注释、英文打印、用 `# TODO`/`# FIXME` 这类占位符。

### 5.6 模板态 vs 交付态（两条要求，不可套错）

本规范区分两种代码，目的不同、要求不同：

| | 模板态（code_starter） | 交付态（求解脚本） |
|---|---|---|
| 文件名 | `optimization.py`、`matlab_ode.m` 等，**按模型族命名** | `problem1.py`、`Q1_solve.py` 等，**按子问题命名** |
| 变量命名 | 允许抽象（`p/c/B`、`m1/m2/k1/k2`），因为尚不知道具体题目 | 必须换成题目术语（`t_attain`、`Initial_BMI`、`person_id`） |
| 注释 | 中文，说明"这是模板，实际从附件读" | 中文，按 §5.2/§5.3 骨架 |
| 目的 | 供 stage 3/5 复用的算法参考 | 附在论文附录、给评委读的代码 |

- §5.5 禁用的 `x1/m1` **只针对交付态**；模板态用抽象变量是正常且必要的，不算违规。
- **中文注释、中文字体、`print` 进度、常量集中对两种态都强制**；docstring 克制、`raise` 克制同样适用。
- **缓存幂等（§5.1 表格里的"直接加载"）是可选的，不是硬性要求**。比赛期间若改了模型，缓存旧结果反而危险，除非能保证文件名/参数未变，否则不要加。

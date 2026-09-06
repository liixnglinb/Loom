# 符号说明表模板 (notation_table — 快速参考)

> stage 4 产出, stage 8 §4 用 LaTeX booktabs。详细操作见 `references/stage_04_foundation.md` Step 3。

---

## 表结构

| 符号 | 含义 | 单位 | 类型 | 取值范围 |
|------|------|------|------|---------|
| $x_i$ | 第 $i$ 个产品产量 | 件 | 决策变量 | $\mathbb{Z}, [0, 50]$ |
| $p_i$ | 单价 | 元/件 | 参数 (附件 1) | - |
| $d_i$ | 需求 | 件 | 随机变量 | $\sim \text{Pois}(\lambda_i)$ |
| $\lambda$ | Lagrangian 乘子 | 无量纲 | 中间变量 | $\geq 0$ |
| $f(x)$ | 总利润 | 元 | 目标函数 | - |

要求:
- 覆盖正文中需要跨段、跨公式或跨子问题理解的实际符号；数量由模型决定
- 有物理量纲的符号必须填单位；无量纲写“无量纲”，索引、集合或不适用项写“不适用”并保持语义清楚
- 每行标明实际类型，例如决策变量 / 状态变量 / 参数 / 随机变量 / 中间变量 / 目标函数；必要时可增加类型

---

## 跨页规范（符号说明表超过一页时必用）

符号说明表行数多时可能跨页。**跨页时每一页都必须呈现完整三线表结构（顶线、表头下线、底线），且非末页右下角以小字标注"续下页"**。实现采用 LaTeX `longtable`（模板已加载 `longtable` 与 `booktabs`）四段式页头/页脚，pandoc 环境下以原生 LaTeX 块写在 markdown 中（`+raw_tex` 会原样透传）：

```latex
% 列数 N 按实际列数调整（此处为 3 列示例）；\multicolumn{N}{r} 中的 N 必须一致
% 用 p{…\textwidth} 列并置 \tabcolsep=0，保证表格左右边界与正文版心严格对齐；
% 三列宽度之和 = 1.0\textwidth（此处 0.26+0.55+0.19）。
\setlength{\tabcolsep}{0pt}%
\begin{longtable}{@{}p{0.26\textwidth}p{0.55\textwidth}p{0.19\textwidth}@{}}
% ---- 第一页表头：顶线 + 表头 + 表头下线 ----
\toprule
符号 & 含义 & 单位 \\
\midrule
\endfirsthead
% ---- 续页表头：每页都重复，保证每页三条线 ----
\toprule
符号 & 含义 & 单位 \\
\midrule
\endhead
% ---- 非末页页脚：底线 + 右下角小字"续下页" ----
\bottomrule
\multicolumn{3}{r}{\footnotesize 续下页} \\
\endfoot
% ---- 末页页脚：仅底线 ----
\bottomrule
\endlastfoot
% ---- 数据行 ----
$x_i$ & 第 $i$ 个产品产量 & 件 \\
$p_i$ & 单价 & 元/件 \\
...（全部符号行）...
\end{longtable}
\setlength{\tabcolsep}{6pt}%
```

规则与自检:
- `\endfirsthead` 前的内容只出现在第一页（顶线 + 表头 + 下线）
- `\endhead` 前的内容在每一续页重复（顶线 + 表头 + 下线）→ **每页都有三条线**
- `\endfoot` 前的内容出现在所有非末页底部：底线 + `\multicolumn{列数}{r}{\footnotesize 续下页}` → **第一页结尾有横线、右下角有"续下页"小字**
- `\endlastfoot` 前的内容只出现在末页底部：仅底线
- **左右对齐正文**：列用 `p{…\textwidth}` 且三列宽度之和 = `\textwidth`；因 longtable 列间默认含 `\tabcolsep` 会使总宽超出正文，须在表前 `\setlength{\tabcolsep}{0pt}`、表尾恢复为 6pt。否则表格右缘会推出版心
- 第一列放符号（左对齐）、中间含义（可换行 `p{}`）、末列单位，`p{}` 列自动按宽折行
- 列数 N 与 `\multicolumn{N}{r}` 的 N 一致；表头行在两个 `\end...head` 段中保持一致
- 反模式 I12：长表跨页缺"续下页"或续页缺三线 → 按本模板重写为 longtable 四段式

---

## 符号约定 (跨子问题统一, anti_pattern B4 防重复)

下标:
- $i$: 产品索引
- $t$: 时间索引
- $s$: 场景索引 (随机规划)
- $j$: 客户/区域索引
- $k$: 阶段索引 (动态规划)

上标:
- $x^*$: 最优解
- $\hat{x}$: 估计值
- $\bar{x}$: 平均值
- $\tilde{x}$: 扰动值

---

## 单位规则

- 物理量: SI 或题目惯例 (米/秒/件/元)
- 比值: "无量纲"
- 货币: 元 / 美元, 全文统一不混用
- 时间: 秒/分/小时/天/月, 全文统一

---

## 反模式自检

- B4 符号重复 (同符号不同含义) → 改名一个
- B5 物理量缺单位或单位冲突 → 补齐并统一；确实不适用时明确标注
- 符号未在 §4 表中出现就用 → 补到表内或脚注

LaTeX booktabs 模板示例: 见 stage_04 §Step 3 (本文不重复)。

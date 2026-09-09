# Advanced Figure Recipes — Clean Academic Edition


High-impact, SCI-quality figure types with clean, publication-ready styling.

Every recipe features: solid colors, single-layer semi-transparent fills, annotation boxes,

subtle grids (alpha=0.15), and minimal decoration. Titles are handled by LaTeX captions.


> **配色规范**: 所有配方统一使用 `PALETTE[n]`（主色系列）或 `COLORS['xxx']`（语义色，如 `_lighten()` 浅色填充）。禁止硬编码 hex 色值。

> **标题规范**: 所有配方不使用 `set_title()`，而由 LaTeX `\caption{}` 处理。

> **格式规范**: 统一去掉 top/right spines；标注框统一用 `bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=..., alpha=0.9)`。

> **曲线原则**: 不使用多段拟合模拟（n_seg=30/40/50/60/80），而用简单的 `plot()`/`hlines()`/`fill_between()`。


---


## 1. Lollipop Chart — 棒棒糖图（渐变色茎 + 排名徽章 + 中位数参考线）


**场景**: 按单一指标对方法/方案排名。比柱状图更简洁，常见于 Nature/Science。

**防重叠**: 使用 `smart_labels()` 自动推开重叠的数值标签。

**风格**: 渐变色从紫罗兰（高分）过渡到珊瑚橙（低分）；线粗、圆点大小也随分数渐变。前三名有排名徽章。中位数参考线分割图面。

**⚠ 关键要点**: 茎线从 x=0 开始；颜色按 HSL 明度线性渐变（避免相邻项同色）；前三名实心圆徽章。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten, smart_labels

setup_style()

import matplotlib.pyplot as plt

import matplotlib.colors as mc

import numpy as np

import colorsys


methods = ['Ours', 'Baseline-A', 'Baseline-B', 'Baseline-C', 'Baseline-D']

scores = [0.923, 0.887, 0.862, 0.841, 0.815]


n = len(methods)

score_min, score_max = min(scores), max(scores)

score_range = score_max - score_min if score_max > score_min else 1


# ── 渐变配色：从紫罗兰 → 珊瑚橙（明度和色相同时渐变）

color_top = '#7B6BA5'     # 紫罗兰（高分，偏冷一点）

color_bottom = '#E08B74'  # 珊瑚橙（低分，偏暖）


def interpolate_color(c1, c2, t):

    """HSL 空间插值：t=0 返回 c1，t=1 返回 c2"""

    r1, g1, b1 = mc.to_rgb(c1)

    r2, g2, b2 = mc.to_rgb(c2)

    h1, l1, s1 = colorsys.rgb_to_hls(r1, g1, b1)

    h2, l2, s2 = colorsys.rgb_to_hls(r2, g2, b2)

    if abs(h2 - h1) > 0.5:

        if h1 < h2: h1 += 1.0

        else: h2 += 1.0

    h = (h1 + (h2 - h1) * t) % 1.0

    l = l1 + (l2 - l1) * t

    s = s1 + (s2 - s1) * t

    return colorsys.hls_to_rgb(h, l, s)


item_colors = [interpolate_color(color_top, color_bottom, i / (n - 1) if n > 1 else 0) for i in range(n)]


# ── 自适应高度（每项 0.46 高度 + 上下留白）

_fig_h = max(4, n * 0.46 + 1.8)

fig, ax = plt.subplots(figsize=(7.5, _fig_h))

y_pos = np.arange(n)


# 极浅网格线

ax.grid(axis='x', alpha=0.12, linestyle='-', color=COLORS['grid'])

ax.set_axisbelow(True)


# 中位数参考线（置于底层）

median_val = np.median(scores)

ax.axvline(median_val, color=COLORS['ref_line'], linestyle=':', linewidth=1.0, alpha=0.5, zorder=1)


# ── 主体：渐变色茎线 + 渐变圆点

for i, (m, s) in enumerate(zip(methods, scores)):

    c = item_colors[i]

    ratio = (s - score_min) / score_range

    lw = 1.6 + 2.0 * ratio


    # 茎线从 0 开始

    ax.plot([0, s], [y_pos[i], y_pos[i]],

            color=c, linewidth=lw, zorder=3, solid_capstyle='round')


    # 端点圆点 —— 大小随分数渐变

    dot_size = 55 + 120 * ratio

    ax.scatter(s, y_pos[i], color=c, s=dot_size, zorder=5,

               edgecolors='white', linewidths=1.8)


    # 数值标签

    ax.text(s + score_range * 0.03, y_pos[i], f'{s:.3f}',

            fontsize=8.5, fontweight='bold' if i < 3 else 'normal',

            color=c, va='center', ha='left')


    # ── 排名徽章区域

    badge_x = -score_range * 0.065

    rank = i + 1

    if rank <= 3:

        badge = plt.Circle((badge_x, y_pos[i]), 0.3,

                            color=_lighten(c, 0.15), zorder=6,

                            transform=ax.transData)

        ax.add_patch(badge)

        ax.text(badge_x, y_pos[i], str(rank),

                fontsize=8.5, fontweight='bold', color='white',

                ha='center', va='center', zorder=7)

    else:

        ax.text(badge_x, y_pos[i], str(rank),

                fontsize=7.5, color=_lighten(c, 0.2),

                ha='center', va='center', fontweight='bold')


# 第一名背景高亮条

ax.axhspan(y_pos[0] - 0.42, y_pos[0] + 0.42, alpha=0.06,

           color=item_colors[0], zorder=0)


# 中位数标注 —— 置于图的顶部

ax.text(median_val, -0.9, f'中位数 {median_val:.3f}',

        fontsize=8, color=COLORS['ref_line'], ha='center', va='bottom',

        bbox=dict(boxstyle='round,pad=0.25', facecolor='white',

                  edgecolor=COLORS['ref_line'], alpha=0.85))


ax.set_yticks(y_pos)

ax.set_yticklabels(methods, fontsize=10)

ax.set_xlabel('F1 Score', fontsize=11)

ax.set_xlim(-score_range * 0.13, score_max + score_range * 0.15)

ax.set_ylim(n - 0.5, -1.4)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_lollipop.pdf')

```


**⚠ 易踩的坑（棒棒糖图专用）：**

```python

# 1. ylim 上方留空：ax.set_ylim(n-0.5, -1.4)，给中位数标注留空间

# 2. xlim 右侧留余量（score_max + score_range*0.15），给数值标签留空间

# 3. xlim 左侧留负值（-score_range*0.13），给排名徽章留空间

# 4. 数值标签偏移用相对值（score_range*0.03），不要用固定像素偏移

# 5. 排名徽章用 plt.Circle + transData，确保圆形不变形

# 6. 中位数标注放在 y=-0.9（图面上方），需要配合上方留空设置

# 7. 当条目数 >15 时，_fig_h 公式自动增高（每项 0.46 高度不会挤压）

```


---


## 2. Dumbbell Chart — 哑铃图（连接线 + 变化率 + 显著性标记）


**场景**: 前后对比、两组差异。比分组柱状图更直观。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import numpy as np


metrics = ['Accuracy', 'Precision', 'Recall', 'F1', 'AUC']

before = [0.82, 0.79, 0.85, 0.81, 0.88]

after = [0.91, 0.88, 0.90, 0.89, 0.94]


# ── 自适应高度

_fig_h = max(3.5, len(metrics) * 0.7 + 1)

fig, ax = plt.subplots(figsize=(8, _fig_h))

y = np.arange(len(metrics))


# Subtle grid

ax.grid(axis='x', alpha=0.15, linestyle='-', color=COLORS['grid'])

ax.set_axisbelow(True)


# Simple connector lines + arrow heads

for i in range(len(metrics)):

    delta = after[i] - before[i]

    pct_change = delta / before[i] * 100

    # Simple connector line

    ax.plot([before[i], after[i]], [y[i], y[i]],

            color=PALETTE[2], linewidth=2.0, solid_capstyle='round')

    # Arrow head at the "after" end

    ax.annotate('', xy=(after[i], y[i]), xytext=(after[i] - 0.012, y[i]),

                arrowprops=dict(arrowstyle='->', color=PALETTE[0], lw=2.0))


    # Before / After dots

    ax.scatter(before[i], y[i], color=PALETTE[3], s=80, zorder=3,

               edgecolors='white', linewidths=1.0, label='Before' if i == 0 else '')

    ax.scatter(after[i], y[i], color=PALETTE[0], s=80, zorder=3,

               edgecolors='white', linewidths=1.0, label='After' if i == 0 else '')


    # % change label

    ax.text(after[i] + 0.015, y[i] - 0.15, f'+{delta:.2f} ({pct_change:+.1f}%)',

            va='center', fontsize=8, color=PALETTE[0], fontweight='bold')


    # Significance marker (stars)

    if pct_change > 8:

        sig = '***'

    elif pct_change > 5:

        sig = '**'

    else:

        sig = '*'

    ax.text(after[i] + 0.015, y[i] + 0.2, sig, va='center', fontsize=9,

            color=COLORS['down'], fontweight='bold')


ax.set_yticks(y)

ax.set_yticklabels(metrics, fontsize=10)

ax.set_xlabel('Score', fontsize=11)

ax.legend(loc='lower right', frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=9,

          fancybox=True, shadow=False)

ax.invert_yaxis()

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_dumbbell.pdf')

```


**⚠ 易踩的坑（哑铃图专用）：**

```python

# 1. % change 标签和星号分两行（y 偏移 -0.15 和 +0.2），不要放在一行

# 2. xlim 右侧留 15% 余量，给 % change 标签和星号留空间

# 3. 当 before/after 值很接近（差 <0.02）时，标签会重叠 → 只标注 after 值

# 4. 图例放 lower right（因为通常数据在上方，不会遮挡）

```


---


## 3. Slope Chart — 斜率图（颜色编码线 + 排名变化标注）


**场景**: 跨条件的排名/趋势变化。比分组柱状图更清晰地展示交叉变化。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import numpy as np


methods = ['Method-A', 'Method-B', 'Method-C', 'Method-D']

dataset1 = [0.92, 0.88, 0.85, 0.90]

dataset2 = [0.87, 0.91, 0.89, 0.86]


fig, ax = plt.subplots(figsize=(6, 5.5))


# Subtle grid

ax.grid(axis='y', alpha=0.15, linestyle='-', color=COLORS['grid'])

ax.set_axisbelow(True)


# Compute ranks

rank1 = list(np.argsort(np.argsort([-v for v in dataset1])) + 1)

rank2 = list(np.argsort(np.argsort([-v for v in dataset2])) + 1)


for i, m in enumerate(methods):

    diff = dataset2[i] - dataset1[i]

    # Green = improve, Red = decline

    base_color = COLORS['up'] if diff >= 0 else COLORS['down']


    # Simple line connecting two points

    ax.plot([0, 1], [dataset1[i], dataset2[i]], color=base_color,

            linewidth=2.5, solid_capstyle='round')


    # Endpoints

    ax.scatter([0], [dataset1[i]], color=base_color, s=90, zorder=5,

               edgecolors='white', linewidths=1.2)

    ax.scatter([1], [dataset2[i]], color=base_color, s=90, zorder=5,

               edgecolors='white', linewidths=1.2)


    # Value labels

    ax.text(-0.08, dataset1[i], f'{dataset1[i]:.2f}', ha='right', va='center',

            fontsize=9, color=base_color)

    ax.text(1.08, dataset2[i], f'{dataset2[i]:.2f}', ha='left', va='center',

            fontsize=9, color=base_color)


    # Rank change annotation

    rank_delta = rank1[i] - rank2[i]  # positive = improved rank

    if rank_delta != 0:

        arrow_sym = '↑' if rank_delta > 0 else '↓'

        rank_color = COLORS['up'] if rank_delta > 0 else COLORS['down']

        ax.text(1.22, dataset2[i], f'{m} {arrow_sym}{abs(rank_delta)}',

                ha='left', va='center', fontsize=8, color=rank_color,

                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=rank_color, alpha=0.9))

    else:

        ax.text(1.22, dataset2[i], f'{m} →', ha='left', va='center',

                fontsize=8, color=COLORS['ref_line'])


ax.set_xticks([0, 1])

ax.set_xticklabels(['Dataset-1', 'Dataset-2'], fontsize=11)

ax.set_xlim(-0.35, 1.65)

ax.set_ylim(min(dataset1 + dataset2) - 0.03, max(dataset1 + dataset2) + 0.03)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

ax.spines['bottom'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_slope.pdf')

```


**⚠ 易踩的坑（Slope Chart 专用）：**

```python

# 1. 当多条数值标签重叠时，只标注变化最大的 2-3 条线，其余省略

# 2. 右侧排名变化标注用 bbox 白底，防止与数值标签混在一起

# 3. xlim 左侧留 0.35，给标签留空间（ax.set_xlim(-0.35, 1.65)）

# 4. 值域较窄（如数值在 0.85-0.92 之间）时，ylim 不要从 0 开始，放大差异

```


---


## 4. Bump Chart — 凹凸图（色带高亮 + 两端排名标签 + "本文"高亮）


**场景**: 跟踪跨数据集/指标的排名变化。比表格更直观。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS

setup_style()

import matplotlib.pyplot as plt

import numpy as np


methods = ['Ours', 'BERT', 'GPT', 'RoBERTa']

datasets = ['MNLI', 'QQP', 'SST-2', 'QNLI']

ranks = [[1, 1, 2, 1], [3, 2, 1, 3], [2, 3, 3, 2], [4, 4, 4, 4]]


fig, ax = plt.subplots(figsize=(8, 5))

x = np.arange(len(datasets))


# Subtle grid

ax.grid(axis='y', alpha=0.15, linestyle='-', color=COLORS['grid'])

ax.set_axisbelow(True)


for i, (m, r) in enumerate(zip(methods, ranks)):

    is_ours = (i == 0)

    lw = 3.5 if is_ours else 1.8

    alpha_line = 1.0 if is_ours else 0.55

    ms = 14 if is_ours else 9


    # Gradient ribbon for "Ours"

    if is_ours:

        for k in range(len(x) - 1):

            x_fill = np.linspace(x[k], x[k + 1], 50)

            y_fill = np.interp(x_fill, x, r)

            ax.fill_between(x_fill, y_fill - 0.15, y_fill + 0.15,

                            alpha=0.15, color=PALETTE[0])


    # Line

    ax.plot(x, r, 'o-', color=PALETTE[i], linewidth=lw, markersize=ms,

            label=m, zorder=3 + (1 if is_ours else 0), alpha=alpha_line,

            markeredgecolor='white', markeredgewidth=1.5 if is_ours else 0.8)


    # Rank labels at both ends

    ax.text(x[0] - 0.2, r[0], f'#{r[0]} {m}', va='center', ha='right',

            fontsize=9, color=PALETTE[i],

            fontweight='bold' if is_ours else 'normal')

    ax.text(x[-1] + 0.2, r[-1], f'#{r[-1]} {m}', va='center', ha='left',

            fontsize=9, color=PALETTE[i],

            fontweight='bold' if is_ours else 'normal')


# Highlight box for "Ours"

ax.annotate('★ Ours: Rank #1 in 3/4 datasets',

            xy=(x[0], ranks[0][0]), xytext=(x[0] + 0.5, ranks[0][0] - 0.6),

            fontsize=8.5, color=PALETTE[0], fontweight='bold',

            arrowprops=dict(arrowstyle='->', color=PALETTE[0], lw=1.2),

            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',

                      edgecolor=PALETTE[0], alpha=0.9))


ax.set_xticks(x)

ax.set_xticklabels(datasets, fontsize=10)

ax.set_yticks([1, 2, 3, 4])

ax.set_yticklabels(['1st', '2nd', '3rd', '4th'], fontsize=10)

ax.set_ylabel('Rank', fontsize=11)

ax.invert_yaxis()

ax.set_xlim(-0.6, len(datasets) - 0.4)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_bump.pdf')

```


**⚠ 易踩的坑（Bump Chart 专用）：**

```python

# 1. 两端排名标签用 ha='right'/ha='left'，不要用 ha='center'（会与线重叠）

# 2. xlim 左侧留 0.6，给两端标签留空间

# 3. 高亮标注不要与排名标签重叠：xytext 偏移至少 0.5 个单位

# 4. 方法数 >6 时，只标注首尾两端，省略中间（减少图面杂乱）

```


---


## 5. Sankey Diagram — 桑基图（D3 风格，矩形节点 + 贝塞尔流带）


**场景**: 资源分配、数据流向、能量流、用户路径。矩形节点（高度=流量）+ 半透明贝塞尔曲线连接带（按 source 分色）。


⛔ **不要用 `matplotlib.sankey.Sankey`**——它出来是"动物形状/箭头风格"，标签重叠、比例失真、整体丑。下面这套用 path + Bezier 手写，是 D3.js / Plotly 风格的现代 Sankey。


```python

import shutil, os

os.makedirs('_utils', exist_ok=True)

for f in ['plot_utils.py']:

    src = os.path.join(os.path.dirname(__file__), f)

    if os.path.exists(src):

        shutil.copy2(src, f'_utils/{f}')


import numpy as np

import matplotlib.pyplot as plt

from matplotlib.path import Path

from matplotlib.patches import PathPatch, Rectangle

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()


def draw_sankey(ax, source_nodes, target_nodes, flows,

                source_colors=None, target_colors=None,

                left_x=0.10, right_x=0.90,

                node_width=0.025, node_gap=0.03,

                title_top=None):

    """D3 风格 Sankey 图（矩形节点 + 贝塞尔流带）。


    Args:

        source_nodes: list of (name, total_value)，例如 [('国产', 1473), ('俄罗斯', 1500)]

        target_nodes: list of (name, total_value)，例如 [('总供给', 3000)]

        flows: list of dict {source_idx: int, target_idx: int, value: float}

        source_colors / target_colors: 可选，None 时自动按 PALETTE 分色

        node_width: 矩形宽度（相对坐标 0-1）

        node_gap: 同侧节点间垂直间距

        title_top: 顶部副标题（如"流量守恒 (万 m³)"）

    """

    total_src = sum(v for _, v in source_nodes)

    total_tgt = sum(v for _, v in target_nodes)

    if abs(total_src - total_tgt) > 1e-3:

        raise ValueError(f'流量不守恒：source 合计 {total_src} ≠ target 合计 {total_tgt}')


    Y_MARGIN = 0.08

    avail_h_src = (1 - 2 * Y_MARGIN) - node_gap * max(0, len(source_nodes) - 1)

    avail_h_tgt = (1 - 2 * Y_MARGIN) - node_gap * max(0, len(target_nodes) - 1)


    src_ranges = []

    y = 1 - Y_MARGIN

    for _, v in source_nodes:

        h = v / total_src * avail_h_src

        src_ranges.append((y - h, y))

        y = y - h - node_gap


    tgt_ranges = []

    y = 1 - Y_MARGIN

    for _, v in target_nodes:

        h = v / total_tgt * avail_h_tgt

        tgt_ranges.append((y - h, y))

        y = y - h - node_gap


    if source_colors is None:

        source_colors = [PALETTE[i % len(PALETTE)] for i in range(len(source_nodes))]

    if target_colors is None:

        target_colors = [COLORS.get('text', '#444444')] * len(target_nodes)


    # 左侧节点矩形 + 标签

    for i, ((name, v), (y0, y1)) in enumerate(zip(source_nodes, src_ranges)):

        rect = Rectangle((left_x - node_width / 2, y0), node_width, y1 - y0,

                         facecolor=source_colors[i], edgecolor='none', alpha=0.92, zorder=3)

        ax.add_patch(rect)

        ax.text(left_x - node_width / 2 - 0.012, (y0 + y1) / 2,

                f'{name}\n{v:g}',

                ha='right', va='center', fontsize=9,

                color=COLORS.get('text', '#222'), fontweight='bold')


    # 右侧节点矩形 + 标签

    for i, ((name, v), (y0, y1)) in enumerate(zip(target_nodes, tgt_ranges)):

        rect = Rectangle((right_x - node_width / 2, y0), node_width, y1 - y0,

                         facecolor=target_colors[i], edgecolor='none', alpha=0.92, zorder=3)

        ax.add_patch(rect)

        ax.text(right_x + node_width / 2 + 0.012, (y0 + y1) / 2,

                f'{name}\n{v:g}',

                ha='left', va='center', fontsize=9,

                color=COLORS.get('text', '#222'), fontweight='bold')


    # 贝塞尔流带

    src_top_used = [r[1] for r in src_ranges]

    tgt_top_used = [r[1] for r in tgt_ranges]


    for flow in flows:

        si, ti, val = flow['source_idx'], flow['target_idx'], flow['value']

        s_h = val / total_src * avail_h_src

        t_h = val / total_tgt * avail_h_tgt

        s_y_top = src_top_used[si]; s_y_bot = s_y_top - s_h; src_top_used[si] = s_y_bot

        t_y_top = tgt_top_used[ti]; t_y_bot = t_y_top - t_h; tgt_top_used[ti] = t_y_bot


        mid_x = (left_x + right_x) / 2

        path_data = [

            (Path.MOVETO,    (left_x + node_width / 2, s_y_top)),

            (Path.CURVE4,    (mid_x, s_y_top)),

            (Path.CURVE4,    (mid_x, t_y_top)),

            (Path.CURVE4,    (right_x - node_width / 2, t_y_top)),

            (Path.LINETO,    (right_x - node_width / 2, t_y_bot)),

            (Path.CURVE4,    (mid_x, t_y_bot)),

            (Path.CURVE4,    (mid_x, s_y_bot)),

            (Path.CURVE4,    (left_x + node_width / 2, s_y_bot)),

            (Path.CLOSEPOLY, (left_x + node_width / 2, s_y_top)),

        ]

        codes, verts = zip(*path_data)

        flow_color = flow.get('color', source_colors[si])

        patch = PathPatch(Path(verts, codes),

                          facecolor=flow_color, edgecolor='none', alpha=0.42, zorder=2)

        ax.add_patch(patch)


    if title_top:

        ax.text(0.5, 0.98, title_top, ha='center', va='top',

                fontsize=10, color=COLORS.get('text', '#444'), fontweight='bold')


    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    ax.set_aspect('auto'); ax.axis('off')


# ── 示例 1: 多 source → 单 target（资源分配场景）

fig, ax = plt.subplots(figsize=(9, 5))

source_nodes = [('国产', 1473), ('俄罗斯', 1500), ('卡塔尔', 27)]

target_nodes = [('总供给 = 需求 (万 m³)', 3000)]

flows = [

    {'source_idx': 0, 'target_idx': 0, 'value': 1473},

    {'source_idx': 1, 'target_idx': 0, 'value': 1500},

    {'source_idx': 2, 'target_idx': 0, 'value': 27},

]

draw_sankey(ax, source_nodes, target_nodes, flows,

            title_top='问题一 最优供应量分配（流量守恒，万 m³）')


auto_rate = 1473 / 3000 * 100

import_rate = (1500 + 27) / 3000 * 100

ax.text(0.05, 0.04,

        f'自给率 = {auto_rate:.1f}%   进口依赖 = {import_rate:.1f}%',

        ha='left', va='bottom', fontsize=8.5,

        color=COLORS.get('text', '#444'),

        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',

                  edgecolor='#cccccc', linewidth=0.5))


fig.tight_layout()

save_fig(fig, 'figures/fig_sankey_supply.pdf')


# ── 示例 2: 单 source → 多 target（数据分流场景）

fig, ax = plt.subplots(figsize=(10, 5.5))

source_nodes = [('原始数据', 1000)]

target_nodes = [('训练集', 600), ('测试集', 300), ('验证集', 100)]

flows = [

    {'source_idx': 0, 'target_idx': 0, 'value': 600, 'color': PALETTE[0]},

    {'source_idx': 0, 'target_idx': 1, 'value': 300, 'color': PALETTE[1]},

    {'source_idx': 0, 'target_idx': 2, 'value': 100, 'color': PALETTE[2]},

]

draw_sankey(ax, source_nodes, target_nodes, flows,

            target_colors=[PALETTE[0], PALETTE[1], PALETTE[2]],

            title_top='数据集划分')

fig.tight_layout()

save_fig(fig, 'figures/fig_sankey_split.pdf')


# ── 示例 3: 多对多

fig, ax = plt.subplots(figsize=(10.5, 6))

source_nodes = [('来源A', 500), ('来源B', 300), ('来源C', 200)]

target_nodes = [('去向X', 400), ('去向Y', 350), ('去向Z', 150), ('去向W', 100)]

flows = [

    {'source_idx': 0, 'target_idx': 0, 'value': 300},

    {'source_idx': 0, 'target_idx': 1, 'value': 150},

    {'source_idx': 0, 'target_idx': 2, 'value':  50},

    {'source_idx': 1, 'target_idx': 0, 'value': 100},

    {'source_idx': 1, 'target_idx': 1, 'value': 150},

    {'source_idx': 1, 'target_idx': 3, 'value':  50},

    {'source_idx': 2, 'target_idx': 1, 'value':  50},

    {'source_idx': 2, 'target_idx': 2, 'value': 100},

    {'source_idx': 2, 'target_idx': 3, 'value':  50},

]

draw_sankey(ax, source_nodes, target_nodes, flows,

            title_top='多对多流向分析')

fig.tight_layout()

save_fig(fig, 'figures/fig_sankey_many.pdf')

```


**⛔ 易踩的坑（Sankey Diagram 专用）：**


1. **流量必须守恒**：source 总和 = target 总和（函数已加 `raise ValueError` 校验，超 1e-3 报错）

2. **节点 ≤ 8 个**：每侧超过 8 节点 → 矩形太薄看不清，改用桑基图 + 滚动条（plotly）或拆成多张图

3. **流 ≤ 15 条**：超过 15 条流 → 视觉混乱，用 Sankey 不合适，改成饼图嵌套或矩阵热力图

4. **图例颜色**：每个 source 用同一颜色，target 矩形可以中性色（灰）或承袭 source 色

5. **数值单位写在 `title_top` 里**（如 "（流量守恒，万 m³）"），不要在每个节点重复

6. **不要用 `matplotlib.sankey.Sankey`**：那个 API 出来是"箭头形状"，标签重叠、比例失真


**⛔ 反例（用户实际踩过的坑）：**


```python

# ❌ 错误：matplotlib.sankey.Sankey 出来是"动物形状"

from matplotlib.sankey import Sankey

sankey = Sankey(ax=ax, scale=0.008, ...)

sankey.add(flows=[1473, 1500, 27, -3000], orientations=[1, 0, -1, 0], ...)

# 结果：3 个 source 从 3 个方向汇聚到 1 个 target → 形状像箭头 / 鱼，不是 Sankey


# ✅ 正确：用上面的 draw_sankey 函数，矩形 + 贝塞尔流带

draw_sankey(ax, source_nodes, target_nodes, flows, title_top='...')

```


---


## 6. Waterfall Chart — 瀑布图（彩色渐变柱图 + 连接线 + 顶部数值标注）


**场景**: 因素分解、消融贡献分析。比柱状图更适合展示增量贡献。

**风格**: 彩色层叠（每步增量形成一层从当前步延伸到右边的色带层）+ 阶梯连线 + 圆点 + 数值标注统一在上方 + 贡献信息图例。比传统瀑布图（仅柱+连线）多了"层叠"视觉隐喻。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import matplotlib.patches as mpatches

import numpy as np


labels = ['Baseline', '+Attention', '+Augment', '+Pretrain', '-Dropout']

deltas = [0.82,        0.04,          0.02,       0.05,       -0.01]


cum = [deltas[0]]

for d in deltas[1:]:

    cum.append(cum[-1] + d)

final_val = cum[-1]

total_delta = final_val - deltas[0]


layer_colors = [COLORS['up'] if d >= 0 else COLORS['down'] for d in deltas[1:]]

n = len(labels)


fig, ax = plt.subplots(figsize=(9, 5))

ax.grid(axis='y', alpha=0.12, linestyle='-', color=COLORS['grid'])

ax.set_axisbelow(True)


x_positions = np.arange(n)


# ── 色带层叠（每步增量的层带位置，延伸到最右边）

for i in range(1, n):

    c = layer_colors[i - 1]

    bottom = min(cum[i-1], cum[i])

    top = max(cum[i-1], cum[i])

    ax.fill_between([x_positions[i] - 0.5, x_positions[-1] + 0.5], bottom, top,

                    alpha=0.15, color=c, zorder=1 + i)

    ax.plot([x_positions[i] - 0.5, x_positions[-1] + 0.5], [cum[i], cum[i]],

            color=c, linewidth=0.7, linestyle='--', alpha=0.35, zorder=1 + i)


# Baseline 底层

ax.fill_between([x_positions[0] - 0.5, x_positions[-1] + 0.5], 0, cum[0],

                alpha=0.06, color=PALETTE[0], zorder=0)


# ── 阶梯连线

ax.step(x_positions, cum, where='mid', color=PALETTE[0], linewidth=2.8, zorder=10)


# ── 圆点

for i in range(n):

    c = PALETTE[0] if i == 0 else layer_colors[i - 1]

    ax.scatter(x_positions[i], cum[i], color=c, s=90, zorder=11,

               edgecolors='white', linewidths=2.0)


# ── 数值标注 —— 所有步骤都标，统一放在圆点上方

for i in range(n):

    c = PALETTE[0] if i == 0 else layer_colors[i - 1]

    ax.text(x_positions[i], cum[i] + 0.008, f'{cum[i]:.3f}', ha='center', va='bottom',

            fontsize=8.5, fontweight='bold' if (i == 0 or i == n-1) else 'normal',

            color=c,

            bbox=dict(boxstyle='round,pad=0.15', facecolor='white',

                      edgecolor=c if (i == 0 or i == n-1) else 'none',

                      alpha=0.9, linewidth=0.5), zorder=12)


# ── 总增量标注（右上角）

ax.text(0.97, 0.95, f'Total: +{total_delta:.2f} (+{total_delta/deltas[0]*100:.1f}%)',

        transform=ax.transAxes, fontsize=9.5, ha='right', va='top',

        fontweight='bold', color=COLORS['up'],

        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',

                  edgecolor=COLORS['up'], alpha=0.9, linewidth=1.0), zorder=15)


# ── 贡献图例（将贡献信息全部放在图例，而非图面上标）

legend_patches = []

for i in range(1, n):

    d = deltas[i]

    c = layer_colors[i - 1]

    sign = '+' if d >= 0 else ''

    pct = abs(d) / total_delta * 100

    patch = mpatches.Patch(facecolor=_lighten(c, 0.4), edgecolor=c, linewidth=1.2,

                           label=f'{labels[i]}  {sign}{d:.2f} ({pct:.0f}%)')

    legend_patches.append(patch)

legend = ax.legend(handles=legend_patches, loc='lower right',

                   frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8.5,

                   facecolor='white', title='Contribution', title_fontsize=9,

                   handlelength=1.5, handleheight=1.0)

legend.set_zorder(15)


ax.set_xticks(x_positions)

ax.set_xticklabels(labels, fontsize=10)

ax.set_ylabel('Accuracy', fontsize=11)

ax.set_xlim(-0.7, n - 0.3)

ax.set_ylim(deltas[0] * 0.92, final_val * 1.12)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_waterfall.pdf')

```


**⚠ 易踩的坑（彩色层叠瀑布图专用）：**

```python

# 1. 数值标注统一在圆点上方（va='bottom'），不要放在下方（色带层叠在下方会遮挡）

# 2. 首尾端点有边框 bbox，中间步骤无边框白底（视觉层次分明）

# 3. 贡献信息放图例而非图面：避免色带中间的标注和阶梯线重叠

# 4. ylim 上方留 12%，给最高点的标注留空间

# 5. 总增量标注用 transform=ax.transAxes 固定在右上角，不受数据范围影响

# 6. 色带 alpha=0.15：太深会让标注不清楚，太浅没有层次感

```


---


## 7. SHAP Summary Plot — SHAP 特征重要性图


**场景**: 特征对模型预测的影响。比普通特征重要性柱状图更丰富——同时展示方向和幅度。

**风格**: 浅色填充+原色边框 bars 用于重要性面板，coolwarm beeswarm 用于 SHAP 面板。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import matplotlib.gridspec as gridspec

import numpy as np


np.random.seed(42)

features = ['Feature A', 'Feature B', 'Feature C', 'Feature D', 'Feature E']

n_samples = 200


fig = plt.figure(figsize=(9, 5))

gs = gridspec.GridSpec(1, 2, width_ratios=[3, 1], wspace=0.05)


# Left panel: SHAP beeswarm

ax_shap = fig.add_subplot(gs[0])

ax_shap.grid(axis='x', alpha=0.15, linestyle='-', color=COLORS['grid'])

ax_shap.set_axisbelow(True)


mean_abs_shap = []

for i, feat in enumerate(features):

    shap_vals = np.random.randn(n_samples) * (len(features) - i) * 0.12

    feat_vals = np.random.rand(n_samples)

    y_jitter = np.random.uniform(-0.3, 0.3, n_samples) + i

    sc = ax_shap.scatter(shap_vals, y_jitter, c=feat_vals, cmap='coolwarm',

                         s=10, alpha=0.65, vmin=0, vmax=1, edgecolors='none')

    mean_abs_shap.append(np.mean(np.abs(shap_vals)))


ax_shap.set_yticks(range(len(features)))

ax_shap.set_yticklabels(features, fontsize=10)

ax_shap.set_xlabel('SHAP value (impact on prediction)', fontsize=10)

ax_shap.axvline(x=0, color=COLORS['ref_line'], linewidth=0.8, linestyle='--')

ax_shap.spines['top'].set_visible(False)

ax_shap.spines['right'].set_visible(False)


# Colorbar

cbar = plt.colorbar(sc, ax=ax_shap, shrink=0.5, pad=0.02, aspect=20)

cbar.set_label('Feature value', fontsize=8)

cbar.ax.tick_params(labelsize=7)


# Right panel: Mean |SHAP| importance bar —— 浅色填充 + 原色边框

ax_bar = fig.add_subplot(gs[1])

for i, v in enumerate(mean_abs_shap):

    is_top = (v == max(mean_abs_shap))

    c = PALETTE[0] if is_top else PALETTE[2]

    ax_bar.barh(i, v, color=_lighten(c, 0.4), edgecolor=c,

                linewidth=1.5, height=0.5, alpha=0.9)

    ax_bar.text(v + 0.002, i, f'{v:.3f}', va='center', fontsize=8, color=COLORS['text'])

ax_bar.set_yticks([])

ax_bar.set_xlabel('Mean |SHAP|', fontsize=9)

ax_bar.spines['top'].set_visible(False)

ax_bar.spines['right'].set_visible(False)

ax_bar.spines['left'].set_visible(False)


fig.tight_layout()

save_fig(fig, 'figures/fig_shap.pdf')

```


---


## 8. Bland-Altman Plot — Bland-Altman 一致性图（分层 CI 带 + 比例偏差线 + 异常值标签）


**场景**: 两种测量方法的一致性评估。医学/工程论文的标准图。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import matplotlib.colors as mcolors

import numpy as np


np.random.seed(42)

method1 = np.random.normal(50, 10, 100)

method2 = method1 + np.random.normal(0.5, 3, 100)

mean_vals = (method1 + method2) / 2

diff_vals = method1 - method2

mean_diff = np.mean(diff_vals)

std_diff = np.std(diff_vals)


fig, ax = plt.subplots(figsize=(7, 5.5))


# Subtle grid

ax.grid(alpha=0.15, linestyle='-', color=COLORS['grid'])

ax.set_axisbelow(True)


# Gradient CI band (fading from center outward)

x_range = np.linspace(mean_vals.min() - 2, mean_vals.max() + 2, 200)

upper = mean_diff + 1.96 * std_diff

lower = mean_diff - 1.96 * std_diff

# Inner band (darker)

ax.fill_between(x_range, mean_diff - 0.5 * std_diff, mean_diff + 0.5 * std_diff,

                alpha=0.15, color=PALETTE[0], label='±0.5 SD')

# Middle band

ax.fill_between(x_range, mean_diff - 1.0 * std_diff, mean_diff + 1.0 * std_diff,

                alpha=0.10, color=PALETTE[0])

# Outer band (lightest)

ax.fill_between(x_range, lower, upper, alpha=0.06, color=PALETTE[3], label='±1.96 SD (95% CI)')


# Scatter points

ax.scatter(mean_vals, diff_vals, color=PALETTE[0], alpha=0.55, s=30,

           edgecolors='white', linewidths=0.5, zorder=3)


# Mean line

ax.axhline(mean_diff, color=PALETTE[0], linestyle='-', linewidth=1.8,

           label=f'Mean bias: {mean_diff:.2f}')

# Limits of agreement

ax.axhline(upper, color=PALETTE[3], linestyle='--', linewidth=1.2,

           label=f'+1.96 SD: {upper:.2f}')

ax.axhline(lower, color=PALETTE[3], linestyle='--', linewidth=1.2,

           label=f'-1.96 SD: {lower:.2f}')


# Proportional bias regression line

z = np.polyfit(mean_vals, diff_vals, 1)

p = np.poly1d(z)

x_fit = np.linspace(mean_vals.min(), mean_vals.max(), 100)

ax.plot(x_fit, p(x_fit), color=COLORS['highlight'], linewidth=1.5, linestyle='-.',

        label=f'Prop. bias (slope={z[0]:.3f})', zorder=4)


# Outlier labels (points beyond ±1.96 SD)

outliers = np.where((diff_vals > upper) | (diff_vals < lower))[0]

for idx in outliers:

    ax.annotate(f'#{idx}', xy=(mean_vals[idx], diff_vals[idx]),

                xytext=(mean_vals[idx] + 1.5, diff_vals[idx] + 0.8),

                fontsize=7, color=COLORS['down'],

                arrowprops=dict(arrowstyle='->', color=COLORS['down'], lw=0.8),

                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',

                          edgecolor=COLORS['down'], alpha=0.9))


ax.set_xlabel('Mean of two methods', fontsize=11)

ax.set_ylabel('Difference (Method 1 − Method 2)', fontsize=11)

ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=7.5, loc='upper left',

          fancybox=True)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_bland_altman.pdf')

```


**⚠ 易踩的坑（Bland-Altman Plot 专用）：**

```python

# 1. 异常值标签用 arrowprops 引线，标签不能离点太远也不能紧贴点位置

# 2. 当异常值聚集时，只标注最突出的 3-5 个，其余用红色圆点标记

# 3. 图例放 upper left（因为通常数据在中间偏右，不会遮挡散点）

# 4. CI 带标签放在图右边缘：ax.text(x_max, upper, ..., ha='left')

```


---


## 9. Calibration Plot — 校准曲线（渐变 CI 带 + 底部直方图 + Brier Score 标注）


**场景**: 概率校准评估。比 ROC 更能反映模型在实际场景中的可靠性。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import matplotlib.gridspec as gridspec

import numpy as np


np.random.seed(42)

bins = np.linspace(0, 1, 11)

bin_centers = (bins[:-1] + bins[1:]) / 2

model_a = np.clip(bin_centers + np.random.uniform(-0.05, 0.05, 10), 0, 1)

model_b = np.clip(bin_centers ** 0.7 + np.random.uniform(-0.03, 0.03, 10), 0, 1)


# Simulated predicted probabilities for histogram

pred_probs_a = np.clip(np.random.beta(2, 2, 500), 0, 1)

pred_probs_b = np.clip(np.random.beta(1.5, 3, 500), 0, 1)


# Brier scores

brier_a = 0.023

brier_b = 0.089


fig = plt.figure(figsize=(6, 7))

gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)


# Top: Calibration curve

ax_cal = fig.add_subplot(gs[0])

ax_cal.grid(alpha=0.15, linestyle='-', color=COLORS['grid'])

ax_cal.set_axisbelow(True)


# Perfect calibration line

ax_cal.plot([0, 1], [0, 1], 'k--', linewidth=0.8, alpha=0.5, label='Perfect')


# Gradient CI band for Model A

ci_width_a = np.random.uniform(0.03, 0.07, 10)

ax_cal.fill_between(bin_centers, model_a - ci_width_a, model_a + ci_width_a,

                     alpha=0.15, color=PALETTE[0])

ax_cal.plot(bin_centers, model_a, 'o-', color=PALETTE[0], linewidth=2.2,

            markersize=7, label=f'Ours (Brier={brier_a:.3f})',

            markeredgecolor='white', markeredgewidth=1.0)


# Gradient CI band for Model B

ci_width_b = np.random.uniform(0.04, 0.09, 10)

ax_cal.fill_between(bin_centers, model_b - ci_width_b, model_b + ci_width_b,

                     alpha=0.12, color=PALETTE[3])

ax_cal.plot(bin_centers, model_b, 's--', color=PALETTE[3], linewidth=2.0,

            markersize=7, label=f'Baseline (Brier={brier_b:.3f})',

            markeredgecolor='white', markeredgewidth=1.0)


# Brier score annotation box

ax_cal.annotate(f'Brier Score\nOurs: {brier_a:.3f}\nBaseline: {brier_b:.3f}',

                xy=(0.05, 0.88), xycoords='axes fraction',

                fontsize=8.5, va='top',

                bbox=dict(boxstyle='round,pad=0.4', facecolor=_lighten(PALETTE[0], 0.7),

                          edgecolor=PALETTE[0], alpha=0.9))


ax_cal.set_ylabel('Fraction of positives', fontsize=11)

ax_cal.set_xlim(0, 1)

ax_cal.set_ylim(0, 1)

ax_cal.set_aspect('equal')

ax_cal.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8.5, loc='lower right')

ax_cal.spines['top'].set_visible(False)

ax_cal.spines['right'].set_visible(False)

ax_cal.set_xticklabels([])


# Bottom: Histogram of predicted probabilities

ax_hist = fig.add_subplot(gs[1])

ax_hist.hist(pred_probs_a, bins=20, alpha=0.5, color=PALETTE[0], label='Ours',

             edgecolor='white', linewidth=0.5)

ax_hist.hist(pred_probs_b, bins=20, alpha=0.4, color=PALETTE[3], label='Baseline',

             edgecolor='white', linewidth=0.5)

ax_hist.set_xlabel('Mean predicted probability', fontsize=11)

ax_hist.set_ylabel('Count', fontsize=10)

ax_hist.set_xlim(0, 1)

ax_hist.legend(frameon=False, fontsize=8)

ax_hist.spines['top'].set_visible(False)

ax_hist.spines['right'].set_visible(False)


fig.tight_layout()

save_fig(fig, 'figures/fig_calibration.pdf')

```


---


## 10. Dot Plot with CI — 点图+置信区间（按显著性渐变着色 + 汇总菱形）


**场景**: 多方法多指标对比。比柱状图信息密度更高——同时展示显著性、汇总估计和各自的置信区间。Nature/Cell 风格。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import matplotlib.colors as mcolors

import numpy as np


methods = ['Ours', 'BERT', 'GPT-4', 'LLaMA', 'T5']

metrics = ['Acc', 'F1', 'Prec', 'Rec']

scores = np.array([[0.92, 0.90, 0.91, 0.89],

                    [0.88, 0.86, 0.89, 0.84],

                    [0.90, 0.88, 0.87, 0.90],

                    [0.85, 0.83, 0.86, 0.81],

                    [0.87, 0.85, 0.88, 0.83]])

ci = np.random.uniform(0.01, 0.03, scores.shape)


# Compute p-values (simulated) for gradient coloring

np.random.seed(42)

pvals = np.random.uniform(0.001, 0.1, scores.shape)

pvals[0, :] = np.random.uniform(0.001, 0.01, 4)  # Ours is most significant


fig, ax = plt.subplots(figsize=(8, 5))


# Subtle grid

ax.grid(axis='x', alpha=0.15, linestyle='-', color=COLORS['grid'])

ax.set_axisbelow(True)


y_base = np.arange(len(methods))

offsets = np.linspace(-0.25, 0.25, len(metrics))


# Gradient colormap for significance

cmap_sig = mcolors.LinearSegmentedColormap.from_list('sig', [COLORS['down'], COLORS['highlight'], COLORS['up']])


for j, metric in enumerate(metrics):

    for i in range(len(methods)):

        # Color by significance (lower p = greener)

        sig_norm = min(pvals[i, j] / 0.1, 1.0)

        dot_color = cmap_sig(1 - sig_norm)

        ax.errorbar(scores[i, j], y_base[i] + offsets[j], xerr=ci[i, j],

                     fmt='o', color=dot_color, markersize=8, capsize=3,

                     linewidth=1.5, markeredgecolor='white', markeredgewidth=0.8,

                     label=metric if i == 0 else '', zorder=3)


# Pooled estimate diamond for each method

pooled = np.mean(scores, axis=1)

pooled_ci = np.mean(ci, axis=1)

for i in range(len(methods)):

    diamond_x = [pooled[i] - pooled_ci[i], pooled[i], pooled[i] + pooled_ci[i], pooled[i]]

    diamond_y = [y_base[i] + 0.35, y_base[i] + 0.42, y_base[i] + 0.35, y_base[i] + 0.28]

    ax.fill(diamond_x, diamond_y, color=PALETTE[0] if i == 0 else COLORS['ref_line'],

            alpha=0.7, zorder=4)

    ax.text(pooled[i] + pooled_ci[i] + 0.008, y_base[i] + 0.35,

            f'{pooled[i]:.3f}', fontsize=7, va='center', color=COLORS['text'])


ax.set_yticks(y_base)

ax.set_yticklabels(methods, fontsize=10)

ax.set_xlabel('Score', fontsize=11)


# Custom legend

from matplotlib.lines import Line2D

legend_elements = [Line2D([0], [0], marker='o', color='w', markerfacecolor=PALETTE[j],

                           markersize=8, label=metrics[j]) for j in range(len(metrics))]

legend_elements.append(Line2D([0], [0], marker='D', color='w', markerfacecolor=COLORS['ref_line'],

                               markersize=8, label='Pooled'))

ax.legend(handles=legend_elements, loc='lower right', frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8, ncol=3)

ax.invert_yaxis()

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_dot_ci.pdf')

```


**⚠ 易踩的坑（Dot Plot with CI 专用）：**

```python

# 1. 数值标签统一放在 CI 右端再偏右：不要放在 CI 内部

# 2. pooled diamond 的标签放在 diamond 右侧：不要放在上方（避免与数据 CI 重叠）

# 3. 自适应高度：_fig_h = max(5, n_studies * 0.4 + 2)

# 4. 基线指标用虚线 axhline，不要用粗横线

```


---


## 11. Cluster Heatmap — 聚类热力图（带树状图 + 聚类边界 + 轮廓系数标注）


**场景**: 基因表达矩阵、特征相关性 + 层次聚类。增加聚类结构信息。

**⚠ 布局**: 只画列方向树状图（不画行方向树状图），避免遮挡 y 轴标签。使用 `fig.add_axes()` 手动分区（不要用 gridspec）。树状图和热力图的 left/width 参数完全一致。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import numpy as np

from scipy.cluster.hierarchy import dendrogram, linkage, fcluster

from scipy.spatial.distance import pdist


np.random.seed(42)

data = np.random.randn(10, 8)

labels_row = [f'Sample-{i+1}' for i in range(10)]

labels_col = [f'Feat-{i+1}' for i in range(8)]


Z_col = linkage(pdist(data.T), method='ward')

Z_row = linkage(pdist(data), method='ward')


n_clusters = 3

col_clusters = fcluster(Z_col, n_clusters, criterion='maxclust')

row_clusters = fcluster(Z_row, n_clusters, criterion='maxclust')


fig = plt.figure(figsize=(10, 8))


# ── 关键：树状图和热力图的 left 和 width 参数完全一致，否则会对不齐

# ── _left 需要足够容纳色条(左侧) + 间距 + y轴标签区域(至少 0.15)

_left = 0.22   # 长文本标签需要更大左边距

_width = 0.56

_cbar_left = _left + _width + 0.03


# 列树状图（只画列方向，不画行方向，避免遮挡标签）

ax_dendro_top = fig.add_axes([_left, 0.86, _width, 0.10])

dn_col = dendrogram(Z_col, ax=ax_dendro_top, leaf_font_size=0,

                     color_threshold=Z_col[-n_clusters + 1, 2],

                     above_threshold_color=COLORS['ref_line'])

ax_dendro_top.set_axis_off()


# Heatmap —— left 和 width 与树状图完全一致

ax_heat = fig.add_axes([_left, 0.08, _width, 0.76])

col_order = dn_col['leaves']

row_order = list(range(len(labels_row)))

ordered_data = data[row_order][:, col_order]


im = ax_heat.imshow(ordered_data, aspect='auto', cmap='coolwarm', interpolation='nearest')

ax_heat.set_xticks(range(len(labels_col)))

ax_heat.set_xticklabels([labels_col[i] for i in col_order], fontsize=8,

                         rotation=45, ha='right')

ax_heat.set_yticks(range(len(labels_row)))

ax_heat.set_yticklabels([labels_row[i] for i in row_order], fontsize=8)


# Cluster boundary lines

sorted_col_clusters = [col_clusters[i] for i in col_order]

for k in range(1, len(sorted_col_clusters)):

    if sorted_col_clusters[k] != sorted_col_clusters[k - 1]:

        ax_heat.axvline(k - 0.5, color='white', linewidth=2.5)

sorted_row_clusters = [row_clusters[i] for i in row_order]

for k in range(1, len(sorted_row_clusters)):

    if sorted_row_clusters[k] != sorted_row_clusters[k - 1]:

        ax_heat.axhline(k - 0.5, color='white', linewidth=2.5)


# Colorbar

ax_cbar = fig.add_axes([_cbar_left, 0.08, 0.02, 0.76])

cbar = plt.colorbar(im, cax=ax_cbar)

cbar.ax.tick_params(labelsize=8)


# Silhouette score annotation

ax_heat.text(0.98, 0.02, 'Silhouette = 0.42',

             transform=ax_heat.transAxes, fontsize=8, ha='right', va='bottom',

             bbox=dict(boxstyle='round,pad=0.3', facecolor=_lighten(PALETTE[0], 0.7),

                       edgecolor=PALETTE[0], alpha=0.9))


save_fig(fig, 'figures/fig_cluster_heatmap.pdf')

```


**⚠ 易踩的坑（聚类热力图专用）：**

```python

# 1. _left 取 0.22，给 y 轴标签 + 左侧色条留够空间（长文本标签需要更多）

# 2. 左侧色条放在 _left-0.05，色条右边界与热力图左边界之间留 0.025 间距

# 3. 树状图和热力图的 left/width 参数完全一致，否则会对不齐

# 4. ★ 行/样本聚类(需要行树状图)：不要把行标签留在左侧——左侧树状图的叶子连线会横穿标签文字。

#    正确做法：行树状图放最左、行标签移到热力图【右侧】(ax_heat.yaxis.tick_right())，两者彻底分开。

#    完整可跑代码见下方「变体：双向聚类热力图(带行树状图 + 标签移右侧)」。

#    (若只做列聚类、行不聚类，仍按上面主配方：只画列树状图、行标签留左侧即可。)

# 5. 不要手动写 fig.tight_layout()。注：save_fig 内部虽会调一次 tight_layout，但对 add_axes 的

#    固定坐标不生效(只打印无害 UserWarning)，手动布局不会被移动——实测保存前后 axes 坐标一致。

# 6. 数值标注颜色需要适应：abs(val)>0.6 用白色字，其余用深色字

# 7. ★ y 标签超长（>20 字符）兜底：调用 auto_truncate_yticklabels(ax_heat, max_chars=18)

#    或在数据准备阶段就用缩写（'avg_silhouette_2024' 而非 'average_silhouette_coefficient_2024'）。

#    plot_utils._save 会在检测到 y label 溢出 figure 左边界时自动截断 + 减字号兜底，

#    但生成阶段就避免超长更稳妥。

# 8. ★ 长标签场景：宽度用 7.0-7.2 英寸（⛔ 上限 7.2，别写 9-10 —— 单栏正文才 6.5in，

#    原生 10in 会被缩到 0.53、刻度 8.5pt 变 4.5pt、线宽腰斩 → 坐标轴糊成一团、线条发虚），

#    并把 _left 提到 0.26-0.30 换取标签空间（7.2×0.28 ≈ 2.0 英寸，够放 18 字符截断后的标签）。

#    figsize=(6, ...) 时即便 _left=0.22 实际像素空间只有 1.3 英寸，长标签必溢出。

#    ⛔ 标签实在放不下就先按第 7 条截断/缩写，不要靠摊大画布 —— 摊得越大缩得越狠，字反而更小。

```


**变体：双向聚类热力图（带行树状图 + 标签移右侧，不糊标签）**


**场景**：需要同时展示**行聚类**(样本/类别聚类)和列聚类，且行标签是中文/长文本。

关键：行树状图放最左，行标签移到热力图**右侧**，两者彻底分开——避免左侧树状图连线横穿标签。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS

setup_style()

import matplotlib.pyplot as plt

import numpy as np

from scipy.cluster.hierarchy import dendrogram, linkage, fcluster

from scipy.spatial.distance import pdist


# data: (n_row, n_col); labels_row 可为中文长标签; z-score 后 vmin/vmax 取 ±2

n_row, n_col = data.shape

Z_row = linkage(pdist(data), method='ward')

Z_col = linkage(pdist(data.T), method='ward')

n_clusters = 3

row_clusters = fcluster(Z_row, n_clusters, criterion='maxclust')

col_clusters = fcluster(Z_col, n_clusters, criterion='maxclust')


fig = plt.figure(figsize=(10, 7))

# 横向分区[左→右]: [行树状图][热力图][右侧标签(自动占位)][色条]

_heat_x, _heat_w, _bottom, _height = 0.19, 0.56, 0.10, 0.72


# 行树状图(左, orientation='left')

ax_dleft = fig.add_axes([0.05, _bottom, 0.12, _height])

dn_row = dendrogram(Z_row, ax=ax_dleft, orientation='left', no_labels=True,

                    color_threshold=Z_row[-n_clusters + 1, 2],

                    above_threshold_color=COLORS['ref_line'])

ax_dleft.invert_yaxis()          # ★ 让叶子[上→下]与 imshow(origin=upper) 同向

ax_dleft.set_axis_off()

row_order = dn_row['leaves']     # ★ invert 后 row_order = leaves 正序(勿加 [::-1]，否则行全错位)


# 列树状图(顶)

ax_dtop = fig.add_axes([_heat_x, 0.84, _heat_w, 0.11])

dn_col = dendrogram(Z_col, ax=ax_dtop, no_labels=True,

                    color_threshold=Z_col[-n_clusters + 1, 2],

                    above_threshold_color=COLORS['ref_line'])

ax_dtop.set_axis_off()

col_order = dn_col['leaves']


# 热力图(left/width 与列树状图完全一致，才对得齐)

ax_heat = fig.add_axes([_heat_x, _bottom, _heat_w, _height])

im = ax_heat.imshow(data[np.ix_(row_order, col_order)], aspect='auto',

                    cmap='coolwarm', interpolation='nearest', vmin=-2, vmax=2)

# ★ 行标签移到右侧，彻底避开左侧树状图连线

ax_heat.set_yticks(range(n_row))

ax_heat.set_yticklabels([labels_row[i] for i in row_order], fontsize=9)

ax_heat.yaxis.tick_right()

ax_heat.yaxis.set_tick_params(length=0)   # 去刻度线只留文字

ax_heat.set_xticks(range(n_col))

ax_heat.set_xticklabels([labels_col[i] for i in col_order], fontsize=8, rotation=45, ha='right')

for s in ax_heat.spines.values():

    s.set_visible(False)


# 聚类分界白线

srow = [row_clusters[i] for i in row_order]

for k in range(1, n_row):

    if srow[k] != srow[k - 1]:

        ax_heat.axhline(k - 0.5, color='white', linewidth=2.5)

scol = [col_clusters[i] for i in col_order]

for k in range(1, n_col):

    if scol[k] != scol[k - 1]:

        ax_heat.axvline(k - 0.5, color='white', linewidth=2.5)


# 色条(最右, 给右侧标签留出 0.75→0.90 的空间)

ax_cbar = fig.add_axes([0.90, _bottom, 0.02, _height])

cbar = plt.colorbar(im, cax=ax_cbar); cbar.ax.tick_params(labelsize=8)

cbar.set_label('成分含量 (列 z-score)', fontsize=9)


save_fig(fig, 'figures/fig_cluster_heatmap.pdf')

```


**⚠ 变体专用坑（已实跑验证）：**

```python

# A. ★★ row_order = dn_row['leaves'] 正序！配 invert_yaxis() 才对齐。

#    误写 leaves[::-1] 会让每一行的标签与数据错位(比"线穿字"更隐蔽、更严重)。

#    自检口诀: 若行有单调趋势(如亮度递增), 出图应看到从上到下大致分组连续。

# B. 行标签一定 yaxis.tick_right()；留在左侧必被树状图连线穿过(用户实测踩坑)。

# C. 右侧中文长标签: 色条左边界(0.90) 与热力图右边界(0.75) 之间留 0.15 给标签。

#    标签更长(>8 中文字)就把色条推到 0.92 或调小 _heat_w。

# D. 行/列树状图的 left/width 必须分别等于热力图的 left/width，否则叶子与格子对不齐。

```


---


## 12. Network Graph — 网络图（节点大小映射度 + 社区凸包 + 边权渐变）


**场景**: 引用网络、知识图谱、社交网络、因果关系。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import matplotlib.colors as mcolors

import numpy as np


try:

    import networkx as nx

except ImportError:

    import subprocess, sys

    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'networkx', '-q'])

    import networkx as nx


from scipy.spatial import ConvexHull


G = nx.karate_club_graph()

communities = list(nx.community.greedy_modularity_communities(G))


# Assign community colors

color_map = {}

for i, comm in enumerate(communities):

    for node in comm:

        color_map[node] = i

node_colors = [PALETTE[color_map[n] % len(PALETTE)] for n in G.nodes()]


# Node sizing by degree

degrees = dict(G.degree())

max_deg = max(degrees.values())

node_sizes = [400 * degrees[n] / max_deg + 80 for n in G.nodes()]


fig, ax = plt.subplots(figsize=(8, 7))

pos = nx.spring_layout(G, seed=42, k=0.5)


# Draw convex hulls for communities

for i, comm in enumerate(communities):

    if len(comm) >= 3:

        points = np.array([pos[n] for n in comm])

        try:

            hull = ConvexHull(points)

            hull_points = points[hull.vertices]

            # Close the polygon

            hull_points = np.vstack([hull_points, hull_points[0]])

            # Expand hull slightly

            centroid = points.mean(axis=0)

            expanded = centroid + 1.15 * (hull_points - centroid)

            ax.fill(expanded[:, 0], expanded[:, 1],

                    color=PALETTE[i % len(PALETTE)], alpha=0.08)

            ax.plot(expanded[:, 0], expanded[:, 1],

                    color=PALETTE[i % len(PALETTE)], linewidth=1.5,

                    linestyle='--', alpha=0.4)

        except Exception:

            pass


# Edge weight gradient

edges = G.edges()

edge_weights = [G[u][v].get('weight', 1) for u, v in edges]

max_w = max(edge_weights) if edge_weights else 1

cmap_edge = mcolors.LinearSegmentedColormap.from_list('ew', [_lighten(PALETTE[0], 0.8), COLORS['ref_line']])

for (u, v), w in zip(edges, edge_weights):

    x0, y0 = pos[u]

    x1, y1 = pos[v]

    norm_w = w / max_w

    ax.plot([x0, x1], [y0, y1], color=cmap_edge(norm_w),

            linewidth=0.5 + 1.5 * norm_w, alpha=0.3 + 0.4 * norm_w, zorder=1)


# Draw nodes

nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=node_sizes,

                        edgecolors='white', linewidths=1.2, alpha=0.9, zorder=3)


# Labels for high-degree nodes only

high_deg_nodes = {n: str(n) for n in G.nodes() if degrees[n] >= 4}

nx.draw_networkx_labels(G, pos, labels=high_deg_nodes, ax=ax,

                         font_size=7, font_color=COLORS['text'], font_weight='bold')


# Legend for communities

from matplotlib.lines import Line2D

legend_elements = [Line2D([0], [0], marker='o', color='w',

                           markerfacecolor=PALETTE[i % len(PALETTE)],

                           markersize=10, label=f'Community {i+1}')

                   for i in range(len(communities))]

ax.legend(handles=legend_elements, loc='upper left', frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8, fancybox=True)


ax.set_axis_off()

fig.tight_layout()

save_fig(fig, 'figures/fig_network.pdf')

```


**⚠ 易踩的坑（Network Graph 专用）：**

```python

# 1. 节点标签用 bbox 白底，防止和边线混在一起

# 2. 边权重标签只标注权重 > 中位数的边，不要每条边都标

# 3. 社区凸包用极浅色填充（alpha=0.08），不要遮挡节点和标签

# 4. 节点太密集时，fontsize 缩到 7，且只标注度数 top-5 的节点

```


---


## 13. Method Comparison Heatmap — 方法对比热力图（排名标注 🥇🥈🥉 + 树状图 + 列最优高亮 + 综合排名）


**场景**: 多方法 × 多指标对比矩阵。比柱状图更紧凑。Nature/Cell 风格。

**风格**: YlOrRd heatmap + 浅色填充+原色边框 用于列最优单元格 + 排名奖牌。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import numpy as np

from scipy.cluster.hierarchy import dendrogram, linkage

from scipy.spatial.distance import pdist


methods = ['Ours', 'LSTM', 'Random Forest', 'Linear Reg']

metrics = ['MAE', 'RMSE', 'R2', 'MAPE(%)', 'Speed']

# Lower is better for MAE/RMSE/MAPE, higher for R2/Speed

data = np.array([

    [0.29, 1.05, 0.987, 2.1, 0.85],

    [72.23, 85.4, 0.812, 15.3, 0.60],

    [0.45, 1.82, 0.965, 3.8, 0.92],

    [137.08, 152.3, 0.421, 48.2, 0.98],

])

higher_better = [False, False, True, False, True]


# Rank medals

rank_symbols = ['🥇', '🥈', '🥉', '④']


# Normalize for color mapping

norm_data = np.zeros_like(data)

for j in range(data.shape[1]):

    col = data[:, j]

    if higher_better[j]:

        norm_data[:, j] = (col - col.min()) / (col.max() - col.min() + 1e-10)

    else:

        norm_data[:, j] = 1 - (col - col.min()) / (col.max() - col.min() + 1e-10)


# Compute overall ranking (average normalized rank)

overall_rank_score = np.mean(norm_data, axis=1)


# Add overall ranking column

metrics_ext = metrics + ['Overall']

data_ext = np.column_stack([data, overall_rank_score])

norm_ext = np.column_stack([norm_data, overall_rank_score / overall_rank_score.max()])


fig = plt.figure(figsize=(9, 4.5))


# Dendrogram on top

ax_dendro = fig.add_axes([0.15, 0.82, 0.65, 0.14])

Z = linkage(pdist(norm_data), method='ward')

dn = dendrogram(Z, labels=methods, ax=ax_dendro, leaf_font_size=0,

                color_threshold=0, above_threshold_color=COLORS['ref_line'])

ax_dendro.set_axis_off()

row_order = dn['leaves']


# Heatmap

ax = fig.add_axes([0.15, 0.12, 0.72, 0.68])

ordered_norm = norm_ext[row_order]

ordered_data = data_ext[row_order]

ordered_methods = [methods[i] for i in row_order]


im = ax.imshow(ordered_norm, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)

ax.set_xticks(range(len(metrics_ext)))

ax.set_xticklabels(metrics_ext, fontsize=10)

ax.set_yticks(range(len(methods)))

ax.set_yticklabels(ordered_methods, fontsize=10)


# Annotate with values, ranks, and 浅色填充+原色边框 for best

for j in range(len(metrics_ext)):

    if j < len(metrics):

        col_vals = data[:, j]

        if higher_better[j]:

            rank_order = np.argsort(-col_vals)

        else:

            rank_order = np.argsort(col_vals)

    else:

        rank_order = np.argsort(-overall_rank_score)


    for i_orig, rank_pos in enumerate(rank_order):

        # Find position in ordered display

        i_display = row_order.index(rank_pos)

        if j < len(metrics):

            val_str = f'{data[rank_pos, j]:.2f}'

        else:

            val_str = f'{overall_rank_score[rank_pos]:.2f}'


        rank_idx = i_orig

        rank_label = rank_symbols[rank_idx] if rank_idx < len(rank_symbols) else ''


        color = 'white' if ordered_norm[i_display, j] > 0.75 or ordered_norm[i_display, j] < 0.25 else 'black'

        weight = 'bold' if rank_idx == 0 else 'normal'


        ax.text(j, i_display, f'{val_str}\n{rank_label}', ha='center', va='center',

                fontsize=8.5, fontweight=weight, color=color)


        # 列最优：浅色填充背景 + 原色粗边框

        if rank_idx == 0:

            rect = plt.Rectangle((j - 0.5, i_display - 0.5), 1, 1,

                                  linewidth=2.5, edgecolor=PALETTE[0],

                                  facecolor=_lighten(PALETTE[0], 0.5),

                                  alpha=0.3, zorder=4)

            ax.add_patch(rect)

            # 原色边框（不透明）

            rect_border = plt.Rectangle((j - 0.5, i_display - 0.5), 1, 1,

                                         linewidth=2.5, edgecolor=PALETTE[0],

                                         facecolor='none', zorder=5)

            ax.add_patch(rect_border)


ax.spines[:].set_visible(False)


# Colorbar

ax_cbar = fig.add_axes([0.89, 0.12, 0.02, 0.68])

cbar = plt.colorbar(im, cax=ax_cbar)

cbar.set_label('Normalized (1=best)', fontsize=8)

cbar.ax.tick_params(labelsize=7)


save_fig(fig, 'figures/fig_method_heatmap.pdf')

```


---


## 14. Parallel Coordinates — 平行坐标图（实线 + "本文"高亮 + 最优区域阴影）


**场景**: 多方法 × 多指标对比。每个指标是一条纵轴，每个方法是一条折线。交叉和分离一目了然。


```python

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()

import matplotlib.pyplot as plt

import numpy as np


methods = ['Ours', 'LSTM', 'Random Forest', 'Linear Reg']

metrics = ['MAE↓', 'RMSE↓', 'R²↑', 'Speed↑', 'Stability↑']

# All normalized to [0,1] where 1=best

data = np.array([

    [0.95, 0.92, 0.987, 0.85, 0.90],

    [0.45, 0.50, 0.812, 0.60, 0.65],

    [0.88, 0.82, 0.965, 0.92, 0.78],

    [0.10, 0.15, 0.421, 0.98, 0.55],

])


fig, ax = plt.subplots(figsize=(9, 5))

x = np.arange(len(metrics))


# Subtle grid

ax.grid(axis='y', alpha=0.15, linestyle='-', color=COLORS['grid'])

ax.set_axisbelow(True)


# Optimal region shading per axis (top 20%)

for j in range(len(metrics)):

    ax.fill_between([j - 0.3, j + 0.3], 0.8, 1.0, alpha=0.06,

                     color=COLORS['up'], zorder=0)

    ax.text(j, 0.82, '最优区', ha='center', fontsize=6, color=COLORS['up'],

            alpha=0.6, fontstyle='italic')


# Draw simple lines per method

for i, (method, row) in enumerate(zip(methods, data)):

    is_ours = (i == 0)


    if is_ours:

        # Thick solid line for "Ours"

        ax.plot(x, row, '-', color=PALETTE[0], linewidth=3.5, zorder=5,

                solid_capstyle='round')

        # Markers

        ax.scatter(x, row, color=PALETTE[0], s=100, zorder=6,

                   edgecolors='white', linewidths=1.5, marker='o')

        # Value labels

        for j, v in enumerate(row):

            ax.text(j, v + 0.04, f'{v:.2f}', ha='center', fontsize=8.5,

                    color=PALETTE[0], fontweight='bold')

        # Highlight label

        ax.text(x[-1] + 0.25, row[-1], f'★ {method}', va='center', fontsize=10,

                color=PALETTE[0], fontweight='bold')

    else:

        # Simple line for other methods

        ax.plot(x, row, '-', color=PALETTE[i], linewidth=1.5, alpha=0.6,

                solid_capstyle='round')

        ax.scatter(x, row, color=PALETTE[i], s=50, zorder=4, alpha=0.7,

                   edgecolors='white', linewidths=0.8)

        ax.text(x[-1] + 0.25, row[-1], method, va='center', fontsize=8.5,

                color=PALETTE[i], alpha=0.8)


ax.set_xticks(x)

ax.set_xticklabels(metrics, fontsize=10.5)

ax.set_ylabel('归一化得分 (1=最优)', fontsize=11)

ax.set_ylim(0, 1.12)

ax.set_xlim(-0.4, len(metrics) - 0.3)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_parallel_coords.pdf')

```


---


## 15. PCA Biplot — PCA 双标图（载荷箭头 + 智能标签 + 解释方差）


**场景**: 降维可视化、特征贡献分析。多元分析章节常用。

**防重叠**: 使用 `smart_labels()` 自动推开重叠的特征名标签——当多个载荷方向相近时尤为关键。


```python

import numpy as np

import matplotlib.pyplot as plt

import matplotlib.colors as mcolors

from _utils.plot_utils import setup_style, save_fig, PALETTE, smart_labels, auto_legend

setup_style()


# === Example data (replace with your PCA results) ===

np.random.seed(42)

n_samples, n_features = 80, 12

feature_names = ['市场规模', '供应链成熟度', '短期恢复能力', '响应梯度元素',

                 '长期恢复速度', '研发投入强度', '短期恢复弹性', '产能利用率',

                 '短期集中度', '专利授权量', '产业链完整度', '客户集中度']


# Simulated PCA scores and loadings

scores = np.random.randn(n_samples, 2) * 2

loadings = np.random.randn(n_features, 2)

loadings = loadings / np.abs(loadings).max(axis=0) * 3  # scale to [-3, 3]

explained_var = [66.3, 11.4]  # explained variance %


fig, ax = plt.subplots(figsize=(8, 7))


# Scatter: sample scores (gray, semi-transparent)

ax.scatter(scores[:, 0], scores[:, 1], s=25, alpha=0.35, color=COLORS['gray'],

           edgecolors='white', linewidths=0.3, zorder=2)


# Loading arrows

arrow_colors = []

for i, (name, lx, ly) in enumerate(zip(feature_names, loadings[:, 0], loadings[:, 1])):

    magnitude = np.sqrt(lx**2 + ly**2)

    color = PALETTE[0]

    arrow_colors.append(color)

    ax.annotate('', xy=(lx, ly), xytext=(0, 0),

                arrowprops=dict(arrowstyle='->', color=color, lw=1.5, alpha=0.7))


# ── 特征名标签 —— smart_labels 自动推开重叠标签

# Offset labels slightly beyond arrow tips

label_xs = [lx * 1.08 for lx in loadings[:, 0]]

label_ys = [ly * 1.08 for ly in loadings[:, 1]]

smart_labels(ax, label_xs, label_ys, feature_names,

             colors=arrow_colors, fontsize=8.5, fontweight='bold',

             offset=(5, 0),

             bbox=dict(boxstyle='round,pad=0.2', facecolor='white',

                       edgecolor=PALETTE[0], alpha=0.8, linewidth=0.5),

             arrowprops=dict(arrowstyle='-', color=COLORS['grid'], lw=0.4),

             force_text=0.8, force_points=0.5)


# Reference lines

ax.axhline(0, color=COLORS['ref_line'], linewidth=0.5, alpha=0.4)

ax.axvline(0, color=COLORS['ref_line'], linewidth=0.5, alpha=0.4)


ax.set_xlabel(f'PC1 ({explained_var[0]:.1f}%)', fontsize=11)

ax.set_ylabel(f'PC2 ({explained_var[1]:.1f}%)', fontsize=11)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

ax.grid(alpha=0.1, linestyle='--')

fig.tight_layout()

save_fig(fig, 'figures/fig_pca_biplot.pdf')

```


**⚠ 易踩的坑（PCA Biplot 专用）：**

```python

# 1. Loading 箭头标签必须用 smart_labels()，箭头方向相近时标签一定会重叠

# 2. 箭头标签用白底 bbox，防止与散点混在一起

# 3. 散点用小尺寸（s=15-25）+ 低 alpha（0.4），给箭头和标签腾出视觉空间

# 4. 特征过多时，只标注最长的箭头，其余用数字 text 标注

```


---


## 16. Diverging Bar Chart — 发散柱状图（淡色填充 + 原色边框 + 相对基线 + 颜色编码方向 + 数值标签）


**场景**: 展示每个方法/变体相对于基线的表现（正值=更好，负值=更差）。比分组柱状图更清晰地传达"改进 vs 退化"的信息。常见于消融实验和敏感性分析。

**风格**: 方向性颜色背景区 + 浅色填充+原色边框柱体 + 阴影加粗 + 方向标注。


```python

import numpy as np

import matplotlib.pyplot as plt

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten, smart_labels

setup_style()


methods = ['Ours (full)', 'w/o Attention', 'w/o Pretrain', 'w/o Augment',

           'Baseline-A', 'Baseline-B', 'Baseline-C']

deltas = [+5.2, +3.1, +1.8, +0.5, 0.0, -1.3, -2.7]


# ── 自适应高度

_fig_h = max(4, len(methods) * 0.7 + 1)

fig, ax = plt.subplots(figsize=(8, _fig_h))

y_pos = np.arange(len(methods))


# 方向性颜色背景

ax.axvspan(0, max(deltas)*1.3, alpha=0.05, color=COLORS['up'], zorder=0)

ax.axvspan(min(deltas)*1.3, 0, alpha=0.05, color=COLORS['down'], zorder=0)


# Color: positive = up(green), negative = down(red)

base_colors = [COLORS['up'] if d >= 0 else COLORS['down'] for d in deltas]


# 柱体阴影

ax.barh(y_pos + 0.03, deltas, height=0.5, color='#cccccc', alpha=0.1, zorder=1)

# ── 主柱体：浅色填充 + 原色边框

bars = ax.barh(y_pos, deltas, height=0.5,

               color=[_lighten(c, 0.4) for c in base_colors],

               edgecolor=base_colors, linewidth=1.5, zorder=3)


# Zero reference line

ax.axvline(0, color=COLORS['text'], linewidth=1.2, zorder=2)


# Value labels at bar ends（白底保护）

for i, (bar, d) in enumerate(zip(bars, deltas)):

    x_pos = d + (0.2 if d >= 0 else -0.2)

    ha = 'left' if d >= 0 else 'right'

    sign = '+' if d > 0 else ''

    ax.text(x_pos, y_pos[i], f'{sign}{d:.1f}%', va='center', ha=ha,

            fontsize=9, fontweight='bold', color=base_colors[i],

            bbox=dict(boxstyle='round,pad=0.1', facecolor='white', edgecolor='none', alpha=0.7))


# Highlight "Ours" row

ax.axhspan(y_pos[0]-0.35, y_pos[0]+0.35, alpha=0.06, color=PALETTE[0], zorder=0)

bars[0].set_edgecolor(PALETTE[0]); bars[0].set_linewidth(2.0)


# 方向标注

ax.text(0.98, 0.02, '更优 →', transform=ax.transAxes, fontsize=8, ha='right',

        color=COLORS['up'], fontweight='bold')

ax.text(0.02, 0.02, '← 更差', transform=ax.transAxes, fontsize=8, ha='left',

        color=COLORS['down'], fontweight='bold')


ax.set_yticks(y_pos)

ax.set_yticklabels(methods, fontsize=10)

ax.set_xlabel('Relative Improvement over Baseline (%)', fontsize=11)

ax.invert_yaxis()

ax.grid(axis='x', alpha=0.12, linestyle='--', color=COLORS['grid'])

ax.spines['left'].set_visible(False)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_diverging_bar.pdf')

```


---


## 17. Back-to-Back Bar Chart — 背靠背柱状图（浅色填充 + 原色边框 + 镜像对比 + 共享 Y 轴 + 差值标签）


**场景**: 两组/两种条件的镜像对比。经典"人口金字塔"风格。适合前后对比、男/女、训练/测试或任何二分对比。


```python

import numpy as np

import matplotlib.pyplot as plt

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()


categories = ['Accuracy', 'Precision', 'Recall', 'F1', 'AUC', 'MCC']

group_a = [92.3, 89.1, 94.5, 91.7, 96.2, 88.4]  # e.g., "Ours"

group_b = [87.5, 84.2, 90.1, 87.0, 93.1, 82.6]  # e.g., "Baseline"


# ── 自适应高度

_fig_h = max(4, len(categories) * 0.7 + 1)

fig, ax = plt.subplots(figsize=(8, _fig_h))

y_pos = np.arange(len(categories))


# ── 左侧（负方向）= Group B —— 浅色填充 + 原色边框

bars_b = ax.barh(y_pos, [-v for v in group_b], height=0.55,

                 color=_lighten(PALETTE[1], 0.4), edgecolor=PALETTE[1],

                 linewidth=1.2, label='Baseline', zorder=3)

# ── 右侧（正方向）= Group A —— 浅色填充 + 原色边框

bars_a = ax.barh(y_pos, group_a, height=0.55,

                 color=_lighten(PALETTE[0], 0.4), edgecolor=PALETTE[0],

                 linewidth=1.2, label='Ours', zorder=3)


# Value labels

for i in range(len(categories)):

    ax.text(group_a[i] + 0.5, y_pos[i], f'{group_a[i]:.1f}',

            va='center', ha='left', fontsize=8.5, color=PALETTE[0], fontweight='bold')

    ax.text(-group_b[i] - 0.5, y_pos[i], f'{group_b[i]:.1f}',

            va='center', ha='right', fontsize=8.5, color=PALETTE[1], fontweight='bold')

    # Gap label in center

    gap = group_a[i] - group_b[i]

    sign = '+' if gap > 0 else ''

    ax.text(0, y_pos[i], f'{sign}{gap:.1f}', va='center', ha='center',

            fontsize=7.5, fontweight='bold', color=COLORS['text'],

            bbox=dict(boxstyle='round,pad=0.2', facecolor='white',

                      edgecolor=COLORS['grid'], alpha=0.9))


ax.set_yticks(y_pos)

ax.set_yticklabels(categories, fontsize=10)

ax.axvline(0, color=COLORS['text'], linewidth=0.8)

ax.set_xlabel('Score (%)', fontsize=11)

ax.legend(loc='lower right', fontsize=9, frameon=False, edgecolor=COLORS['grid'])


# Clean up x-axis to show absolute values

ticks = ax.get_xticks()

ax.set_xticklabels([f'{abs(t):.0f}' for t in ticks])

ax.invert_yaxis()

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

ax.grid(axis='x', alpha=0.1, linestyle='--')

fig.tight_layout()

save_fig(fig, 'figures/fig_back2back.pdf')

```


---


## 18. Paired Dot Plot — 配对点图（个体变化连线 + 均值偏移箭头 + 显著性）


**场景**: 展示配对观测（同一受试者/样本在两种条件下的值）。每条线连接同一实体的前后值，揭示分组柱状图隐藏的个体差异。常见于医学、A/B 测试和实验设计论文。


```python

import numpy as np

import matplotlib.pyplot as plt

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS

setup_style()


np.random.seed(42)

n = 20

labels = ['Before', 'After']

before = np.random.normal(75, 8, n)

after = before + np.random.normal(5, 4, n)  # general improvement with variance


fig, ax = plt.subplots(figsize=(5, 6))


# Individual paired lines

for i in range(n):

    color = PALETTE[0] if after[i] > before[i] else PALETTE[1]

    ax.plot([0, 1], [before[i], after[i]], color=color, alpha=0.35,

            linewidth=1.2, zorder=2)

    ax.scatter([0, 1], [before[i], after[i]], color=color, s=30,

               edgecolors='white', linewidths=0.5, zorder=3, alpha=0.6)


# Mean markers (large, prominent)

mean_before, mean_after = before.mean(), after.mean()

ax.scatter(0, mean_before, s=200, color=PALETTE[1], marker='D',

           edgecolors='white', linewidths=2, zorder=5, label=f'Mean Before: {mean_before:.1f}')

ax.scatter(1, mean_after, s=200, color=PALETTE[0], marker='D',

           edgecolors='white', linewidths=2, zorder=5, label=f'Mean After: {mean_after:.1f}')


# Mean shift arrow

ax.annotate('', xy=(1, mean_after), xytext=(0, mean_before),

            arrowprops=dict(arrowstyle='->', color=COLORS['text'], lw=2.5,

                            connectionstyle='arc3,rad=0.15'))

delta = mean_after - mean_before

ax.text(0.5, (mean_before + mean_after) / 2 + 2,

        f'Δ = +{delta:.1f}', ha='center', fontsize=10, fontweight='bold',

        color=PALETTE[0],

        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',

                  edgecolor=PALETTE[0], alpha=0.9))


# Significance annotation

from scipy import stats

t_stat, p_val = stats.ttest_rel(after, before)

sig_text = f'p = {p_val:.4f}' if p_val >= 0.001 else 'p < 0.001'

ax.text(0.5, max(max(before), max(after)) + 4, sig_text,

        ha='center', fontsize=9, fontstyle='italic', color=COLORS['text'])


ax.set_xticks([0, 1])

ax.set_xticklabels(labels, fontsize=12, fontweight='bold')

ax.set_ylabel('Score', fontsize=11)

ax.set_xlim(-0.4, 1.4)

ax.legend(loc='lower right', fontsize=8, frameon=False, edgecolor=COLORS['grid'])

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

ax.grid(axis='y', alpha=0.1, linestyle='--')

fig.tight_layout()

save_fig(fig, 'figures/fig_paired_dot.pdf')

```


**⚠ 易踩的坑（Paired Dot Plot 专用）：**

```python

# 1. 显著性标注不要与数据点重叠：放在 y 位置 = max(data) + offset

# 2. 均值偏移箭头放在图右侧空白区域，不要穿过数据点之间

# 3. 个体变化线用低 alpha（0.3），不要遮挡均值标记

# 4. p 值标注放在数据上方（fontsize=8），不要太大

```


---


## 19. Ridgeline Plot — 山脊图（堆叠分布对比 + 渐变填充 + 中位数线）


**场景**: 在紧凑布局中比较多组（5-15 组）的分布。每组有自己的密度曲线，垂直方向略有重叠。比多个直方图或小提琴图更节省空间。在数据新闻和学术论文中越来越流行。


```python

import numpy as np

import matplotlib.pyplot as plt

from scipy.stats import gaussian_kde

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()


np.random.seed(42)

groups = ['Model A', 'Model B', 'Model C', 'Model D', 'Model E',

          'Model F', 'Model G', 'Model H']

n_groups = len(groups)


# Generate sample data (replace with real data)

data = []

for i in range(n_groups):

    center = 70 + i * 3 + np.random.randn() * 2

    spread = 5 + np.random.rand() * 5

    d = np.random.normal(center, spread, 200)

    data.append(d)


fig, ax = plt.subplots(figsize=(8, 6))

overlap = 0.6  # vertical overlap factor

x_grid = np.linspace(min(d.min() for d in data) - 5,

                      max(d.max() for d in data) + 5, 300)


for i in range(n_groups - 1, -1, -1):  # draw back to front

    kde = gaussian_kde(data[i], bw_method=0.3)

    density = kde(x_grid)

    # Normalize density to consistent height

    density = density / density.max() * 0.8


    baseline = i * overlap

    color = PALETTE[i % len(PALETTE)]

    light = _lighten(color, 0.5)


    # Gradient fill

    ax.fill_between(x_grid, baseline, baseline + density,

                    color=light, alpha=0.85, zorder=n_groups - i)

    ax.plot(x_grid, baseline + density, color=color, linewidth=1.5,

            zorder=n_groups - i + 0.5)


    # Median line

    median = np.median(data[i])

    med_density = kde(median)[0] / density.max() * 0.8

    ax.plot([median, median], [baseline, baseline + med_density],

            color=color, linewidth=1.5, linestyle='--', alpha=0.7,

            zorder=n_groups - i + 1)

    ax.text(median, baseline + med_density + 0.02,

            f'{median:.1f}', ha='center', fontsize=7, color=color,

            fontweight='bold', zorder=n_groups + 10)


    # Group label

    ax.text(x_grid[0] - 1, baseline + 0.15, groups[i],

            ha='right', va='center', fontsize=9, fontweight='bold',

            color=color)


ax.set_yticks([])

ax.set_xlabel('Score', fontsize=11)

ax.spines['left'].set_visible(False)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

fig.tight_layout()

save_fig(fig, 'figures/fig_ridgeline.pdf')

```


**⚠ 易踩的坑（Ridgeline Plot 专用）：**

```python

# 1. 相邻密度曲线的 y 间距 ≥ 2.5：太密会导致曲线互相遮挡

# 2. 中位数线标签放在曲线右侧：不要放在曲线内部

# 3. Shapiro-Wilk 标注放在数据右端再偏右：用 bbox 白底

# 4. 组数 >8 时，自适应高度 _fig_h = max(6, n_groups * 1.2 + 1)

```


---


## 20. Grouped Violin Plot (Multi-Group Distribution Comparison + Median + Quartile Lines)


**Use case**: Compare distribution shapes across 2-4 groups for multiple categories. More compact than Rain Cloud when you have many categories. Shows full distribution shape unlike box plots.


```python

import numpy as np

import matplotlib.pyplot as plt

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten

setup_style()


np.random.seed(42)

categories = ['Dataset A', 'Dataset B', 'Dataset C', 'Dataset D']

group_names = ['Ours', 'Baseline-1', 'Baseline-2']

n_groups = len(group_names)


# Generate sample data (replace with real results)

all_data = {}

for g, gname in enumerate(group_names):

    all_data[gname] = []

    for c in range(len(categories)):

        center = 80 + g * (-3) + c * 2 + np.random.randn()

        d = np.random.normal(center, 3 + g, 50)

        all_data[gname].append(d)


fig, ax = plt.subplots(figsize=(9, 5))

width = 0.25

positions_base = np.arange(len(categories))


for g, gname in enumerate(group_names):

    positions = positions_base + (g - n_groups / 2 + 0.5) * width

    color = PALETTE[g % len(PALETTE)]

    light = _lighten(color, 0.4)


    parts = ax.violinplot(all_data[gname], positions=positions,

                          widths=width * 0.85, showmeans=False,

                          showmedians=False, showextrema=False)


    for pc in parts['bodies']:

        pc.set_facecolor(light)

        pc.set_edgecolor(color)

        pc.set_linewidth(1.2)

        pc.set_alpha(0.8)


    # Add median + quartile lines manually

    for i, d in enumerate(all_data[gname]):

        q1, med, q3 = np.percentile(d, [25, 50, 75])

        pos = positions[i]

        # Median dot

        ax.scatter(pos, med, color=color, s=30, zorder=5,

                   edgecolors='white', linewidths=0.8)

        # Quartile whisker

        ax.vlines(pos, q1, q3, color=color, linewidth=2.5, zorder=4)


    # Invisible scatter for legend

    ax.scatter([], [], color=color, s=60, label=gname, edgecolors='white')


ax.set_xticks(positions_base)

ax.set_xticklabels(categories, fontsize=10)

ax.set_ylabel('Score', fontsize=11)

ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=9)

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

ax.grid(axis='y', alpha=0.1, linestyle='--')

fig.tight_layout()

save_fig(fig, 'figures/fig_grouped_violin.pdf')

```


---


## 21. Fan Chart — 预测扇形图（多层 CI 带 + 历史/预测分隔 + 中位数线）


**场景**: 经济预测、能源需求、流行病传播、气候情景。央行（英格兰银行）首创的可视化标准。多层颜色带 50% / 80% / 95% 分位数，历史区实线，预测区虚线/中心。


```python

import numpy as np

import matplotlib.pyplot as plt

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten


setup_style()

np.random.seed(42)


# === 模拟时序：历史 24 个月 + 预测 12 个月 ===

n_hist = 24; n_pred = 12

t = np.arange(n_hist + n_pred)

hist = 100 + np.cumsum(np.random.normal(0, 1.5, n_hist))

# 预测：均值随机游走，方差随时间扩散

pred_mean = hist[-1] + np.cumsum(np.random.normal(0.3, 0.5, n_pred))

pred_std = np.sqrt(np.arange(1, n_pred + 1)) * 1.6   # 不确定性随时间增长


# 预测分位数

quantiles = {

    'p05': pred_mean - 1.96 * pred_std, 'p95': pred_mean + 1.96 * pred_std,

    'p10': pred_mean - 1.28 * pred_std, 'p90': pred_mean + 1.28 * pred_std,

    'p25': pred_mean - 0.67 * pred_std, 'p75': pred_mean + 0.67 * pred_std,

}


fig, ax = plt.subplots(figsize=(8, 4.5))


# === 历史段：实线 ===

ax.plot(t[:n_hist], hist, color=COLORS['text'], linewidth=1.8, zorder=4, label='历史值')

ax.scatter(t[n_hist-1], hist[-1], s=50, color=COLORS['text'], zorder=5,

           edgecolor='white', linewidth=1)


# === 预测段：多层 CI 带（外到内 alpha 递增）===

t_pred = t[n_hist-1:]

# 拼接：起点用历史最后值，让带子接续

pred_full = np.concatenate(([hist[-1]], pred_mean))

quant_full = {k: np.concatenate(([hist[-1]], v)) for k, v in quantiles.items()}


# 5%-95%（外层，最浅）

ax.fill_between(t_pred, quant_full['p05'], quant_full['p95'],

                color=_lighten(PALETTE[0], 0.65), alpha=0.55, linewidth=0,

                label='95% 区间', zorder=1)

# 10%-90%

ax.fill_between(t_pred, quant_full['p10'], quant_full['p90'],

                color=_lighten(PALETTE[0], 0.4), alpha=0.7, linewidth=0,

                label='80% 区间', zorder=2)

# 25%-75%（内层，最深）

ax.fill_between(t_pred, quant_full['p25'], quant_full['p75'],

                color=_lighten(PALETTE[0], 0.2), alpha=0.8, linewidth=0,

                label='50% 区间', zorder=3)

# 中位数预测线（虚线区别历史）

ax.plot(t_pred, pred_full, color=PALETTE[0], linewidth=1.8, linestyle='--', zorder=4,

        label='中位数预测')


# === 历史/预测分隔线 ===

ax.axvline(n_hist - 1, color=COLORS['ref_line'], linestyle=':', linewidth=1.1, alpha=0.6)

ax.text(n_hist - 1, ax.get_ylim()[1] * 0.97 if False else hist.max() * 1.02,

        '预测起点', fontsize=8, ha='center', va='bottom',

        color=COLORS['ref_line'], style='italic',

        bbox=dict(boxstyle='round,pad=0.2', facecolor='white',

                  edgecolor=COLORS['grid'], alpha=0.9, linewidth=0.4))


# === 终点不确定性范围标注 ===

y_min = quant_full['p05'][-1]; y_max = quant_full['p95'][-1]

ax.annotate('', xy=(t[-1] + 0.2, y_min), xytext=(t[-1] + 0.2, y_max),

            arrowprops=dict(arrowstyle='<->', color=COLORS['highlight'], lw=1.2))

ax.text(t[-1] + 0.8, (y_min + y_max) / 2,

        f'95% 跨度\n{y_max - y_min:.1f}', fontsize=8, va='center',

        color=COLORS['highlight'], fontweight='bold',

        bbox=dict(boxstyle='round,pad=0.2', facecolor='white',

                  edgecolor=COLORS['highlight'], alpha=0.9, linewidth=0.5))


ax.set_xlabel('时间（月）', fontsize=10)

ax.set_ylabel('指标值', fontsize=10)

ax.legend(loc='upper left', frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8, ncol=2)

ax.grid(axis='y', alpha=0.12, linestyle='--', color=COLORS['grid'])

ax.spines['top'].set_visible(False)

ax.spines['right'].set_visible(False)

ax.set_xlim(0, t[-1] + 3)

fig.tight_layout()

save_fig(fig, 'figures/fig_fan_chart.pdf')

```


**★ 设计要点：**

- **多层 CI 用 `_lighten(PALETTE[0], k)` 渐变** 而非透明度叠加（避免颜色脏）

- **历史 实线 + 预测 虚线**：让读者一眼区分"已知"和"推断"

- **分隔线 + 文字标签**：明确"哪里开始是预测"


---


## 22. Calendar Heatmap — 日历热图（一年 7×53 网格 + 月份分隔 + 顶部色条）


**场景**: 时序观察（每日数据：交易量、能耗、降雨、用户活跃）。GitHub 贡献图风格。一眼看出周期性 / 节假日 / 异常日。


```python

import numpy as np

import matplotlib.pyplot as plt

from matplotlib.patches import Rectangle

from matplotlib.colors import LinearSegmentedColormap

from datetime import date, timedelta

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten


setup_style()

np.random.seed(42)


# === 模拟一年的日数据（周末偏低，月底偏高，几个事件峰值）===

start = date(2024, 1, 1)

n_days = 366

daily = np.random.gamma(2.0, 1.2, n_days)  # 基线

for i in range(n_days):

    d = start + timedelta(days=i)

    if d.weekday() >= 5: daily[i] *= 0.55  # 周末

    if d.day >= 28: daily[i] *= 1.3  # 月底

# 几个事件峰值

for ev in [40, 95, 180, 290]:

    daily[ev:ev+3] *= 2.5


# === 转 7×53 矩阵：行=周中第几天（周一-周日），列=年中第几周 ===

grid = np.full((7, 54), np.nan)

month_starts = []  # 记录每月第一天位置（用于画分隔线）

for i in range(n_days):

    d = start + timedelta(days=i)

    week = int(d.strftime('%W'))  # ISO 周

    weekday = d.weekday()  # 0=Mon

    grid[weekday, week] = daily[i]

    if d.day == 1:

        month_starts.append((d.month, week, weekday))


# === 主色调渐变 colormap（用 PALETTE[0] 的浅→深）===

base = PALETTE[0]

cmap_calendar = LinearSegmentedColormap.from_list(

    'cal', [_lighten(base, 0.92), _lighten(base, 0.5), base, _lighten(base, -0.15) if False else base],

    N=128

)


fig, ax = plt.subplots(figsize=(11, 2.6))

im = ax.imshow(grid, aspect='equal', cmap=cmap_calendar, vmin=0,

               vmax=np.nanpercentile(grid, 98))


# === 月份分隔线 + 月名标注 ===

month_names = ['1月', '2月', '3月', '4月', '5月', '6月',

               '7月', '8月', '9月', '10月', '11月', '12月']

for m, wk, _ in month_starts:

    ax.axvline(wk - 0.5, color=COLORS['grid'], linewidth=0.8, alpha=0.5)

    ax.text(wk + 0.5, -1.0, month_names[m - 1], fontsize=8,

            ha='left', va='center', color=COLORS['text'])


# === Y 轴：仅显示 Mon / Wed / Fri ===

ax.set_yticks([0, 2, 4, 6])

ax.set_yticklabels(['周一', '周三', '周五', '周日'], fontsize=8)

ax.set_xticks([])

ax.tick_params(axis='y', length=0)

for spine in ax.spines.values(): spine.set_visible(False)


# === 顶部 colorbar（横向）===

cbar = fig.colorbar(im, ax=ax, orientation='horizontal', shrink=0.35,

                    pad=0.25, aspect=30)

cbar.set_label('日均值', fontsize=8)

cbar.ax.tick_params(labelsize=7, length=0)

cbar.outline.set_linewidth(0)


# === 异常日（top 1%）标注 ===

threshold = np.nanpercentile(daily, 99)

outliers_idx = np.where(daily > threshold)[0]

for idx in outliers_idx[:5]:  # 最多标 5 个

    d = start + timedelta(days=int(idx))

    wk = int(d.strftime('%W')); wd = d.weekday()

    ax.add_patch(Rectangle((wk - 0.45, wd - 0.45), 0.9, 0.9,

                            fill=False, edgecolor=COLORS['highlight'],

                            linewidth=1.3, zorder=5))


fig.tight_layout()

save_fig(fig, 'figures/fig_calendar_heatmap.pdf')

```


**★ 设计要点：**

- **方形 cell**（`aspect='equal'`）— GitHub 风格视觉一致性

- **月名只标月初**，不要每周一标 — 避免拥挤

- **异常日用 PALETTE 高亮色描边**，不抢色阶主轴


---


## 23. Pair Plot / Scatter Matrix — 配对图（对角线 KDE + 上三角相关系数 + 下三角散点拟合）


**场景**: 多变量数据探索（统计、社科、生信）。N×N 网格，对角线显示边际分布，下三角散点+回归线，上三角相关系数（按强度上色）。


```python

import numpy as np

import matplotlib.pyplot as plt

from scipy.stats import gaussian_kde, pearsonr

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten


setup_style()

np.random.seed(42)


# === 模拟 4 个变量（含正/负/弱相关）===

n = 250

v1 = np.random.normal(0, 1, n)

v2 = 0.75 * v1 + np.random.normal(0, 0.55, n)        # 强正相关

v3 = -0.55 * v1 + 0.3 * v2 + np.random.normal(0, 0.7, n)  # 中等负相关

v4 = np.random.normal(0, 1, n)                        # 弱相关

data = np.column_stack([v1, v2, v3, v4])

names = ['X1', 'X2', 'X3', 'X4']

N = len(names)


fig, axes = plt.subplots(N, N, figsize=(8.5, 8.5))


for i in range(N):

    for j in range(N):

        ax = axes[i, j]

        if i == j:

            # ★ 对角线：直方图 + KDE

            ax.hist(data[:, i], bins=22, color=_lighten(PALETTE[i % len(PALETTE)], 0.55),

                    edgecolor=PALETTE[i % len(PALETTE)], linewidth=0.5, alpha=0.85)

            ax2 = ax.twinx()

            xg = np.linspace(data[:, i].min(), data[:, i].max(), 200)

            ax2.plot(xg, gaussian_kde(data[:, i])(xg),

                     color=PALETTE[i % len(PALETTE)], linewidth=1.5)

            ax2.set_yticks([])

            ax2.spines['top'].set_visible(False)

            ax2.spines['right'].set_visible(False)

            ax2.spines['left'].set_visible(False)

            ax.text(0.05, 0.92, names[i], transform=ax.transAxes,

                    fontsize=11, fontweight='bold', color=PALETTE[i % len(PALETTE)],

                    va='top', ha='left')

        elif i > j:

            # ★ 下三角：散点 + 拟合线

            ax.scatter(data[:, j], data[:, i], s=10, alpha=0.35,

                       color=PALETTE[0], edgecolor='white', linewidth=0.2)

            # 简易线性拟合

            slope, intercept = np.polyfit(data[:, j], data[:, i], 1)

            xfit = np.linspace(data[:, j].min(), data[:, j].max(), 60)

            yfit = slope * xfit + intercept

            ax.plot(xfit, yfit, color=COLORS['highlight'], linewidth=1.4,

                    alpha=0.85, zorder=5)

        else:

            # ★ 上三角：相关系数（按强度上色 + 字号映射强度）

            r, p = pearsonr(data[:, j], data[:, i])

            # 强度映射到背景颜色

            if r > 0:

                bg = _lighten(PALETTE[0], 1 - abs(r) * 0.7)

            else:

                bg = _lighten(COLORS['down'], 1 - abs(r) * 0.7)

            ax.set_facecolor(bg)

            sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else ''))

            fs = 10 + abs(r) * 12  # 字号随 |r| 增大

            ax.text(0.5, 0.55, f'{r:+.2f}', transform=ax.transAxes,

                    fontsize=fs, fontweight='bold',

                    color=COLORS['text'], ha='center', va='center')

            if sig:

                ax.text(0.5, 0.18, sig, transform=ax.transAxes,

                        fontsize=11, color=COLORS['text'], ha='center')


        # 仅在最下/最左行留刻度

        if i < N - 1:

            ax.tick_params(axis='x', labelbottom=False)

        else:

            ax.tick_params(labelsize=7)

        if j > 0:

            ax.tick_params(axis='y', labelleft=False)

        else:

            ax.tick_params(labelsize=7)

        if i != j:

            ax.spines['top'].set_visible(False)

            ax.spines['right'].set_visible(False)

            ax.grid(alpha=0.08, linestyle='--', color=COLORS['grid'])


fig.tight_layout(pad=0.4)

save_fig(fig, 'figures/fig_pair_plot.pdf')

```


**★ 设计要点：**

- **对角线 KDE 用 twinx** 叠加，避免抢直方图高度

- **上三角相关系数字号映射 |r|**：强相关一眼可见

- **背景色饱和度映射 |r|**：从浅到深直观展示

- **下三角 alpha=0.35** 让密集区显得"实"，稀疏区显得"虚"


---


## 24. Triptych — 三联图（input / 中间表示 / output 横向对比 + 流向箭头）


**场景**: CV / NLP / AI 定性结果展示。三个等宽子图横向并列，子图间用箭头暗示数据流，共享色标（如适用）。


```python

import numpy as np

import matplotlib.pyplot as plt

from matplotlib.gridspec import GridSpec

from matplotlib.patches import FancyArrowPatch

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten


setup_style()

np.random.seed(42)


# === 模拟数据：输入图 / 注意力图 / 输出图 ===

H, W = 80, 80

y, x = np.mgrid[0:H, 0:W]

input_img = np.exp(-((x - 28)**2 + (y - 32)**2) / 250) + \

            0.6 * np.exp(-((x - 52)**2 + (y - 48)**2) / 200) + \

            np.random.normal(0, 0.04, (H, W))

attention = np.exp(-((x - 40)**2 + (y - 40)**2) / 500) * (input_img > 0.2)

output_img = input_img * attention * 1.6


# === 1 行 3 列 + 上方薄色条 ===

fig = plt.figure(figsize=(9, 4))

gs = GridSpec(2, 3, height_ratios=[0.5, 6], hspace=0.05, wspace=0.12)


titles = ['(a) 输入', '(b) 注意力图', '(c) 重构输出']

images = [input_img, attention, output_img]

v = max(np.max(im) for im in images)


axes_img = []

for col in range(3):

    ax = fig.add_subplot(gs[1, col])

    im = ax.imshow(images[col], cmap='viridis', vmin=0, vmax=v,

                   interpolation='bilinear')

    ax.set_title(titles[col], fontsize=11, fontweight='bold',

                 color=COLORS['text'], pad=8)

    ax.axis('off')

    axes_img.append((ax, im))


# === 顶部共享色条 ===

cbar_ax = fig.add_subplot(gs[0, :])

cbar = fig.colorbar(axes_img[0][1], cax=cbar_ax, orientation='horizontal')

cbar.set_label('归一化激活', fontsize=8)

cbar.ax.tick_params(labelsize=7, length=2)

cbar.outline.set_linewidth(0.4)

cbar.outline.set_edgecolor(COLORS['grid'])


# === 子图间流向箭头（用 figure-level transform）===

def add_arrow(fig, axL, axR, label=None):

    bbL = axL.get_position(); bbR = axR.get_position()

    y_mid = (bbL.y0 + bbL.y1) / 2

    arrow = FancyArrowPatch((bbL.x1 + 0.005, y_mid), (bbR.x0 - 0.005, y_mid),

                             transform=fig.transFigure,

                             arrowstyle='->', mutation_scale=14,

                             color=COLORS['highlight'], linewidth=1.5,

                             clip_on=False)

    fig.patches.append(arrow)

    if label:

        fig.text((bbL.x1 + bbR.x0) / 2, y_mid + 0.04, label,

                 fontsize=8, ha='center', color=COLORS['highlight'],

                 fontweight='bold', style='italic')


add_arrow(fig, axes_img[0][0], axes_img[1][0], 'Encoder')

add_arrow(fig, axes_img[1][0], axes_img[2][0], 'Decoder')


save_fig(fig, 'figures/fig_triptych.pdf')

```


**★ 设计要点：**

- **GridSpec 控制顶部 colorbar + 三子图**：保证 colorbar 跨越三列

- **`axis('off')` + `set_title()`**：图像类子图统一约定

- **箭头用 `fig.transFigure`** 而非 axes 坐标，跨子图绘制

- **`vmin=0, vmax=v` 跨子图统一**：让 colorbar 对所有子图有意义


---


## 25. Streamgraph — 流图（居中堆叠基线 + 多类别 + 末端标签）


**场景**: 时序中多类别的相对占比变化（话题趋势、技术栈、人口构成）。居中基线让单类别波动看起来"自然"，比传统堆叠图更动态。


```python

import numpy as np

import matplotlib.pyplot as plt

from scipy.ndimage import gaussian_filter1d

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten


setup_style()

np.random.seed(42)


# === 模拟 5 个类别在 50 个时间点的数值 ===

n_t = 50; n_cat = 5

t = np.arange(n_t)

# 每个类别有不同的生命周期形状

shapes = [

    20 + 30 * np.exp(-((t - 20)**2) / 250),                # 凸起在中间

    10 + 15 * (1 / (1 + np.exp(-0.2 * (t - 25)))),         # 后期增长

    25 - 20 * (1 / (1 + np.exp(-0.2 * (t - 15)))) + 5,     # 早期衰退

    18 * np.sin(t * 0.3) ** 2 + 5,                         # 周期波动

    12 + np.random.normal(0, 2, n_t)                        # 平稳基线

]

data = np.array([gaussian_filter1d(s, sigma=2) for s in shapes])

data = np.clip(data, 0.5, None)  # 保证非负


# === 居中基线：每个时刻总值除以 2，作为偏移 ===

total = data.sum(axis=0)

baseline = -total / 2  # 起点放底，向上堆叠

fig, ax = plt.subplots(figsize=(9, 4.5))


names = ['类别 A', '类别 B', '类别 C', '类别 D', '类别 E']

cumsum = baseline.copy()

for i, (vals, name) in enumerate(zip(data, names)):

    color = PALETTE[i % len(PALETTE)]

    ax.fill_between(t, cumsum, cumsum + vals,

                    color=_lighten(color, 0.25), alpha=0.88,

                    edgecolor=color, linewidth=0.5, label=name)

    # ★ 末端标签：放在每条流带末端的中心

    end_mid = cumsum[-1] + vals[-1] / 2

    ax.text(t[-1] + 0.7, end_mid, name, fontsize=8, va='center',

            color=color, fontweight='bold',

            bbox=dict(boxstyle='round,pad=0.18', facecolor='white',

                      edgecolor=color, alpha=0.9, linewidth=0.5))

    cumsum += vals


# 中心参考线

ax.axhline(0, color=COLORS['ref_line'], linewidth=0.5, alpha=0.4, linestyle='-')


ax.set_xlabel('时间', fontsize=10)

ax.set_yticks([])  # 居中堆叠图通常省略 y 轴刻度（数值由颜色面积表达）

ax.set_xlim(t[0], t[-1] + 7)

for sp in ['top', 'right', 'left']: ax.spines[sp].set_visible(False)

ax.tick_params(axis='y', length=0)

ax.grid(axis='x', alpha=0.08, linestyle='--', color=COLORS['grid'])


# 顶部小注释解释读法

ax.text(0.02, 0.97, '流带厚度 = 该时刻的数值；垂直位置无意义',

        transform=ax.transAxes, fontsize=7, color=COLORS['text'],

        style='italic', va='top',

        bbox=dict(boxstyle='round,pad=0.2', facecolor='white',

                  edgecolor=COLORS['grid'], alpha=0.85, linewidth=0.3))


fig.tight_layout()

save_fig(fig, 'figures/fig_streamgraph.pdf')

```


**★ 设计要点：**

- **居中基线 `baseline = -total / 2`** 是 streamgraph 的关键 — 让单类别波动看起来自然

- **`gaussian_filter1d`** 平滑边界 — 避免毛刺感

- **末端标签** 比 legend 更好看 — 让读者眼睛跟着流走到尽头

- **`set_yticks([])`** — y 轴无意义，强制省略避免误导


---


## 26. Bivariate Choropleth / 双变量热图 — 二维联合分布（3×3 配色矩阵 + 主图 + 图例）


**场景**: 双变量空间分布（社会-经济、风险-暴露、降水-气温）。一个图同时表达两个变量的高/中/低组合。配 3×3 颜色矩阵作图例。


```python

import numpy as np

import matplotlib.pyplot as plt

from matplotlib.gridspec import GridSpec

from matplotlib.colors import LinearSegmentedColormap

from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten


setup_style()

np.random.seed(42)


# === 模拟 2 个变量在 30×30 网格上的取值 ===

N = 30

y, x = np.mgrid[0:N, 0:N]

var_a = np.exp(-((x - 10)**2 + (y - 12)**2) / 100) + 0.3 * np.random.rand(N, N)

var_b = np.exp(-((x - 20)**2 + (y - 22)**2) / 120) + 0.3 * np.random.rand(N, N)

var_a = (var_a - var_a.min()) / (var_a.max() - var_a.min())

var_b = (var_b - var_b.min()) / (var_b.max() - var_b.min())


# === 3×3 双变量配色（X 维度用 PALETTE[0] 渐变，Y 维度用 PALETTE[1] 渐变，组合产生中间色）===

def bivariate_color(a, b):

    """a, b in [0,1] -> RGB. 用两个主色的加权混合。"""

    c1 = np.array([int(PALETTE[0].lstrip('#')[i:i+2], 16)/255 for i in (0,2,4)])  # 蓝

    c2 = np.array([int(PALETTE[1].lstrip('#')[i:i+2], 16)/255 for i in (0,2,4)])  # 橙

    base = np.array([0.97, 0.97, 0.97])  # 浅灰底

    return base * (1 - 0.5*a - 0.5*b) + c1 * 0.5*a + c2 * 0.5*b


# 量化到 3×3 等级

qa = np.clip(np.digitize(var_a, np.quantile(var_a, [0.33, 0.67])), 0, 2)

qb = np.clip(np.digitize(var_b, np.quantile(var_b, [0.33, 0.67])), 0, 2)


# 构造 RGB 图像

rgb = np.zeros((N, N, 3))

for i in range(N):

    for j in range(N):

        rgb[i, j] = bivariate_color(qa[i, j] / 2, qb[i, j] / 2)


# === 主图 + 右下小图例（3×3 矩阵）===

fig = plt.figure(figsize=(7.5, 5))

gs = GridSpec(1, 2, width_ratios=[3, 1], wspace=0.15)

ax_main = fig.add_subplot(gs[0, 0])

ax_main.imshow(rgb, origin='lower', interpolation='nearest')

ax_main.set_xlabel('经度网格', fontsize=10)

ax_main.set_ylabel('纬度网格', fontsize=10)

ax_main.set_title('双变量空间分布', fontsize=11, color=COLORS['text'], pad=6)

ax_main.tick_params(labelsize=8)

for sp in ax_main.spines.values(): sp.set_edgecolor(COLORS['grid']); sp.set_linewidth(0.5)


# === 3×3 图例矩阵 ===

ax_leg = fig.add_subplot(gs[0, 1])

legend_grid = np.zeros((3, 3, 3))

for i in range(3):

    for j in range(3):

        legend_grid[2-i, j] = bivariate_color(j / 2, i / 2)

ax_leg.imshow(legend_grid, origin='lower', interpolation='nearest')

ax_leg.set_xticks([0, 1, 2]); ax_leg.set_yticks([0, 1, 2])

ax_leg.set_xticklabels(['低', '中', '高'], fontsize=8)

ax_leg.set_yticklabels(['低', '中', '高'], fontsize=8)

ax_leg.set_xlabel('变量 A →', fontsize=9, color=PALETTE[0], fontweight='bold')

ax_leg.set_ylabel('变量 B →', fontsize=9, color=PALETTE[1], fontweight='bold')

ax_leg.set_title('图例', fontsize=9, color=COLORS['text'], pad=4)

for sp in ax_leg.spines.values(): sp.set_edgecolor(COLORS['grid']); sp.set_linewidth(0.5)

ax_leg.tick_params(length=0)


# 在图例每格中标"AaBb"短标识

for i in range(3):

    for j in range(3):

        ax_leg.text(j, 2-i, f'A{j+1}B{i+1}', ha='center', va='center',

                    fontsize=7, color=COLORS['text'], fontweight='bold')


fig.tight_layout()

save_fig(fig, 'figures/fig_bivariate.pdf')

```


**★ 设计要点：**

- **3×3 矩阵图例** 是双变量图的灵魂 — 没图例读者完全不知道颜色含义

- **PALETTE[0] (蓝) + PALETTE[1] (橙) 混合** 自动产生 9 种和谐组合

- **`np.digitize` 量化到 3 等级** — 让色块离散，避免连续色混乱

- **图例每格写 AaBb 标识** — 比纯配色更清楚

---

## 27. Significance Bar — 显著性柱状图（误差棒 + 星号 + 显著性连线）

**场景**: 多组方法对比，要同时展示均值、误差与组间显著性（AI 顶会/实验部分标配）。比"只有误差棒"更硬核。
**⚠ 关键要点**: 误差棒用 SEM（标准误）或 95% CI，注明在图注；星号按 p 值分档（***<0.001 / **<0.01 / *<0.05 / n.s.）；显著性连线高度按从低到高错开，避免重叠。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS
setup_style()
import matplotlib.pyplot as plt
import numpy as np

groups = ['Ours', 'Baseline-A', 'Baseline-B', 'Baseline-C', 'Baseline-D']
means = [0.923, 0.887, 0.862, 0.841, 0.815]
sems  = [0.011, 0.014, 0.016, 0.018, 0.020]
x = np.arange(len(groups))

fig, ax = plt.subplots(figsize=(6.0, 4.2))
bars = ax.bar(x, means, yerr=sems, capsize=3, width=0.62,
              color=[PALETTE[0]] + [PALETTE[1]]*(len(groups)-1),
              error_kw=dict(lw=1.0))
ax.bar_label(bars, fmt='%.3f', fontsize=8, padding=3)

def stars(p): return '***' if p<0.001 else ('**' if p<0.01 else ('*' if p<0.05 else 'n.s.'))
ps  = [0.0001, 0.0012, 0.004, 0.02]                      # Ours vs 各基线
y_max = max(m+s for m, s in zip(means, sems))
step, h = y_max*0.09, y_max*0.05
for i, p in enumerate(ps, start=1):                       # 第 i 根连线，高度递增错开
    y = y_max + step*i
    ax.plot([0, 0, i, i], [y, y+h, y+h, y], lw=1.0, color=COLORS['text'])
    ax.text(i/2, y+h, stars(p), ha='center', va='bottom', fontsize=9)

ax.set_xticks(x); ax.set_xticklabels(groups, fontsize=9)
ax.set_ylabel('Accuracy', fontsize=10)
ax.set_ylim(0, y_max + step*(len(ps)+1) + h + y_max*0.08)
ax.set_xticklabels(groups, rotation=12, fontsize=8)
fig.tight_layout()
save_fig(fig, 'figures/fig_sigbar.pdf')
```

## 28. Forest Plot — 森林图（效应量/回归系数 + CI 汇总）

**场景**: 把多个变量/模型的效应量（回归系数、OR、风险比）与置信区间画在同一横轴上，一目了然。用于灵敏度、变量重要性、元分析。
**⚠ 关键要点**: 零点参考线必画；点=点估计、线=CI；按效应量排序；CI 过宽标"不可靠"。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS
setup_style()
import matplotlib.pyplot as plt
import numpy as np

names = ['Temp', 'Humidity', 'Wind', 'Pressure', 'Aerosol']
coef  = [0.42, -0.31, 0.18, -0.12, 0.05]
ci_lo = [0.35, -0.40, 0.10, -0.22, -0.08]
ci_hi = [0.49, -0.22, 0.26, -0.02, 0.18]
y_pos = np.arange(len(names))[::-1]

fig, ax = plt.subplots(figsize=(6.0, 3.8))
ax.axvline(0, color=COLORS['text'], lw=0.8, ls='--', alpha=0.5)
for y, c, lo, hi in zip(y_pos, coef, ci_lo, ci_hi):
    ax.plot([lo, hi], [y, y], lw=2.4, color=PALETTE[1], solid_capstyle='round')
    ax.scatter([c], [y], s=48, color=PALETTE[0], zorder=3)
    ax.annotate(f'{c:.2f} [{lo:.2f}, {hi:.2f}]', xy=(hi, y), xytext=(6, 0),
                textcoords='offset points', fontsize=8, color=COLORS['text'])
ax.set_yticks(y_pos); ax.set_yticklabels(names, fontsize=9)
ax.set_xlabel('Effect size (95% CI)', fontsize=10)
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_forest.pdf')
```

## 29. CUSUM Chart — 累积和图（过程漂移/突变点监测）

**场景**: 监控"过程中途是否发生突变"（如设备劣化、网购行为变化、疫情阶段切换）。比逐点折线更能放大微小偏移。
**⚠ 关键要点**: CUSUM = 相对目标值偏差的累加；斜率突然变大 = 发生漂移，在图上标注变点位置；配合控制限 h=5σ。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS
setup_style()
import matplotlib.pyplot as plt
import numpy as np

rng = np.random.default_rng(42)
n, mu0, sigma, delta = 120, 50.0, 3.0, 1.5          # 60 点后均值偏移 +1.5σ
y = np.r_[rng.normal(mu0, sigma, 60), rng.normal(mu0+delta, sigma, n-60)]
cusum = np.cumsum(y - mu0)
t = np.arange(1, n+1)
h = 5 * sigma                                          # 控制限

fig, ax = plt.subplots(figsize=(6.0, 3.6))
ax.plot(t, cusum, color=PALETTE[0], lw=1.6)
ax.axhline(h, color=COLORS['red'], lw=0.8, ls='--'); ax.axhline(-h, color=COLORS['red'], lw=0.8, ls='--')
idx = np.argmax(cusum > h) if np.any(cusum > h) else None
if idx is not None:
    ax.axvline(t[idx], color=PALETTE[1], lw=1.2, ls=':')
    ax.annotate('drift onset ≈ t={}'.format(t[idx]), xy=(t[idx], cusum[idx]),
                xytext=(10, -14), textcoords='offset points', fontsize=8, color=PALETTE[1])
ax.set_xlabel('t'); ax.set_ylabel('CUSUM')
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_cusum.pdf')
```

## 30. Quantile Trend Band — 分位数趋势带（mean±Q1/Q3 平滑带）

**场景**: 多次重复运行取均值的表现（收敛曲线/误差曲线），同时展示波动范围，让"复现性"可视化。比单线±1σ 更抗离群。
**⚠ 关键要点**: 中线=中位数（或均值），带=Q1–Q3（或 5–95 分位），别用 min/max（被离群撑爆）。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, _lighten
setup_style()
import matplotlib.pyplot as plt
import numpy as np

runs = 30; steps = 200
rng = np.random.default_rng(0)
trajs = np.cumsum(rng.normal(0, 1, (runs, steps)) / np.sqrt(np.arange(1, steps+1)), axis=1)
dom = np.arange(steps)
med = np.percentile(trajs, 50, axis=0)
q1  = np.percentile(trajs, 25, axis=0)
q3  = np.percentile(trajs, 75, axis=0)

fig, ax = plt.subplots(figsize=(6.0, 3.6))
ax.fill_between(dom, q1, q3, color=_lighten(PALETTE[0], 0.35), lw=0, alpha=0.75)
ax.plot(dom, med, color=PALETTE[0], lw=1.8)
ax.plot(dom, np.percentile(trajs, 5, axis=0), color=PALETTE[1], lw=0.8, alpha=.6)
ax.plot(dom, np.percentile(trajs, 95, axis=0), color=PALETTE[1], lw=0.8, alpha=.6)
ax.set_xlabel('iteration'); ax.set_ylabel('metric')
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_qband.pdf')
```

## 31. Q-Q Plot — 分位数-分位数图（分布假设检验）

**场景**: 检验数据是否符合正态/某分布，或两分布是否同分布。回归/ANOVA 前必查"残差正态性"。
**⚠ 关键要点**: 理论分位 vs 样本分位；贴合 y=x 直线=符合分布；尾部偏离=肥尾/离群；配 Shapiro/KS 统计量一起报告。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS
setup_style()
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

x = np.random.default_rng(1).normal(0, 1, 200)         # 换成真实残差
os, os_sorted = stats.probplot(x, dist='norm', plot=None)
theoretical = np.sort(stats.norm.ppf((np.arange(1, len(x)+1)-0.5)/len(x)))

fig, ax = plt.subplots(figsize=(3.8, 3.8))
ax.scatter(theoretical, os_sorted, s=14, color=PALETTE[0], alpha=.8)
slope, intercept, r, _, _ = stats.linregress(theoretical, os_sorted)
lim = ax.get_xlim() if False else None
xs = np.linspace(theoretical.min(), theoretical.max(), 50)
ax.plot(xs, intercept + slope*xs, color=PALETTE[1], lw=1.4)
ax.set_xlabel('Theoretical quantiles'); ax.set_ylabel('Sample quantiles')
ax.text(0.05, 0.92, f'R² = {r**2:.3f}', transform=ax.transAxes, fontsize=9,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_qq.pdf')
```

## 32. ECDF — 经验累积分布图（两分布整体对比）

**场景**: 不想分箱就看"谁整体更大/更分散"——ECDF 一图包含全部分位，两分布对比无需核密度选择。
**⚠ 关键要点**: 用 sort 后的值绘阶梯线；多条曲线对比时颜色区分+图例；可标注"某分位差"（如 90th 分位差）。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE
setup_style()
import matplotlib.pyplot as plt
import numpy as np

rng = np.random.default_rng(2)
a = rng.normal(0, 1, 500); b = rng.normal(0.4, 1.1, 500)

def _ecdf(v):
    s = np.sort(v); return s, np.arange(1, len(v)+1)/len(v)

fig, ax = plt.subplots(figsize=(6.0, 3.6))
for data, c, lb in [(a, PALETTE[0], 'Method A'), (b, PALETTE[1], 'Method B')]:
    s, p = _ecdf(data)
    ax.step(s, p, where='post', color=c, lw=1.8, label=lb)
ax.axhline(0.9, color='gray', lw=0.8, ls=':')
s_a, _ = _ecdf(a)
ax.annotate('90th pct', xy=(np.percentile(a, 90), 0.9), xytext=(8, -4),
            textcoords='offset points', fontsize=8)
ax.set_xlabel('value'); ax.set_ylabel('CDF')
ax.legend(frameon=False, fontsize=9)
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_ecdf.pdf')
```

## 33. Joint Plot — 联合分布图（散点 + 边缘直方/密度）

**场景**: 双变量关系要同时看"散点形态 + 单变量边缘分布"。回归分析/特征相关性展示的"信息密度"担当。
**⚠ 关键要点**: 用 GridSpec 放大图 + 左右/上边缘直方；边缘分布用直方（密度需选带宽，易误导）。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE
setup_style()
import matplotlib.pyplot as plt
import numpy as np

rng = np.random.default_rng(3)
X = rng.normal(0, 1, 800); Y = 0.8*X + rng.normal(0, 0.5, 800)

fig = plt.figure(figsize=(5.6, 5.0))
gs = fig.add_gridspec(2, 2, width_ratios=(4, 1), height_ratios=(1, 4),
                      wspace=0.05, hspace=0.05)
ax = fig.add_subplot(gs[1, 0]); ax_top = fig.add_subplot(gs[0, 0], sharex=ax)
ax_ri = fig.add_subplot(gs[1, 1], sharey=ax)

ax.scatter(X, Y, s=6, color=PALETTE[0], alpha=.45)
ax_top.hist(X, bins=40, color=PALETTE[1], alpha=.8)
ax_ri.hist(Y, bins=40, color=PALETTE[1], alpha=.8, orientation='horizontal')
for a in (ax_top, ax_ri):
    a.axis('off')
ax.set_xlabel('X'); ax.set_ylabel('Y')
fig.tight_layout()
save_fig(fig, 'figures/fig_joint.pdf')
```

## 34. Residual Diagnostics — 残差诊断四联图（回归模型体检）

**场景**: 回归/拟合完成后的"体检报告"：残差是否有模式、是否正态、异方差、是否有强影响点。四联图是统计论文的标配。
**⚠ 关键要点**: 四个子图：残差 vs 拟合值（应无结构）、Q-Q 正态（此前 recipe#39）、尺度位置（|残差|^0.5 vs 拟合）、杠杆-残差（Cook 距离圈）；异常点标 ID。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS
setup_style()
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

rng = np.random.default_rng(4)
X = rng.uniform(0, 10, 150)
y = 2.5 + 1.3*X + rng.normal(0, 1.2, 150)
slope, intercept, r, p, se = stats.linregress(X, y)
fit = intercept + slope*X
resid = y - fit
lev = 1/len(X) + (X - X.mean())**2 / np.sum((X - X.mean())**2)   # 杠杆值

fig, axes = plt.subplots(2, 2, figsize=(6.4, 5.4))
axes[0, 0].scatter(fit, resid, s=12, color=PALETTE[0], alpha=.7)
axes[0, 0].axhline(0, color='gray', lw=0.8, ls='--')
axes[0, 0].set_title('Residuals vs Fitted', fontsize=9)
os, os_sorted = stats.probplot(resid, dist='norm', plot=None)
axes[0, 1].scatter(os[0], os_sorted, s=12, color=PALETTE[0], alpha=.7)
axes[0, 1].set_title('Normal Q-Q', fontsize=9)
axes[1, 0].scatter(fit, np.sqrt(np.abs(resid)), s=12, color=PALETTE[0], alpha=.7)
axes[1, 0].set_title('Scale-Location', fontsize=9)
axes[1, 1].scatter(lev, resid, s=12, color=PALETTE[0], alpha=.7)
axes[1, 1].axhline(0, color='gray', lw=0.8, ls='--')
axes[1, 1].set_title('Leverage vs Residual', fontsize=9)
for a in axes.flat:
    a.tick_params(labelsize=8); a.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_resid.pdf')
```

## 35. Significance Heatmap — 相关显著性热力图（数值 + p 值星号）

**场景**: 多变量相关矩阵，直接标 r 值还不够——把显著性也叠上去（* p<0.05 等），比"纯热力"更有统计说服力。
**⚠ 关键要点**: 上三角标 r、下三角用星号（或统一标 r + 星号）；对角线下三角留白更克制；色标范围固定 -1..1。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE
setup_style()
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

rng = np.random.default_rng(5)
vars_ = ['A', 'B', 'C', 'D', 'E']
D = rng.normal(0, 1, (120, 5))
D[:, 2] = 0.7*D[:, 0] + 0.3*rng.normal(0, 1, 120)
n = D.shape[1]
R = np.corrcoef(D.T)

def sg(p): return '***' if p < .001 else ('**' if p < .01 else ('*' if p < .05 else ''))
fig, ax = plt.subplots(figsize=(5.4, 4.6))
im = ax.imshow(R, cmap='RdBu_r', vmin=-1, vmax=1)
for i in range(n):
    for j in range(n):
        r = R[i, j]
        if i < j:
            _, p = stats.pearsonr(D[:, i], D[:, j])
            ax.text(j, i, f'{r:.2f}{sg(p)}', ha='center', va='center', fontsize=8)
for i in range(n):
    ax.text(i, i, '1', ha='center', va='center', fontsize=8, color='gray')
ax.set_xticks(range(n)); ax.set_yticks(range(n))
ax.set_xticklabels(vars_, fontsize=9); ax.set_yticklabels(vars_, fontsize=9)
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
fig.tight_layout()
save_fig(fig, 'figures/fig_sigheat.pdf')
```

## 36. Tornado Chart — 灵敏度龙卷风图（参数影响排序）

**场景**: 单参数上下浮动 X% 对结果的影响排序——灵敏度分析"最直观"的呈现，数学建模论文加分图。
**⚠ 关键要点**: 水平条按影响幅度排序（大在上）；左右两个方向分别表示参数上调/下调；中线标记基准值；影响值用百分比相对差。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, _lighten
setup_style()
import matplotlib.pyplot as plt
import numpy as np

params = ['Demand', 'Cost', 'Capacity', 'Price', 'Interest', 'Tax']
low  = [-0.32, -0.24, -0.18, -0.10, -0.06, -0.02]   # 参数 -20% 时的结果相对变化
high = [ 0.28,  0.21,  0.15,  0.11,  0.05,  0.03]   # 参数 +20%
order = np.argsort([max(abs(a), abs(b)) for a, b in zip(low, high)])[::-1]
y = np.arange(len(params))

fig, ax = plt.subplots(figsize=(6.2, 4.0))
ax.barh(y, [high[i] for i in order], height=0.55, color=PALETTE[0], label='+20%')
ax.barh(y, [low[i]  for i in order], height=0.55, color=PALETTE[1], label='-20%')
ax.axvline(0, color='gray', lw=0.8)
ax.set_yticks(y); ax.set_yticklabels([params[i] for i in order], fontsize=9)
ax.set_xlabel('Relative change of result (pct)')
ax.legend(frameon=False, fontsize=9, loc='lower right')
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_tornado.pdf')
```

## 37. Gantt Chart — 甘特图（任务排程/时间线）

**场景**: 调度/排产/项目计划：每个任务从 start 到 end 的横条，可叠加关键路径/资源占用。数模中矿山排产、车间调度、工程计划题必用。
**⚠ 关键要点**: barh 表示任务区间；同一机器上任务不重叠；关键路径任务用强调色+实线框，非关键用浅色；横轴刻度对齐日期或时刻。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, _lighten
setup_style()
import matplotlib.pyplot as plt
import numpy as np

tasks = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
starts = [0, 2, 1, 4, 3, 6]; ends = [2, 5, 4, 6, 6, 8]
critical = [True, False, True, False, True, True]
y_pos = np.arange(len(tasks))

fig, ax = plt.subplots(figsize=(6.4, 3.4))
for y, s, e, c in zip(y_pos, starts, ends, critical):
    ax.barh(y, e-s, left=s, height=0.58,
            color=PALETTE[0] if c else _lighten(PALETTE[1], 0.25),
            edgecolor='#333' if c else 'none', lw=0.8)
    ax.text(s+0.05, y, f'{s}', va='center', fontsize=7, color='white')
ax.set_yticks(y_pos); ax.set_yticklabels(tasks, fontsize=9)
ax.set_xlim(0, 9); ax.set_xlabel('Time unit')
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_gantt.pdf')
```

## 38. Phase Portrait — 相平面图（微分方程动力学）

**场景**: 传染病 SIR / 种群 Lotka-Volterra / 摆等动力学系统：画出相平面上的轨迹方向场与轨线，展示平衡点与稳定性。数模"机理建模"题的点睛图。
**⚠ 关键要点**: quiver 画方向场；streamplot 或数值积分画多条轨线；标注平衡点（空心圆）与稳定性结论。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE
setup_style()
import matplotlib.pyplot as plt
import numpy as np

def f(x, y):                                  # Lotka–Volterra 增广：x,y 两物种
    return (x*(0.8-0.2*y), y*(-0.5+0.12*x))
X = np.linspace(0.2, 6, 22); Y = np.linspace(0.2, 5, 22)
XX, YY = np.meshgrid(X, Y); U, V = f(XX, YY)
M = np.hypot(U, V); U, V = U/M, V/M

fig, ax = plt.subplots(figsize=(4.8, 4.2))
ax.quiver(XX, YY, U, V, color='#c9ccd1', width=0.0035)
t = np.linspace(0, 30, 2000)
for x0, y0 in [(2.6, 3.6), (3.6, 2.2), (0.5, 1.5)]:   # 多条轨线
    xq, yq = x0, y0; traj = np.zeros((len(t), 2)); traj[0] = (x0, y0)
    for k in range(1, len(t)):
        dx, dy = f(xq, yq); xq, yq = xq+dx*0.015, yq+dy*0.015
        traj[k] = (xq, yq)
    ax.plot(traj[:, 0], traj[:, 1], lw=1.5, color=PALETTE[0])
eq = (0.5/0.12, 0.8/0.2)
ax.scatter([eq[0]], [eq[1]], s=40, facecolors='none', edgecolors=PALETTE[1], lw=1.5)
ax.annotate('equilibrium', eq, xytext=(8, 8), textcoords='offset points', fontsize=8)
ax.set_xlabel('Prey (x)'); ax.set_ylabel('Predator (y)')
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_phase.pdf')
```

## 39. Parameter Sweep Heatmap — 参数扫描热力图（双参数灵敏度）

**场景**: 两个参数取网格值，结果值着色的灵敏度扫描（如 α×β → 误差）。一图看完双参数交互对结果的影响。
**⚠ 关键要点**: 用 pcolormesh/imshow + origin='lower'；坐标轴标参数名与取值；叠加最优区域圈注；色图用感知均匀（viridis/plasma）或 RdBu 分正负。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE
setup_style()
import matplotlib.pyplot as plt
import numpy as np

p1 = np.linspace(0.1, 1.0, 40); p2 = np.linspace(0.1, 1.0, 40)   # 参数网格
P1, P2 = np.meshgrid(p1, p2)
Z = np.abs(P1 - 0.45) + 2*np.abs(P2 - 0.6) + 0.02*np.random.default_rng(6).normal(0, 1, P1.shape)

fig, ax = plt.subplots(figsize=(5.6, 4.4))
im = ax.pcolormesh(P1, P2, Z, shading='auto', cmap='plasma')
i, j = np.unravel_index(np.argmin(Z), Z.shape)
ax.annotate('optimum', xy=(p1[j], p2[i]), xytext=(8, 8), textcoords='offset points',
            fontsize=8, arrowprops=dict(arrowstyle='-', color='white', lw=0.8))
ax.set_xlabel('Parameter A'); ax.set_ylabel('Parameter B')
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label='error')
fig.tight_layout()
save_fig(fig, 'figures/fig_paramgrid.pdf')
```

## 40. Sequence Diagram — 时序图（HTML 引擎模板）

**场景**: 系统/算法交互、协议交换（请求-响应、三方协作）。非数据图，由 paper-figure-html 引擎产出自包含 HTML，再截图导出 PDF/PNG。
**⚠ 关键要点**: 参与者竖线 + 消息横箭头 + 时间自上而下；只画"关键交互"，别把函数调用全部堆上；消息标签用动词短语；同步用实线实箭头、返回用虚线。

```html
<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<style>body{margin:24px;font-family:system-ui,sans-serif}
.seq{position:relative;border:1px solid #ddd;padding:20px 28px 28px;background:#fff}
.lane{position:absolute;top:52px;bottom:0;width:1px;background:#bbb}
.part{position:absolute;top:8px;transform:translateX(-50%);font-size:13px;font-weight:600;white-space:nowrap}
.msg{position:absolute;height:1px;background:#333}
.msg b{position:absolute;left:50%;top:-15px;transform:translateX(-50%);font-size:11px;color:#333;white-space:nowrap;font-weight:400}
.ret{background:#999;border-top:1px dashed #999;height:0}
</style></head><body>
<div class="seq" style="height:300px">
  <!-- 三条参与者竖线：x 坐标自定 -->
  <div class="lane" style="left:100px"></div><div class="lane" style="left:260px"></div><div class="lane" style="left:420px"></div>
  <div class="part" style="left:100px">客户端</div><div class="part" style="left:260px">平台</div><div class="part" style="left:420px">数据库</div>
  <!-- 消息：从 x1 到 x2，top 逐行增加 -->
  <div class="msg" style="left:100px;top:90px;width:160px"><b>提交请求</b></div>
  <div class="msg" style="left:260px;top:150px;width:160px"><b>查询数据</b></div>
  <div class="msg ret" style="left:260px;top:210px;width:160px"><b>返回结果</b></div>
  <div class="msg" style="left:100px;top:270px;width:160px"><b>响应应答</b></div>
</div>
</body></html>
```

## 41. State Diagram — 状态机图（HTML 引擎模板）

**场景**: 状态转移/生命周期（订单状态、任务状态、算法阶段）。非数据图，由 paper-figure-html 引擎产出。
**⚠ 关键要点**: 圆角矩形=状态、箭头=转移（标签写触发条件）、实心圆=初始、双层圆=终止；状态 ≤7 个，否则分两图。

```html
<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<style>body{margin:24px;font-family:system-ui,sans-serif}
.st{position:absolute;border:1.6px solid #333;border-radius:12px;padding:8px 14px;background:#fff;font-size:13px;white-space:nowrap;transform:translate(-50%,-50%)}
.st.start{width:10px;height:10px;background:#333;border-radius:50%;padding:0}
.st.end{width:18px;height:18px;background:#fff;border:2px solid #333;border-radius:50%;padding:0}
.edge{position:absolute;height:0;border-top:1.4px solid #333;transform-origin:0 0}
.edge b{position:absolute;top:-15px;left:50%;transform:translateX(-50%);font-size:11px;white-space:nowrap;font-weight:400}
</style></head><body>
<div style="position:relative;width:560px;height:260px;border:1px solid #ddd">
  <div class="st start" style="left:50px;top:130px"></div>
  <div class="st" style="left:180px;top:70px">待审核</div>
  <div class="st" style="left:180px;top:200px">已驳回</div>
  <div class="st" style="left:360px;top:70px">运行中</div>
  <div class="st" style="left:360px;top:200px">已暂停</div>
  <div class="st end" style="left:500px;top:130px"></div>
  <!-- 转移线：连接各状态中心；标签写条件 -->
  <div class="edge" style="left:50px;top:130px;width:130px;transform:rotate(-27deg)"><b>提交</b></div>
  <div class="edge" style="left:180px;top:87px;width:180px"><b>通过</b></div>
  <div class="edge" style="left:180px;top:136px;width:130px;transform:rotate(27deg)"><b>驳回</b></div>
  <div class="edge" style="left:360px;top:87px;width:125px"><b>完成</b></div>
</div>
</body></html>
```

## 42. Swimlane — 泳道图（HTML 引擎模板）

**场景**: 跨角色/部门流程（需求→评审→开发→验收），职责泳道划分。非数据图，由 paper-figure-html 引擎产出。
**⚠ 关键要点**: 每泳道一个角色；步骤方块放所属泳道、行号递增；跨泳道箭头体现交接；"泳道内步骤不回流"是一致性检查点。

```html
<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<style>body{margin:24px;font-family:system-ui,sans-serif}
.lane{display:grid;grid-template-columns:90px 1fr;border:1px solid #ddd;margin-bottom:10px}
.lane-name{background:#f4f4f6;font-size:12px;font-weight:600;display:flex;align-items:center;justify-content:center}
.steps{display:flex;gap:12px;align-items:center;padding:12px;min-height:64px;position:relative}
.box{border:1.5px solid #333;border-radius:10px;padding:8px 14px;font-size:12px;background:#fff;white-space:nowrap}
.arrow{color:#666;font-size:14px}
</style></head><body>
<div class="lane"><div class="lane-name">产品</div>
  <div class="steps"><div class="box">发起需求</div><span class="arrow">→</span><div class="box">评审定稿</div></div></div>
<div class="lane"><div class="lane-name">研发</div>
  <div class="steps"><div class="box">方案设计</div><span class="arrow">→</span><div class="box">编码实现</div><span class="arrow">→</span><div class="box">自测</div></div></div>
<div class="lane"><div class="lane-name">测试</div>
  <div class="steps"><div class="box">集成测试</div><span class="arrow">→</span><div class="box">回归</div></div></div>
</body></html>
```

## 43. Indicator Tree — 指标体系树（HTML 引擎模板）

**场景**: AHP 层次结构、评价指标体系（目标→准则→方案）、组织树、依赖树。非数据图，由 paper-figure-html 引擎产出。
**⚠ 关键要点**: 自上而下分层；每层同级横排、字数对齐；连线从父节点中心垂直下再水平分叉（flex 树最稳）；叶子节点颜色统一浅填充。

```html
<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<style>body{margin:24px;font-family:system-ui,sans-serif}
.tree{display:flex;flex-direction:column;align-items:center;gap:18px}
.level{display:flex;gap:16px;justify-content:center}
.node{border:1.5px solid #333;border-radius:10px;padding:8px 16px;font-size:13px;background:#fff;white-space:nowrap;text-align:center}
.node.leaf{background:#f7f7f9}
.branch{position:relative;align-self:stretch}
</style></head><body>
<div class="tree">
  <div class="node" style="font-weight:600">综合评价</div>
  <div class="level"><div class="node">指标 A</div><div class="node">指标 B</div><div class="node">指标 C</div></div>
  <div class="level">
    <div class="node leaf">方案 1</div><div class="node leaf">方案 2</div><div class="node leaf">方案 3</div>
    <div class="node leaf">方案 4</div><div class="node leaf">方案 5</div><div class="node leaf">方案 6</div>
  </div>
</div>
</body></html>
```



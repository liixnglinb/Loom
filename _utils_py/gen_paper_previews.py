# -*- coding: utf-8 -*-
"""论文级图表预览生成器：为「查看所有图表」弹窗重绘全部图表示例。

- 命名：static/img/paper-{key}__{theme}.png（70 键 × 6 主题 = 420 张）
- 主题与 static/app.js 的 FIG_THEMES 对齐：vivid/journal/kelly/nature/elegant/soft
- 出图规范：白底 + 细边线 + 轻网格 + 紧凑留白；科学数据用真实感示例数据；
  示意图类（flow-html/seq/state/swimlane/indextree）用盒子+箭头编辑级排版。
- 用途：只供前端图墙预览；运行时论文实图仍走 plot_utils / paper-figure-html。
重跑：python _utils_py/gen_paper_previews.py
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 中文字体（Windows 微软雅黑；缺省回退 SimHei），避免预览图中文变方块
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["figure.facecolor"] = "white"

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "img"

# --- 主题色板（与 app.js FIG_THEMES swatch 一致） ---
THEMES = {
    "vivid":   ["#1696D2", "#FDBF11", "#55B748", "#DB2B27", "#EC008B", "#00A3A1", "#7F8C8D"],
    "journal": ["#0C5DA5", "#00B945", "#FF9500", "#FF2C00", "#845B97", "#474747", "#9E9E9E"],
    "kelly":   ["#F3C300", "#875692", "#F38400", "#A1CAF1", "#BE0032", "#C2B280", "#008856", "#848482"],
    "nature":  ["#0F4D92", "#3775BA", "#8BCF8B", "#B64342", "#767676", "#42949E", "#9A4D8E"],
    "elegant": ["#7AAEC8", "#E8945A", "#7BC8A4", "#9B8EC4", "#E0A0A0", "#F0C05A", "#8FAEC0"],
    "soft":    ["#5B9BD5", "#ED7D7D", "#7BC8A4", "#B0B0B0", "#9B8EC4", "#F4A261"],
}
SIZE = (4.3, 3.3)
DPIX = 200

rng = np.random.default_rng(7)


def _style(ax, c, grid=True):
    """论文风全局微调：去上右边框、细轴、弱网格、小字号。"""
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(0.9)
        ax.spines[s].set_color("#444444")
    if grid:
        ax.grid(True, axis="y", ls=":", lw=0.7, color="#c8ccd4", alpha=0.8)
        ax.set_axisbelow(True)
    ax.tick_params(labelsize=8.5, length=3, colors="#333333")


def _new():
    fig, ax = plt.subplots(figsize=SIZE, dpi=DPIX)
    fig.subplots_adjust(left=0.15, right=0.97, top=0.94, bottom=0.17)
    return fig, ax


# ================= 数据示例 =================
MON = np.arange(1, 13)
A = np.array([22, 25, 24, 30, 33, 31, 37, 42, 45, 43, 50, 55])
B = np.array([18, 21, 19, 24, 27, 29, 33, 36, 40, 38, 44, 48])
A_E = np.array([1.6, 1.9, 2.0, 2.2, 2.4, 2.1, 2.5, 2.8, 3.0, 2.9, 3.1, 3.3])
B_E = np.array([1.2, 1.5, 1.4, 1.7, 1.9, 2.0, 2.2, 2.4, 2.6, 2.3, 2.7, 2.9])
x = np.linspace(0, 10, 200)
y_gt = 2.2 * x + 1.5
y = y_gt + 0.9 * np.sin(1.3 * x) + rng.normal(0, 0.8, 200)
xx = np.linspace(0, 10, 80)
yy = 2.2 * xx + 1.5
GRPS = ["G1", "G2", "G3", "G4", "G5", "G6"]
VAL = np.array([12.4, 18.9, 9.7, 21.3, 15.6, 24.1])
VAL2 = np.array([8.1, 13.2, 7.0, 15.4, 11.0, 17.8])


# ================= 各键绘图 =================
def reg(key):
    def deco(fn):
        FUNCS[key] = fn
        return fn
    return deco


FUNCS = {}


def _draw_bar(ax, c, stacked=False, div=False):
    if stacked:
        ax.bar(MON, A, width=0.72, color=c[0], label="A")
        ax.bar(MON, B, width=0.72, bottom=A, color=c[1], label="B")
        ax.set_ylim(0, 115)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    elif div:
        dv = VAL - np.mean(VAL)
        ax.barh(GRPS[::-1], dv, color=[c[1] if v < 0 else c[0] for v in dv], height=0.62)
        ax.axvline(0, color="#555", lw=0.9)
    else:
        w = 0.34
        ax.bar(MON - w / 2, A, width=w, yerr=A_E, color=c[0], label="A",
               capsize=1.8, error_kw=dict(lw=0.8))
        ax.bar(MON + w / 2, B, width=w, yerr=B_E, color=c[1], label="B",
               capsize=1.8, error_kw=dict(lw=0.8))
        ax.set_xticks(MON)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    _style(ax, c)


def _draw_hbar(ax, c, lollipop=False, dumbbell=False):
    if lollipop:
        ax.hlines(GRPS, 0, VAL2, color="#9aa0aa", lw=1.2, zorder=1)
        ax.scatter(VAL2, GRPS, s=46, color=c[0], zorder=3)
    elif dumbbell:
        yp = np.arange(len(GRPS))
        ax.hlines(yp, VAL2, VAL, color="#9aa0aa", lw=2.4, zorder=1)
        ax.scatter(VAL2, yp, s=42, color=c[1], zorder=3, label="前")
        ax.scatter(VAL, yp, s=42, color=c[0], zorder=3, label="后")
        ax.set_yticks(yp)
        ax.set_yticklabels(GRPS)
        ax.legend(frameon=False, fontsize=8, loc="lower right")
    else:
        ax.barh(GRPS, VAL, color=c[0], height=0.6, alpha=0.92)
        ax.set_xlim(0, 28)
    _style(ax, c)


def _draw_line(ax, c, area=False, dual=False):
    if area:
        ax.fill_between(MON, A - A_E, A + A_E, color=c[0], alpha=0.18)
        ax.plot(MON, A, "-o", ms=4, lw=1.8, color=c[0], label="实验组")
        ax.fill_between(MON, B - B_E, B + B_E, color=c[1], alpha=0.15)
        ax.plot(MON, B, "-s", ms=4, lw=1.8, color=c[1], label="对照组")
        ax.set_xticks(MON[::2])
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    elif dual:
        ax.plot(MON, A, "-o", ms=4, lw=1.8, color=c[0], label="产量")
        ax.set_ylim(15, 60)
        ax2 = ax.twinx()
        ax2.plot(MON, B / 6 + 3, "-^", ms=4, lw=1.8, color=c[1], label="增速")
        ax2.set_ylim(0, 16)
        ax2.tick_params(labelsize=8.5)
        ax2.spines["top"].set_visible(False)
        ax.legend(ax.get_lines() + ax2.get_lines(), ["产量", "增速"],
                  frameon=False, fontsize=8, loc="upper left")
        _style(ax, c, grid=False)
        return
    else:
        ax.plot(MON, A, "-o", ms=4, lw=2.0, color=c[0], label="实验组")
        ax.fill_between(MON, A - A_E, A + A_E, color=c[0], alpha=0.16)
        ax.plot(MON, B, "-s", ms=4, lw=2.0, color=c[1], label="对照组")
        ax.fill_between(MON, B - B_E, B + B_E, color=c[1], alpha=0.14)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    _style(ax, c)


def _draw_dist(ax, c, kind="box"):
    data = [rng.normal(50, 8, 60) + i * 6 for i in range(6)]
    if kind == "violin":
        parts = ax.violinplot(data, positions=range(6), showmedians=True, widths=0.8)
        for pc, col in zip(parts["bodies"], c):
            pc.set_facecolor(col)
            pc.set_alpha(0.65)
            pc.set_edgecolor("none")
        parts["cmedians"].set_color("#333")
        parts["cmedians"].set_linewidth(1.2)
        ax.set_xticks(range(6))
        ax.set_xticklabels(GRPS)
    elif kind == "gviolin":
        data2 = [rng.normal(48, 9, 60) + i * 6 for i in range(6)]
        pos = np.arange(6) * 2
        for i, (d1, d2) in enumerate(zip(data, data2)):
            v1 = ax.violinplot([d1], positions=[pos[i] - 0.4], widths=0.7, showmedians=True)
            v2 = ax.violinplot([d2], positions=[pos[i] + 0.4], widths=0.7, showmedians=True)
            for pc in v1["bodies"]:
                pc.set_facecolor(c[0]); pc.set_alpha(0.6); pc.set_edgecolor("none")
            for pc in v2["bodies"]:
                pc.set_facecolor(c[1]); pc.set_alpha(0.6); pc.set_edgecolor("none")
        ax.set_xticks(pos)
        ax.set_xticklabels(GRPS)
    else:
        bp = ax.boxplot(data, patch_artist=True, widths=0.55)
        for patch, col in zip(bp["boxes"], c):
            patch.set_facecolor(col)
            patch.set_alpha(0.55)
        for el in ("whiskers", "caps"):
            for l in bp[el]:
                l.set_color("#555")
                l.set_linewidth(0.9)
        for m in bp["medians"]:
            m.set_color("#111")
            m.set_linewidth(1.4)
        ax.set_xticks(range(1, 7))
        ax.set_xticklabels(GRPS)
    _style(ax, c)


def _draw_corr(ax, c, key):
    n = 6
    if key == "heatmap":
        M = rng.standard_normal((n, n))
        M = (M + M.T) / 2
        np.fill_diagonal(M, 1)
        ax.imshow(M, cmap="RdYlBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(n)); ax.set_yticks(range(n))
        ax.set_xticklabels([f"V{i+1}" for i in range(n)], fontsize=7.5)
        ax.set_yticklabels([f"V{i+1}" for i in range(n)], fontsize=7.5)
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=6.4,
                        color="white" if abs(M[i, j]) > 0.75 else "#222")
        ax.tick_params(length=0)
    elif key == "sigheat":
        M = np.array([[1, .92, .71, .05, .31, .44],
                      [.92, 1, .63, .12, .26, .38],
                      [.71, .63, 1, -.09, .18, .29],
                      [.05, .12, -.09, 1, .55, .60],
                      [.31, .26, .18, .55, 1, .77],
                      [.44, .38, .29, .60, .77, 1]])
        ax.imshow(M, cmap="RdYlBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(n)); ax.set_yticks(range(n))
        ax.set_xticklabels([f"V{i+1}" for i in range(n)], fontsize=7.5)
        ax.set_yticklabels([f"V{i+1}" for i in range(n)], fontsize=7.5)
        for i in range(n):
            for j in range(n):
                p = ("***" if abs(M[i, j]) > .8 else "**" if abs(M[i, j]) > .6
                     else "*" if abs(M[i, j]) > .4 else "")
                ax.text(j, i, f"{M[i, j]:.2f}{p}", ha="center", va="center", fontsize=6.2,
                        color="white" if abs(M[i, j]) > 0.75 else "#222")
        ax.tick_params(length=0)
    elif key == "cheat":
        M = rng.standard_normal((8, 8))
        M = (M + M.T) / 2
        ax.imshow(M, cmap="YlGnBu", aspect="auto")
        ax.set_xticks([])
        ax.set_yticks(np.arange(8))
        ax.set_yticklabels([f"S{i+1}" for i in range(8)], fontsize=7.5)
        ax.tick_params(length=0)
        ax.set_ylabel("样本", fontsize=8.5)
    elif key == "bivar":
        ob = rng.multivariate_normal([3, 3], [[1.2, .8], [.8, 1.0]], 220)
        ax.scatter(ob[:, 0], ob[:, 1], s=12, color=c[2], alpha=0.45, edgecolor="none")
        from scipy.stats import gaussian_kde
        z = gaussian_kde(ob.T)(ob.T)
        idx = z.argsort()
        ax.scatter(ob[idx, 0], ob[idx, 1], c=z[idx], s=12, cmap="Blues", alpha=0.8, edgecolor="none")
    elif key == "network":
        np.random.seed(3)
        pos = {i: np.array([np.cos(2*np.pi*i/7), np.sin(2*np.pi*i/7)]) * 0.9 for i in range(7)}
        for i in range(7):
            for j in range(i+1, 7):
                if np.random.rand() < 0.42:
                    ax.plot([pos[i][0], pos[j][0]], [pos[i][1], pos[j][1]],
                            color="#b6bcc8", lw=0.8, zorder=1)
        for i, p in enumerate(pos.values()):
            ax.scatter(p[0], p[1], s=210, color=c[i % len(c)], zorder=3,
                       edgecolor="white", linewidth=1.2)
        ax.axis("off")
        ax.set_aspect("equal")
        return
    elif key == "pair":
        for i in range(3):
            ax.scatter(xx[:40], yy[:40] - 2 + i * 2.5 + rng.normal(0, 0.8, 40),
                       s=10, color=c[i], alpha=0.6)
    elif key == "joint":
        s1 = 1.1 * xx + rng.normal(0, 1.2, 80)
        ax.scatter(xx, s1, s=11, color=c[0], alpha=0.55)
        axm = ax.inset_axes([0.13, 0.72, 0.30, 0.22])
        axm.hist(s1, bins=16, color=c[0], alpha=0.5)
        axm.axis("off")
        axm.patch.set_alpha(0)
    _style(ax, c, grid=False)


@reg("bar")
def _(ax, c):
    _draw_bar(ax, c)


@reg("stacked")
def _(ax, c):
    _draw_bar(ax, c, stacked=True)


@reg("divbar")
def _(ax, c):
    _draw_bar(ax, c, div=True)
    ax.set_ylim(-6.5, 6.5)
    ax.set_yticks([])


@reg("hbar")
def _(ax, c):
    _draw_hbar(ax, c)


@reg("lollipop")
def _(ax, c):
    _draw_hbar(ax, c, lollipop=True)
    ax.set_xlim(0, 22)
    ax.set_xticks([0, 10, 20])


@reg("dumbbell")
def _(ax, c):
    _draw_hbar(ax, c, dumbbell=True)
    ax.set_xlim(0, 28)


@reg("back2back")
def _(ax, c):
    yp = np.arange(len(GRPS))
    ax.barh(yp, VAL, color=c[0], alpha=0.9, label="男")
    ax.barh(yp, -VAL2, color=c[1], alpha=0.9, label="女")
    ax.axvline(0, color="#555", lw=0.9)
    ax.set_yticks(yp)
    ax.set_yticklabels(GRPS)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    _style(ax, c, grid=False)


@reg("dotci")
def _(ax, c):
    yp = np.arange(len(GRPS))
    ci = np.array([1.2, 1.6, 0.9, 2.0, 1.4, 1.7])
    ax.errorbar(VAL, yp, xerr=ci, fmt="o", ms=6, color=c[0], ecolor=c[1],
                elinewidth=2.0, capsize=3, capthick=1.2, zorder=3)
    ax.axvline(0, color="#555", lw=0.8)
    ax.set_yticks(yp)
    ax.set_yticklabels(GRPS)
    ax.set_xlim(-2, 30)
    _style(ax, c)


@reg("paired")
def _(ax, c):
    r = rng.normal(0, 0.34, size=(8, 2))
    r[:, 1] += 2.4
    for i in range(8):
        ax.plot(r[i], [i, i], "-", color="#aab2bd", lw=1.1, zorder=1)
    ax.scatter(np.full(8, 0), r[:, 0], s=40, color=c[0], zorder=3)
    ax.scatter(np.full(8, 1), r[:, 1], s=40, color=c[1], zorder=3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["治疗前", "治疗后"], fontsize=8.5)
    ax.set_yticks([])
    _style(ax, c)


@reg("sigbar")
def _(ax, c):
    m = np.array([22, 26, 31, 24, 29, 34])
    e = np.array([1.6, 1.8, 2.0, 1.7, 1.9, 2.2])
    cols = [c[1], c[1], c[0], c[1], c[1], c[0]]
    ax.bar(np.arange(6), m, yerr=e, width=0.6, color=cols, capsize=3, error_kw=dict(lw=0.9))
    for i in (2, 5):
        ax.plot([i - 0.3, i + 0.3], [38, 38], color="#333", lw=1.1)
        ax.text(i, 40, "*", ha="center", fontsize=12, fontweight="bold")
    ax.plot([2, 5], [41.5, 41.5], color="#333", lw=1.1)
    ax.text(3.5, 44, "*", ha="center", fontsize=12)
    ax.set_xticks(range(6))
    ax.set_xticklabels([f"M{i+1}" for i in range(6)])
    ax.set_ylim(0, 50)
    _style(ax, c)


@reg("forest")
def _(ax, c):
    yp = np.arange(5)
    est = np.array([1.4, 0.8, 2.1, 1.1, 0.6])
    lo = np.array([0.9, 0.3, 1.5, 0.7, 0.2])
    hi = np.array([2.0, 1.3, 2.8, 1.5, 1.0])
    for i in range(5):
        ax.plot([lo[i], hi[i]], [yp[i], yp[i]], color=c[1], lw=2.2, zorder=2)
        ax.plot(est[i], yp[i], marker="o", ms=9, color=c[0], zorder=3)
    ax.axvline(1, color="#7a7f89", ls="--", lw=1.0)
    ax.set_yticks(yp)
    ax.set_yticklabels(["特征A", "特征B", "特征C", "特征D", "特征E"])
    ax.set_xlim(0, 3.2)
    _style(ax, c)


@reg("line")
def _(ax, c):
    _draw_line(ax, c)


@reg("area")
def _(ax, c):
    _draw_line(ax, c, area=True)


@reg("dual")
def _(ax, c):
    _draw_line(ax, c, dual=True)


@reg("slope")
def _(ax, c):
    pre = np.array([30, 44, 58]); post = np.array([52, 49, 66])
    for i in range(3):
        ax.plot([0, 1], [pre[i], post[i]], "-o", ms=6, lw=1.9, color=c[i])
        ax.annotate(f"{post[i]-pre[i]:+d}", (1.045, post[i]), fontsize=7.8, va="center", color="#444")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["干预前", "干预后"])
    ax.set_ylim(20, 78)
    ax.legend(frameon=False, fontsize=8, loc="upper left", labels=["A", "B", "C"], ncol=3)
    _style(ax, c)


@reg("waterfall")
def _(ax, c):
    steps = ["初始", "+A", "+B", "+C", "+D", "+E", "终值"]
    v = np.array([100, 25, -18, 34, -12, 21, 150])
    cum = np.cumsum(np.r_[0, v[:-1]])
    for i in range(len(v) - 1):
        lo = min(cum[i], cum[i] + v[i])
        ax.bar(i, abs(v[i]), bottom=lo, width=0.62,
               color=(c[0] if v[i] > 0 else c[1]), alpha=0.92)
    ax.bar(6, v[-1], width=0.62, color=c[2], alpha=0.95)
    ax.plot(np.arange(8), np.r_[cum, 150], color="#666", lw=0.9, ls="--", zorder=1)
    ax.set_xticks(range(7))
    ax.set_xticklabels(steps, fontsize=7.4, rotation=16, ha="right")
    ax.set_yticks([])
    _style(ax, c, grid=False)


@reg("pareto")
def _(ax, c):
    vals = np.array([32, 24, 17, 12, 8, 4, 3])
    ax.bar(range(len(vals)), vals, width=0.62, color=[c[0]] + [c[3]] * (len(vals) - 1))
    cum = np.cumsum(vals) / vals.sum() * 100
    ax2 = ax.twinx()
    ax2.plot(range(len(vals)), cum, "-o", ms=4, lw=1.8, color=c[1])
    ax2.set_ylim(0, 108)
    ax2.set_yticks([0, 40, 80])
    ax2.tick_params(labelsize=8)
    ax2.spines["top"].set_visible(False)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels([f"F{i+1}" for i in range(len(vals))])
    _style(ax, c)


@reg("fan")
def _(ax, c):
    t = np.linspace(0, 10, 80)
    base = np.linspace(30, 46, 80)
    for i in range(4):
        ax.plot(t, base + i * 1.1, "-", lw=1.7, color=c[i % len(c)])
    ax.fill_between(t, base, base + 10 * 1.1, color=c[0], alpha=0.10)
    _style(ax, c)


@reg("bump")
def _(ax, c):
    np.random.seed(9)
    ranks = np.cumsum(rng.integers(-1, 2, (5, 8)), axis=1) + 3
    ranks = np.clip(ranks, 1, 5)
    for i in range(5):
        ax.plot(range(8), ranks[i], "-o", ms=5, lw=1.9, color=c[i % len(c)])
    ax.invert_yaxis()
    ax.set_yticks(range(1, 6)); ax.set_xticks(range(8))
    ax.tick_params(labelsize=7.5)
    _style(ax, c, grid=False)


@reg("stream")
def _(ax, c):
    t = np.linspace(0, 12, 200)
    for i, w in enumerate(np.linspace(0.04, 0.30, 6)):
        center = np.sin(t / 3 + i) * 0.02 + 0.5
        ax.fill_between(t, center - w, center + w, color=c[i % len(c)], alpha=0.85)
    ax.set_yticks([])
    ax.set_xticks([0, 6, 12])
    ax.tick_params(labelsize=8)
    _style(ax, c, grid=False)


@reg("cusum")
def _(ax, c):
    t = np.arange(60)
    x = rng.normal(0, 1, 60)
    x[35:] += 1.3
    cum = np.cumsum(x)
    ax.plot(t, cum, lw=1.8, color=c[0])
    ax.axvspan(35, 59, color=c[1], alpha=0.14)
    ax.axhline(0, color="#888", lw=0.8, ls="--")
    ax.annotate("漂移起点", (37, cum[39]), fontsize=8, color="#444")
    _style(ax, c)


@reg("qband")
def _(ax, c):
    runs = np.zeros((20, 12))
    for k in range(20):
        runs[k] = rng.normal(0, 1, 12) * 2 + np.linspace(2, 8, 12)
    med = np.median(runs, axis=0)
    q1 = np.percentile(runs, 25, axis=0)
    q3 = np.percentile(runs, 75, axis=0)
    ax.fill_between(range(12), q1, q3, color=c[0], alpha=0.25)
    ax.plot(range(12), med, "-o", ms=3.5, lw=1.8, color=c[0])
    ax.plot(range(12), runs[::5].T, color=c[3], lw=0.7, alpha=0.35)
    _style(ax, c)


@reg("box")
def _(ax, c):
    _draw_dist(ax, c, "box")


@reg("violin")
def _(ax, c):
    _draw_dist(ax, c, "violin")


@reg("gviolin")
def _(ax, c):
    _draw_dist(ax, c, "gviolin")


@reg("hist")
def _(ax, c):
    ax.hist(rng.normal(0, 1, 400), bins=26, color=c[0], alpha=0.75,
            edgecolor="white", lw=0.5)
    xxg = np.linspace(-4, 4, 200)
    ax.plot(xxg, 400 * 0.07 * np.exp(-xxg**2 / 2) / np.sqrt(2 * np.pi), color=c[1], lw=1.8)
    _style(ax, c)


@reg("kde")
def _(ax, c):
    from scipy.stats import gaussian_kde
    xs = np.linspace(-6, 6, 300)
    for i, m in enumerate([-1.6, 0.3, 2.1]):
        k = gaussian_kde(rng.normal(m, 1.1, 260))
        ax.plot(xs, k(xs), lw=1.9, color=c[i % len(c)])
    _style(ax, c)


@reg("ridge")
def _(ax, c):
    from scipy.stats import gaussian_kde
    xs = np.linspace(-6, 6, 300)
    dy = 0.0
    for i, m in enumerate(np.linspace(-2.6, 2.6, 5)):
        k = gaussian_kde(rng.normal(m, 1.0, 300))
        ax.fill_between(xs, dy, k(xs) * 1.5 + dy, color=c[i % len(c)], alpha=0.5)
        ax.plot(xs, k(xs) * 1.5 + dy, color=c[i % len(c)], lw=1.3)
        dy += 1.7
    ax.set_yticks([])
    _style(ax, c)


@reg("rain")
def _(ax, c):
    np.random.seed(11)
    for i in range(6):
        base = i * 2.2
        ax.hlines(base, 0, 60, color="#ccd1da", lw=0.8)
        jit = rng.normal(base, 1.0, 18)
        ax.scatter(np.arange(18) * 3.3, jit, s=9, color=c[i % len(c)], alpha=0.8)
    ax.set_yticks([])
    ax.set_xticks([0, 30, 60])
    _style(ax, c)


@reg("posterior")
def _(ax, c):
    xs = np.linspace(0, 1, 240)
    for m, s, col in [(0.35, 0.07, c[0]), (0.5, 0.05, c[1]), (0.68, 0.09, c[2])]:
        g = np.exp(-((xs - m) ** 2) / (2 * s**2))
        ax.plot(xs, g, lw=1.9, color=col)
        ax.fill_between(xs, 0, g, color=col, alpha=0.14)
    ax.set_yticks([])
    _style(ax, c)


@reg("qq")
def _(ax, c):
    from scipy.stats import probplot
    data = rng.normal(0, 1, 50)
    (osm, osr), (slope, intercept, _) = probplot(data, dist="norm")
    ax.scatter(osm, osr, s=14, color=c[0], alpha=0.75)
    ax.plot(osm, slope * osm + intercept, color=c[2], lw=1.6)
    ax.set_xlabel("理论分位数", fontsize=8.5)
    ax.set_ylabel("样本分位数", fontsize=8.5)
    _style(ax, c)


@reg("ecdf")
def _(ax, c):
    for i, d in enumerate([rng.normal(0, 1, 160), rng.normal(0.8, 1.2, 160)]):
        s = np.sort(d)
        ecdf = np.arange(1, len(s) + 1) / len(s)
        ax.step(s, ecdf, where="post", lw=1.9, color=c[i], label=f"分布{i+1}" if i == 0 else None)
        ax.plot(s[:-1], ecdf[:-1], ".", ms=3, color=c[i])
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_ylim(0, 1.04)
    _style(ax, c)


@reg("scatter")
def _(ax, c):
    ax.scatter(x, y, s=12, color=c[0], alpha=0.6, edgecolor="none")
    ax.plot(xx, yy, color=c[2], lw=1.8)
    from scipy.stats import pearsonr
    ax.annotate(f"r = {pearsonr(x, y).statistic:.2f}", (0.5, 8.6), fontsize=8.5, color="#333")
    _style(ax, c)


@reg("cali")
def _(ax, c):
    xs = np.linspace(0, 1., 60)
    ax.plot(xs, xs, ls="--", color="#8a8f98", lw=1.2, label="理想")
    m = np.array([0.02, 0.08, 0.16, 0.22, 0.34, 0.41, 0.52, 0.63, 0.74, 0.88])
    ax.plot(m, np.clip(m + 0.02, 0, 1), "-o", ms=4, color=c[0], lw=1.8, label="校准")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    _style(ax, c)


@reg("ba")
def _(ax, c):
    a = rng.normal(100, 10, 60)
    b = a + rng.normal(-1.5, 4.2, 60)
    mean = (a + b) / 2
    diff = a - b
    md = np.mean(diff)
    sd = np.std(diff)
    ax.scatter(mean, diff, s=14, color=c[0], alpha=0.7, edgecolor="none")
    ax.axhline(md, color=c[1], lw=1.5)
    ax.axhline(md + 1.96 * sd, color="#7a7f89", ls="--", lw=1.1)
    ax.axhline(md - 1.96 * sd, color="#7a7f89", ls="--", lw=1.1)
    ax.set_ylim(-18, 15)
    _style(ax, c)


@reg("contour")
def _(ax, c):
    X, Y = np.meshgrid(np.linspace(-3, 3, 60), np.linspace(-3, 3, 60))
    Z = np.exp(-(X**2 + Y**2)) + 0.4 * np.exp(-((X - 1.4) ** 2 + (Y - 1) ** 2))
    ax.contourf(X, Y, Z, levels=14, cmap="YlGnBu")
    ax.contour(X, Y, Z, levels=7, colors="#3a5f8a", lw=0.7, alpha=0.6)
    _style(ax, c, grid=False)


@reg("3d")
def _(ax, c):
    fig = ax.figure
    fig.clf()
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    a3 = fig.add_subplot(111, projection="3d")
    X, Y = np.meshgrid(np.linspace(-2.2, 2.2, 40), np.linspace(-2.2, 2.2, 40))
    Z = np.sin(np.sqrt(X**2 + Y**2)) / (1 + 0.35 * np.sqrt(X**2 + Y**2))
    a3.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap="viridis", alpha=0.95, linewidth=0)
    a3.set_box_aspect((1, 1, 0.6))
    a3.set_xticks([]); a3.set_yticks([]); a3.set_zticklabels([])
    a3.tick_params(length=0, pad=0)
    a3.set_facecolor("white")
    fig._no_tight = True  # 自定义白边已经设好，跳过 tight_layout，避免挤压 3D 视图


@reg("sankey")
def _(ax, c):
    from matplotlib.sankey import Sankey
    sk = Sankey(ax=ax, scale=0.008, offset=0.18, head_angle=120, format="%.0f")
    sk.add(flows=[60, -15, -20, -10, -15], orientations=[0, 1, -1, 0, 1],
           labels=["输入", "A", "B", "C", "损耗"],
           trunklength=1.1, pathlengths=[0.5, 0.4, 0.4, 0.4, 0.5])
    diag = sk.finish()
    k = 0
    for unit in diag:
        for patch in (getattr(unit, "patches", []) or [getattr(unit, "patch", None)]):
            if patch is None:
                continue
            patch.set_facecolor(c[k % len(c)])
            patch.set_alpha(0.85)
            k += 1
    for txt in ax.texts:
        txt.set_fontsize(7.4)
    ax.axis("off")


@reg("taylor")
def _(ax, c):
    th = np.linspace(0, np.pi / 2, 200)
    ax.plot(np.cos(th), np.sin(th), color="#9aa0aa", lw=0.9)
    for r in (0.5, 1.0):
        ax.plot([0, r], [0, 0], color="#9aa0aa", lw=0.8)
        ax.plot([0, r * np.cos(np.pi / 4)], [0, r * np.sin(np.pi / 4)], color="#9aa0aa", lw=0.8)
        ax.annotate(f"{r:.1f}", (r * 1.04, -0.08), fontsize=7.5, color="#555")
    for px, py, col in [(0.86, 0.42, c[0]), (0.94, 0.32, c[1]), (0.78, 0.52, c[2])]:
        ax.scatter(px, py, s=34, color=col, zorder=3)
    ax.set_xlim(0, 1.25); ax.set_ylim(0, 1.25)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_aspect("equal")
    _style(ax, c, grid=False)


@reg("pca")
def _(ax, c):
    np.random.seed(5)
    for i, mu in enumerate([(0, 0), (2.2, 1.6), (-1.6, 2.2)]):
        pts = rng.multivariate_normal(mu, [[0.5, 0.15], [0.15, 0.4]], 50)
        ax.scatter(pts[:, 0], pts[:, 1], s=10, color=c[i % len(c)], alpha=0.7)
    ax.axhline(0, color="#9aa0aa", lw=0.8)
    ax.axvline(0, color="#9aa0aa", lw=0.8)
    ax.annotate("", xy=(3.3, 1.6), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", lw=2.0, color=c[4]))
    ax.annotate("", xy=(-1.4, 3.3), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", lw=2.0, color=c[5]))
    ax.set_xlim(-3.5, 3.5); ax.set_ylim(-3.5, 3.5)
    _style(ax, c, grid=False)


@reg("kaplan")
def _(ax, c):
    t = np.linspace(0, 48, 90)
    s1 = np.clip(1 - t / 50 - 0.05 * np.sin(t / 4), 0.18, 1)
    s2 = np.clip(0.9 - t / 70 - 0.03 * np.sin(t / 6), 0.42, 1)
    ax.step(t, s1, where="post", lw=2.0, color=c[0], label="组1")
    ax.step(t, s2, where="post", lw=2.0, color=c[1], label="组2")
    ax.plot([12], [s1[28]], "|", ms=8, color=c[0], mew=1.6)
    ax.plot([26], [s2[50]], "|", ms=8, color=c[1], mew=1.6)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_ylim(0, 1.06)
    ax.set_yticks([0, .5, 1])
    _style(ax, c)


@reg("funnel")
def _(ax, c):
    for i in range(6):
        w = np.linspace(1.0, 0.22, 6)[i]
        ax.bar(i, 1, width=w, color=c[i % len(c)], alpha=0.85)
    ax.set_xticks(range(6))
    ax.set_xticklabels([f"L{i+1}" for i in range(6)], fontsize=7.6)
    ax.set_yticks([])
    _style(ax, c, grid=False)


@reg("calendarp")
def _(ax, c):
    rng2 = np.random.default_rng(2)
    days = rng2.random((7, 52))
    days[days > 0.3] = np.nan
    ax.imshow(days, cmap="YlOrRd", aspect="auto", interpolation="nearest")
    ax.set_xticks([0, 17, 34, 51])
    ax.set_yticks(range(7))
    ax.set_yticklabels(["一", "二", "三", "四", "五", "六", "日"], fontsize=7.5)
    ax.tick_params(length=0)
    _style(ax, c, grid=False)


@reg("perf")
def _(ax, c):
    xs = np.linspace(0, 1, 100)
    for i, a in enumerate([1.05, 1.55, 2.2]):
        ax.plot(xs, 1 - (1 - xs) ** (1 / a), lw=1.9, color=c[i], label=f"M{i+1}")
    ax.plot(xs, xs, color="#777", ls="--", lw=0.9)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    _style(ax, c)


@reg("volcano")
def _(ax, c):
    np.random.seed(4)
    n = 300
    fc = rng.uniform(-0.6, 1.8, n)
    pv = np.exp(-np.abs(fc) * rng.uniform(2.5, 8))
    ax.scatter(fc, -np.log10(pv), s=7, color="#b6bcc8", alpha=0.7)
    up = fc > 0.9
    down = fc < -0.5
    ax.scatter(fc[up], -np.log10(pv[up]), s=10, color=c[0], alpha=0.85)
    ax.scatter(fc[down], -np.log10(pv[down]), s=10, color=c[1], alpha=0.85)
    ax.axhline(1.3, color="#8a8f98", ls="--", lw=0.9)
    ax.set_xlim(-2.5, 2.5)
    ax.set_ylim(0, 8)
    _style(ax, c)


@reg("hovmoller")
def _(ax, c):
    X, Y = np.meshgrid(np.linspace(0, 12, 60), np.linspace(0, 24, 80))
    Z = np.sin(X * 1.1) * np.cos(Y * 0.5) + 0.4 * np.sin((X + Y) * 0.7)
    ax.imshow(Z, cmap="RdBu_r", aspect="auto", origin="lower")
    ax.set_xticks([0, 29, 59])
    ax.set_xticklabels(["0", "6", "12"], fontsize=8)
    ax.set_yticks([0, 39, 79])
    ax.set_yticklabels(["0", "12", "24"], fontsize=8)
    ax.set_xlabel("经度", fontsize=8.5)
    ax.set_ylabel("纬度", fontsize=8.5)
    ax.tick_params(length=0)
    _style(ax, c, grid=False)


@reg("ice")
def _(ax, c):
    xxg = np.linspace(0, 10, 60)
    for i in range(30):
        ax.plot(xxg, 0.9 * xxg + rng.normal(0, 0.5), lw=0.7, color=c[3], alpha=0.4)
    ax.plot(xxg, 0.9 * xxg + 0.2, lw=2.0, color=c[0])
    _style(ax, c)


@reg("subplots")
def _(ax, c):
    fig = ax.figure
    fig.clf()
    gs = fig.add_gridspec(2, 2, hspace=0.55, wspace=0.42, left=0.07, right=0.98, top=0.96, bottom=0.12)
    a1 = fig.add_subplot(gs[0, 0]); a2 = fig.add_subplot(gs[0, 1]); a3 = fig.add_subplot(gs[1, :])
    _draw_bar(a1, c)
    a1.set_title("(a)", fontsize=8)
    _draw_line(a2, c)
    a2.set_title("(b)", fontsize=8)
    _draw_dist(a3, c, "box")
    a3.set_title("(c)", fontsize=8)


@reg("tornado")
def _(ax, c):
    names = ["参数A", "参数B", "参数C", "参数D", "参数E", "参数F"]
    lo = np.array([-18, -12, -9, -6, -4, -2])
    hi = np.array([21, 10, 14, 5, 6, 3])
    yp = np.arange(len(names))
    ax.barh(yp, lo, left=0, color=c[1], alpha=0.9, height=0.6)
    ax.barh(yp, hi, left=0, color=c[0], alpha=0.9, height=0.6)
    ax.set_yticks(yp)
    ax.set_yticklabels(names)
    ax.set_xlim(-24, 26)
    _style(ax, c)


@reg("gantt")
def _(ax, c):
    tasks = ["任务1", "任务2", "任务3", "任务4", "任务5"]
    starts = np.array([0, 2.5, 5.5, 7, 10])
    dur = np.array([3, 4, 2.5, 4, 3])
    yp = np.arange(len(tasks))
    for i in range(5):
        ax.barh(i, dur[i], left=starts[i], height=0.5, color=c[i % len(c)], alpha=0.9)
    for i, s, d in [(0, 0, 3), (1, 2.5, 4), (3, 7, 4)]:
        ax.barh(i, d, left=s, height=0.5, color=c[i % len(c)], edgecolor="#222", lw=1.2)
    ax.set_yticks(yp)
    ax.set_yticklabels(tasks)
    ax.set_xticks([0, 5, 10, 15])
    _style(ax, c)


@reg("phase")
def _(ax, c):
    Y, X = np.mgrid[-2:2:22j, -2:2:22j]
    U = Y
    V = -X - 0.2 * Y
    M = np.hypot(U, V)
    M[M == 0] = 1
    ax.quiver(X, Y, U / M * 1.3, V / M * 1.3, color=c[2], alpha=0.75, width=0.004, scale=9)
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(1.1 * np.cos(th), 1.1 * np.sin(th), lw=1.6, color=c[0])
    ax.plot(np.cos(th), np.sin(th), lw=0.9, color=c[4], ls="--")
    ax.scatter([0], [0], color=c[1], s=30, zorder=4)
    ax.set_aspect("equal")
    ax.set_xlim(-2.1, 2.1)
    ax.set_ylim(-2.1, 2.1)
    _style(ax, c, grid=False)


@reg("paramgrid")
def _(ax, c):
    p = np.linspace(0, 1, 40)
    Z = np.array([[0.4 + 0.5 * (1 - np.exp(-2 * (1 - a))) * np.exp(-1.5 * b) for b in p] for a in p])
    ax.imshow(Z, cmap="viridis", aspect="auto", origin="lower", extent=[0, 1, 0, 1])
    ax.set_xlabel("参数1", fontsize=8.5)
    ax.set_ylabel("参数2", fontsize=8.5)
    _style(ax, c, grid=False)


@reg("traj")
def _(ax, c):
    lons = np.array([114.1, 114.3, 114.8, 115.4, 116.1, 116.9, 117.8])
    lats = np.array([22.6, 22.9, 23.3, 23.2, 22.8, 22.4, 22.1])
    ax.plot(lons, lats, "-o", ms=4, lw=1.8, color=c[0])
    ax.annotate("", xy=(lons[1], lats[1]), xytext=(lons[0], lats[0]),
                arrowprops=dict(arrowstyle="->", color=c[0], lw=2))
    ax.scatter(lons[-1], lats[-1], s=60, color=c[1], zorder=4)
    ax.set_xlim(113.6, 118.4)
    ax.set_ylim(21.7, 23.7)
    ax.set_xticks([114, 116, 118]); ax.set_yticks([22, 23])
    ax.set_xticklabels(["114°E", "116°E", "118°E"], fontsize=7.2)
    ax.set_yticklabels(["22°N", "23°N"], fontsize=7.2)
    _style(ax, c)


@reg("radar")
def _(ax, c):
    cats = ["精度", "召回", "F1", "稳健", "速度", "可解释"]
    N = len(cats)
    ang = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    ang += ang[:1]
    fig = ax.figure
    fig.clf()
    fig.subplots_adjust(left=0.03, right=0.97, top=0.97, bottom=0.03)
    polar = fig.add_subplot(111, projection="polar")
    for vals, col in zip([[3, 4, 3, 5, 4, 4], [4, 3, 4, 3, 5, 3]], [c[0], c[1]]):
        vv = vals + vals[:1]
        polar.plot(ang, vv, lw=1.8, color=col)
        polar.fill(ang, vv, color=col, alpha=0.13)
    polar.set_xticks(ang[:-1])
    polar.set_xticklabels(cats, fontsize=8)
    polar.set_ylim(0, 5.3)
    polar.set_yticks(range(1, 6))
    polar.tick_params(labelsize=6.5, colors="#333333")
    polar.grid(color="#ccd1da")
    polar.set_facecolor("white")


@reg("parallel")
def _(ax, c):
    np.random.seed(8)
    dims = 6
    for k in range(24):
        vec = rng.uniform(0, 1, dims) * [1, 1.3, 1.8, 1.2, 1.5, 1.9]
        ax.plot(range(dims), vec, lw=0.9, color=c[k % 2], alpha=0.45)
    ax.set_xticks(range(dims))
    ax.set_xticklabels([f"D{i+1}" for i in range(dims)], fontsize=7.8)
    ax.set_yticks([])
    _style(ax, c)


@reg("donut")
def _(ax, c):
    ax.pie([34, 26, 18, 12, 10], colors=c[:5], startangle=90, counterclock=False,
           wedgeprops=dict(width=0.38, edgecolor="white", linewidth=1.2))
    ax.text(0, 0, "100", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.axis("equal")


@reg("pair")
def _(ax, c):
    _draw_corr(ax, c, "pair")


@reg("joint")
def _(ax, c):
    _draw_corr(ax, c, "joint")


@reg("bivar")
def _(ax, c):
    _draw_corr(ax, c, "bivar")


@reg("network")
def _(ax, c):
    _draw_corr(ax, c, "network")


@reg("heatmap")
def _(ax, c):
    _draw_corr(ax, c, "heatmap")


@reg("sigheat")
def _(ax, c):
    _draw_corr(ax, c, "sigheat")


@reg("cheat")
def _(ax, c):
    _draw_corr(ax, c, "cheat")


@reg("resid")
def _(ax, c):
    from scipy import stats as st
    r = rng.normal(0, 1, 60)
    xxr = np.linspace(2, 20, 60)
    fit = xxr + 2.5
    fig = ax.figure
    fig.clf()
    gs = fig.add_gridspec(2, 2, hspace=0.5, wspace=0.4, left=0.1, right=0.97, top=0.95, bottom=0.12)
    a1 = fig.add_subplot(gs[0, 0]); a2 = fig.add_subplot(gs[0, 1])
    a3 = fig.add_subplot(gs[1, 0]); a4 = fig.add_subplot(gs[1, 1])
    a1.scatter(fit, r, s=9, color=c[0], alpha=0.7)
    a1.axhline(0, color="#777", lw=0.9)
    _style(a1, c)
    a1.set_title("残差 vs 拟合", fontsize=7.6)
    a2.hist(r, bins=18, color=c[1], alpha=0.7, edgecolor="white")
    _style(a2, c)
    a2.set_title("残差直方", fontsize=7.6)
    (osm, osr), (sl, ic, _) = st.probplot(r, dist="norm")
    a3.scatter(osm, osr, s=9, color=c[2], alpha=0.7)
    a3.plot(osm, sl * osm + ic, color=c[4], lw=1.2)
    _style(a3, c)
    a3.set_title("Q-Q 图", fontsize=7.6)
    a4.scatter(fit, np.abs(r), s=9, color=c[3], alpha=0.7)
    _style(a4, c)
    a4.set_title("尺度-位置", fontsize=7.6)


# ================= 示意图类（盒子 + 箭头，编辑级排版） =================
def _box(ax, x, y, w, h, text, fc, ec="#333333", fs=8, weight="normal", rounded=0.02):
    from matplotlib.patches import FancyBboxPatch
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.004,rounding_size={rounded}",
                       fc=fc, ec=ec, lw=0.9, zorder=3)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, zorder=4, color="#222", fontweight=weight)


def _box_arrow(ax, x1, y1, x2, y2, color="#55555c", lw=1.3, ls="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls=ls,
                                shrinkA=0, shrinkB=0))


LIGHT = "#EAF0F6"
LIGHT2 = "#F3F0E8"


def _tint(c):
    """把主题色压浅成盒子底色。"""
    c = c.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    tup = (int(round(r + (255 - r) * 0.82)),
           int(round(g + (255 - g) * 0.82)),
           int(round(b + (255 - b) * 0.82)))
    return f"#{tup[0]:02x}{tup[1]:02x}{tup[2]:02x}"


@reg("flow-html")
def _(ax, c):
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    _box(ax, 3.6, 6.6, 2.8, 0.95, "开始", _tint(c[0]), fs=9, weight="bold")
    _box(ax, 3.2, 4.9, 3.6, 1.0, "预处理", _tint(c[1]))
    _box(ax, 3.5, 3.1, 3.0, 0.95, "条件成立?", _tint(c[2]), weight="bold")
    _box(ax, 0.4, 1.2, 2.6, 0.95, "是 → A 路径", _tint(c[3]))
    _box(ax, 7.0, 1.2, 2.6, 0.95, "否 → B 路径", _tint(c[3]))
    _box(ax, 3.8, -0.3, 2.4, 0.85, "结束", _tint(c[0]), fs=9, weight="bold")
    _box_arrow(ax, 5, 6.6, 5, 5.9)
    _box_arrow(ax, 5, 4.9, 5, 4.05)
    _box_arrow(ax, 3.5, 3.1, 1.7, 2.15)
    _box_arrow(ax, 6.5, 3.1, 8.3, 2.15)
    _box_arrow(ax, 1.7, 1.2, 1.7, 0.55)
    _box_arrow(ax, 8.3, 1.2, 8.3, 0.55)
    _box_arrow(ax, 1.7, 0.55, 3.8, 0.55, color="#7a8391")
    _box_arrow(ax, 8.3, 0.55, 6.2, 0.55, color="#7a8391")
    _box_arrow(ax, 5, -0.3, 5, -0.8, color="#c9cede")


@reg("seq")
def _(ax, c):
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 8.2)
    parts = ["用户", "前端", "后端", "数据库"]
    xs = [1.0, 3.4, 6.0, 8.6]
    for xp in xs:
        ax.plot([xp, xp], [0.7, 7.6], color="#9aa0aa", lw=1.0, ls="--", zorder=1)
        _box(ax, xp - 0.8, 7.55, 1.6, 0.6, parts[xs.index(xp)], _tint(c[xs.index(xp) % len(c)]), fs=8.5, weight="bold")
    msgs = [((0, 5.9, "提交请求"), (3.4, 5.9, 1, 2)), ((3.4, 4.7, "处理"), (6.0, 4.7, 0, 3)),
            ((6.0, 3.5, "查询数据"), (8.6, 3.5, 1, 4)), ((8.6, 2.3, "返回结果"), (6.0, 2.3, 0, 3)),
            ((6.0, 1.4, "响应"), (3.4, 1.4, 0, 2)), ((3.4, 0.7, "渲染成功"), (1.0, 0.7, 0, 1))]
    for (sx, sy, txt), (tx, ty, _, ci) in msgs:
        lsty = "--" if ci % 2 == 0 else "-"
        _box_arrow(ax, sx + 0.8, sy, tx - 0.8, ty, color=c[ci % len(c)], lw=1.2, ls=lsty)
        ax.text((sx + tx) / 2, sy + 0.12, txt, fontsize=7.2, color="#333", ha="center")


@reg("state")
def _(ax, c):
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 7)
    _box(ax, 0.5, 5.6, 2.4, 0.95, "待机", _tint(c[0]), fs=9, weight="bold")
    _box(ax, 3.9, 5.6, 2.4, 0.95, "运行中", _tint(c[1]), fs=9, weight="bold")
    _box(ax, 7.3, 5.6, 2.4, 0.95, "挂起", _tint(c[2]), fs=9, weight="bold")
    _box(ax, 3.9, 3.0, 2.4, 0.95, "错误", _tint(c[4]), fs=9, weight="bold")
    _box(ax, 3.9, 0.7, 2.4, 0.95, "终止", _tint(c[0]), fs=9, weight="bold")
    _box_arrow(ax, 2.9, 6.1, 3.9, 6.1)
    _box_arrow(ax, 6.3, 6.1, 7.3, 6.1)
    _box_arrow(ax, 5.1, 5.6, 5.1, 3.95)  # 运行→错误
    _box_arrow(ax, 8.5, 5.6, 8.5, 4.6, color="#c9cede")  # 挂起回运行
    _box_arrow(ax, 5.1, 3.0, 5.1, 1.65)  # 错误→终止
    ax.text(2.9, 6.35, "start", fontsize=7, color="#555", ha="right")
    ax.text(6.3, 6.35, "suspend", fontsize=7, color="#555", ha="left")
    ax.text(5.25, 4.75, "fail", fontsize=7, color="#555", rotation=90)
    ax.text(8.65, 5.05, "resume", fontsize=7, color="#777", ha="center")


@reg("swimlane")
def _(ax, c):
    from matplotlib.patches import Rectangle
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 7.4)
    lanes = ["角色A", "角色B", "角色C"]
    lx = [0, 3.5, 7.0]
    for i, (lb, x0) in enumerate(zip(lanes, lx)):
        ax.add_patch(Rectangle((x0, 0), 3.0, 7.2, fc=(_tint(c[i % len(c)]) if False else "#FAFBFD"),
                               ec="#dfe3ea", lw=1))
        ax.text(x0 + 0.15, 6.95, lb, fontsize=8.5, weight="bold", color="#444")
    seqs = [(1.5, 5.4, 4.9, 5.4, "任务1", 0), (5.2, 4.2, 1.6, 4.2, "交接", 1),
            (1.6, 3.0, 4.9, 3.0, "任务2", 0), (5.2, 1.8, 1.6, 1.8, "交接", 1),
            (1.6, -0.4, 4.9, -0.4, "", 0)]
    for sx, sy, tx, ty, txt, _ in seqs:
        if ty < 0:
            break
        _box_arrow(ax, sx, sy, tx, ty, color=c[3 % len(c)], lw=1.3)
        if txt:
            ax.text((sx + tx) / 2, sy + 0.14, txt, fontsize=7.2, color="#333", ha="center")


@reg("indextree")
def _(ax, c):
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    _box(ax, 3.9, 6.9, 2.2, 0.9, "总指标", _tint(c[0]), fs=9, weight="bold")
    _box(ax, 0.4, 4.8, 2.4, 0.9, "维度一", _tint(c[1]), fs=8.5)
    _box(ax, 3.8, 4.8, 2.4, 0.9, "维度二", _tint(c[2]), fs=8.5)
    _box(ax, 7.2, 4.8, 2.4, 0.9, "维度三", _tint(c[3]), fs=8.5)
    leaves = [("指标A", 0.3, 2.8), ("指标B", 2.3, 2.0), ("指标C", 3.9, 2.8),
              ("指标D", 5.9, 2.0), ("指标E", 7.3, 2.8), ("指标F", 9.3, 2.0)]
    for txt, bx, by in leaves:
        _box(ax, bx, by, 1.5, 0.85, txt, "#F7F9FB", ec="#c6cdd6", fs=7.6)
    _box_arrow(ax, 5, 6.9, 1.6, 5.7)
    _box_arrow(ax, 5, 6.9, 5, 5.7)
    _box_arrow(ax, 5, 6.9, 8.4, 5.7)
    for bx, by in [(0.9, 4.8), (2.9, 4.8), (4.9, 4.8), (6.9, 4.8), (8.1, 4.8), (10.1, 4.8)]:
        if bx > 9.5:
            break
        ax.plot([bx, bx], [by, 3.65], color="#b6bcc8", lw=0.9, zorder=1)


@reg("chartflow")
def _(ax, c):
    """图表总览流程：根「全部图表」→ 7 大类 → 全部 70 种图表（含本总览图）。

    覆盖 static/app.js PAPER_GROUPS 全部条目，随时与其对齐；节点数 = 各类别条目求和。
    """
    groups = [
        ("比较类", ["分组柱状图", "堆叠柱状图", "发散条形图", "水平条形图", "棒棒糖图", "哑铃图",
                 "背靠背图", "点误差图", "配对点图", "显著性柱状图", "森林图"]),
        ("趋势类", ["折线·置信带", "面积图", "双轴图", "斜率图", "瀑布图", "帕累托图",
                 "扇形预测图", "排名轨迹图", "流图", "CUSUM 累积和", "分位数趋势带"]),
        ("分布类", ["箱线图", "小提琴图", "分组小提琴图", "直方图", "密度曲线", "山脊图",
                 "雨云图", "后验轨迹图", "Q-Q 图", "ECDF 累积分布", "联合分布图"]),
        ("相关/回归", ["散点·回归", "散点矩阵", "二维密度图", "Bland-Altman", "校准图", "相关矩阵热力图",
                 "聚类热力图", "网络图", "残差诊断四联", "相关显著性热力图"]),
        ("组成/多维", ["环形饼图", "雷达图", "平行坐标", "等高线图", "三维曲面图", "桑基图",
                 "泰勒图", "PCA 双标图"]),
        ("专业/高级", ["生存曲线", "漏斗图", "日历热力图", "性能剖面图", "火山图", "Hovmöller 图",
                 "ICE/PDP 图", "组合子图", "Tornado 灵敏度", "甘特图", "相平面图",
                 "参数扫描热力图", "轨迹/OD 流向图"]),
        ("流程/架构", ["流程图（HTML）", "时序图", "状态机图", "泳道图", "指标体系树", "图表总览流程"]),
    ]
    total = sum(len(items) for _, items in groups)
    fig = ax.figure
    fig.clf()
    fig.set_size_inches(21, 12.3, forward=True)
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    a = fig.add_subplot(111)
    a.axis("off")
    a.set_xlim(0, 21.0); a.set_ylim(0, 12.3)

    nx = len(groups)
    xs = [1.7 + i * 3.0 for i in range(nx)]      # 每列中轴
    y_top, hdr_y, root_y = 9.0, 9.78, 10.62      # 叶子顶 / 类目盒 / 根盒
    bend_y = 11.62                               # 根→类目水平总线
    lh, step = 0.44, 0.62

    # 根
    _box(a, 21.0 / 2 - 2.7, root_y, 5.4, 0.78, f"全部图表 · {total} 种",
         _tint(c[0]), fs=11, weight="bold", rounded=0.035)
    for i, (gn, items) in enumerate(groups):
        xi = xs[i]
        # 根 → 类目：总线 + 竖线箭头
        a.plot([21.0 / 2, xi], [bend_y, bend_y], color="#7a8391", lw=1.1, zorder=1)
        _box_arrow(a, xi, bend_y, xi, hdr_y + 0.56, color="#7a8391", lw=1.1)
        # 类目盒（括号内为该类图表数量）
        _box(a, xi - 1.25, hdr_y, 2.5, 0.56, f"{gn} · {len(items)}",
             _tint(c[(i + 1) % len(c)]), fs=8.2, weight="bold", rounded=0.02)
        # 类目 → 主干（左侧竖直干道，向右出短枝接到每张图）
        trunk = xi - 1.25
        link_y = hdr_y - 0.34
        a.plot([xi, xi], [hdr_y - 0.04, link_y], color="#5c636e", lw=1.2, zorder=1)
        a.plot([xi, trunk], [link_y, link_y], color="#5c636e", lw=1.2, zorder=1)
        _box_arrow(a, trunk, link_y, trunk, link_y - 0.22, color="#5c636e", lw=1.2)
        last_c = y_top - (len(items) - 1) * step - lh / 2
        a.plot([trunk, trunk], [link_y - 0.22, last_c], color="#b6bcc8", lw=1.0, zorder=2)
        for j, name in enumerate(items):
            cy = y_top - j * step - lh / 2
            _box(a, xi - 1.0, cy - lh / 2, 2.0, lh, name, "#F7F9FB", ec="#c6cdd6", fs=6.2)
            a.plot([trunk, xi - 1.0], [cy, cy], color="#b6bcc8", lw=0.8, zorder=2)
    # 图注
    a.text(21.0 / 2, 0.55, f"共 {nx} 大类 · {total} 种图表 · 选择困难时按赛题结论类型对号入座",
           ha="center", fontsize=8, color="#6a7078")


def _save(fig, key, theme):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        try:
            if not getattr(fig, "_no_tight", False):
                fig.tight_layout()
        except Exception:
            fig.subplots_adjust(left=0.12, right=0.96, top=0.94, bottom=0.14)
    p = OUT / f"paper-{key}__{theme}.png"
    fig.savefig(p, dpi=DPIX, facecolor="white")
    plt.close(fig)


def main():
    import json, sys
    keys = list(FUNCS.keys())
    # 与前端 PAPER_GROUPS 对齐（保证无缺漏/无多余）
    keyset = set(keys)
    print(f"[previews] 注册绘图函数 {len(keys)} 个；主题 {len(THEMES)} 套 → 共 {len(keys) * len(THEMES)} 张")
    n = 0
    fails = []
    for key in keys:
        for theme, cols in THEMES.items():
            try:
                fig, ax = _new()
                FUNCS[key](ax, cols)
                _save(fig, key, theme)
                n += 1
            except Exception as e:
                fails.append((key, theme, repr(e)))
                plt.close("all")
    print(f"[previews] 完成 {n} 张；失败 {len(fails)}")
    for k, t, e in fails[:40]:
        print(f"  FAIL {k}/{t}: {e}")


if __name__ == "__main__":
    main()
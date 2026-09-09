"""
统计类 code starter — 对应论文 §7 统计检验 / 数据预处理
适用: 描述性统计 / 假设检验 / 方差分析 ANOVA / 相关分析 / 分布拟合 / 插值拟合

库依赖:
- scipy.stats (检验/分布/相关)
- statsmodels (ANOVA)
- numpy.polyfit, scipy.optimize.curve_fit (拟合)

国赛常见用法: 数据预处理、显著性检验、相关性分析、曲线拟合
"""

import numpy as np
import pandas as pd
import scipy.stats as st
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline, interp1d
from scipy.optimize import curve_fit
from pathlib import Path

np.random.seed(42)
# 中文字体, 避免论文图中文乱码
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. 描述性统计
# ============================================================
def descriptive_stats(df):
    """
    Args:
        df: DataFrame, 数值列
    Returns:
        DataFrame: 均值/中位数/标准差/偏度/峰度/极值
    """
    desc = df.describe().T
    desc["偏度"] = df.skew()
    desc["峰度"] = df.kurt()
    return desc


# ============================================================
# 2. 正态性检验
# ============================================================
def normality_tests(x):
    """
    Shapiro-Wilk + D'Agostino + 偏度峰度联合检验
    Returns:
        dict {test: (statistic, pvalue)}
    """
    x = np.asarray(x, dtype=float)
    out = {}
    out["shapiro"] = st.shapiro(x)
    out["normaltest"] = st.normaltest(x)
    return out


# ============================================================
# 3. 假设检验 (t / 秩和 / 卡方)
# ============================================================
def hypothesis_test(group1, group2=None, kind="ttest"):
    """
    Args:
        group1, group2: 一维数组 (group2 为 None 时单样本)
        kind: "ttest" (双样本独立) / "paired" (配对) / "wilcoxon" (秩和)
    Returns:
        dict with keys: statistic, pvalue, significant (p<0.05)
    """
    alpha = 0.05
    if kind == "ttest":
        stat, p = st.ttest_ind(group1, group2, equal_var=False)
    elif kind == "paired":
        stat, p = st.ttest_rel(group1, group2)
    elif kind == "wilcoxon":
        stat, p = st.wilcoxon(group1, group2)
    return {"statistic": stat, "pvalue": p, "significant": p < alpha}


def chi2_test(contingency_table):
    """卡方独立性检验"""
    stat, p, dof, expected = st.chi2_contingency(np.asarray(contingency_table))
    return {"statistic": stat, "pvalue": p, "dof": dof, "expected": expected,
            "significant": p < 0.05}


# ============================================================
# 4. 方差分析 ANOVA
# ============================================================
def anova_oneway(*groups):
    """
    单因素方差分析 (对应论文"双因素方差分析"前的基础)
    Returns:
        dict with keys: F, pvalue, significant
    """
    F, p = st.f_oneway(*groups)
    return {"F": F, "pvalue": p, "significant": p < 0.05}


def anova_twoway(df, value, factor1, factor2):
    """
    双因素方差分析 (含交互作用)
    Args:
        df: DataFrame
        value: 数值列名
        factor1, factor2: 类别列名
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    formula = f"{value} ~ C({factor1}) * C({factor2})"
    model = ols(formula, data=df).fit()
    table = sm.stats.anova_lm(model, typ=2)
    return {"anova_table": table, "model": model}


# ============================================================
# 5. 相关分析
# ============================================================
def correlation_matrix(df, method="pearson"):
    """
    method: "pearson" / "spearman" / "kendall"
    Returns:
        dict with keys: corr (DataFrame), pvalue (DataFrame)
    """
    corr = df.corr(method=method)
    pvals = pd.DataFrame(np.ones_like(corr.values), index=corr.index, columns=corr.columns)
    cols = list(df.columns)
    for i, ci in enumerate(cols):
        for j, cj in enumerate(cols):
            if i != j:
                if method == "pearson":
                    _, p = st.pearsonr(df[ci], df[cj])
                elif method == "spearman":
                    _, p = st.spearmanr(df[ci], df[cj])
                else:
                    _, p = st.kendalltau(df[ci], df[cj])
                pvals.loc[ci, cj] = p
    return {"corr": corr, "pvalue": pvals}


# ============================================================
# 6. 分布拟合 + KS 检验
# ============================================================
def fit_distribution(x, dist="norm"):
    """
    Args:
        x: 一维数据
        dist: "norm" / "expon" / "gamma" / "lognorm"
    Returns:
        dict with keys: params, ks_statistic, ks_pvalue
    """
    dist_fn = getattr(st, dist)
    params = dist_fn.fit(x)
    ks, p = st.kstest(x, dist, args=params)
    return {"params": params, "ks_statistic": ks, "ks_pvalue": p}


# ============================================================
# 7. 插值与拟合
# ============================================================
def spline_interp(x, y, x_new):
    """三次样条插值"""
    cs = CubicSpline(x, y)
    return cs(x_new)


def poly_fit(x, y, degree=2):
    """多项式最小二乘拟合"""
    coeffs = np.polyfit(x, y, degree)
    poly = np.poly1d(coeffs)
    return {"coeffs": coeffs, "poly": poly, "pred": poly(x),
            "r2": r2(y, poly(x))}


def curve_fit_model(x, y, func, p0=None):
    """任意非线性函数拟合 (如 Logistic/指数/幂律)"""
    popt, pcov = curve_fit(func, x, y, p0=p0, maxfev=10000)
    pred = func(x, *popt)
    return {"params": popt, "cov": pcov, "pred": pred, "r2": r2(y, pred)}


def r2(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    return 1 - ss_res / (ss_tot + 1e-12)


# ============================================================
# 8. 可视化
# ============================================================
def plot_corr_heatmap(corr, title="相关性热力图"):
    import seaborn as sns
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
    ax.set_title(title)
    plt.tight_layout()
    return fig


# ============================================================
# 主流程示例 (对应论文 §7)
# ============================================================
if __name__ == "__main__":
    # 模拟数据 (实际从附件读)
    np.random.seed(42)
    x = np.linspace(0, 10, 100)
    y_clean = 2 + 0.5 * x
    y = y_clean + np.random.normal(0, 1, 100)

    # 线性拟合
    fit = poly_fit(x, y, degree=1)
    print(f"线性拟合 R²: {fit['r2']:.4f}, 系数: {fit['coeffs']}")

    # 正态性
    nt = normality_tests(y)
    print(f"Shapiro p = {nt['shapiro'].pvalue:.4f}")

    # 相关
    df = pd.DataFrame({"x": x, "y": y})
    corr_res = correlation_matrix(df)
    print(f"Pearson 相关系数: {corr_res['corr'].iloc[0, 1]:.4f}")

    fig = plot_corr_heatmap(corr_res["corr"])
    plt.savefig("figures/statistics_corr.png", dpi=300)
    print("已保存 figures/statistics_corr.png")

"""
仿真类 code starter — 对应论文 §5.x 仿真 / §6 灵敏度
适用: 蒙特卡罗 / 拉丁超立方采样 (LHS) / 系统动力学 ODE / Agent-based

这是可改写的实现起点，不是竞赛加分配方。只有当参数分布、扰动范围、样本量与当前问题有依据时，才使用相应方法；模型名称应准确描述实际实现。
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from pathlib import Path

np.random.seed(42)
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. 蒙特卡罗 (Monte Carlo) 基本框架
# ============================================================
def monte_carlo(simulator, n_samples=1000, **distributions):
    """
    Args:
        simulator: 单次仿真函数, 接受关键字参数, 返回标量或 dict
        n_samples: 样本数
        distributions: dict of {param_name: callable returning ndarray of size n}
    Returns:
        list of simulator return values
    """
    samples = {k: dist(n_samples) for k, dist in distributions.items()}
    results = []
    for i in range(n_samples):
        kwargs = {k: samples[k][i] for k in distributions}
        results.append(simulator(**kwargs))
    return results, samples


# ============================================================
# 2. 拉丁超立方采样 LHS（适用于需要覆盖多维参数空间的场景）
# ============================================================
def lhs_sampling(d, n, bounds=None, seed=42):
    """
    Args:
        d: 维度 (扰动参数数量)
        n: 样本数
        bounds: list of (low, high) tuples, 长度 d. 默认 [0, 1]
    Returns:
        ndarray (n, d)
    """
    sampler = qmc.LatinHypercube(d=d, seed=seed)
    unit = sampler.random(n=n)  # ∈ [0, 1]^d
    if bounds is None:
        return unit
    lows = np.array([b[0] for b in bounds])
    highs = np.array([b[1] for b in bounds])
    return lows + unit * (highs - lows)


def joint_sensitivity_lhs(simulator, baseline_params, perturbation_levels=None, n_samples=200):
    """
    对所有 baseline_params 做联合 LHS 扰动 (winning_patterns §7)

    Args:
        simulator: callable(**params) -> scalar
        baseline_params: dict {param: baseline_value}
        perturbation_levels: list of perturbation ratios, e.g., [0.05, 0.10, 0.20]
        n_samples: per level
    Returns:
        dict {level: {"samples": ndarray, "outputs": ndarray, "stats": dict}}
    """
    if perturbation_levels is None:
        # 示例默认值；实际使用时应由历史波动、测量误差或业务边界替换。
        perturbation_levels = [0.05, 0.10, 0.20]

    param_names = list(baseline_params.keys())
    d = len(param_names)
    baseline_values = np.array([baseline_params[k] for k in param_names])

    results = {}
    for level in perturbation_levels:
        bounds = [(v * (1 - level), v * (1 + level)) for v in baseline_values]
        samples = lhs_sampling(d, n_samples, bounds)
        outputs = []
        for i in range(n_samples):
            params = {k: samples[i, j] for j, k in enumerate(param_names)}
            outputs.append(simulator(**params))
        outputs = np.array(outputs)
        stats = {
            "mean": outputs.mean(),
            "std": outputs.std(),
            "p5": np.percentile(outputs, 5),
            "p95": np.percentile(outputs, 95),
            "cv": outputs.std() / abs(outputs.mean() + 1e-12),
        }
        results[level] = {"samples": samples, "outputs": outputs, "stats": stats}
    return results, param_names


# ============================================================
# 3. Sobol 全局灵敏度（存在参数交互且样本预算允许时选用）
# ============================================================
def sobol_indices(simulator, param_names, baseline_params, n_samples=1024):
    """
    需要 SALib 库
    Returns: dict {param: {S1, ST}}
    """
    try:
        from SALib.sample import saltelli
        from SALib.analyze import sobol
    except ImportError:
        print("⚠ SALib 未安装, 跳过 Sobol")
        return None

    bounds = [[v * 0.8, v * 1.2] for v in baseline_params.values()]
    problem = {
        "num_vars": len(param_names),
        "names": param_names,
        "bounds": bounds,
    }
    samples = saltelli.sample(problem, n_samples)
    outputs = np.array([simulator(**dict(zip(param_names, s))) for s in samples])
    Si = sobol.analyze(problem, outputs, print_to_console=False)
    return {param: {"S1": float(Si["S1"][i]), "ST": float(Si["ST"][i])}
            for i, param in enumerate(param_names)}


# ============================================================
# 4. ODE 系统仿真示例（带隔离移除项的 SEIR）
# ============================================================
def seir_with_quarantine(t, y, beta, sigma, gamma, kappa):
    """
    SEIR 示例：感染者以 kappa 速率进入移除状态。

    y = [S, E, I, R]
    """
    S, E, I, R = y
    N = S + E + I + R
    dS = -beta * S * I / N
    dE = beta * S * I / N - sigma * E
    dI = sigma * E - gamma * I - kappa * I  # kappa 是隔离率
    dR = gamma * I + kappa * I
    return [dS, dE, dI, dR]


def simulate_seir(N=10000, I0=10, beta=0.3, sigma=0.2, gamma=0.1, kappa=0.05, T=180):
    y0 = [N - I0, 0, I0, 0]
    sol = solve_ivp(seir_with_quarantine, (0, T), y0,
                     args=(beta, sigma, gamma, kappa), dense_output=True,
                     t_eval=np.arange(0, T + 1))
    return {"t": sol.t, "S": sol.y[0], "E": sol.y[1], "I": sol.y[2], "R": sol.y[3],
            "peak_I": sol.y[2].max(), "peak_t": sol.t[sol.y[2].argmax()]}


# ============================================================
# 5. 可视化辅助
# ============================================================
def plot_lhs_pairs(samples, outputs, param_names):
    """
    pairs plot (sensitivity_table.md 图 1)
    """
    df = pd.DataFrame(samples, columns=param_names)
    df["output"] = outputs
    try:
        import seaborn as sns
        g = sns.pairplot(df, diag_kind="kde", plot_kws={"alpha": 0.4})
        return g.fig
    except ImportError:
        # 备用: 简单矩阵
        d = len(param_names)
        fig, axes = plt.subplots(d, d, figsize=(d*3, d*3))
        for i in range(d):
            for j in range(d):
                if i == j:
                    axes[i, j].hist(samples[:, i], bins=20, color='steelblue')
                else:
                    axes[i, j].scatter(samples[:, j], samples[:, i],
                                        c=outputs, cmap='viridis', s=10, alpha=0.5)
                if i == d - 1:
                    axes[i, j].set_xlabel(param_names[j])
                if j == 0:
                    axes[i, j].set_ylabel(param_names[i])
        plt.tight_layout()
        return fig


def plot_tornado(sobol_result, output_label="目标函数"):
    """
    Tornado 图 (sensitivity_table.md 图 2)
    """
    sorted_items = sorted(sobol_result.items(), key=lambda x: x[1]["S1"])
    names = [item[0] for item in sorted_items]
    s1s = [item[1]["S1"] for item in sorted_items]
    sts = [item[1]["ST"] for item in sorted_items]

    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(y - 0.2, s1s, 0.4, label="一阶 $S_1$", color="steelblue")
    ax.barh(y + 0.2, sts, 0.4, label="总指数 $S_T$", color="orangered")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Sobol 灵敏度指数")
    ax.set_title(f"{output_label} Sobol 灵敏度指数")
    ax.legend()
    plt.tight_layout()
    return fig


# ============================================================
# 6. M/M/1 排队系统: 解析公式 + 离散事件仿真
# ============================================================
def mm1_queue(lambda_, mu, T=24, warmup=1):
    """
    M/M/1 排队: 泊松到达 + 指数服务 + 单服务台, 求平均队长/等待指标。

    解析指标 (Little 定律, rho=lambda/mu):
        L  = rho/(1-rho)        平均队长 (系统中的顾客数, 含正在服务)
        Lq = rho^2/(1-rho)      平均等待队长 (队列中的顾客数)
        W  = L/lambda           平均逗留时间 (等待 + 服务)
        Wq = Lq/lambda          平均等待时间 (仅排队)

    Args:
        lambda_: 顾客到达率 (单位时间到达数), 要求 lambda_ < mu
        mu: 服务率 (单位时间服务数), rho = lambda_/mu < 1 才稳定
        T: 仿真总时长
        warmup: 预热时长, 忽略此期间到达的顾客以消除初始瞬态
    Returns:
        dict with keys: rho, L, Lq, W, Wq, sim_avg_wait,
                        inter_arrivals, wait_times (供绘图)
    """
    if lambda_ <= 0 or mu <= 0:
        raise ValueError("到达率与服务率都必须是正数")
    if lambda_ >= mu:
        raise ValueError("到达率须小于服务率 (rho<1), 否则队列无限增长")
    rho = lambda_ / mu
    # ---- 解析公式 ----
    L = rho / (1 - rho)
    Lq = rho ** 2 / (1 - rho)
    W = L / lambda_
    Wq = Lq / lambda_

    # ---- 离散事件仿真 ----
    # 到达过程为泊松过程, 顾客到达间隔服从指数分布 Exp(lambda_)
    t = 0.0
    arrival_times = []
    while t < T:
        t += np.random.exponential(1.0 / lambda_)
        arrival_times.append(t)
    arrival_times = np.array(arrival_times)
    arrival_times = arrival_times[arrival_times <= T]

    # 逐顾客: 服务时长 Exp(mu), 用事件调度推进
    wait_times = []
    busy_until = 0.0          # 服务台下一次空闲时刻
    for arr in arrival_times:
        service = np.random.exponential(1.0 / mu)   # 一次服务时长
        start = max(arr, busy_until)                # 实际开始服务时刻
        wait = start - arr                          # 在队列中等待的时间
        busy_until = start + service
        wait_times.append(wait)
    wait_times = np.array(wait_times)

    # 去掉预热期顾客后再计平均等待
    n_warm = int(np.searchsorted(arrival_times, warmup))
    sim_wait = wait_times[n_warm:]
    sim_avg_wait = float(sim_wait.mean()) if sim_wait.size else 0.0
    inter_arrivals = np.diff(np.insert(arrival_times, 0, 0.0))
    return {"rho": rho, "L": L, "Lq": Lq, "W": W, "Wq": Wq,
            "sim_avg_wait": sim_avg_wait,
            "inter_arrivals": inter_arrivals, "wait_times": wait_times}


# ============================================================
# 7. 一维元胞自动机 (Elementary Cellular Automaton, numpy 自实现)
# ============================================================
def cellular_automata(grid, rule_number, steps):
    """
    一维基本元胞自动机: 每个细胞依其自身 + 左右邻居共 3 格状态,
    查规则表 (rule_number 的 8 位二进制) 更新, 边界按周期处理。

    Args:
        grid: 一维初始网格 (长度为 width), 取值 0/1
        rule_number: 规则号 (0..255), 如 rule 30/90/110/184
        steps: 演化步数
    Returns:
        dict with key: grid_history, 形状 (steps+1, width) 的二维演化数组
                       (每行为一代, 首行为初始构型)
    """
    grid = np.asarray(grid, dtype=int).ravel()
    width = grid.shape[0]
    # 规则映射表: 邻居三元组 (L, C, R) 转索引 (L<<2 | C<<1 | R)
    rule = np.array([(rule_number >> b) & 1 for b in range(8)], dtype=int)
    history = [grid.copy()]
    state = grid
    for _ in range(steps):
        L = np.roll(state, 1)     # 左邻居 (边界周期)
        R = np.roll(state, -1)    # 右邻居
        idx = (L << 2) | (state << 1) | R
        state = rule[idx]
        history.append(state.copy())
    return {"grid_history": np.vstack(history)}   # (steps+1, width)


# ============================================================
# 主流程示例 (对应论文 §5.x + §6)
# ============================================================
if __name__ == "__main__":
    # SEIR 仿真示例
    result = simulate_seir(N=10000, I0=10, beta=0.3, sigma=0.2, gamma=0.1, kappa=0.05)
    print(f"峰值感染数: {result['peak_I']:.0f}")
    print(f"峰值时间: 第 {result['peak_t']:.1f} 天")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(result["t"], result["S"], label="易感 S")
    ax.plot(result["t"], result["E"], label="潜伏 E")
    ax.plot(result["t"], result["I"], label="感染 I", color='red', lw=2)
    ax.plot(result["t"], result["R"], label="康复 R")
    ax.set_xlabel("时间 (天)")
    ax.set_ylabel("人数")
    ax.set_title("带隔离移除项的 SEIR 模型仿真")
    ax.legend()
    plt.tight_layout()
    plt.savefig("figures/simulation_seir.png", dpi=300)

    # LHS 联合灵敏度
    def simulator(beta, sigma, gamma, kappa):
        r = simulate_seir(beta=beta, sigma=sigma, gamma=gamma, kappa=kappa)
        return r["peak_I"]

    baseline = {"beta": 0.3, "sigma": 0.2, "gamma": 0.1, "kappa": 0.05}
    sens_results, param_names = joint_sensitivity_lhs(
        simulator, baseline, perturbation_levels=[0.05, 0.10, 0.20], n_samples=100
    )
    for level, r in sens_results.items():
        print(f"\n扰动 ±{level*100:.0f}%:")
        print(f"  Peak I 5%-95% 区间: [{r['stats']['p5']:.0f}, {r['stats']['p95']:.0f}]")
        print(f"  CV: {r['stats']['cv']*100:.2f}%")

    # 画 LHS pairs (取 ±10% 档)
    fig = plot_lhs_pairs(sens_results[0.10]["samples"],
                          sens_results[0.10]["outputs"], param_names)
    plt.savefig("figures/simulation_lhs_pairs.png", dpi=300)
    print("\n所有图已保存 figures/")

    # ---- M/M/1 排队: 解析 vs 仿真 ----
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    q = mm1_queue(lambda_=2.0, mu=3.0, T=5000, warmup=50)
    print("\n===== M/M/1 排队系统 =====")
    print(f"rho={q['rho']:.3f}")
    print(f"解析: L={q['L']:.3f}, Lq={q['Lq']:.3f}, W={q['W']:.3f}, Wq={q['Wq']:.3f}")
    print(f"仿真: 平均等待 = {q['sim_avg_wait']:.3f}")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(q["inter_arrivals"], bins=40, color="steelblue", edgecolor="white")
    axes[0].set_xlabel("到达间隔"); axes[0].set_ylabel("频数")
    axes[0].set_title("M/M/1 顾客到达间隔分布")
    axes[1].hist(q["wait_times"], bins=40, color="orangered", edgecolor="white")
    axes[1].set_xlabel("等待时间"); axes[1].set_ylabel("频数")
    axes[1].set_title("M/M/1 顾客等待时间分布")
    plt.tight_layout()
    plt.savefig("figures/simulation_mm1_wait.png", dpi=300)
    print("已保存 figures/simulation_mm1_wait.png")

    # ---- 一维元胞自动机 rule 110 ----
    init = np.zeros(101, dtype=int); init[50] = 1   # 单点种子, 中间触发
    ca = cellular_automata(init, rule_number=110, steps=80)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(ca["grid_history"], cmap="gray_r", aspect="auto")
    ax.set_xlabel("空间位置")
    ax.set_ylabel("演化步")
    ax.set_title("一维元胞自动机 rule 110 时空演化")
    plt.tight_layout()
    plt.savefig("figures/simulation_ca_rule110.png", dpi=300)
    print("已保存 figures/simulation_ca_rule110.png")

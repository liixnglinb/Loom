"""
优化类 code starter — 对应论文 §5.x.2 求解算法
适用: 线性规划 (LP) / 整数规划 (IP/MILP) / 二次规划 (QP) / 凸优化

库依赖:
- cvxpy (DSL, 自动选择 solver)
- scipy.optimize (轻量级)
- pulp (MILP 备选)

国赛常见用法: 调度、配比、选址、组合优化
"""

import numpy as np
import pandas as pd
import cvxpy as cp
from scipy.optimize import linprog, minimize
import matplotlib.pyplot as plt
from pathlib import Path

# ---- 全局可复现性 ----
np.random.seed(42)

# 中文字体, 避免论文图中文乱码
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ---- 输出目录自动创建 (P2-5 修复) ----
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. LP / MILP 模板 (cvxpy)
# ============================================================
def solve_milp_template(p, c, B, x_max=50):
    """
    最大化 sum_i (p_i - c_i) * x_i
    s.t.  sum_i c_i * x_i <= B
          0 <= x_i <= x_max, integer

    Args:
        p: ndarray (n,) 单价
        c: ndarray (n,) 成本
        B: float 总预算
        x_max: int 单品上限

    Returns:
        dict with keys: x_star, obj, status, solve_time
    """
    n = len(p)
    x = cp.Variable(n, integer=True)
    objective = cp.Maximize((p - c) @ x)
    constraints = [
        c @ x <= B,
        x >= 0,
        x <= x_max,
    ]
    prob = cp.Problem(objective, constraints)
    prob.solve()  # 自动选择可用 solver (GLPK_MI 未装时回退默认)

    return {
        "x_star": x.value.astype(int) if x.value is not None else None,
        "obj": prob.value,
        "status": prob.status,
        "solve_time_s": prob.solver_stats.solve_time,
    }


# ============================================================
# 2. 凸优化模板 (cvxpy)
# ============================================================
def solve_convex_template(A, b, lambda_reg=0.1):
    """
    Ridge 回归示例:
    minimize ||A x - b||_2^2 + lambda * ||x||_2^2
    """
    n = A.shape[1]
    x = cp.Variable(n)
    objective = cp.Minimize(cp.sum_squares(A @ x - b) + lambda_reg * cp.sum_squares(x))
    prob = cp.Problem(objective)
    prob.solve()
    return {"x_star": x.value, "obj": prob.value, "status": prob.status}


# ============================================================
# 3. 多目标 (加权法) 模板
# ============================================================
def solve_multiobjective_weighted(objs, constraints, weights):
    """
    minimize sum_k w_k * f_k(x)

    Args:
        objs: list of cvxpy expressions, 每个是一个目标
        constraints: list of cvxpy constraints
        weights: list of float, 加权 (∑=1)
    """
    weighted_obj = sum(w * o for w, o in zip(weights, objs))
    prob = cp.Problem(cp.Minimize(weighted_obj), constraints)
    prob.solve()
    return prob


# ============================================================
# 4. 启发式 (遗传算法 GA, 自实现简化版)
# ============================================================
def genetic_algorithm(fitness, n_vars, bounds, n_pop=100, n_gen=200,
                      crossover_rate=0.8, mutation_rate=0.1):
    """
    自适应交叉率 GA (winning_patterns §4 命名变体写法)
    """
    pop = np.random.uniform(bounds[0], bounds[1], (n_pop, n_vars))
    best_history = []

    for gen in range(n_gen):
        scores = np.array([fitness(ind) for ind in pop])
        # 轮盘赌选择
        probs = scores / scores.sum() if scores.sum() > 0 else np.ones(n_pop) / n_pop
        indices = np.random.choice(n_pop, n_pop, p=probs)
        new_pop = pop[indices].copy()
        # 交叉
        for i in range(0, n_pop - 1, 2):
            if np.random.random() < crossover_rate:
                point = np.random.randint(1, n_vars)
                new_pop[i, point:], new_pop[i+1, point:] = \
                    new_pop[i+1, point:].copy(), new_pop[i, point:].copy()
        # 变异
        mask = np.random.random((n_pop, n_vars)) < mutation_rate
        noise = np.random.normal(0, 0.1, (n_pop, n_vars))
        new_pop = np.where(mask, new_pop + noise, new_pop)
        new_pop = np.clip(new_pop, bounds[0], bounds[1])
        pop = new_pop
        best_history.append(scores.max())

    best_idx = np.argmax([fitness(ind) for ind in pop])
    return {"x_star": pop[best_idx], "obj": fitness(pop[best_idx]), "history": best_history}


# ============================================================
# 5. 可行贪心基线
# ============================================================
def greedy_budget_baseline(p, c, B, x_max=50):
    """按单位成本利润从高到低分配预算, 返回可行的整数基线。

    与“每个产品都单独使用整份预算”不同, 本基线在所有产品间
    共享同一个剩余预算, 因此始终满足 ``c @ x <= B``。
    """
    p = np.asarray(p, dtype=float)
    c = np.asarray(c, dtype=float)
    if p.ndim != 1 or c.ndim != 1 or p.shape != c.shape:
        raise ValueError("p 和 c 必须是形状相同的一维数组")
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(c)):
        raise ValueError("p 和 c 必须全部为有限数")
    if np.any(c < 0):
        raise ValueError("成本 c 不能为负数")
    if not np.isfinite(B) or B < 0:
        raise ValueError("预算 B 必须是非负有限数")

    if np.isscalar(x_max):
        caps = np.full(len(p), x_max, dtype=float)
    else:
        caps = np.asarray(x_max, dtype=float)
        if caps.shape != p.shape:
            raise ValueError("数组形式的 x_max 必须与 p 形状相同")
    if (not np.all(np.isfinite(caps)) or np.any(caps < 0)
            or not np.all(caps == np.floor(caps))):
        raise ValueError("x_max 必须是非负整数")
    caps = caps.astype(int)

    margin = p - c
    x = np.zeros(len(p), dtype=int)

    # 零成本且正利润的产品不消耗预算, 可直接取上限。
    free_profitable = (c == 0) & (margin > 0)
    x[free_profitable] = caps[free_profitable]

    candidates = np.flatnonzero((c > 0) & (margin > 0) & (caps > 0))
    ratios = margin[candidates] / c[candidates]
    # 先比单位成本利润, 同比率时先选单件利润更高者。
    order = candidates[np.lexsort((-margin[candidates], -ratios))]

    remaining = float(B)
    for i in order:
        affordable = int(np.floor(remaining / c[i] + 1e-12))
        quantity = min(caps[i], max(0, affordable))
        # 抵消浮点数据刚好在整数边界时可能的越界。
        while quantity > 0 and quantity * c[i] > remaining + 1e-10:
            quantity -= 1
        x[i] = quantity
        remaining -= quantity * c[i]

    budget_used = float(c @ x)
    if budget_used > B + 1e-8:
        raise RuntimeError("贪心基线产生了不可行解")
    return {
        "x_star": x,
        "obj": float(margin @ x),
        "budget_used": budget_used,
    }


# ============================================================
# 6. Sanity check 套件 (anti_pattern D2)
# ============================================================
def sanity_check(result, expected_range=None, baseline=None):
    """
    四步 sanity check:
    1. 状态正常?
    2. 数量级合理?
    3. 边界 case?
    4. 比 baseline 强?
    """
    checks = {}
    checks["status_ok"] = result.get("status", "").lower() in ["optimal", "ok", "success"]
    if expected_range:
        x = result["x_star"]
        checks["range_ok"] = bool(np.all((x >= expected_range[0]) & (x <= expected_range[1])))
    if baseline is not None:
        checks["beats_baseline"] = result["obj"] >= baseline - 1e-9
    return checks


# ============================================================
# 6.1 粒子群优化 (PSO, 自实现)
# ============================================================
def particle_swarm(fitness, bounds, n_particles=30, n_iter=200,
                   w=0.7, c1=1.5, c2=1.5):
    """
    标准粒子群优化 (Particle Swarm Optimization)。

    适用场景: 连续/离散变量的全局寻优, 作为对 LP/MILP 的启发式替代,
    尤其适合目标函数不可导、非凸多峰 (如本文多峰测试函数) 的情形。

    Args:
        fitness: callable, f(x) -> float (求最小值)
        bounds: (lb, ub) 或 [(lb1,ub1), ...], 变量边界
        n_particles: int 粒子数
        n_iter: int 迭代轮数
        w: float 惯性权重
        c1: float 个体认知学习因子
        c2: float 全局社会学习因子

    Returns:
        dict with keys: x_star, obj, history
    """
    bound = np.asarray(bounds, dtype=float)
    if bound.ndim == 1:
        b = np.tile(bound, (2, 1)).T   # 每个变量统一 [lb, ub]
    else:
        b = bound
    n_vars = b.shape[0]
    lb, ub = b[:, 0], b[:, 1]

    # Step 1: 随机初始化粒子位置与速度
    pos = np.random.uniform(lb, ub, (n_particles, n_vars))
    vel = np.random.uniform(-(ub - lb), ub - lb, (n_particles, n_vars))
    pbest = pos.copy()                                       # 个体最优
    pbest_val = np.array([fitness(p) for p in pos])
    gbest = pbest[np.argmin(pbest_val)].copy()               # 全局最优
    gbest_val = pbest_val.min()
    history = []

    # Step 2: 迭代更新 (速度 + 位置 + 边界裁剪)
    for _ in range(n_iter):
        r1 = np.random.random((n_particles, n_vars))
        r2 = np.random.random((n_particles, n_vars))
        vel = w * vel + c1 * r1 * (pbest - pos) + c2 * r2 * (gbest - pos)
        pos = np.clip(pos + vel, lb, ub)
        # 评估并更新个体/全局最优
        vals = np.array([fitness(p) for p in pos])
        improve = vals < pbest_val
        pbest[improve] = pos[improve]
        pbest_val[improve] = vals[improve]
        if pbest_val.min() < gbest_val:
            gbest_val = pbest_val.min()
            gbest = pbest[np.argmin(pbest_val)].copy()
        history.append(gbest_val)

    return {"x_star": gbest, "obj": gbest_val, "history": history}


# ============================================================
# 6.2 模拟退火 (SA, 自实现)
# ============================================================
def simulated_annealing(fitness, bounds, T0=100, T_end=1e-3,
                        alpha=0.9, max_iter=1000):
    """
    模拟退火 (Simulated Annealing)。

    适用场景: 组合/连续全局寻优, 通过 Metropolis 准则以一定概率
    接受劣解从而跳出局部最优, 对多峰函数尤其有效。

    Args:
        fitness: callable, f(x) -> float (求最小值)
        bounds: (lb, ub) 或 [(lb1,ub1), ...], 变量边界
        T0: float 初始温度
        T_end: float 终止温度
        alpha: float 降温因子 (每轮 T *= alpha)
        max_iter: int 每个温度下的内层迭代次数

    Returns:
        dict with keys: x_star, obj, history
    """
    bound = np.asarray(bounds, dtype=float)
    if bound.ndim == 1:
        b = np.tile(bound, (2, 1)).T
    else:
        b = bound
    n_vars = b.shape[0]
    lb, ub = b[:, 0], b[:, 1]
    rng = np.random.default_rng(42)                          # 局部可复现

    # Step 1: 随机初始化当前解
    x_cur = np.random.uniform(lb, ub, n_vars)
    val_cur = fitness(x_cur)
    x_best, val_best = x_cur.copy(), val_cur
    history = []
    T = T0

    # Step 2: 降温循环 + 邻域扰动 + Metropolis 接受准则
    while T > T_end:
        for _ in range(max_iter):
            step = (ub - lb) * (T / T0) * 0.1                # 扰动幅度随温度减小
            x_new = np.clip(x_cur + rng.normal(0, 1, n_vars) * step, lb, ub)
            val_new = fitness(x_new)
            delta = val_new - val_cur
            if delta < 0 or rng.random() < np.exp(-delta / T):
                x_cur, val_cur = x_new, val_new              # Metropolis 接受
            if val_cur < val_best:
                x_best, val_best = x_cur.copy(), val_cur
        history.append(val_best)
        T *= alpha

    return {"x_star": x_best, "obj": val_best, "history": history}


# ============================================================
# 7. 主流程示例 (Q1 求解, 对应论文 §5.1)
# ============================================================
if __name__ == "__main__":
    # 加载数据 (示例数据, 实际从附件读)
    n = 100
    p = np.random.uniform(50, 200, n)
    c = np.random.uniform(20, 100, n)
    B = 100000

    # 求解
    result = solve_milp_template(p, c, B, x_max=50)
    print(f"Q1 状态: {result['status']}")
    print(f"Q1 最优利润: {result['obj']:.2f} 元")
    print(f"Q1 求解时间: {result['solve_time_s']:.2f} s")

    # Sanity check
    baseline_result = greedy_budget_baseline(p, c, B, x_max=50)
    baseline_profit = baseline_result["obj"]
    checks = sanity_check(result, expected_range=(0, 50), baseline=baseline_profit)
    print(f"Sanity checks: {checks}")
    if abs(baseline_profit) > 1e-12:
        improvement = (result["obj"] - baseline_profit) / abs(baseline_profit) * 100
        print(f"相对贪心 baseline 提升: {improvement:.2f}%")
    else:
        print("相对贪心 baseline 提升: baseline 为 0, 不计算百分比")

    # 保存结果 (供 stage 6 灵敏度复用)
    np.save("results/Q1_x_star.npy", result["x_star"])

    # 可视化
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(range(n), result["x_star"], color='steelblue')
    ax.set_xlabel("产品编号")
    ax.set_ylabel("最优产量 (件)")
    ax.set_title("Q1 最优生产计划")
    plt.tight_layout()
    plt.savefig("figures/Q1_x_star.png", dpi=300)
    print("已保存 figures/Q1_x_star.png")

    # ---- 启发式演示: PSO / SA 求解多峰测试函数 ----
    def multi_peak(x):
        # 多峰测试函数: 全局最小接近原点, 含周期性振荡
        return -np.sin(x[0]) - np.cos(x[1]) + x[0] ** 2 / 50 + x[1] ** 2 / 50

    bnd = (-10, 10)
    pso_res = particle_swarm(multi_peak, bnd)
    sa_res = simulated_annealing(multi_peak, bnd)
    print(f"PSO 最优: x_star={pso_res['x_star']}, obj={pso_res['obj']:.4f}")
    print(f"SA  最优: x_star={sa_res['x_star']}, obj={sa_res['obj']:.4f}")

    # 收敛历史曲线
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(pso_res["history"], label="PSO")
    ax.plot(sa_res["history"], label="SA")
    ax.set_xlabel("迭代次数")
    ax.set_ylabel("目标值 (越小越好)")
    ax.set_title("PSO / SA 收敛历史")
    ax.legend()
    plt.tight_layout()
    plt.savefig("figures/heuristic_convergence.png", dpi=300)
    print("已保存 figures/heuristic_convergence.png")

"""
动力系统类 code starter — 对应论文 §5.x 机理建模 (A 题核心)
适用: 常微分方程 ODE / 偏微分方程 PDE / 差分方程 / 优化阻尼参数

库依赖:
- scipy.integrate.solve_ivp (ODE 数值解)
- numpy (差分方程)

国赛常见用法: 运动学/波动/扩散/传染病/种群/波浪能装置受力模型
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import minimize, differential_evolution
from pathlib import Path

np.random.seed(42)
# 中文字体, 避免论文图中文乱码
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. ODE 系统通用求解器
# ============================================================
def solve_ode_system(rhs, t_span, y0, params=None, t_eval=None, method="RK45"):
    """
    Args:
        rhs: callable(t, y, *params) -> dy/dt 列表
        t_span: (t0, t1)
        y0: 初始状态数组
        params: 传给 rhs 的额外参数
        method: "RK45" / "BDF" (刚性) / "LSODA" (自适应)
    Returns:
        dict with keys: t, y (shape (n_states, n_t)), success, message
    """
    sol = solve_ivp(rhs, t_span, y0, args=params or (), method=method,
                    dense_output=True, t_eval=t_eval, rtol=1e-6, atol=1e-8)
    return {"t": sol.t, "y": sol.y, "success": sol.success, "message": sol.message}


# ============================================================
# 2. 常系数线性系统 (解析解对照)
# ============================================================
def linear_system_matrix(A, y0, t):
    """
    线性系统 dy/dt = A y, 用矩阵指数求解析解, 与数值解互证
    Returns:
        dict with keys: y_analytic (n, len(t)), y_numeric, error
    """
    t = np.asarray(t, dtype=float)
    y0 = np.asarray(y0, dtype=float)
    from scipy.linalg import expm
    y_analytic = np.zeros((len(y0), len(t)))
    for i, ti in enumerate(t):
        y_analytic[:, i] = expm(A * ti) @ y0
    # 数值解对照
    def rhs(tt, y):
        return A @ y
    num = solve_ode_system(rhs, (t[0], t[-1]), y0, t_eval=t)
    y_numeric = num["y"]
    error = np.max(np.abs(y_analytic - y_numeric))
    return {"y_analytic": y_analytic, "y_numeric": y_numeric, "error": error}


# ============================================================
# 3. 参数优化 (如波浪能最优阻尼系数)
# ============================================================
def optimize_params(simulate, param_bounds, objective="max", n_workers=1):
    """
    用差分进化/遗传式全局搜索最优参数 (对应论文"遗传算法求最优阻尼系数")

    Args:
        simulate: callable(param_tuple) -> 目标值 (标量)
        param_bounds: list of (low, high)
        objective: "max" / "min"
    Returns:
        dict with keys: x_opt, fun_opt, success
    """
    def neg(x):
        val = simulate(x)
        return -val if objective == "max" else val

    res = differential_evolution(neg, param_bounds, seed=42,
                                 tol=1e-6, maxiter=300)
    fun_opt = -res.fun if objective == "max" else res.fun
    return {"x_opt": res.x, "fun_opt": fun_opt, "success": res.success}


# ============================================================
# 4. 差分方程 (离散迭代)
# ============================================================
def difference_equation(step_fn, x0, n_steps, params=None):
    """
    Args:
        step_fn: callable(x_prev, *params) -> x_next
        x0: 初始值 (标量或数组)
        n_steps: 迭代步数
    Returns:
        ndarray (n_steps+1, ...) 全部状态
    """
    x = np.zeros((n_steps + 1,) + np.shape(x0))
    x[0] = x0
    for k in range(n_steps):
        x[k + 1] = step_fn(x[k], *(params or ()))
    return x


# ============================================================
# 5. 示例模型: 振荡浮子式波浪能装置 (二阶微分方程组)
# ============================================================
def wave_energy_dynamics(t, y, m1, m2, k1, k2, c1, c2, F0, omega):
    """
    双质量弹簧阻尼系统 (垂荡): y = [z1, v1, z2, v2]
    m1 z1'' + c1 z1' + k1 z1 - c2(z2'-z1') - k2(z2-z1) = F0 sin(w t)
    m2 z2'' + c2(z2'-z1') + k2(z2-z1) = 0
    """
    z1, v1, z2, v2 = y
    F = F0 * np.sin(omega * t)
    a1 = (F - c1 * v1 - k1 * z1 + c2 * (v2 - v1) + k2 * (z2 - z1)) / m1
    a2 = (-c2 * (v2 - v1) - k2 * (z2 - z1)) / m2
    return [v1, a1, v2, a2]


def simulate_wave_energy(params, T=60, F0=1.0, omega=1.0):
    """
    返回平均输出功率 (目标函数, 用于优化阻尼)

    Args:
        params: (m1, m2, k1, k2, c1, c2)
    """
    m1, m2, k1, k2, c1, c2 = params
    y0 = [0.0, 0.0, 0.0, 0.0]
    t_eval = np.linspace(0, T, int(T * 20))
    sol = solve_ode_system(wave_energy_dynamics, (0, T), y0,
                           params=(m1, m2, k1, k2, c1, c2, F0, omega),
                           t_eval=t_eval)
    v1 = sol["y"][1]
    # 阻尼耗散功率 P = c1 * v1^2, 取平均
    P_avg = c1 * np.mean(v1 ** 2)
    return P_avg


# ============================================================
# 6. 可视化
# ============================================================
def plot_states(t, y, state_names, title="系统状态演化"):
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, name in enumerate(state_names):
        ax.plot(t, y[i], label=name, lw=1.5)
    ax.set_xlabel("时间")
    ax.set_ylabel("状态")
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    return fig


# ============================================================
# 主流程示例 (对应论文 §5.x)
# ============================================================
if __name__ == "__main__":
    # 1. 常系数线性系统解析/数值互证
    A = np.array([[-0.5, 0.1], [0.1, -0.3]])
    y0 = np.array([1.0, 0.5])
    t = np.linspace(0, 20, 100)
    lin = linear_system_matrix(A, y0, t)
    print(f"解析解与数值解最大误差: {lin['error']:.2e}")

    # 2. 波浪能装置参数优化
    fixed = {"m1": 5000, "m2": 3000, "k1": 80000, "k2": 30000, "F0": 1e4, "omega": 0.7}
    def sim(x):
        m1, m2, k1, k2, c1, c2 = x
        return simulate_wave_energy([m1, m2, k1, k2, c1, c2],
                                    T=40, F0=fixed["F0"], omega=fixed["omega"])
    # 固定质量与刚度, 只优化阻尼
    def sim_damp(x):
        c1, c2 = x
        return simulate_wave_energy([fixed["m1"], fixed["m2"], fixed["k1"],
                                     fixed["k2"], c1, c2],
                                    T=40, F0=fixed["F0"], omega=fixed["omega"])
    opt = optimize_params(sim_damp, [(100, 20000), (100, 20000)], objective="max")
    print(f"最优阻尼系数: c1={opt['x_opt'][0]:.1f}, c2={opt['x_opt'][1]:.1f}")
    print(f"最大平均输出功率: {opt['fun_opt']:.2f} W")

    # 3. 可视化示例
    sol = solve_ode_system(
        wave_energy_dynamics, (0, 40),
        [0, 0, 0, 0],
        params=(fixed["m1"], fixed["m2"], fixed["k1"], fixed["k2"],
                opt["x_opt"][0], opt["x_opt"][1], fixed["F0"], fixed["omega"]),
        t_eval=np.linspace(0, 40, 400),
    )
    fig = plot_states(sol["t"], sol["y"], ["z1", "v1", "z2", "v2"], "浮子-振子位移速度")
    plt.savefig("figures/dynamical_wave.png", dpi=300)
    print("已保存 figures/dynamical_wave.png")

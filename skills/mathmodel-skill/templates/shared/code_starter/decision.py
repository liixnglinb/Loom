"""
决策类 code starter — 对应论文 §10 决策分析
适用: 博弈论 (纳什均衡) / 马尔可夫决策过程 MDP / 期望效用决策 / 多阶段决策

库依赖:
- nashpy (纳什均衡)
- mdptoolbox (MDP 求解, 可选)
- 自实现 (期望效用 / 决策树)

国赛常见用法: 定价竞争、攻防策略、多阶段投资决策、动态博弈
"""

import numpy as np
from pathlib import Path

np.random.seed(42)
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. 双人有限博弈 — 纯策略纳什均衡
# ============================================================
def pure_nash(A, B):
    """
    Args:
        A: (m, n) 玩家1 收益矩阵
        B: (m, n) 玩家2 收益矩阵
    Returns:
        list of (i, j): 纯策略纳什均衡 (若存在)
    """
    m, n = A.shape
    equilibria = []
    for i in range(m):
        for j in range(n):
            # 玩家1 在列 j 下选行 i 是否最优
            best_row = A[i, j] >= A[:, j].max() - 1e-9
            # 玩家2 在行 i 下选列 j 是否最优
            best_col = B[i, j] >= B[i, :].max() - 1e-9
            if best_row and best_col:
                equilibria.append((i, j))
    return equilibria


def mixed_nash(A, B, tol=1e-6, max_iter=10000):
    """
    用迭代 (fictitious play 简化) 求混合纳什均衡近似
    注: 完整求解可用 nashpy, 这里给出可运行的近似实现
    Returns:
        dict with keys: p (玩家1 混合策略), q (玩家2 混合策略)
    """
    try:
        import nashpy as nash
        game = nash.Game(A, B)
        eqs = list(game.support_enumeration())
        if eqs:
            p, q = eqs[0]
            return {"p": np.asarray(p, dtype=float), "q": np.asarray(q, dtype=float),
                    "method": "nashpy"}
        # 支持枚举为空(通常表示无混合均衡), 返回均匀近似并明确标记, 不返回 None
        m, n = A.shape
        return {"p": np.full(m, 1.0 / m), "q": np.full(n, 1.0 / n),
                "method": "no_equilibrium"}
    except ImportError:
        # 简化: 每个玩家随机策略 (占位, 实际需用支持枚举/线性互补)
        m, n = A.shape
        p = np.full(m, 1.0 / m)
        q = np.full(n, 1.0 / n)
        return {"p": p, "q": q, "method": "uniform_approx"}


# ============================================================
# 2. 期望效用决策 (决策树分析)
# ============================================================
def expected_utility_decision(actions):
    """
    Args:
        actions: list of dict {name, outcomes: [(prob, utility), ...]}
    Returns:
        dict with keys: best_action, best_utility, all_utilities
    """
    results = []
    for act in actions:
        eu = sum(p * u for p, u in act["outcomes"])
        results.append({"name": act["name"], "utility": eu})
    best = max(results, key=lambda r: r["utility"])
    return {"best_action": best["name"], "best_utility": best["utility"],
            "all_utilities": results}


# ============================================================
# 3. 多阶段决策 (动态规划 / 回溯)
# ============================================================
def multistage_decision(stages, state_transitions, value_fn):
    """
    通用多阶段动态规划 (最大化期望/确定收益)

    Args:
        stages: list of stage index
        state_transitions: callable(stage, state, action) -> next_state
        value_fn: callable(stage, state, action) -> (immediate_reward, next_state)
    Returns:
        dict with keys: optimal_path, total_value
    """
    # 简化的倒推: 假设离散状态集合已知
    # 这里实现为接口, 具体状态空间需由调用方定义
    raise NotImplementedError(
        "请按具体题目定义状态/动作/转移; 参考 2024 B 题状态-决策模型")


# ============================================================
# 4. MDP 求解 (值迭代) — 自实现
# ============================================================
def value_iteration(P, R, gamma=0.9, theta=1e-6, max_iter=1000):
    """
    马尔可夫决策过程值迭代

    Args:
        P: (n_states, n_actions, n_states) 转移概率
        R: (n_states, n_actions) 即时奖励
        gamma: 折扣因子
    Returns:
        dict with keys: V (最优值函数), policy, n_iter
    """
    n_s, n_a, _ = P.shape
    V = np.zeros(n_s)
    for k in range(max_iter):
        delta = 0
        V_new = V.copy()
        for s in range(n_s):
            Q = np.zeros(n_a)
            for a in range(n_a):
                Q[a] = R[s, a] + gamma * (P[s, a] @ V)
            V_new[s] = Q.max()
            delta = max(delta, abs(V_new[s] - V[s]))
        V = V_new
        if delta < theta:
            break
    policy = np.argmax([
        [R[s, a] + gamma * (P[s, a] @ V) for a in range(P.shape[1])]
        for s in range(n_s)
    ], axis=1)
    return {"V": V, "policy": policy, "n_iter": k + 1}


# ============================================================
# 5. Stackelberg / 动态博弈 (占位模板)
# ============================================================
def stackelberg_leader(leader_actions, follower_response, objective="max"):
    """
    领导者-跟随者博弈: 领导者选动作使目标最优, 跟随者响应给定

    Args:
        leader_actions: list 领导者可选动作
        follower_response: callable(action) -> follower 的最优响应
        objective: "max" / "min" 领导者的目标方向
    """
    best = None
    best_score = None
    for a in leader_actions:
        resp = follower_response(a)
        score = resp["leader_payoff"]
        if best_score is None or (objective == "max" and score > best_score) \
                or (objective == "min" and score < best_score):
            best_score = score
            best = {"leader_action": a, "follower_response": resp}
    return {"best": best, "best_score": best_score}


# ============================================================
# 主流程示例 (对应论文 §10)
# ============================================================
if __name__ == "__main__":
    # 1. 纯策略纳什均衡 (囚徒困境)
    A = np.array([[3, 0], [5, 1]])   # 玩家1 收益
    B = np.array([[3, 5], [0, 1]])   # 玩家2 收益
    eqs = pure_nash(A, B)
    print(f"纯策略纳什均衡: {eqs}")

    # 2. 期望效用决策 (要不要检测)
    actions = [
        {"name": "检测", "outcomes": [(0.9, 100), (0.1, -50)]},
        {"name": "不检测", "outcomes": [(0.7, 80), (0.3, -20)]},
    ]
    dec = expected_utility_decision(actions)
    print(f"最优决策: {dec['best_action']} (期望收益 {dec['best_utility']:.1f})")

    # 3. MDP 值迭代 (3 状态 2 动作示例)
    P = np.zeros((3, 2, 3))
    P[0, 0] = [0.8, 0.2, 0]; P[0, 1] = [0.3, 0.7, 0]
    P[1, 0] = [0.5, 0.5, 0]; P[1, 1] = [0, 0.9, 0.1]
    P[2, 0] = [0, 0.2, 0.8]; P[2, 1] = [0, 0, 1.0]
    R = np.array([[10, 8], [5, 3], [1, 0]], dtype=float)
    mdp = value_iteration(P, R, gamma=0.9)
    print(f"MDP 最优策略: {mdp['policy']}, 迭代 {mdp['n_iter']} 次")

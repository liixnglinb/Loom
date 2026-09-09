"""
图论类 code starter — 对应论文 §5.x 网络/路径/流量
适用: 最短路 / 最大流 / 最小费用流 / 最小生成树 / 中心性 / 社团检测 / TSP

库依赖:
- networkx (核心图论)
- OR-Tools (TSP/VRP 可选)

国赛常见用法: 交通路网、配送路径、网络流调度
"""

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

np.random.seed(42)
# 中文字体, 避免论文图中文乱码
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. 最短路 (Dijkstra / Floyd)
# ============================================================
def shortest_path(adj, source, target=None, method="dijkstra"):
    """
    Args:
        adj: (n, n) 邻接矩阵, 无连接处填 inf
        source: int 起点
        target: int 终点 (None 则求全部)
        method: "dijkstra" / "floyd"
    Returns:
        dict with keys: dist, path (target 非 None), dist_all (floyd 或 dijkstra 全源)
    """
    G = nx.from_numpy_array(np.asarray(adj), create_using=nx.DiGraph)
    if method == "dijkstra":
        if target is None:
            d = dict(nx.single_source_dijkstra_path_length(G, source))
            return {"dist_all": d}
        path = nx.dijkstra_path(G, source, target)
        dist = nx.dijkstra_path_length(G, source, target)
        return {"dist": dist, "path": path}
    # 全源最短路 (networkx 用全源 Dijkstra, 结果与 Floyd-Warshall 等价)
    dist = dict(nx.all_pairs_dijkstra_path_length(G))
    return {"dist_all": dist}


# ============================================================
# 2. 最大流 / 最小费用流
# ============================================================
def _to_digraph(adj_cap):
    """把容量矩阵转成有向图, 显式设置 capacity 属性 (0 无边)"""
    G = nx.DiGraph()
    n = adj_cap.shape[0]
    for i in range(n):
        G.add_node(i)
        for j in range(n):
            if adj_cap[i, j] > 0:
                G.add_edge(i, j, capacity=float(adj_cap[i, j]))
    return G


def max_flow(adj_cap, source, sink):
    """
    Args:
        adj_cap: (n, n) 容量矩阵
        source: int 源点
        sink: int 汇点
    Returns:
        dict with keys: flow_value, flow_dict
    """
    G = _to_digraph(np.asarray(adj_cap))
    value, flow = nx.maximum_flow(G, source, sink)
    return {"flow_value": value, "flow_dict": flow}


def min_cost_flow(adj_cap, adj_cost, source, sink, demand):
    """最小费用流: 在容量下求 source→sink 流量为 demand 的最小费用方案。

    networkx 的 min_cost_flow 系列把供需写在节点的 ``demand`` 属性上:
    负值表示净流出(源), 正值表示净流入(汇), 其余节点为 0。
    """
    G = _to_digraph(np.asarray(adj_cap))
    for u, v in list(G.edges()):
        G[u][v]["weight"] = float(adj_cost[u, v])
    try:
        # 除 source/sink 外, 其余节点的净供需都为 0
        for node in G.nodes():
            G.nodes[node]["demand"] = 0
        G.nodes[source]["demand"] = float(-demand)   # 源: 净流出
        G.nodes[sink]["demand"] = float(demand)      # 汇: 净流入
        flows = nx.min_cost_flow(G)
        total_cost = sum(
            G[u][v]["weight"] * flows[u][v]
            for u, v in G.edges()
            if flows.get(u, {}).get(v, 0) > 0
        )
        return {"min_cost": total_cost, "flows": flows}
    except nx.NetworkXUnfeasible:
        return {"min_cost": None, "flows": None}


# ============================================================
# 3. 最小生成树 MST
# ============================================================
def mst(adj_weight):
    """
    Args:
        adj_weight: (n, n) 权重矩阵 (无向)
    Returns:
        dict with keys: tree_edges, total_weight
    """
    G = nx.from_numpy_array(np.asarray(adj_weight))
    T = nx.minimum_spanning_tree(G)
    return {"tree_edges": list(T.edges(data=True)), "total_weight": T.size(weight="weight")}


# ============================================================
# 4. 中心性
# ============================================================
def centrality(adj_weight, metrics=("degree", "betweenness", "pagerank")):
    """
    Args:
        metrics: tuple of "degree"/"betweenness"/"closeness"/"pagerank"/"eigenvector"
    Returns:
        dict {metric: {node: value}}
    """
    G = nx.from_numpy_array(np.asarray(adj_weight))
    out = {}
    for m in metrics:
        if m == "degree":
            out[m] = dict(G.degree(weight="weight"))
        elif m == "betweenness":
            out[m] = nx.betweenness_centrality(G, weight="weight")
        elif m == "closeness":
            out[m] = nx.closeness_centrality(G)
        elif m == "pagerank":
            out[m] = nx.pagerank(G, weight="weight")
        elif m == "eigenvector":
            out[m] = nx.eigenvector_centrality(G, weight="weight")
    return out


# ============================================================
# 5. TSP / VRP (OR-Tools 可选)
# ============================================================
def tsp(dist_matrix):
    """
    Args:
        dist_matrix: (n, n) 距离矩阵
    Returns:
        dict with keys: route (list of node), distance
    """
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
        n = dist_matrix.shape[0]
        manager = pywrapcp.RoutingIndexManager(n, 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def dist_callback(from_idx, to_idx):
            return int(round(dist_matrix[manager.IndexToNode(from_idx),
                                        manager.IndexToNode(to_idx)] * 1000))
        transit = routing.RegisterTransitCallback(dist_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit)
        search = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = search
        solution = routing.SolveWithParameters(params)
        if not solution:
            return {"route": None, "distance": None}
        idx = routing.Start(0)
        route = []
        while not routing.IsEnd(idx):
            route.append(manager.IndexToNode(idx))
            idx = solution.Value(routing.NextVar(idx))
        route.append(0)
        return {"route": route, "distance": solution.ObjectiveValue() / 1000.0}
    except ImportError:
        print("⚠ OR-Tools 未安装, 使用 networkx 近似解")
        G = nx.complete_graph(dist_matrix.shape[0])
        for i in G.nodes:
            for j in G.nodes:
                G[i][j]["weight"] = dist_matrix[i, j]
        approx = nx.approximation.traveling_salesman_problem(G, cycle=True)
        d = sum(dist_matrix[approx[i], approx[i + 1]] for i in range(len(approx) - 1))
        return {"route": approx, "distance": d}


# ============================================================
# 6. 可视化
# ============================================================
def plot_graph(adj_weight, path=None, title="网络图", node_labels=None):
    G = nx.from_numpy_array(np.asarray(adj_weight))
    pos = nx.spring_layout(G, seed=42)
    fig, ax = plt.subplots(figsize=(9, 6))
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="steelblue", node_size=400)
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.5)
    if path:
        edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
        nx.draw_networkx_edges(G, pos, edgelist=edges, ax=ax,
                               edge_color="red", width=2.5)
    labels = node_labels or {i: str(i) for i in G.nodes}
    nx.draw_networkx_labels(G, pos, labels, ax=ax)
    ax.set_title(title)
    ax.axis("off")
    plt.tight_layout()
    return fig


# ============================================================
# 主流程示例 (对应论文 §5.x)
# ============================================================
if __name__ == "__main__":
    # 示例: 5 节点有向加权图 (实际从附件读)
    adj = np.array([
        [0, 2, 5, np.inf, np.inf],
        [np.inf, 0, 1, 4, np.inf],
        [np.inf, np.inf, 0, 2, 3],
        [np.inf, np.inf, np.inf, 0, 1],
        [np.inf, np.inf, np.inf, np.inf, 0],
    ])

    # 最短路
    sp = shortest_path(adj, 0, 4)
    print(f"0->4 最短路径: {sp['path']}, 距离: {sp['dist']}")

    # 最大流 (无向示例图需先构造容量矩阵)
    cap = np.array([
        [0, 4, 3, 0, 0],
        [0, 0, 2, 2, 0],
        [0, 0, 0, 3, 2],
        [0, 0, 0, 0, 3],
        [0, 0, 0, 0, 0],
    ])
    mf = max_flow(cap, 0, 4)
    print(f"最大流: {mf['flow_value']}")

    # 中心性
    undirected = np.array([
        [0, 1, 1, 0, 0],
        [1, 0, 1, 1, 0],
        [1, 1, 0, 1, 1],
        [0, 1, 1, 0, 1],
        [0, 0, 1, 1, 0],
    ])
    cen = centrality(undirected)
    print(f"中介中心性: {cen['betweenness']}")

    # 可视化
    fig = plot_graph(undirected, title="示例网络")
    plt.savefig("figures/graph_example.png", dpi=300)
    print("已保存 figures/graph_example.png")

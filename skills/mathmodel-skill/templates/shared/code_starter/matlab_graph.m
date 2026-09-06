%% matlab_graph.m — 图论类求解模板 (C 题常用, 亦可 A/B)
% 对应论文 §5.x 图建模与最短路/最小生成树/最大流
% 调用: matlab -batch "run('matlab_graph.m')"
% 国赛常见: 配送路径最短路、管网最小生成树、通信/供水最大流、物流网络
clear; clc; rng(42);

% 基于脚本自身路径构造输出目录, 保证 -batch 运行与位置无关
scriptDir = fileparts(mfilename('fullpath'));
figDir = fullfile(scriptDir, 'figures');
resDir = fullfile(scriptDir, 'results');
if ~exist(figDir, 'dir'), mkdir(figDir); end
if ~exist(resDir, 'dir'), mkdir(resDir); end

%% 1. 参数定义: 6 节点带权有向网 (节点1为源点, 节点6为汇点)
% 邻接表: [起点, 终点, 权重, (可选)容量]
edges = [1 2 4; 1 3 2; 2 3 1; 2 4 5; 3 4 8; 3 5 10; 4 5 2; 4 6 6; 5 6 4];
cap   = [4; 2; 3; 5; 2; 2; 3; 6; 4];   % 每边容量 (最大流使用)
s_from = edges(:, 1); s_to = edges(:, 2); s_w = edges(:, 3);

%% 2. 模型建立: 用 graph/digraph 建图 (新旧版本兼容)
% Step1 说明: 新版用 digraph + shortestpath/minspantree/maxflow;
%            旧版用 sparse 邻接矩阵 + graphshortestpath/graphminspantree/graphmaxflow
% Step2 优先新接口, 失败则退回稀疏矩阵旧接口
use_new = false;
try
    G = digraph(s_from, s_to, s_w);      % 新建图对象
    use_new = true;
catch
    A = sparse([s_from; s_to], [s_to; s_from], [s_w; s_w], 6, 6); % 无向对称化
    use_new = false;
end

%% 3-1. 最短路: 节点1 到节点6 的最短路径
% 注意: 新版 shortestpath 返回 [P, d] = 最短路径节点序列, 距离
if use_new
    [path_short, d_short] = shortestpath(G, 1, 6);   % 新版 (P在前, 距离在后)
else
    [d_short, path_short] = graphshortestpath(A, 1, 'directed', true, 'method', 'Dijkstra');
end
fprintf('最短路 1→6 距离 = %.0f, 路径: %s\n', d_short, mat2str(path_short));

%% 3-2. 最小生成树 Minimum Spanning Tree (MST): 用无向图
if use_new
    Gund = graph(min(edges(:,1), edges(:,2)), max(edges(:,1), edges(:,2)), s_w);
    T = minspantree(Gund);               % 新版 minspantree
    mst_w = sum(T.Edges.Weight);
else
    [T_sparse, pred] = graphminspantree(A, 'Method', 'Kruskal'); %#ok
    mst_w = sum(nonzeros(T_sparse));
end
fprintf('最小生成树总权重 = %.0f\n', mst_w);

%% 3-3. 最大流 Max Flow: 节点1 → 节点6
if use_new
    % 需带容量的有向图, 重建 capacity 图
    Gc = digraph(s_from, s_to, cap);
    [maxflow_v, ~, ~] = maxflow(Gc, 1, 6);   % 新版 maxflow
else
    Ac = sparse(s_from, s_to, cap, 6, 6);     % 有向容量矩阵
    [maxflow_v, ~] = graphmaxflow(Ac, 1, 6);  %#ok  % 旧版 graphmaxflow
end
fprintf('最大流 1→6 = %.0f\n', maxflow_v);

%% 4. 最小生成树自实现验证 (Kruskal, 集成解较小时备用)
% Step1 说明: 用作 minspantree/graphminspantree 不可用时的替代与交叉验证
% Step2 边按权重升序处理, 用并查集 (Union-Find) 选边直到连通全部节点
[~, ord] = sort(s_w);          % 按权重升序的边下标
parent = 1:6;                  % 并查集父指针, parent(i)=i 表示 i 为根
mst_sum = 0; cnt = 0;
for k = 1:numel(ord)
    ii = ord(k);
    e = edges(ii, :);
    if find_alt(parent, e(1)) ~= find_alt(parent, e(2))   % 两端不在同一集合
        parent = union_alt(parent, e(1), e(2));           % 合并
        mst_sum = mst_sum + e(3); cnt = cnt + 1;
        if cnt == 6 - 1, break; end                       % 已连通 n-1 条边
    end
end
fprintf('Kruskal 自实现 MST 总权重 = %.0f (含 %d 条边)\n', mst_sum, cnt);

%% 5. 结果可视化
% 最短路路径 (粗红), MST 边 (粗蓝) 叠加示意
if use_new
    figure('Color', 'w');
    p = plot(G, 'EdgeLabel', G.Edges.Weight, 'LineWidth', 1.2);
    highlight(p, path_short, 'EdgeColor', 'r', 'LineWidth', 2.5);
    highlight(p, [1 6], 'NodeColor', 'g', 'MarkerSize', 12);
    highlight(p, [2 3 4 5], 'NodeColor', 'k', 'MarkerSize', 9);
    title(sprintf('最短路 1→6 距离=%.0f', d_short)); grid on;
    saveas(gcf, fullfile(figDir, 'matlab_graph_shortest.png'));
    fprintf('已保存 to figures/matlab_graph_shortest.png\n');
end

%% 6. 结果落盘
res_g = table(d_short, string(sprintf('%s', mat2str(path_short))), ...
    mst_w, mst_sum, maxflow_v, ...
    'VariableNames', {'short_dist', 'short_path', 'mst_weight', 'mst_kruskal', 'maxflow'});
writetable(res_g, fullfile(resDir, 'result_matlab_graph.xlsx'));
fprintf('已保存 results/result_matlab_graph.xlsx\n');

%% 子函数: 并查集 Find (路径压缩, 返回根节点)
function r = find_alt(p, u)
    while p(u) ~= u, u = p(u); end
    r = u;
end
%% 子函数: 并查集 Union (按根合并)
function p = union_alt(p, u, v)
    while p(u) ~= u, u = p(u); end
    while p(v) ~= v, v = p(v); end
    if u ~= v, p(max(u, v)) = min(u, v); end
end
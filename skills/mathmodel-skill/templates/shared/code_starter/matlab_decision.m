%% matlab_decision.m — 决策/博弈类求解模板 (双人博弈 / 风险决策)
% 对应论文 §5.x 博弈均衡 · 期望效用决策树 · 动态规划
% 调用: matlab -batch "run('matlab_decision.m')"
% 国赛常见: 收益竞争定价、风险投资决策、有限阶段资源配置、拍卖/讨价还价
clear; clc; rng(42);

% 基于脚本自身路径构造输出目录, 保证 -batch 运行与位置无关
scriptDir = fileparts(mfilename('fullpath'));
figDir = fullfile(scriptDir, 'figures');
resDir = fullfile(scriptDir, 'results');
if ~exist(figDir, 'dir'), mkdir(figDir); end
if ~exist(resDir, 'dir'), mkdir(resDir); end

%% 1. 参数定义: 双人纯策略博弈收益矩阵 (行=玩家A, 列=玩家B, 每元素=[A收益, B收益])
% 经典"囚徒困境"式: 合作/背叛
P_aa = [0 0; 0 0];   % 占位, 实际收益张量见下
pay_A = [ [3 0]; [5 1] ];   % 玩家A收益, 行i=策略A_i, 列j=策略B_j
pay_B = [ [3 5]; [0 1] ];   % 玩家B收益 (与A对称即对称博弈)
nA = size(pay_A, 1); nB = size(pay_B, 2);
stratA = {'合作', '背叛'};  % 行策略名
stratB = {'合作', '背叛'};  % 列策略名

%% 2. 模型建立
% Step1 说明: 纯策略纳什均衡 (Pure-Strategy Nash Equilibrium, PSNE)
%            每个玩家选择给定对方选择下的最优响应 (Best Response) 组合
% Step2 构造最优响应集合
brA = zeros(nA, 1);   % 玩家A对B每个策略的最优行
brB = zeros(nB, 1);   % 玩家B对A每个策略的最优列
for j = 1:nB
    [~, brA(j)] = max(pay_A(:, j));   % 固定B策略j, A选择收益最大行
end
for i = 1:nA
    [~, brB(i)] = max(pay_B(i, :));   % 固定A策略i, B选择收益最大列
end

%% 3. 数值求解: 双循环找最优响应对 = 纯策略纳什均衡
eq_list = [];   % 记录所有均衡 (i, j)
for i = 1:nA
    for j = 1:nB
        is_brA = (brA(j) == i);   % A对B策略j的最优响应为 i
        is_brB = (brB(i) == j);   % B对A策略i的最优响应为 j
        if is_brA && is_brB
            eq_list = [eq_list; i j]; %#ok
        end
    end
end
fprintf('纯策略纳什均衡个数 = %d\n', size(eq_list, 1));
for k = 1:size(eq_list, 1)
    i = eq_list(k, 1); j = eq_list(k, 2);
    fprintf('均衡 %d: A=%s, B=%s, 收益 A=%d B=%d\n', k, ...
        stratA{i}, stratB{j}, pay_A(i, j), pay_B(i, j));
end

%% 4. 期望效用决策 (决策树) 示例: 新产品开发是否投资
% Step1 说明: 决策树含决策节点(投/不投)与机会节点(高销/低销), 按期望效用取最大
% Step2 参数: 投资成本 100, 高销概率 p=0.6 收入 300, 低销 1-p 收入 80; 不投资收益 0
invest_cost = 100;  prob_high = 0.6;  payoff_high = 300;  payoff_low = 80;
EU_invest = prob_high * (payoff_high - invest_cost) + ...
            (1 - prob_high) * (payoff_low - invest_cost);  % 期望净收益
EU_noinvest = 0;
fprintf('投资期望净收益 = %.2f, 不投资期望收益 = %.2f\n', EU_invest, EU_noinvest);
if EU_invest > EU_noinvest
    fprintf('决策建议: 投资 (期望效用更高)\n');
else
    fprintf('决策建议: 不投资\n');
end
% Step3 灵敏度: 高销概率临界值 (使投资与不投资无差异)
p_crit = invest_cost / (payoff_high - payoff_low);   % 求解 EU_invest=0
fprintf('临界高销概率 (取舍无差异) = %.4f\n', p_crit);

%% 5. (可选) 多阶段动态规划: 定期补货成本最小化
% Step1 说明: 阶段=时间点 t, 状态=当前库存 x, 决策=是否/补多少到目标库存 S
%           转移: 下一阶段库存减需求 d, 用贝尔曼方程倒推最小期望总成本
% Step2 假设确定性需求 d=40/期, 补货单价 5, 单次补货固定 20, 库存持有成本 1/单位/期
T_dp = 3;            % 阶段数 (3期)
cap_x = 100;         % 库存上限
d_dp = 40;           % 每期需求
buy_cost = 5;  order_fix = 20;  hold_cost = 1;  S_dp = 80;  % 目标库存
J = zeros(T_dp + 1, cap_x + 1);   % 价值函数表 (成本), 下标对应库存0..cap
J(end, :) = 0;                    % 末段不剩成本
for t = T_dp:-1:1                 % 倒推
    for x = 0:cap_x
        best = inf;
        % 决策选项: 不补货 (x>=d) 或补到 S_dp 使库存达标
        cand_opts = [];
        if x >= d_dp                      % 方案1: 什么都不做, 满足需求
            cost1 = hold_cost * (x - d_dp) + J(t+1, x - d_dp + 1);
            cand_opts = [cand_opts cost1]; %#ok
        end
        if x < S_dp                       % 方案2: 补到 S_dp
            y = S_dp;
            if y >= d_dp
                cost2 = order_fix + buy_cost * (y - x) + ...
                        hold_cost * (y - d_dp) + J(t+1, y - d_dp + 1);
                cand_opts = [cand_opts cost2]; %#ok
            end
        end
        if ~isempty(cand_opts), best = min(cand_opts); end
        J(t, x + 1) = best;
    end
end
fprintf('多阶段DP 3期最小期望总成本 (初始库存0) = %.2f\n', J(1, 1));
fprintf('多阶段DP 3期最小期望总成本 (初始库存80) = %.2f\n', J(1, S_dp + 1));

%% 6. 结果可视化: 博弈收益 与 决策树期望
% 博弈收益热力图
figure('Color', 'w');
imagesc(pay_A); colorbar;
set(gca, 'XTick', 1:nB, 'YTick', 1:nA, ...
         'XTickLabel', stratB, 'YTickLabel', stratA);
xlabel('玩家 B'); ylabel('玩家 A'); title('玩家A 收益矩阵 (含纳什均衡点)');
if ~isempty(eq_list)
    hold on; plot(eq_list(:, 2), eq_list(:, 1), 'ro', 'MarkerSize', 14, 'LineWidth', 2);
end
grid off; axis tight;
saveas(gcf, fullfile(figDir, 'matlab_decision_payoff.png'));
fprintf('已保存 to figures/matlab_decision_payoff.png\n');

%% 结果落盘
eq_str = '';
for k = 1:size(eq_list, 1)
    eq_str = [eq_str sprintf('(%s,%s);', stratA{eq_list(k,1)}, stratB{eq_list(k,2)})]; %#ok
end
if isempty(eq_str), eq_str = 'none'; end
res_d = table(string(eq_str), EU_invest, EU_noinvest, p_crit, J(1, 1), ...
    'VariableNames', {'NE_list', 'EU_invest', 'EU_noinvest', 'p_crit', 'DP_mincost'});
writetable(res_d, fullfile(resDir, 'result_matlab_decision.xlsx'));
fprintf('已保存 results/result_matlab_decision.xlsx\n');
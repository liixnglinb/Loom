%% matlab_simulation.m — 仿真/灵敏度分析模板 (A 题)
% 对应论文 §5.x 蒙特卡罗仿真 · 采样设计 · 系统级联仿真 · 灵敏度分析
% 调用: matlab -batch "run('matlab_simulation.m')"
% 国赛常见: 传染病 SEIR 传播、风险评估蒙特卡罗、排队/库存仿真、参数灵敏度
clear; clc; rng(42);

% 基于脚本自身路径构造输出目录, 保证 -batch 运行与位置无关
scriptDir = fileparts(mfilename('fullpath'));
figDir = fullfile(scriptDir, 'figures');
resDir = fullfile(scriptDir, 'results');
if ~exist(figDir, 'dir'), mkdir(figDir); end
if ~exist(resDir, 'dir'), mkdir(resDir); end

%% 1. 蒙特卡罗模拟: 估计库存系统平均补货成本
% Step1 说明: 需求量 d 服从均值为 100、标准差 20 的正态分布(截断为正), 单件成本 10
%            缺货惩罚 5/件, 订货提前期忽略, 每次补货固定成本 50
mu_d = 100;   sigma_d = 20;  % 需求量均值/标准差
unit_cost = 10;   stockout_penalty = 5;   order_fixed = 50;
S = 120;     % 目标库存 (订到 S)
N = 1e4;     % 仿真次数
total_cost = zeros(N, 1);
% Step2 蒙特卡罗主循环: 对每次重复采样需求量并计算总成本
for i = 1:N
    d = max(0, mu_d + sigma_d * randn);   % 随机需求 (等价 numpy.random.normal)
    if d <= S
        cost_i = order_fixed + unit_cost * (S - d);   % 仅补货固定成本+采购
    else
        cost_i = order_fixed + unit_cost * 0 + stockout_penalty * (d - S);  % 缺货
    end
    total_cost(i) = cost_i;
end
mean_cost = mean(total_cost);    % 期望补货成本
std_cost  = std(total_cost);     % 标准差
fprintf('蒙特卡罗 %d 次: 期望补货成本 = %.2f, 标准差 = %.2f\n', N, mean_cost, std_cost);

%% 2. 拉丁超立方采样 (Latin Hypercube Sampling, LHS)
% Step1 说明: 相较 rand 的独立随机采样, LHS 将每个维度均匀划分为 N 层并各取一点,
%            使样本更均匀覆盖参数空间, 常用于高维灵敏度/不确定性分析
% Step2 优先使用 lhsdesign; 若不可用则用 rand 分层采样替代
d_lhs = 3;   % 采样维度 (如 传染率 恢复率 接触率)
n_lhs = 200; % 样本数
try
    X_lhs = lhsdesign(n_lhs, d_lhs);              % 各列∈[0,1], 分层均匀
    lidx = 'lhsdesign 内置函数';
catch
    X_lhs = (rand(n_lhs, d_lhs) + ...
            repmat((0:n_lhs-1)', 1, d_lhs)) / n_lhs;   % 自实现分层采样
    lidx = '自实现分层采样 (lhsdesign 不可用)';
end
% 将标准均匀样本映射到物理范围 [0,0.3]×[0.1,0.9]×[0.1,0.4]
X_phys = X_lhs .* repmat([0.3 0.8 0.3], n_lhs, 1) + ...
                 repmat([0 0.1 0.1], n_lhs, 1);
fprintf('LHS 采样方式: %s, 样本数 %d, 维度 %d\n', lidx, n_lhs, d_lhs);
fprintf('LHS 各维边缘分布覆盖: min=%.3f max=%.3f\n', ...
    min(X_lhs(:)), max(X_lhs(:)));

%% 3. ODE 系统级联仿真: SEIR 传染病模型
% Step1 模型代入: 易感 S - 暴露 E - 感染 I - 移除 R, 常微分方程组
%   dS/dt = -beta*S*I/N
%   dE/dt =  beta*S*I/N - sigma*E
%   dI/dt =  sigma*E - gamma*I
%   dR/dt =  gamma*I
% Step2 参数定义
Npop = 1e4;  beta0 = 0.5;  sigmaSE = 1/5;  gammaIR = 1/7;  dur = 60;
seirfun = @(t, y) [
    -beta0 * y(1) * y(3) / Npop;
     beta0 * y(1) * y(3) / Npop - sigmaSE * y(2);
     sigmaSE * y(2) - gammaIR * y(3);
     gammaIR * y(3)
];
% Step3 数值求解 (ode45 自适应步长), 初始 5 人感染
x0 = [Npop - 5; 0; 5; 0];
[t_seir, Y] = ode45(seirfun, [0 dur], x0, odeset('RelTol', 1e-6));
peak_I = max(Y(:, 3));
fprintf('SEIR 峰值感染数 = %.0f (时刻 %.1f d), 终期易感 %.0f\n', ...
    peak_I, t_seir(Y(:,3) == peak_I), Y(end,1));

%% 4. 参数灵敏度分析: 传染率 beta 扰动 ±5/10/20%
% Step1 说明: 固定其余参数, 仅对 beta 扰动 r 倍, 观察终期病例数与峰值变化
% Step2 对每个扰动水平求解并记录关键指标
del_list = [-0.2, -0.1, -0.05, 0, 0.05, 0.1, 0.2];  % 相对扰动
final_case = zeros(size(del_list));
peak_case  = zeros(size(del_list));
for k = 1:numel(del_list)
    beta = beta0 * (1 + del_list(k));
    fk = @(t, y) [
        -beta * y(1) * y(3) / Npop;
         beta * y(1) * y(3) / Npop - sigmaSE * y(2);
         sigmaSE * y(2) - gammaIR * y(3);
         gammaIR * y(3)
    ];
    [~, Yk] = ode45(fk, [0 dur], x0, odeset('RelTol', 1e-6));
    final_case(k) = Npop - Yk(end, 1);   % 累计感染
    peak_case(k)  = max(Yk(:, 3));        % 峰值感染数
end

%% 5. 结果可视化
% Step1 SEIR 传播曲线
figure('Color', 'w');
plot(t_seir, Y(:,1), 'b-', t_seir, Y(:,2), 'm-', ...
     t_seir, Y(:,3), 'r-', t_seir, Y(:,4), 'g-', 'LineWidth', 1.5);
xlabel('时间 (d)'); ylabel('人数');
legend('易感 S', '暴露 E', '感染 I', '移除 R');
title('SEIR 传染病传播曲线'); grid on;
saveas(gcf, fullfile(figDir, 'matlab_simulation_seir.png'));

% Step2 灵敏度曲线
figure('Color', 'w');
yyaxis left;
plot(del_list*100, final_case / Npop * 100, 'o-', 'LineWidth', 1.5);
ylabel('终期累计感染率 (%)');
yyaxis right;
plot(del_list*100, peak_case, 's--', 'LineWidth', 1.5);
ylabel('峰值感染数');
xlabel('传染率 β 相对扰动 (%)');
legend('累计感染率', '峰值感染数', 'Location', 'northwest');
title('传染率 β 灵敏度分析'); grid on;
saveas(gcf, fullfile(figDir, 'matlab_simulation_sens.png'));
fprintf('已保存 2 张图到 figures/\n');

%% 6. 结果落盘 (对应论文 result*.xlsx)
sens_tab = table((1+del_list)' * beta0, del_list' * 100, ...
    final_case' / Npop * 100, peak_case', ...
    'VariableNames', {'beta', 'delta_pct', 'final_inf_rate', 'peak_inf'});
writetable(sens_tab, fullfile(resDir, 'result_matlab_simulation.xlsx'));

mc_tab = table(mean_cost, std_cost, N, ...
    'VariableNames', {'mean_cost', 'std_cost', 'n_sim'});
writetable(mc_tab, fullfile(resDir, 'result_matlab_montecarlo.xlsx'));
fprintf('已保存 results/result_matlab_simulation.xlsx\n');
fprintf('已保存 results/result_matlab_montecarlo.xlsx\n');

%% 7. M/M/1 排队系统: 解析公式 vs 离散事件仿真
% Step1 解析: Little 定律, 服务强度 rho = lambda/mu 须 < 1 才稳定
lambda_q = 2.0;  mu_q = 3.0;        % 到达率 / 服务率
rho_q = lambda_q / mu_q;
L_q  = rho_q / (1 - rho_q);         % 平均队长 (系统中的顾客数)
Lq_q = rho_q^2 / (1 - rho_q);       % 平均等待队长 (队列中的顾客数)
W_q  = L_q / lambda_q;              % 平均逗留时间 (等待 + 服务)
Wq_q = Lq_q / lambda_q;             % 平均等待时间 (仅排队)

% Step2 离散事件仿真: 泊松到达间隔 Exp(lambda), 服务时长 Exp(mu), 用 rand 生成
%   (注: 指数分布采样 = -log(rand)/rate)
T_q = 5000;  Nc = round(T_q * lambda_q * 10);   % 顾客样本预算
arr_q = zeros(Nc, 1);  t_q = 0;
for k = 1:Nc
    t_q = t_q - log(rand) / lambda_q;           % 顾客到达时刻
    arr_q(k) = t_q;
end
arr_q = arr_q(arr_q <= T_q);                    % 截断到仿真时长内
Nq = numel(arr_q);
wait_q = zeros(Nq, 1);  busy_q = 0;  cnt_s = 0;
for k = 1:Nq
    ser_q = -log(rand) / mu_q;                  % 一次服务时长
    start_q = max(arr_q(k), busy_q);            % 实际开始服务时刻
    wait_q(k) = start_q - arr_q(k);             % 排队等待时间
    busy_q = start_q + ser_q;                   % 服务台下次空闲时刻
    cnt_s = cnt_s + 1;
end
n_warm = sum(arr_q < 50);                       % 预热阶段 (前 50 时间单位)
sim_wait_q = wait_q(n_warm+1:cnt_s);
sim_avg_wait = mean(sim_wait_q);

fprintf('\n===== M/M/1 排队系统 =====\n');
fprintf('rho=%.4f\n', rho_q);
fprintf('解析: L=%.4f  Lq=%.4f  W=%.4f  Wq=%.4f\n', L_q, Lq_q, W_q, Wq_q);
fprintf('仿真: 平均等待 Wq_sim=%.4f (顾客数 %d)\n', sim_avg_wait, cnt_s - n_warm);

% Step3 等待时间分布图存 figures/
figure('Color', 'w');
histogram(sim_wait_q, 40, 'FaceColor', [0.3 0.6 0.9]);
xlabel('等待时间'); ylabel('频数'); title('M/M/1 排队顾客等待时间分布'); grid on;
saveas(gcf, fullfile(figDir, 'matlab_simulation_mm1_wait.png'));
fprintf('已保存 figures/matlab_simulation_mm1_wait.png\n');

% Step4 结果落盘
mm1_tab = table(lambda_q, mu_q, rho_q, L_q, Lq_q, W_q, Wq_q, sim_avg_wait, ...
    'VariableNames', {'lambda', 'mu', 'rho', 'L', 'Lq', 'W', 'Wq', 'sim_avg_wait'});
writetable(mm1_tab, fullfile(resDir, 'result_matlab_mm1.xlsx'));
fprintf('已保存 results/result_matlab_mm1.xlsx\n');

%% 8. 元胞自动机: Game of Life (二维, conv2 自实现, 含边界)
% 规则: 活细胞邻居为 2 或 3 时存活, 死细胞邻居恰为 3 时新生;
%       用 conv2 卷积核统计 Moore 8 邻域活邻居数, 边界按 0 填充(视为死细胞)。
G_rng = rand(80, 80) < 0.25;            % 随机初始构型, 约 25% 活细胞
K_ca  = [1 1 1; 1 0 1; 1 1 1];          % Moore 邻居卷积核 (不含中心)
steps_ca = 60;
CA_hist = zeros(80, 80, steps_ca + 1);
CA_hist(:, :, 1) = G_rng;
for s = 1:steps_ca
    nb = conv2(G_rng, K_ca, 'same');    % 各细胞活邻居数
    G_rng = (G_rng & (nb == 2)) | (nb == 3);   % 生死演化规则
    CA_hist(:, :, s + 1) = G_rng;
end

figure('Color', 'w');
subplot(1, 2, 1);
imagesc(CA_hist(:, :, end)); colormap(gray); axis image off;
title('Game of Life 末代构型');
subplot(1, 2, 2);
imagesc(squeeze(CA_hist(40, :, :))'); colormap(gray); axis xy;
xlabel('细胞位置'); ylabel('演化步'); title('第 40 行时空演化 (时间剖面)');
saveas(gcf, fullfile(figDir, 'matlab_simulation_ca.png'));
fprintf('已保存 figures/matlab_simulation_ca.png\n');
fprintf('仿真脚本运行完成\n');
%% matlab_ode.m — 机理/微分方程类求解模板 (A 题)
% 对应论文 §5.x 基础机理模型建立与数值求解
% 调用: matlab -batch "run('matlab_ode.m')"
% 国赛常见: 运动学方程、波动方程、扩散方程、传染病模型、波浪能装置
clear; clc; rng(42);

%% 1. 参数定义
m1 = 5000;   % 浮子质量 kg
m2 = 3000;   % 振子质量 kg
k1 = 8e4;    % 主弹簧刚度 N/m
k2 = 3e4;    % 次弹簧刚度 N/m
c1 = 5e3;    % 主阻尼 (待优化)
c2 = 5e3;    % 次阻尼
F0 = 1e4;    % 波浪激励力幅值 N
omega = 0.7; % 激励角频率 rad/s
T = 40;      % 仿真时长 s

%% 2. 机理方程 (二自由度垂荡系统)
% m1 z1'' + c1 z1' + k1 z1 - c2(z2'-z1') - k2(z2-z1) = F0 sin(w t)
% m2 z2'' + c2(z2'-z1') + k2(z2-z1) = 0
odefun = @(t, y) [
    y(2);
    (F0*sin(omega*t) - c1*y(2) - k1*y(1) + c2*(y(4)-y(2)) + k2*(y(3)-y(1)))/m1;
    y(4);
    (-c2*(y(4)-y(2)) - k2*(y(3)-y(1)))/m2
];

y0 = [0; 0; 0; 0];          % 初始 [z1, v1, z2, v2]
tspan = [0 T];
opts = odeset('RelTol', 1e-6, 'AbsTol', 1e-8);

%% 3. 数值求解 (ode45 自适应步长)
[t, y] = ode45(odefun, tspan, y0, opts);
z1 = y(:, 1); v1 = y(:, 2); z2 = y(:, 3); v2 = y(:, 4);

%% 4. 结果: 平均输出功率 P = mean(c1 * v1^2)
P_avg = c1 * mean(v1.^2);
fprintf('平均输出功率: %.2f W\n', P_avg);

%% 5. 结果可视化
figure('Color', 'w');
subplot(2,1,1);
plot(t, z1, 'b-', t, z2, 'r--', 'LineWidth', 1.5);
xlabel('时间 (s)'); ylabel('位移 (m)');
legend('浮子 z1', '振子 z2'); grid on; title('浮子-振子位移');
subplot(2,1,2);
plot(t, v1, 'b-', t, v2, 'r--', 'LineWidth', 1.5);
xlabel('时间 (s)'); ylabel('速度 (m/s)');
legend('浮子 v1', '振子 v2'); grid on; title('浮子-振子速度');
saveas(gcf, 'figures/matlab_ode_result.png');

%% 6. 结果落盘 (对应论文 result*.xlsx)
result_table = table(t, z1, v1, z2, v2, 'VariableNames', ...
    {'time', 'z1', 'v1', 'z2', 'v2'});
writetable(result_table, 'results/result_matlab_ode.xlsx');
fprintf('已保存 results/result_matlab_ode.xlsx\n');

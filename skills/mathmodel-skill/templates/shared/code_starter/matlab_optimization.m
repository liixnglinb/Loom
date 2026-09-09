%% matlab_optimization.m — 优化类求解模板 (A/B 题)
% 对应论文 §5.x 求解算法 (LP / MILP / NLP / 多目标)
% 调用: matlab -batch "run('matlab_optimization.m')"
% 国赛常见: 调度、配比、选址、最优阻尼系数
clear; clc; rng(42);

%% 1. 线性规划 LP (linprog) 示例: 资源分配
% 目标 min c'x, 约束 A*x <= b, Aeq*x = beq, lb <= x <= ub
c = [-3; -2];                 % 求 max 转 min (取负)
A = [1 1; 2 1];               % 约束
b = [8; 10];
lb = [0; 0];
[x_lp, fval_lp] = linprog(c, A, b, [], [], lb);
fprintf('LP 最优解: x = [%.2f, %.2f], 最优值 = %.2f\n', ...
    x_lp(1), x_lp(2), -fval_lp);

%% 2. 整数规划 MILP (intlinprog)
intcon = 1:2;
[x_ip, fval_ip] = intlinprog(c, intcon, A, b, [], [], lb);
fprintf('MILP 最优解: x = [%.0f, %.0f], 最优值 = %.2f\n', ...
    x_ip(1), x_ip(2), -fval_ip);

%% 3. 非线性规划 NLP (fmincon): 最优阻尼系数
% 目标: 最大化平均输出功率 (浮子/振子二自由度系统)
m1 = 5000; m2 = 3000; k1 = 8e4; k2 = 3e4;
F0 = 1e4; omega = 0.7; T = 40;

avg_power = @(cvec) -mean_power(cvec, m1, m2, k1, k2, F0, omega, T);
lb_d = [1e2, 1e2]; ub_d = [2e4, 2e4];
x0 = [5e3, 5e3];
opts = optimoptions('fmincon', 'Display', 'off');
[c_opt, fval] = fmincon(avg_power, x0, [], [], [], [], lb_d, ub_d, [], opts);
fprintf('NLP 最优阻尼: c1 = %.1f, c2 = %.1f, 最大平均功率 = %.2f W\n', ...
    c_opt(1), c_opt(2), -fval);

%% 4. 多目标 (加权法) 示例
% 双目标: 最小化成本 与 最大化产能 (加权合并)
% 此处用 gamultiobj 可得到 Pareto; 加权法 min w1*f1 + w2*f2
w = [0.5, 0.5];
obj_w = @(x) w(1) * x(1)^2 + w(2) * (10 - x(2))^2;
x_w = fmincon(obj_w, [3; 3], [], [], [], [], [0; 0], [10; 10], [], opts);
fprintf('加权多目标: x = [%.2f, %.2f]\n', x_w(1), x_w(2));

%% 结果落盘
result = table(x_lp(1), x_lp(2), -fval_lp, c_opt(1), c_opt(2), -fval, ...
    'VariableNames', {'x1_lp', 'x2_lp', 'obj_lp', 'c1_opt', 'c2_opt', 'max_power'});
writetable(result, 'results/result_matlab_opt.xlsx');
fprintf('已保存 results/result_matlab_opt.xlsx\n');

%% 5. 粒子群优化 PSO (自实现) — 多峰测试函数
% 目标: min f(x) = -sin(x1) - cos(x2) + x1^2/50 + x2^2/50
f_multi = @(x) -sin(x(1)) - cos(x(2)) + x(1)^2/50 + x(2)^2/50;
lb2 = -10; ub2 = 10;
n_p = 30; n_iter = 200; w = 0.7; c1 = 1.5; c2 = 1.5;
pos_p = rand(n_p, 2) * (ub2 - lb2) + lb2;              % 粒子位置
vel_p = rand(n_p, 2) * (ub2 - lb2) - (ub2 - lb2)/2;    % 粒子速度
pbest_p = pos_p;
pbest_val = zeros(n_p, 1);
for i = 1:n_p
    pbest_val(i) = f_multi(pos_p(i, :));
end
[gbest_val, gidx] = min(pbest_val);
gbest_p = pos_p(gidx, :);                              % 全局最优
hist_p = zeros(n_iter, 1);
for it = 1:n_iter
    r1 = rand(n_p, 2); r2 = rand(n_p, 2);
    vel_p = w*vel_p + c1*r1.*(pbest_p - pos_p) + c2*r2.*(gbest_p - pos_p);
    pos_p = pos_p + vel_p;
    pos_p = min(max(pos_p, lb2), ub2);                 % 边界约束
    for i = 1:n_p
        v = f_multi(pos_p(i, :));
        if v < pbest_val(i)
            pbest_val(i) = v; pbest_p(i, :) = pos_p(i, :);
        end
    end
    [gbest_val, gidx] = min(pbest_val);
    gbest_p = pbest_p(gidx, :);
    hist_p(it) = gbest_val;
end
fprintf('PSO 最优: x = [%.4f, %.4f], obj = %.4f\n', ...
    gbest_p(1), gbest_p(2), gbest_val);

%% 6. 模拟退火 SA (自实现) — 同多峰测试函数
T0 = 100; T_end = 1e-3; alpha = 0.9; max_iter = 1000;
x_cur = lb2 + rand(1, 2) * (ub2 - lb2);
val_cur = f_multi(x_cur);
x_best = x_cur; val_best = val_cur;
T = T0; hist_s = [];
while T > T_end
    for k = 1:max_iter
        step = (ub2 - lb2) * (T / T0) * 0.1;           % 扰动幅度随温度衰减
        x_new = x_cur + randn(1, 2) * step;
        x_new = min(max(x_new, lb2), ub2);             % 边界约束
        val_new = f_multi(x_new);
        delta = val_new - val_cur;
        if delta < 0 || rand() < exp(-delta / T)       % Metropolis 接受准则
            x_cur = x_new; val_cur = val_new;
        end
        if val_cur < val_best
            x_best = x_cur; val_best = val_cur;
        end
    end
    hist_s = [hist_s, val_best];
    T = T * alpha;
end
fprintf('SA  最优: x = [%.4f, %.4f], obj = %.4f\n', ...
    x_best(1), x_best(2), val_best);

%% 7. 收敛曲线 + 结果落盘
figure('Color', 'w');
plot(1:length(hist_p), hist_p, 'r-o', 'LineWidth', 1.2); hold on;
plot(1:length(hist_s), hist_s, 'b-s', 'LineWidth', 1.2);
xlabel('迭代次数'); ylabel('目标值 (越小越好)');
title('PSO / SA 收敛历史'); legend('PSO', 'SA');
grid on; saveas(gcf, 'figures/heuristic_convergence_matlab.png');
fprintf('已保存 figures/heuristic_convergence_matlab.png\n');

res_heu = table(gbest_p(1), gbest_p(2), gbest_val, ...
    x_best(1), x_best(2), val_best, ...
    'VariableNames', {'pso_x1', 'pso_x2', 'pso_obj', 'sa_x1', 'sa_x2', 'sa_obj'});
writetable(res_heu, 'results/result_heuristic_pso_sa.xlsx');
fprintf('已保存 results/result_heuristic_pso_sa.xlsx\n');

%% 子函数: 二自由度系统平均功率 (供 fmincon 目标)
function P = mean_power(cvec, m1, m2, k1, k2, F0, omega, T)
    c1 = cvec(1); c2 = cvec(2);
    odefun = @(t, y) [
        y(2);
        (F0*sin(omega*t) - c1*y(2) - k1*y(1) + c2*(y(4)-y(2)) + k2*(y(3)-y(1)))/m1;
        y(4);
        (-c2*(y(4)-y(2)) - k2*(y(3)-y(1)))/m2
    ];
    [~, y] = ode45(odefun, [0 T], [0;0;0;0], odeset('RelTol', 1e-5));
    P = c1 * mean(y(:, 2).^2);
end

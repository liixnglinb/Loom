%% matlab_prediction.m — 预测/回归类求解模板 (C/E 题)
% 对应论文 §5.x 预测模型建立与精度分析
% 调用: matlab -batch "run('matlab_prediction.m')"
% 国赛常见: 销量/产量预测、人口预测、能耗预测、趋势外推、灰色预测
% 本模板用模拟数据即可运行，实际赛题替换为附件数据并核对量纲
clear; clc; rng(42);
if ~exist('figures', 'dir'); mkdir('figures'); end   % 保证图表目录存在
if ~exist('results', 'dir'); mkdir('results'); end   % 保证结果目录存在

%% 1. 参数定义与模拟数据生成
% 模拟序列 = "确定性趋势(线性+周期) + 随机噪声"，对应国赛常见数据形态
N = 60;                              % 样本长度
t = (1:N)';                          % 时间自变量 1~60
y_obs = 2.0 + 0.4*t + 3*sin(t/5) + 2*randn(N,1);   % 观测值(含噪声)

% 灰色预测 GM(1,1) 输入: 取单调递增的近等比序列，否则先做平滑预处理
x0 = 100 + 2*(1:20)' + 0.5*randn(20,1);            % 原始序列，长度 20

%% 2. 模型建立
% 2.1 一元线性回归（Linear Regression）：y = beta0 + beta1*t + eps
%     用最小二乘法(Ordinary Least Squares, OLS)估计参数，对应论文"回归模型表达式"
% 2.2 多项式拟合（Polynomial Fitting）：y = p1 t^2 + p2 t + p3，polyfit 求系数
% 2.3 指数平滑（Exponential Smoothing）：s_t = alpha*y_t + (1-alpha)*s_{t-1}
%     用于平滑噪声、短期外推；缺失值用 fillmissing 线性插值填补
% 2.4 灰色预测（Grey Model, GM(1,1)）：对累加序列建立一阶单变量灰色微分方程，
%     发展系数 a 与灰作用量 u 用最小二乘估计，再累减还原预测值

%% 3. 数值求解
% 3.1 线性回归求解 (fitlm 输出参数估计+t检验+拟合优度; 无该工具箱时回退到 polyfit 的等价 OLS)
if exist('fitlm', 'file')
    mdl  = fitlm(t, y_obs);
    b    = mdl.Coefficients.Estimate;    % [截距; 斜率]
    y_lr = predict(mdl, t);              % 线性回归拟合值
else
    pf_lr = polyfit(t, y_obs, 1);        % 与最小二乘等价的回退(斜率, 截距)
    b     = [pf_lr(2), pf_lr(1)];        % 统一为 [截距; 斜率]
    y_lr  = polyval(pf_lr, t);
end

% 3.2 多项式拟合求解 (polyfit/polyval)
p     = polyfit(t, y_obs, 2);
y_poly = polyval(p, t);

% 3.3 指数平滑求解 (自实现一次指数平滑)
alpha = 0.4;
s     = zeros(size(y_obs));
s(1)  = y_obs(1);
for k = 2:N                          % Step1: 递推更新平滑值
    s(k) = alpha*y_obs(k) + (1-alpha)*s(k-1);
end
% Step2: fillmissing 线性插值填补缺失示例 (人为挖空 3 个点)
y_missing         = y_obs;
y_missing([10 20 30]) = NaN;
y_filled          = fillmissing(y_missing, 'linear');

% 3.4 灰色预测 GM(1,1) 求解 (自实现，见文件尾部子函数)
[gm_pred, gm_a, gm_u] = grey_gm11(x0);

%% 4. 结果: 各预测模型关键数值输出
r2   = @(y, yp) 1 - sum((y-yp).^2)/sum((y-mean(y)).^2);   % 决定系数 R²
mae  = @(y, yp) mean(abs(y-yp));                          % 平均绝对误差
fprintf('==== 预测模型精度对比 ====\n');
fprintf('线性回归   : R²=%.4f, MAE=%.4f, 斜率=%.4f, 截距=%.4f\n', ...
    r2(y_obs, y_lr), mae(y_obs, y_lr), b(2), b(1));
fprintf('多项式(2次): R²=%.4f, MAE=%.4f\n', r2(y_obs, y_poly), mae(y_obs, y_poly));
fprintf('指数平滑   : MAE=%.4f\n', mae(y_obs, s));
fprintf('灰色GM(1,1): 发展系数 a=%.4f, 灰作用量 u=%.4f\n', gm_a, gm_u);
fprintf('GM(1,1) 后3期还原值: %.2f, %.2f, %.2f\n', gm_pred(end-2:end));

%% 5. 可视化: 各模型拟合/预测对比
figure('Color', 'w');
subplot(2,2,1);
plot(t, y_obs, 'o', t, y_lr, 'r-', 'LineWidth', 1.5);
xlabel('时间 t'); ylabel('观测 y'); legend('观测', '线性回归'); grid on; title('线性回归');
subplot(2,2,2);
plot(t, y_obs, 'o', t, y_poly, 'g-', 'LineWidth', 1.5);
xlabel('时间 t'); ylabel('观测 y'); legend('观测', '多项式'); grid on; title('多项式拟合');
subplot(2,2,3);
plot(t, y_obs, 'o', t, s, 'm-', 'LineWidth', 1.5);
xlabel('时间 t'); ylabel('观测 y'); legend('观测', '指数平滑'); grid on; title('指数平滑');
subplot(2,2,4);
plot(1:numel(x0), x0, 'o', 1:numel(x0), gm_pred, 'r-', 'LineWidth', 1.5);
xlabel('期数 k'); ylabel('序列值'); legend('原始', 'GM(1,1)拟合'); grid on;
title('灰色预测 GM(1,1)');
saveas(gcf, 'figures/matlab_prediction.png');

%% 6. 结果落盘 (对应论文 result*.xlsx)
res_pred = table(r2(y_obs, y_lr), r2(y_obs, y_poly), mae(y_obs, s), gm_a, gm_u, ...
    'VariableNames', {'r2_lr', 'r2_poly', 'mae_ema', 'gm_a', 'gm_u'});
writetable(res_pred, 'results/result_matlab_prediction.xlsx');
writetable(table(t, y_obs, y_lr, y_poly, s), 'results/result_matlab_prediction_data.xlsx');
fprintf('已保存 figures/matlab_prediction.png 与 results/result_matlab_prediction*.xlsx\n');

%% 7. SARIMA 季节ARIMA 演示 (国赛高频, 带季节周期)
% 思路: 带明显季节周期的时序用季节 ARIMA(SARIMA) 刻画, 兼顾趋势+周期+噪声。
% 说明: 若已安装 Econometrics Toolbox 可用 arima/estimate/forecast 直接建模;
%       否则用自实现的"季节外推"(季节型平移+趋势)作等价演示。
y_s = 20 + 0.05*(1:24)' + 3*sin((1:24)'*2*pi/6) + 0.5*randn(24, 1);  % 短季节序列(周期6)
hs = 6;                                   % 预测步数(一个季节周期)
if exist('arima', 'file') > 0
    % Econometrics Toolbox: SARIMA (p,d,q)(P,D,Q)_s, 此处取 (1,1,0)(1,0,0)_6
    model_s = arima('Constant', NaN, 'ARLags', 1, 'D', 1, 'Seasonality', 6, ...
                    'SARLags', 1, 'Distribution', 'Gaussian');
    est_s = estimate(model_s, y_s, 'Display', 'off');
    yf = forecast(est_s, hs, 'Y0', y_s);
    fprintf('SARIMA (Econometrics Toolbox): 未来 %d 期预测: %s\n', hs, sprintf('%.2f  ', yf));
else
    % 未检测到 Econometrics Toolbox: 需该工具箱才可用 arima/sarima,
    % 此处用自实现"季节外推"代替: 上一周期同期值 + 全程平均增量(趋势)。
    period = 6;
    trend_step = mean(diff(y_s));               % 平均每步增量(趋势)
    yf = zeros(hs, 1);
    for h = 1:hs
        idx = numel(y_s) - period + h;          % 上一周期对应下标
        yf(h) = y_s(idx) + period * trend_step; % 季节型 + 趋势外推
    end
    fprintf('(未检测到 Econometrics Toolbox; 需该工具箱才可用 arima/sarima)\n');
    fprintf('自实现季节外推替代: 未来 %d 期预测: %s\n', hs, sprintf('%.2f  ', yf));
end

% SARIMA 预测可视化
figure('Color', 'w');
plot(1:numel(y_s), y_s, 'o'); hold on;
plot(numel(y_s)+(1:hs), yf, 'r-+', 'LineWidth', 1.5);
xlabel('时间'); ylabel('y'); legend('观测', 'SARIMA/季节外推预测'); grid on;
title('SARIMA 季节预测');
saveas(gcf, 'figures/matlab_prediction_sarima.png');
writetable(table((1:hs)', yf, 'VariableNames', {'step', 'sarima_forecast'}), ...
    'results/result_matlab_prediction_sarima.xlsx');
fprintf('已保存 figures/matlab_prediction_sarima.png 与 results/result_matlab_prediction_sarima.xlsx\n');

%% 子函数: 灰色预测 GM(1,1) 自实现
% Grey Model, GM(1,1) 一阶单变量灰色模型
% Step1: 一次累加生成(Accumulating Generation Operator, AGO) x1
% Step2: 构造紧邻均值背景值 z1(k)
% Step3: 构造矩阵 B/Y，最小二乘估计参数 (a 发展系数, u 灰作用量)
% Step4: 白化方程求解并累减(IAOG)还原得到原始量预测
function [pred, a, u] = grey_gm11(x0)
    x0 = x0(:);                                  % 保证为列向量
    n  = numel(x0);
    x1 = cumsum(x0);                             % Step1: 一次累加生成
    z1 = 0.5*(x1(2:end) + x1(1:end-1));          % Step2: 紧邻均值背景值
    B  = [-z1, ones(n-1, 1)];                    % Step3: 数据矩阵 B
    Y  = x0(2:end);                              % Step3: 数据向量 Y
    P  = (B'*B) \ (B'*Y);                        % Step3: 最小二乘 [a; u]
    a  = P(1); u = P(2);
    k  = (0:n-1)';                               % Step4: 白化方程解
    if abs(a) < 1e-12                            % a→0 时用解析极限, 避免除以 0
        x1_hat = x0(1) + u * k;
    else
        x1_hat = (x0(1) - u/a) * exp(-a*k) + u/a;
    end
    x1_hat(1) = x0(1);
    pred = [x1_hat(1); diff(x1_hat)];            % Step4: 累减(IAOG)还原
end
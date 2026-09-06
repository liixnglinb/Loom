%% matlab_stats.m — 统计检验/分布分析模板 (C/E 题)
% 对应论文 §5.x 数据预处理、显著性检验与分布拟合
% 调用: matlab -batch "run('matlab_stats.m')"
% 国赛常见: 描述统计、相关分析、均值检验、方差分析(Analysis of Variance, ANOVA)、卡方检验、正态性检验
% 本模板用模拟数据即可运行，实际赛题替换为附件数据
clear; clc; rng(42);
% 前置检查: 本脚本依赖 ttest/anova1/chi2gof/fitdist/kstest 等统计函数,
% 需安装 Statistics and Machine Learning Toolbox (缺失时 base 无法复现, 直接给出明确报错)
if ~exist('ttest', 'file')
    error('缺少 Statistics and Machine Learning Toolbox, 无法运行 ttest/anova1/chi2gof/fitdist 等统计检验, 请安装后重试');
end
if ~exist('figures', 'dir'); mkdir('figures'); end   % 保证图表目录存在
if ~exist('results', 'dir'); mkdir('results'); end   % 保证结果目录存在

%% 1. 描述性统计 (集中趋势/离散程度/分布形状)
% 生成两组模拟样本: g2 均值略高于 g1，用于后续检验
g1 = 5 + 1.2*randn(50, 1);
g2 = 6 + 1.5*randn(50, 1);
m1 = mean(g1);  s1 = std(g1);  sk1 = skewness(g1);  k1 = kurtosis(g1);
m2 = mean(g2);  s2 = std(g2);  sk2 = skewness(g2);  k2 = kurtosis(g2);
fprintf('组1: 均值=%.3f 标准差=%.3f 偏度=%.3f 峰度=%.3f\n', m1, s1, sk1, k1);
fprintf('组2: 均值=%.3f 标准差=%.3f 偏度=%.3f 峰度=%.3f\n', m2, s2, sk2, k2);

%% 2. 相关分析 (Pearson 相关系数)
xr = randn(80, 1);                    % 自变量
yr = 0.8*xr + 0.6*randn(80, 1);       % 线性相关因变量
[R, Pval] = corrcoef(xr, yr);         % R 相关系数阵, Pval 显著性 p 值
fprintf('Pearson 相关系数 r=%.4f, p=%.4f\n', R(1, 2), Pval(1, 2));

%% 3. 均值检验 (t 检验)
% 3.1 ttest 单样本: H0: 总体均值 = 6
[h1, p1] = ttest(g1, 6);
if h1
    fprintf('单样本t检验(均值=6): 拒绝H0, p=%.4f\n', p1);
else
    fprintf('单样本t检验(均值=6): 不拒绝H0, p=%.4f\n', p1);
end
% 3.2 ttest2 双独立样本: H0: 两组均值相等
[h2, p2] = ttest2(g1, g2);
if h2
    fprintf('双样本t检验: 两组均值显著不同, p=%.4f\n', p2);
else
    fprintf('双样本t检验: 两组均值无显著差异, p=%.4f\n', p2);
end

%% 4. 方差分析 (ANOVA)
% 4.1 anova1 单因素方差分析: 3 组数据均值是否有显著差异
xval  = [g1; g1+3; randn(50,1)+4];    % 人为制造组间差异的 3 组样本
gA    = [repmat({'g1'}, 50, 1); repmat({'g2'}, 50, 1); repmat({'g3'}, 50, 1)];
[p_anova, tbl] = anova1(xval, gA, 'off');
fprintf('单因素ANOVA: p=%.4f, F=%.3f\n', p_anova, tbl{2, 5});
% 4.2 anovan 双因素方差分析: 因素A(3水平) x 因素B(2水平), 含交互项
nrep = 8;
totA = 3*2*nrep;
xA = zeros(totA, 1); fA = zeros(totA, 1); fB = zeros(totA, 1);
idx = 0;
for ia = 1:3                            % Step1: 遍历因素 A 的 3 个水平
    for ib = 1:2                        % Step2: 遍历因素 B 的 2 个水平
        block = 2*ia + ib + randn(nrep, 1);   % 模拟主效应+噪声
        xA(idx+1:idx+nrep) = block;
        fA(idx+1:idx+nrep) = ia;
        fB(idx+1:idx+nrep) = ib;
        idx = idx + nrep;
    end
end
[p_anovan] = anovan(xA, {fA, fB}, 'model', 'interaction', ...
    'varnames', {'A', 'B'});
fprintf('双因素ANOVA: A p=%.3f, B p=%.3f, 交互A*B p=%.3f\n', p_anovan);

%% 5. 卡方拟合优度检验 (chi2gof)
% H0: 样本服从正态分布 (用于检验频率分布是否与理论分布一致)
xchi = randn(200, 1);                  % 标准正态样本
[hchi, pchi] = chi2gof(xchi, 'CDF', @(z) normcdf(z, mean(xchi), std(xchi)));
fprintf('卡方拟合优度检验(正态): h=%d, p=%.4f\n', hchi, pchi);

%% 6. 分布拟合 (fitdist + kstest)
% 用极大似然估计(Maximum Likelihood Estimation, MLE)拟合正态分布，
% 再用 Kolmogorov-Smirnov(K-S) 检验验证拟合优度
pd  = fitdist(g1, 'Normal');           % 正态分布拟合, 得到 mu/sigma
[hk, pk] = kstest(g1, 'CDF', pd);      % K-S 检验: H0 样本来自 pd
fprintf('正态拟合: mu=%.3f, sigma=%.3f, K-S p=%.4f, h=%d\n', ...
    pd.mu, pd.sigma, pk, hk);

%% 7. 可视化: 分布与检验结果
figure('Color', 'w');
subplot(2,2,1);
histogram(g1, 12, 'FaceColor', 'b', 'FaceAlpha', 0.5); hold on;
histogram(g2, 12, 'FaceColor', 'r', 'FaceAlpha', 0.5);
xlabel('取值'); ylabel('频数'); legend('组1', '组2'); grid on; title('两组分布对比');
subplot(2,2,2);
plot(xr, yr, 'o'); hold on;
pfit = polyfit(xr, yr, 1);
plot(xr, polyval(pfit, xr), 'r-', 'LineWidth', 1.5);
xlabel('x'); ylabel('y'); legend('散点', '回归线'); grid on; title('相关与回归');
subplot(2,2,3);
boxplot(xval, gA);
xlabel('分组'); ylabel('取值'); grid on; title('单因素 ANOVA 组间箱线图');
subplot(2,2,4);
histogram(xchi, 20, 'Normalization', 'pdf', 'FaceColor', 'g'); hold on;
zz = linspace(min(xchi), max(xchi), 200);
plot(zz, normpdf(zz, mean(xchi), std(xchi)), 'r-', 'LineWidth', 1.5);
xlabel('取值'); ylabel('概率密度'); legend('经验分布', '理论正态'); grid on;
title('正态性检验(K-S/卡方)');
saveas(gcf, 'figures/matlab_stats.png');

%% 8. 结果落盘 (对应论文 result*.xlsx)
res_stats = table(m1, s1, sk1, k1, R(1,2), Pval(1,2), p1, p2, p_anova, pchi, pk, ...
    'VariableNames', {'mean1', 'std1', 'skew1', 'kurt1', 'r_pearson', ...
    'r_pval', 't1_p', 't2_p', 'anova_p', 'chi2_p', 'kstest_p'});
writetable(res_stats, 'results/result_matlab_stats.xlsx');
fprintf('已保存 figures/matlab_stats.png 与 results/result_matlab_stats.xlsx\n');
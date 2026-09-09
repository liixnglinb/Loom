%% matlab_evaluation.m — 评价/决策类求解模板 (D/F 题)
% 对应论文 §5.x 综合评价模型 (AHP / 熵权法 / TOPSIS / 模糊综合评价)
% 调用: matlab -batch "run('matlab_evaluation.m')"
% 国赛常见: 综合评价、方案优选、能力评估、城市/企业/项目竞争力评价
% 数据源: 5 个对象 × 4 个指标 模拟数据 (实际从附件读入)
clear; clc; rng(42);

%% 1. 参数定义 (模拟数据: 5 个对象, 4 个正向指标)
% 指标全部为正向 (值越大越好); 若有负向指标, 改 indicator_sign = 0 且标准化时取倒数差
X = [85 90 78 92;      % 对象 1
     72 88 85 80;      % 对象 2
     95 75 90 85;      % 对象 3
     80 82 88 78;      % 对象 4
     70 95 82 88];     % 对象 5
indicator_name = {'技术水平', '成本效益', '服务质量', '环境影响'};
indicator_sign = ones(1, 4);     % 1=正向, 0=负向
n = size(X, 1);                  % 对象数
m = size(X, 2);                  % 指标数
fprintf('读入评价矩阵: %d 个对象, %d 个指标\n\n', n, m);

% AHP 判断矩阵 (4×4, 行/指标为主题, 对角线为 1, A(i,j)*A(j,i)=1)
A = [1    2    3    4;
     1/2  1    2    3;
     1/3  1/2  1    2;
     1/4  1/3  1/2  1];

%% 2. AHP 层次分析法（Analytic Hierarchy Process, AHP）— 主观权重
% 思路: 将复杂问题分解为层次结构, 凭专家两两比较构造判断矩阵, 最后可归结为
% 计算判断矩阵的最大特征根对应的特征向量并归一化得到权重 (此处用几何平均近似)。
% Step1 几何平均法求权重
geo_mean = prod(A, 2) .^ (1 / m);   % 各指标行向量的几何平均
w_ahp = geo_mean / sum(geo_mean);   % 归一化得权重

% Step2 求最大特征根 lambda_max
Aw = A * w_ahp;
lambda_max = mean(Aw ./ w_ahp);

% Step3 一致性检验: CI 与随机一致性指标 RI 之比 CR, 要求 CR < 0.1
CI = (lambda_max - m) / (m - 1);
RI_table = [0 0 0.58 0.90 1.12 1.24 1.32 1.41 1.45 1.49 1.51 1.48 1.56 1.57 1.59];
RI = RI_table(m);
CR = CI / RI;
fprintf('AHP: lambda_max=%.4f, CI=%.4f, CR=%.4f %s\n', ...
    lambda_max, CI, CR, ternary(CR < 0.1, '一致性通过', '一致性较差, 需调整判断矩阵'));
fprintf('AHP 权重: %s\n\n', sprintf('%.4f  ', w_ahp));

%% 3. 熵权法 — 客观权重
% 思路: 指标取值差异越大信息熵越小, 所含信息越多, 权重越高 (信息熵, information
% entropy)。先对原始数据进行标准化, 再求信息熵与差异系数, 最终归一化得权重。
% Step1 数据标准化 (min-max, 依据指标正负向)
Xmin = min(X); Xmax = max(X);
Xstd = zeros(n, m);
for j = 1:m
    if indicator_sign(j) == 1
        Xstd(:, j) = (X(:, j) - Xmin(j)) / (Xmax(j) - Xmin(j));
    else
        Xstd(:, j) = (Xmax(j) - X(:, j)) / (Xmax(j) - Xmin(j));
    end
end

% Step2 计算第 j 指标下第 i 对象占该指标的比重 p_ij
P = Xstd ./ (sum(Xstd) + eps);

% Step3 计算信息熵 e_j 与差异系数 d_j
k = 1 / log(max(n, 2));                 % 常数系数 (n=1 时熵权无意义, 兜底避免除零)
P_log = P; P_log(P == 0) = 1;         % 0 取 log 无意义, 用 1 替代使该项贡献为 0
e_j = -k * sum(P .* log(P_log), 1);   % 信息熵
d_j = 1 - e_j;                        % 差异系数 (信息效用值)
w_ent = d_j / sum(d_j);               % 归一化得熵权
fprintf('熵权法信息熵: %s\n', sprintf('%.4f  ', e_j));
fprintf('熵权法权重  : %s\n\n', sprintf('%.4f  ', w_ent));

%% 4. TOPSIS（Technique for Order Preference by Similarity to Ideal Solution）
% 思路: 找出方案集内的正理想解与负理想解, 计算各对象与二者的欧氏距离, 用相对
% 接近度排序 (贴近度越大越优)。下面采用 AHP 与熵权的主观/客观组合权重。
alpha = 0.5;                          % 组合比例, 1=全主观(AHP), 0=全客观(熵权)
w_comb = alpha * w_ahp(:)' + (1 - alpha) * w_ent(:)';  % 统一转为 1×m 行向量
w_comb = w_comb / sum(w_comb);

% Step1 向量归一化并按权重加权
Xvec = X ./ sqrt(sum(X .^ 2, 1) + eps);   % 归一化
V = Xvec .* w_comb;                       % 加权决策矩阵

% Step2 确定正负理想解 (正向取每列最大, 负向取每列最小)
V_pos = zeros(1, m); V_neg = zeros(1, m);
for j = 1:m
    if indicator_sign(j) == 1
        V_pos(j) = max(V(:, j));  V_neg(j) = min(V(:, j));
    else
        V_pos(j) = min(V(:, j));  V_neg(j) = max(V(:, j));
    end
end

% Step3 计算各对象到正负理想解的欧氏距离
D_pos = sqrt(sum((V - V_pos) .^ 2, 2));
D_neg = sqrt(sum((V - V_neg) .^ 2, 2));

% Step4 相对接近度 C_i 并降序排名
C = D_neg ./ (D_pos + D_neg + eps);
[~, idx_rank] = sort(C, 'descend');
fprintf('组合权重: %s\n', sprintf('%.4f  ', w_comb));
fprintf('TOPSIS 相对接近度: %s\n', sprintf('%.4f  ', C));
fprintf('TOPSIS 排序(对象): %s\n\n', sprintf('Obj%d ', idx_rank));

%% 5. 模糊综合评价（Fuzzy Comprehensive Evaluation, FCE，可选）
% 思路: 用模糊隶属关系矩阵 R 刻画各指标对各等级的支持度, 经权重矩阵加权得综合
% 隶属度向量 B, 再对等级分值加权得综合得分。配 AHP/熵权权重即可。
grades = [1 0.8 0.6 0.4 0.2];        % 5 个评价等级 (优 良 中 差 劣) 分值
thr = [0.8 0.6 0.4 0.2 0];           % 等级判定阈值 (基于标准化值)
R = zeros(m, numel(grades));
for j = 1:m
    for g = 1:numel(grades)
        R(j, g) = sum(Xstd(:, j) >= thr(g)) / n;   % 达到该等级阈值对象占比
    end
end
B = w_ent * R;                       % M(·,+) 算子加权合成
B_norm = B / sum(B);                 % 归一化隶属度向量
fce_score = dot(B_norm, grades);
fprintf('模糊综合隶属度向量(优→劣): %s\n', sprintf('%.3f  ', B_norm));
fprintf('模糊综合评价得分: %.4f\n\n', fce_score);

%% 6. 结果: 汇总三种权重与 TOPSIS 排名
fprintf('===== 结果汇总 =====\n');
fprintf('指标: %s\n', sprintf('%s  ', indicator_name{:}));
fprintf('AHP 权重      : %s\n', sprintf('%.4f  ', w_ahp));
fprintf('熵权          : %s\n', sprintf('%.4f  ', w_ent));
fprintf('组合权重      : %s\n', sprintf('%.4f  ', w_comb));
fprintf('最优对象为第 %d 个对象 (对应论文最优方案结论)\n', idx_rank(1));

%% 7. 结果可视化
if ~exist('figures', 'dir'), mkdir('figures'); end
figure('Color', 'w', 'Position', [100 100 900 400]);
subplot(1, 2, 1);                       % 权重对比柱状图
bar([w_ahp(:), w_ent(:), w_comb(:)], 'grouped');
set(gca, 'XTickLabel', indicator_name, 'XTickLabelRotation', 20);
legend('AHP', '熵权', '组合', 'Location', 'northwest');
xlabel('评价指标'); ylabel('权重'); title('主客观权重对比'); grid on;
subplot(1, 2, 2);                       % TOPSIS 接近度排序条形图
[Cs, ord] = sort(C, 'descend');
barh(ord, Cs, 'FaceColor', [0.2 0.6 0.9]);
set(gca, 'YTick', 1:n, 'YTickLabel', cellfun(@(s) ['对象' num2str(s)], num2cell(1:n), 'UniformOutput', false), 'YDir', 'reverse');
xlabel('相对接近度'); ylabel('评价对象'); title('TOPSIS 综合得分'); grid on;
saveas(gcf, 'figures/matlab_evaluation_result.png');
fprintf('已保存 figures/matlab_evaluation_result.png\n');

%% 8. 结果落盘 (对应论文 result*.xlsx)
if ~exist('results', 'dir'), mkdir('results'); end
% 对象评价表 (每行一个对象): 各指标原始值 + TOPSIS 综合得分
result_table = table([1:n]', X(:, 1), X(:, 2), X(:, 3), X(:, 4), C(:), ...
    'VariableNames', {'object_id', indicator_name{:}, 'topsis_score'});
writetable(result_table, 'results/result_matlab_evaluation.xlsx');
% 权重表 (每行一个方法): AHP / 熵权 / 组合
weight_table = table(w_ahp(:)', w_ent(:)', w_comb(:)', ...
    'VariableNames', {'w_ahp', 'w_entropy', 'w_combined'});
writetable(weight_table, 'results/result_matlab_evaluation_weights.xlsx');
fprintf('已保存 results/result_matlab_evaluation*.xlsx\n');
fprintf('综合评价脚本运行完成 (可改用 AHP-熵权-TOPSIS 组合应用于实际题目)\n');

%% 9. 灰色关联分析 (Grey Relational Analysis, GRA，可选)
% 思路: 通过比较序列与最优参考序列在几何形状上的接近程度衡量关联度, 适于样本
% 少、指标无量纲差异大、数据规律弱的小样本综合评价。核心是关联系数与关联度。
% Step1 构造比较序列 X_gra (对象×指标) 与参考序列 (各指标正向最优取值)
X_gra = [0.90 0.75 0.62 0.40 0.58;   % 对象 1
         0.80 0.70 0.78 0.55 0.72;   % 对象 2
         0.60 0.88 0.90 0.70 0.65;   % 对象 3
         0.50 0.60 0.72 0.85 0.80;   % 对象 4
         0.70 0.82 0.66 0.60 0.68];  % 对象 5
ref_gra = max(X_gra);                % 参考序列: 每列取最优 (正向取最大)
rho_g = 0.5;                         % 分辨系数, 通常 0.5

% Step2 初值化: 每列除以该列第一个值, 消除量纲
X0     = X_gra ./ X_gra(1, :);
X0_ref = ref_gra ./ X_gra(1, :);

% Step3 差序列与两级最小差 / 两级最大差
delta_g = abs(X0 - X0_ref);
min_d = min(delta_g(:));
max_d = max(delta_g(:));

% Step4 关联系数矩阵, 再按指标取均值得关联度
ksi_g   = (min_d + rho_g * max_d) ./ (delta_g + rho_g * max_d);
gra_deg = mean(ksi_g, 2);            % 各对象关联度
[gra_sort, gra_ord] = sort(gra_deg, 'descend');
fprintf('\n灰色关联度: %s\n', sprintf('%.4f  ', gra_deg));
fprintf('灰色关联排序(对象): %s\n', sprintf('Obj%d ', gra_ord));

% Step5 关联度条形图存 figures/
figure('Color', 'w', 'Position', [100 100 700 400]);
bar(gra_deg, 'FaceColor', [0.8 0.3 0.3]);
set(gca, 'XTick', 1:size(X_gra, 1), 'XTickLabel', ...
    cellfun(@(s) ['对象' num2str(s)], num2cell(1:size(X_gra, 1)), 'UniformOutput', false));
ylabel('灰色关联度'); title('灰色关联分析 -- 各对象关联度'); grid on;
saveas(gcf, 'figures/matlab_evaluation_gra.png');
fprintf('已保存 figures/matlab_evaluation_gra.png\n');

% Step6 结果落盘
if ~exist('results', 'dir'), mkdir('results'); end
gra_tab = table((1:size(X_gra, 1))', gra_deg, ...
    'VariableNames', {'object_id', 'gra_degree'});
writetable(gra_tab, 'results/result_matlab_evaluation_gra.xlsx');
fprintf('已保存 results/result_matlab_evaluation_gra.xlsx\n');

%% 子函数: 三元条件 (仿 C 三元, 保持代码简洁)
function out = ternary(cond, a, b)
    if cond, out = a; else, out = b; end
end
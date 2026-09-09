%% matlab_classification.m — 分类/聚类类求解模板 (C 题数据挖掘)
% 对应论文 §5.x 聚类与判别/分类模型
% 调用: matlab -batch "run('matlab_classification.m')"
% 国赛常见: 样本分类、客户分群、类别识别、降维可视化
% 依赖: 优先使用统计与机器学习工具箱; 无工具箱则自实现 K-means
clear; clc; rng(42);
have_stats = exist('fitcdiscr', 'file') > 0;  % 是否安装统计工具箱（用函数存在性检测更可靠）

%% 1. 参数定义 (模拟二维两类数据, 实际从附件读入)
% 两类样本, 二维特征, 各 50 个
n_grp = 50;
X = [randn(n_grp, 2) + 2; randn(n_grp, 2) - 1];   % 类1中心(+2,+2), 类2中心(-1,-1)
y_true = [ones(n_grp, 1); 2 * ones(n_grp, 1)];     % 真实类别 1/2
N = size(X, 1);
fprintf('读入样本: %d 个点, %d 维特征, 已知标签用于验证\n\n', N, size(X, 2));

%% 2. K-means 聚类 (无标签学习 -> 肘部法确定类数)
% 思路: 把 N 个样本划到 k 个簇使簇内平方和 (SSE, sum of squared errors) 最小。
% 肘部法逐 k 计算 SSE, 找拐点作为最佳类数; 轮廓系数衡量簇内紧、簇间松。
% 注: 无状态工具箱时用自实现 K-means (Step1~Step5)。

% Step1 计算 k=1..6 的簇内平方和 SSE (肘部法)
kmax = 6;
SSE = zeros(kmax, 1);
centroids_all = {};
label_all = {};
for k = 1:kmax
    if have_stats
        [lab, cen] = kmeans(X, k, 'Replicates', 10, 'MaxIter', 300);
    else   % 自实现: 随机初值 + 迭代到收敛 (简单起见固定初值)
        [lab, cen] = my_kmeans(X, k);
    end
    SSE(k) = sum(sum((X - cen(lab, :)) .^ 2, 2));
    centroids_all{k} = cen; label_all{k} = lab;
end
% Step2 依据肘部图人工判定最佳类数 (此处两簇中心分离, 选 k=2)
k_opt = 2;
lab_k = label_all{k_opt};
fprintf('肘部法 SSE(k=1..%d): %s\n', kmax, sprintf('%.2f  ', SSE'));
fprintf('选取最佳类数 k=%d (论文需结合肘部图拐点论证)\n\n', k_opt);

% Step3 轮廓系数评价聚类质量 (若工具箱可用)
if have_stats
    s = silhouette(X, lab_k);
    avg_s = mean(s);
    fprintf('聚类轮廓系数 (coefficient): 均值 = %.4f %s\n', avg_s, s_mean_msg(avg_s));
else
    avg_s = NaN;
    fprintf('未安装统计工具箱, 跳过轮廓系数 (silhouette) 计算 (Silhouette coefficient)\n');
end

%% 3. 判别分析 (监督分类, 需统计工具箱)
% 思路: 依据已知类别样本拟合判别函数 (线性判别式 Linear Discriminant),
% 对新样本判别归属类别。此处用前 70% 训练、后 30% 测试验证准确率。
if have_stats
    % Step1 划分训练/测试
    rng(42);
    idx = randperm(N);  tr = idx(1:round(0.7 * N));  te = idx(round(0.7 * N) + 1:end);
    % Step2 线性判别分析 fitcdiscr 并预测
    mdl = fitcdiscr(X(tr, :), y_true(tr));
    y_pred = predict(mdl, X(te, :));
    % Step3 准确率与混淆矩阵
    acc = mean(y_pred == y_true(te));
    Cmat = confusionmat(y_true(te), y_pred);
    fprintf('判别分析 (linear discriminant analysis, LDA):\n');
    fprintf('  测试集准确率 = %.2f%%, 混淆矩阵如下:\n', 100 * acc);
    disp(Cmat);
else
    acc = NaN;
    disp('未安装统计工具箱, 无法使用 fitcdiscr (判别分析), 跳过. 可安装工具箱或仅用 K-means 输出.');
end

%% 4. 主成分分析 PCA（Principal Component Analysis，可选, 供降维可视化）
% 思路: 通过正交变换将相关指标转换为互不相关的主成分, 用前两个主成分投影实现
% 高维数据的可视化与降维。无工具箱时用特征值分解 svd 自实现即可。
if have_stats
    [coeff, ~, latent, ~, explained] = pca(X);
else
    % 自实现 PCA: 中心化 -> 协方差 -> 特征值分解
    Xc = X - mean(X, 1);
    Cxx = Xc' * Xc / (N - 1);
    [coeff, latent] = eig(Cxx);
    [latent, ord] = sort(diag(latent), 'descend');
    coeff = coeff(:, ord);
    explained = 100 * latent / sum(latent);
end
fprintf('PCA 前两主成分方差贡献率: %.2f%% + %.2f%% = %.2f%%\n', ...
    explained(1), explained(2), explained(1) + explained(2));

%% 5. 结果可视化
if ~exist('figures', 'dir'), mkdir('figures'); end
figure('Color', 'w', 'Position', [100 100 1100 400]);

subplot(1, 3, 1);                       % 原始数据散点 (含真实标签)
plot(X(y_true == 1, 1), X(y_true == 1, 2), 'b.', 'MarkerSize', 12); hold on;
plot(X(y_true == 2, 1), X(y_true == 2, 2), 'r.', 'MarkerSize', 12);
xlabel('特征 1'); ylabel('特征 2'); title('原始数据 (真实标签)'); grid on; legend('类1', '类2');

subplot(1, 3, 2);                       % K-means 聚类结果
plot(X(lab_k == 1, 1), X(lab_k == 1, 2), 'b.', 'MarkerSize', 12); hold on;
plot(X(lab_k == 2, 1), X(lab_k == 2, 2), 'r.', 'MarkerSize', 12);
plot(centroids_all{k_opt}(:, 1), centroids_all{k_opt}(:, 2), ...
    'ks', 'MarkerSize', 12, 'MarkerFaceColor', 'y', 'LineWidth', 1.5);
xlabel('特征 1'); ylabel('特征 2'); title('K-means 聚类 (k=2)'); grid on; legend('簇1', '簇2', '质心');

subplot(1, 3, 3);                       % 肘部法曲线
plot(1:kmax, SSE, '-o', 'LineWidth', 1.5, 'MarkerFaceColor', 'r');
xlabel('聚类数 k'); ylabel('簇内平方和 SSE'); title('肘部法选 k'); grid on;

saveas(gcf, 'figures/matlab_classification_result.png');
fprintf('已保存 figures/matlab_classification_result.png\n');

%% 6. 结果落盘 (对应论文 result*.xlsx)
if ~exist('results', 'dir'), mkdir('results'); end
result_table = table([1:N]', X(:, 1), X(:, 2), y_true, lab_k, ...
    'VariableNames', {'sample_id', 'feat1', 'feat2', 'true_label', 'kmeans_label'});
writetable(result_table, 'results/result_matlab_classification.xlsx');
% 汇总指标
metric = table(k_opt, avg_s, acc, explained(1), explained(2), ...
    'VariableNames', {'k_opt', 'silhouette_mean', 'lda_test_acc', 'pc1_var', 'pc2_var'});
writetable(metric, 'results/metrics_matlab_classification.xlsx');
fprintf('已保存 results/result_matlab_classification.xlsx 与 metrics_matlab_classification.xlsx\n');

%% 7. 层次聚类 (Agglomerative Hierarchical, 国赛高频)
% 思路: 每个样本自成一簇, 按相近程度逐级合并生成树形谱系(dendrogram)。
% 有统计工具箱用 linkage/dendrogram; 无则用自实现单连接(single linkage)层次合并。
if have_stats
    % Step1 成对距离 + 凝聚层次聚类 (平均距离法 average linkage)
    D_dist = pdist(X);
    Z_link = linkage(D_dist, 'average');     % 层次合并树
    lab_h = cluster(Z_link, 'MaxClust', 2);  % 切成 2 簇
    % Step2 树状图 (谱系图)
    figure('Color', 'w');
    dendrogram(Z_link, 0, 'ColorThreshold', 'default');
    title('层次聚类树状图 Dendrogram'); xlabel('样本'); ylabel('距离');
    saveas(gcf, 'figures/matlab_classification_dendrogram.png');
else
    lab_h = my_single_linkage(X, 2);
    fprintf('未安装统计工具箱, 用自实现单连接层次聚类替代 linkage/dendrogram\n');
end
fprintf('层次聚类分到的簇: %s\n', sprintf('%d  ', lab_h'));

% 层次聚类结果散点着色 (用 plot 而非 gscatter, 免依赖统计工具箱)
figure('Color', 'w', 'Position', [100 100 520 400]);
plot(X(lab_h == 1, 1), X(lab_h == 1, 2), 'b.', 'MarkerSize', 12); hold on;
plot(X(lab_h == 2, 1), X(lab_h == 2, 2), 'r.', 'MarkerSize', 12);
xlabel('特征 1'); ylabel('特征 2'); title('层次聚类结果 (2 簇)'); grid on; legend('簇1', '簇2');
saveas(gcf, 'figures/matlab_classification_hierarchical.png');
% 落盘层次聚类标签
writetable(table(y_true, lab_h, 'VariableNames', {'true_label', 'hier_label'}), ...
    'results/result_matlab_classification_hier.xlsx');
fprintf('已保存 figures/matlab_classification_dendrogram.png 与 matlab_classification_hierarchical.png\n');
fprintf('分类/聚类脚本运行完成 (可替换 Y_true 用于监督验证或无标签聚类)\n');

%% 子函数: 自实现 K-means (无统计工具箱时调用)
function [label, centroid] = my_kmeans(X, k)
    [N, d] = size(X);
    % Step1 随机选 k 个初始质心
    rng(42);
    init_idx = randperm(N, k);
    centroid = X(init_idx, :);
    label = zeros(N, 1);
    max_iter = 300;
    for it = 1:max_iter
        % Step2 计算到各质心的距离并就近分配
        old_label = label;
        D = pdist2_mine(X, centroid);
        [~, label] = min(D, [], 2);
        % Step3 更新质心为簇内均值
        for j = 1:k
            centroid(j, :) = mean(X(label == j, :), 1);
        end
        % Step4 收敛判断 (标签不再变化或质心不变)
        if it > 1 && isequal(old_label, label)
            break;
        end
    end
end

%% 子函数: 自实现欧氏距离矩阵 D(i,j) = ||X(i,:) - C(j,:)||
function D = pdist2_mine(X, C)
    N = size(X, 1); k = size(C, 1);
    D = zeros(N, k);
    for j = 1:k
        D(:, j) = sum((X - C(j, :)) .^ 2, 2);   % 平方距离即可, 开根不改变最近性
    end
end

%% 子函数: 自实现单连接(single linkage)凝聚层次聚类, 返回 k 个簇标签
% Step1: 每个样本自成一簇; Step2: 反复合并簇间最近样本距离(单连接)最小者;
% Step3: 直到簇数减到 k。每次合并簇数减 1, 故只需合并 n-k 次。
function label = my_single_linkage(X, k)
    n = size(X, 1);
    clusters = cell(n, 1);
    for i = 1:n, clusters{i} = i; end     % Step1 每点一簇
    n_clu = n;
    while n_clu > k                        % Step2/3 反复合并
        best_d = Inf; best_i = 0; best_j = 0;
        for i = 1:n_clu
            for j = i + 1:n_clu
                dij = distances_between(X, clusters{i}, clusters{j});
                if dij < best_d, best_d = dij; best_i = i; best_j = j; end
            end
        end
        clusters{best_i} = [clusters{best_i}, clusters{best_j}];
        clusters(best_j) = [];
        n_clu = n_clu - 1;
    end
    label = zeros(n, 1);
    for c = 1:numel(clusters)
        label(clusters{c}) = c;
    end
end

%% 子函数: 两簇间单连接距离 = 最近的一对样本间欧氏距离
function d = distances_between(X, ca, cb)
    d = Inf;
    for i = ca
        for j = cb
            dij = sqrt(sum((X(i, :) - X(j, :)) .^ 2));
            if dij < d, d = dij; end
        end
    end
end

%% 子函数: 轮廓系数均值的中文定性描述
function msg = s_mean_msg(sv)
    if sv >= 0.7,      msg = '(聚类结构强)';
    elseif sv >= 0.5,  msg = '(聚类结构合理)';
    elseif sv >= 0.25, msg = '(聚类结构较弱)';
    else,              msg = '(聚类结构差, 应重选 k)';
    end
end
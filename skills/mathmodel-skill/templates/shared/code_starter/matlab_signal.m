%% matlab_signal.m — 信号处理/时频分析类求解模板 (C/D 题)
% 对应论文 §5.x 数据预处理与时频特征提取 (去噪、频谱、周期判定)
% 调用: matlab -batch "run('matlab_signal.m')"
% 国赛常见: 周期性监测数据、振动/声学信号、气象水文时序、波形特征提取
clear; clc; rng(42);

%% 1. 参数定义与含噪周期信号构造
% 目标: 用正弦+噪声模拟一段含噪周期信号, 验证 FFT 与小波去噪的效果
fs = 1000;              % 采样频率 (Sampling Frequency) Hz
T_dur = 10;             % 信号时长 s
t = (0:1/fs:T_dur-1/fs)';       % 时间轴
f1 = 5;                 % 主频率分量1 Hz
f2 = 50;                % 主频率分量2 Hz
x_clean = sin(2*pi*f1*t) + 0.5*sin(2*pi*f2*t);   % 干净周期信号
noise = 0.3*randn(length(t), 1);                  % 高斯白噪声
x = x_clean + noise;    % 含噪信号
fprintf('已构造含噪周期信号, 采样率=%d Hz, 时长=%.0f s, 点数=%d\n', ...
    fs, T_dur, length(t));

%% 2. 傅里叶变换 (Fast Fourier Transform, FFT) 频谱分析
% 说明: FFT 将时域信号变换到频域, 用 fftshift 把零频移到中心便于观察,
%       通过频谱峰值索引可反推主频率与主周期, 这是国赛周期判定的常用手段。
N = length(x);                            % 点数
X = fft(x);                               % 双边傅里叶变换
X_shift = fftshift(X);                    % 零频居中
f_axis = (-N/2 : N/2-1)*(fs/N);           % 频轴 (单位 Hz)
mag = abs(X_shift)/N;                     % 幅值谱 (归一化)

% 只考察正频率段, 找主频率
pos_f = f_axis(N/2+1 : end);              % 正频率轴
pos_mag = mag(N/2+1 : end);
[max_mag, idx_pos] = max(pos_mag);        % 找幅度最大处
f_dom = pos_f(idx_pos);                   % 主频率 Hz
T_dom = 1/f_dom;                          % 主周期 s
fprintf('FFT 检测主频率 = %.3f Hz, 对应主周期 = %.3f s\n', f_dom, T_dom);

%% 3. 时序周期性判定 (FFT 找主周期 + 二次谐波确认)
% 说明: 仅最高峰可能受噪声干扰, 故同时确认分量 f1 附近的能量, 提高周期判据鲁棒性。
% Step1: 选取幅度谱前若干最大峰值
[~, sort_idx] = sort(pos_mag, 'descend');
top_k = 3;                                % 考察前 top_k 个峰值
peak_freqs = pos_f(sort_idx(1:top_k));
peak_mags = pos_mag(sort_idx(1:top_k));
fprintf('FFT 前%d个峰值频率: %s Hz\n', top_k, mat2str(peak_freqs, 3));

% Step2: 输出明确周期结论
period_flag = '该序列呈现明显周期性';
if f_dom > 0.5 && max_mag > 0.3
    fprintf('周期性判定: %s, 主周期 T = %.3f s\n', period_flag, T_dom);
else
    fprintf('周期性较弱, 建议结合时序图与自相关进一步判定\n');
end

%% 4. 小波分析去噪 (wdenoise, 不可用则用 wthresh 阈值)
% 说明: 小波变换把信号分解到多尺度, 对高尺度(高频噪声)系数做阈值收缩后再重构,
%       可在保留真实突变的同时抑制白噪声, 优于单一平滑滤波。无误时自动回退到阈值去噪。
sigLen = length(x);
try
    % Step1: 使用 wdenoise 对小波包进行软阈值去噪 (需 Wavelet Toolbox)
    x_den = wdenoise(x, 5, 'Wavelet', 'sym4');   % 5 层分解, sym4 小波
    method_used = 'wdenoise (sym4, 5层)';
catch
    % Step2: 若 wdenoise 不可用, 手动小波分解 + 软阈值收缩重构
    [c, l] = wavedec(x, 5, 'sym4');              % 5 层离散小波分解
    thr = wthrmngr('dw1ddenoLVL', 'sqtwolog', c, l);   % 通用阈值
    c_thr = wthresh(c, 's', thr);                % 软阈值收缩
    x_den = waverec(c_thr, l, 'sym4');           % 重构
    method_used = 'wthresh 软阈值 (fallback)';
end
% 用信噪比 (Signal-to-Noise Ratio, SNR) 与均方根误差验证去噪效果
snr_before = snr(x_clean, x - x_clean);
snr_after  = snr(x_clean, x_den - x_clean);
rmse_before = sqrt(mean((x - x_clean).^2));
rmse_after  = sqrt(mean((x_den - x_clean).^2));
fprintf('去噪方法: %s\n', method_used);
fprintf('去噪前 SNR=%.2f dB, RMSE=%.4f; 去噪后 SNR=%.2f dB, RMSE=%.4f\n', ...
    snr_before, rmse_before, snr_after, rmse_after);

%% 5. 低通/移动平均滤波去噪 (与上面不同: 保留趋势、抑制毛刺)
% 说明: 移动平均是零设计成本的时域平滑, 适合毛刺噪声; 此处自实现窗长 W 的滑动平均。
%       与第4节小波去噪互为对照, 展示"变换域去噪 vs 时域平滑"两种范式。
W = 11;                             % 窗口长度 (奇数)
kernel = ones(W, 1)/W;
x_smooth = filter(kernel, 1, x);    % 因果滑动平均 (matlab 自实现滤波)
rmse_smooth = sqrt(mean((x_smooth - x_clean).^2));
fprintf('移动平均(窗长=%d) 去噪 RMSE=%.4f\n', W, rmse_smooth);

%% 5. 结果可视化
% 图1: 时域 (原信号 / 小波去噪) 对比
figure('Color', 'w');
subplot(2,2,1);
plot(t, x, 'b-', 'LineWidth', 0.8); hold on;
plot(t, x_den, 'r-', 'LineWidth', 1.2);
xlabel('时间 (s)'); ylabel('幅值'); 
legend('含噪信号', '小波去噪'); grid on;
title('时域: 含噪信号与小波去噪', 'FontSize', 10);
xlim([0 2]);

% 图2: 频谱 (用于周期判定)
subplot(2,2,2);
plot(pos_f, pos_mag, 'k-', 'LineWidth', 0.8); hold on;
stem(peak_freqs, peak_mags, 'r', 'LineWidth', 1.2);
xlabel('频率 (Hz)'); ylabel('幅值');
legend('幅值谱', '峰值'); grid on;
title(sprintf('频谱分析与主频率 f=%.2f Hz', f_dom), 'FontSize', 10);
xlim([0 100]);

% 图3: 周期性可视化 (主周期分段的波形堆叠)
subplot(2,2,3);
T_show = round(T_dom*fs);                    % 主周期对应的采样点数
n_seg = floor(max(t)/T_dom);                 % 可完整切出的周期段数
hold on;
for k = 1:min(n_seg, 6)
    seg = x_den((k-1)*T_show+1 : k*T_show);
    plot((0:T_show-1)/fs, seg, 'LineWidth', 0.9);
end
xlabel('周期内时间 (s)'); ylabel('幅值'); grid on;
title(sprintf('周期性验证: 主周期 T=%.3f s', T_dom), 'FontSize', 10);

% 图4: 三类信号的去噪误差对比 (RMSE)
subplot(2,2,4);
bar([rmse_before, rmse_after, rmse_smooth]);
set(gca, 'XTickLabel', {'滤波前', '小波去噪', '滑动平均'});
ylabel('RMSE'); grid on;
title('去噪效果对比 (RMSE 越低越好)', 'FontSize', 10);
saveas(gcf, 'figures/matlab_signal_result.png');
fprintf('已保存 figures/matlab_signal_result.png\n');

%% 6. 结果落盘 (波形与频谱特征, 对应论文 result*.xlsx)
sig_table = table(t, x, x_den, x_smooth, 'VariableNames', ...
    {'time', 'x_noisy', 'x_wden', 'x_smooth'});
writetable(sig_table, 'results/result_matlab_signal.xlsx');
feat_table = table(f_dom, T_dom, max_mag, snr_before, snr_after, rmse_before, rmse_after, ...
    'VariableNames', {'main_freq_Hz', 'main_period_s', 'fft_mag', ...
    'snr_before_dB', 'snr_after_dB', 'rmse_before', 'rmse_after'});
writetable(feat_table, 'results/result_matlab_signal_feat.xlsx');
fprintf('已保存 results/result_matlab_signal.xlsx 与 result_matlab_signal_feat.xlsx\n');
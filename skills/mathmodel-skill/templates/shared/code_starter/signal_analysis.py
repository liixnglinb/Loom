"""
信号处理 / 时频分析类 code starter — 对应论文 §9 信号处理
适用: 傅里叶变换 FFT / 小波分析 / 压缩感知重构 / 频谱分析

库依赖:
- numpy.fft, scipy.fft
- pywt (小波)
- sklearn.linear_model.OrthogonalMatchingPursuit (OMP 压缩感知)

国赛常见用法: 超分辨定位、频谱特征提取、时序周期识别、信号去噪
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

np.random.seed(42)
# 中文字体, 避免论文图中文乱码
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. FFT 频谱分析
# ============================================================
def fft_spectrum(x, fs=1.0):
    """
    Args:
        x: 一维信号
        fs: 采样频率 (Hz)
    Returns:
        dict with keys: freqs, amplitude, phase, top_freqs (前5)
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    fft_vals = np.fft.fft(x)
    freqs = np.fft.fftfreq(n, 1.0 / fs)
    # 只保留正频率
    half = n // 2
    freqs = freqs[:half]
    amplitude = np.abs(fft_vals[:half]) / n
    phase = np.angle(fft_vals[:half])
    # 前5大频率
    idx = np.argsort(amplitude)[::-1][:5]
    top_freqs = [(freqs[i], amplitude[i]) for i in idx if amplitude[i] > 1e-9]
    return {"freqs": freqs, "amplitude": amplitude, "phase": phase,
            "top_freqs": top_freqs}


def find_periods(x, fs=1.0, top_n=3):
    """
    通过 FFT 找信号主周期 (对应论文"时序周期性判定")
    Returns:
        list of (period, amplitude), period 以采样单位计
    """
    spec = fft_spectrum(x, fs)
    out = []
    for f, a in spec["top_freqs"]:
        if f > 0:
            out.append((1.0 / f, a))
    return out[:top_n]


# ============================================================
# 2. 小波去噪
# ============================================================
def wavelet_denoise(x, wavelet="db4", level=3, mode="soft"):
    """
    Args:
        wavelet: 小波基 (db4/sym4/haar)
        level: 分解层数
        mode: "soft" / "hard"
    Returns:
        dict with keys: x_denoised, level, wavelet
    """
    import pywt
    coeffs = pywt.wavedec(x, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    threshold = sigma * np.sqrt(2 * np.log(len(x)))
    coeffs_denoised = [coeffs[0]]
    for c in coeffs[1:]:
        coeffs_denoised.append(pywt.threshold(c, threshold, mode=mode))
    x_denoised = pywt.waverec(coeffs_denoised, wavelet)
    return {"x_denoised": x_denoised, "level": level, "wavelet": wavelet}


def wavelet_variance(x, wavelet="morl", scales=None):
    """
    小波方差分析 (对应论文"小波方差与实部等值线图求周期")
    Returns:
        dict with keys: scales, variance
    """
    import pywt
    if scales is None:
        scales = np.arange(1, 32)
    coefs, freqs = pywt.cwt(x, scales, wavelet)
    variance = np.var(np.abs(coefs), axis=1)
    return {"scales": scales, "variance": variance}


# ============================================================
# 3. 压缩感知重构 (OMP / LASSO)
# ============================================================
def cs_reconstruct(A, y, k=None, method="omp"):
    """
    欠采样观测 y = A x 下利用稀疏性重构 x

    Args:
        A: (m, n) 测量矩阵, m < n
        y: (m,) 观测
        k: 稀疏度 (OMP 迭代数)
        method: "omp" / "lasso"
    Returns:
        dict with keys: x_hat, error, method
    """
    from sklearn.linear_model import OrthogonalMatchingPursuit, Lasso
    y = np.asarray(y, dtype=float)
    if method == "omp":
        if k is None:
            k = 5
        model = OrthogonalMatchingPursuit(n_nonzero_coefs=k)
    else:
        model = Lasso(alpha=0.01)
    model.fit(A, y)
    x_hat = model.coef_
    return {"x_hat": x_hat, "method": method}


# ============================================================
# 4. 可视化
# ============================================================
def plot_signal_spectrum(x, fs=1.0, title="信号与频谱"):
    spec = fft_spectrum(x, fs)
    fig, axes = plt.subplots(2, 1, figsize=(10, 7))
    t = np.arange(len(x)) / fs
    axes[0].plot(t, x)
    axes[0].set_title("时域信号")
    axes[0].set_xlabel("时间")
    axes[1].stem(spec["freqs"][: len(spec["freqs"]) // 2], spec["amplitude"][: len(spec["freqs"]) // 2])
    axes[1].set_title("频谱")
    axes[1].set_xlabel("频率")
    axes[1].set_ylabel("振幅")
    fig.suptitle(title)
    plt.tight_layout()
    return fig


# ============================================================
# 主流程示例 (对应论文 §9)
# ============================================================
if __name__ == "__main__":
    # 合成含噪声周期信号 (模拟实际测量)
    fs = 100
    t = np.arange(0, 10, 1 / fs)
    x_true = 2 * np.sin(2 * np.pi * 1.5 * t) + 1.0 * np.sin(2 * np.pi * 7.0 * t)
    x = x_true + np.random.normal(0, 0.3, len(t))

    # FFT 找主频率
    periods = find_periods(x, fs, top_n=2)
    print(f"主周期: {[(f'{p[0]:.2f} 采样单位', f'振幅 {p[1]:.3f}') for p in periods]}")

    # 小波去噪
    denoised = wavelet_denoise(x, wavelet="db4", level=3)
    snr_before = 10 * np.log10(np.var(x_true) / np.var(x - x_true))
    snr_after = 10 * np.log10(np.var(x_true) / np.var(denoised["x_denoised"] - x_true))
    print(f"去噪前 SNR: {snr_before:.2f} dB, 去噪后 SNR: {snr_after:.2f} dB")

    # 压缩感知示例 (稀疏信号)
    n, m = 200, 80
    x_sparse = np.zeros(n)
    x_sparse[[20, 60, 150]] = [3.0, -2.0, 1.5]
    A = np.random.randn(m, n) / np.sqrt(m)
    y = A @ x_sparse
    cs = cs_reconstruct(A, y, k=3, method="omp")
    rec_error = np.linalg.norm(cs["x_hat"] - x_sparse) / np.linalg.norm(x_sparse)
    print(f"OMP 重构相对误差: {rec_error:.4f}")

    fig = plot_signal_spectrum(x, fs, "含噪信号频谱")
    plt.savefig("figures/signal_fft.png", dpi=300)
    print("已保存 figures/signal_fft.png")

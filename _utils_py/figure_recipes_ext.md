# 扩展图型配方（figure_recipes_ext — v0.8.5 新增 25 种）

> 与 chart_library.md「扩展图型」索引配对。每个配方含：判定一句话 + 可直接抄的 matplotlib 关键代码。
> 用 Python + matplotlib；风格基线统一走 `plot_utils.setup_style()`；出图后必跑 `figure_check.py` 质检。

## ext#1 气泡图（多维比较）
**判定**：三/四维比较（X、Y 之外还要再编码一维，如面积=第三变量、颜色=第四变量）。
```python
import numpy as np, matplotlib.pyplot as plt
x, y = data["x"], data["y"]; s = data["z"]; color = data["w"]
fig, ax = plt.subplots(figsize=(6, 4.4))
sc = ax.scatter(x, y, s=s, c=color, cmap="viridis", alpha=.72, edgecolors="#333", linewidths=.5)
fig.colorbar(sc, ax=ax)
```

## ext#2 收敛曲线（启发式算法）
**判定**：遗传/模拟退火/粒子群等迭代求解，画最优值随代数下降，标收敛点。
```python
it = np.arange(len(best_hist))
ax.plot(it, best_hist, "-o", ms=3, lw=1.8)
ax.annotate("收敛", xy=(len(it)-1, best_hist[-1]), xytext=(len(it)*.7, best_hist[0]*1.2),
            arrowprops=dict(arrowstyle="->"))
ax.set_xlabel("迭代代数"); ax.set_ylabel("最优值")
```

## ext#3 阶梯图（离散跳变）
**判定**：离散事件驱动的不连续序列（阈值触发/库存补货/分段费率/开关状态）。
```python
t = np.arange(len(v))
ax.step(t, v, where="post", lw=2)
ax.fill_between(t, 0, v, step="post", alpha=.12)
```

## ext#4 事件时间线
**判定**：标注关键里程碑/异常时点，配合因果叙述（滑坡时点、政策零时刻、故障点）。
```python
ax.hlines(0, 0, 10, color="#888", lw=1.2)
for name, x, col in events:              # events=[("异常",5,"#d33"), ...]
    ax.plot([x, x], [-.4, .4], color=col, lw=2); ax.scatter([x], [0], s=36, color=col, zorder=3)
    ax.text(x, .55, name, ha="center")
ax.axis("off"); ax.set_ylim(-1.2, 1.5)
```

## ext#5 学习曲线（train/val）
**判定**：神经网络/迭代模型训练 vs 验证损失，判断过拟合与早停点。
```python
ax.plot(epochs, train_loss, lw=2, label="训练")
ax.plot(epochs, val_loss, lw=2, label="验证")
ax.axvline(best_epoch, color="#888", ls="--"); ax.annotate("早停点", (best_epoch+.3, train_loss[0]*.9))
ax.legend(); ax.set_xlabel("轮次"); ax.set_ylabel("损失")
```

## ext#6 灰色预测 GM(1,1)
**判定**：小样本（≥4 个点）趋势外推，预测未来点 + 区间（灰色系统理论）。
```python
t = np.arange(len(y)); ax.plot(t, y, "-o", ms=4)          # 历史
tt = np.arange(len(y), len(y)+h); yy = y[-1]*1.08**np.arange(1, h+1)   # 示例外推，正式用 GM(1,1) 累减还原
ax.plot(tt, yy, "--"); ax.fill_between(tt, yy*.94, yy*1.06, alpha=.15)
ax.axvline(len(y)-1, color="#999", ls=":")
```

## ext#7 蒙特卡洛模拟带
**判定**：随机模拟/随机过程不确定性，展示中位数与 95% 置信带（Monte Carlo）。
```python
med = np.median(paths, axis=0); lo = np.percentile(paths, 2.5, axis=0); hi = np.percentile(paths, 97.5, axis=0)
for p in paths[::4]: ax.plot(p, lw=.55, color="#ccc", alpha=.35)
ax.fill_between(t, lo, hi, alpha=.22); ax.plot(med, lw=2)
```

## ext#8 聚类谱系图（层次聚类）
**判定**：系统聚类（样本或变量），画树状图支撑聚类数选取。
```python
from scipy.cluster.hierarchy import linkage, dendrogram
dendrogram(linkage(X, method="ward"), no_labels=True, color_threshold=0)
```

## ext#9 分裂小提琴图（双组分布）
**判定**：同类别下两组（前后测/男-女/两方案）左右半拼的分布对比。
```python
from scipy.stats import gaussian_kde
gr = np.linspace(vmin, vmax, 40)
v1 = gaussian_kde(d1)(gr); v1 *= .6/v1.max();  v2 = gaussian_kde(d2)(gr); v2 *= .6/v2.max()
ax.plot(i-v1, gr, lw=1.5); ax.plot(i+v2, gr, lw=1.5)
ax.fill_betweenx(gr, i-v1, i, alpha=.25); ax.fill_betweenx(gr, i, i+v2, alpha=.25)
```

## ext#10 预测-观测 1:1 散点
**判定**：模型验证，预测 vs 真实散点贴近 y=x 越好，附 R²。
```python
ax.scatter(obs, pred, s=14, alpha=.6, edgecolors="white", linewidths=.4)
lim = (min(obs.min(), pred.min()), max(obs.max(), pred.max()))
ax.plot(lim, lim, "--", color="#777"); ax.annotate(f"R² = {r2:.2f}", (lim[0], lim[1]*.85))
ax.set_xlabel("观测值"); ax.set_ylabel("预测值")
```

## ext#11 旭日图（层级占比）
**判定**：多级占比（外环细分内环大类），层级构成展示。
```python
from matplotlib.patches import Wedge
ax.axis("off")
th = 0
for v, col in zip(inner_vals, cols):
    ax.add_patch(Wedge((0,0), .55, th, th+v*3.6, width=.22, fc=col)); th += v*3.6
th = 0
for v, col in zip(outer_vals, cols2):
    ax.add_patch(Wedge((0,0), .95, th, th+v*3.6, width=.3, fc=col)); th += v*3.6
ax.set_aspect("equal"); ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.2, 1.2)
```

## ext#12 弦图（关系/流向矩阵）
**判定**：两两关联/权重较大（产业关联、区域客流、变量耦合、资金流向）。
```python
# 用循环：节点均布圆周，pair 的弧线用贝塞尔（Path.CURVE3），线宽=权重。
import matplotlib.path as mpath; from matplotlib.patches import PathPatch
p1, p2 = nodes[i], nodes[j]; mid = (p1+p2)/2; ctrl = mid*1.4
ax.add_patch(PathPatch(mpath.Path([p1, ctrl, p2], [mpath.Path.MOVETO, mpath.Path.CURVE3, mpath.Path.CURVE3]),
                       fc="none", ec=col, lw=8*w, alpha=.6))
```

## ext#13 三维散点
**判定**：三变量联合分布、多目标空间结构（matplotlib 3D）。
```python
ax = fig.add_subplot(111, projection="3d")
ax.scatter(x, y, z, s=10, alpha=.6); ax.set_box_aspect((1,1,.7)); ax.view_init(elev=25, azim=-60)
```

## ext#14 三维柱状图
**判定**：双分类因素取值高度对比（A×B 效应）。
```python
ax = fig.add_subplot(111, projection="3d")
ax.bar3d(X.ravel()-.35, Y.ravel()-.35, 0, .7, .7, Z.ravel(), color=cols, alpha=.9)
```

## ext#15 三维等高线（响应面）
**判定**：双参数目标/响应面寻优，可行域与极值直观。
```python
ax = fig.add_subplot(111, projection="3d")
ax.contour3D(X, Y, Z, 18, cmap="viridis"); ax.view_init(elev=35, azim=-55)
```

## ext#16 ROC 曲线 + AUC
**判定**：二分类/预测模型性能评价，附 AUC。
```python
fpr, tpr, _ = roc_curve(y_true, y_score)
ax.plot(fpr, tpr, lw=2); ax.fill_between(fpr, tpr, 0, alpha=.15)
ax.plot([0,1],[0,1], "--", color="#999"); ax.annotate(f"AUC = {auc(fpr,tpr):.2f}", (.45, .3))
ax.set_xlabel("假阳率"); ax.set_ylabel("真阳率")
```

## ext#17 混淆矩阵
**判定**：分类错误结构，行=真实列=预测。
```python
ax.imshow(cm, cmap="YlGnBu"); 
for i in range(n): 
    for j in range(n): ax.text(j, i, f"{cm[i,j]}", ha="center", va="center")
ax.set_xticks(range(n)); ax.set_yticks(range(n)); ax.set_xticklabels(labels); ax.set_yticklabels(labels)
```

## ext#18 Pareto 前沿（多目标）
**判定**：多目标优化（NSGA-II 等）解集折衷，标前沿线与折衷解。
```python
ax.scatter(f1, f2, s=20, alpha=.85); ax.scatter(pf1, pf2, s=70, color="#FDBF11", zorder=4)
for x, y, lb in zip(pf1, pf2, labels): ax.text(x, y, lb, fontweight="bold", ha="center")
ax.set_xlabel("目标 1（越小越好）"); ax.set_ylabel("目标 2（越小越好）")
```

## ext#19 中国省区填色地图
**判定**：地理题（疫情/物流/灾害/区域差异），按省份指标填色（用 `_utils/china_provinces.geojson`）。
```python
import json; gj = json.load(open("_utils/china_provinces.geojson", encoding="utf-8"))
for f in gj["features"]:
    g = f["geometry"]; polys = [g["coordinates"]] if g["type"]=="Polygon" else g["coordinates"]
    for poly in polys:
        ax.add_patch(Polygon(np.array(poly[0]), fc=plt.cm.YlOrRd(value_by_province(f)), ec="white", lw=.3))
ax.set_xlim(72, 136); ax.set_ylim(16, 54); ax.axis("off")
```

## ext#20 流线矢量场
**判定**：风场/流速场/物流流场（向量场的连续流线）。
```python
Y, X = np.mgrid[ymin:ymax:nj, xmin:xmax:ni]; U, V = u(X,Y), v(X,Y)
ax.streamplot(X, Y, U, V, color=np.hypot(U, V), cmap="viridis", density=1.1)
```

## ext#21 特征重要性
**判定**：机器学习模型（随机森林/XGBoost/回归系数）变量贡献排序。
```python
ax.barh(names, importances, color=main_color); ax.set_xlabel("重要性")
```

## ext#22 神经网络结构示意
**判定**：AI/深度学习模型结构说明（输入-隐藏-输出层）。
```python
ax.axis("off")
for xi, n in zip(xs, sizes):
    ys = [top - i*(span/max(1,n-1)) for i in range(n)]
    ax.scatter([xi]*n, ys, s=210, color=col, edgecolors="white")
for i in range(len(xs)-1):
    for y1 in ys_layer[i]:
        for y2 in ys_layer[i+1]: ax.plot([xs[i], xs[i+1]], [y1, y2], color="#b6bcc8", lw=.8)
```

## ext#23 决策树示意
**判定**：分类/判定的树状分支（特征阈值→叶结论）。
```python
ax.axis("off")
def node(x, y, t, leaf=False):
    ax.add_patch(plt.Rectangle((x-.9, y-.34), 1.8, .68, fc="#eef3f9" if not leaf else main_color, ec="#666"))
    ax.text(x, y, t, ha="center", va="center")
# 根/叶节点 + 是/否分支线，照 ext 样例布局
```

## ext#24 模糊隶属函数
**判定**：模糊综合评价（隶属度分层：低/中/高 三角或梯形曲线）。
```python
def tri(a, b, c): return np.maximum(0, np.minimum((x-a)/(b-a), (c-x)/(c-b)))
ax.plot(x, tri(a1,b1,c1), lw=2, label="低"); ax.plot(x, tri(a2,b2,c2), lw=2, label="中"); ax.plot(x, tri(a3,b3,c3), lw=2, label="高")
ax.legend(); ax.set_yticks([0, 1]); ax.set_ylim(-.05, 1.1)
```

## ext#25 AHP 判断矩阵
**判定**：层次分析法两两比较（评价类），画判断矩阵热力 + 权重。
```python
M = np.array([[1,3,5,7],[1/3,1,3,5],[1/5,1/3,1,3],[1/7,1/5,1/3,1]])
ax.imshow(M, cmap="YlGnBu")
for i in range(4):
    for j in range(4): ax.text(j, i, f"{M[i,j]:g}", ha="center", fontsize=7)
ax.set_xticks(range(4)); ax.set_yticks(range(4)); ax.set_xticklabels(criteria); ax.set_yticklabels(criteria)
```
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tikz_check.py — TikZ 架构图质量自检(pure-stdlib 版,对齐 _utils/tikz_check.sh)。

用法:
    python tikz_check.py [figures/tikz_architecture_examples.tex]

退出码: 0=通过(含文件不存在跳过)  非0=CRITICAL 条数(有任一 CRITICAL 即失败阻断)。
逻辑与 .sh 完全一致(配色/裸色覆盖/彩虹/浅色文字/opacity/锚点聚集/重叠/连线穿过/
中文宽度),仅把 bash+grep+awk 换成纯 Python。
"""
import re
import sys
from pathlib import Path

tex_path = Path(sys.argv[1] if len(sys.argv) > 1 else "figures/tikz_architecture_examples.tex")
critical = 0


def count(pat, s, flags=0):
    """grep -oP 计数(去重简化:按匹配实例计数,语义等价 grep -o | wc -l)。"""
    return len(re.findall(pat, s, flags)) if s else 0


def has(pat, s, flags=0):
    return bool(re.search(pat, s, flags))


if not tex_path.is_file():
    print(f"TikZ 文件不存在: {tex_path}，跳过")
    raise SystemExit(0)

tex = tex_path.read_text(encoding="utf-8", errors="ignore")

print(f"=== TikZ 架构图质量自检: {tex_path} ===")

# ---- 模板配色检查(几何图/黑白线稿/命名色方案豁免) ----
has_rgb_style = count(r"rgb,255:red,", tex)
skip_palette = 0
if has(r"\\coordinate|\\usetikzlibrary\{[^}]*calc", tex):
    skip_palette = 1
if has(r"fill=\w+!\d", tex):
    skip_palette = 1
if not has(r"(rgb,255:red|=\{?(red|orange|green|blue|cyan|violet|purple|brown|teal|indigo|olive|pink|lime|magenta|yellow)\b)", tex):
    skip_palette = 1
if has_rgb_style < 2 and skip_palette == 0:
    print("CRITICAL: 节点没有使用配色（rgb,255 或 命名色浅填充方案，见 tikz_rules.md 6 套方案）")
    critical += 1
elif skip_palette == 1 and has_rgb_style < 2:
    print("INFO: 几何图/黑白线稿/命名色方案 — 跳过「节点成套 rgb,255 配色」检查（彩虹/深色仍照查）")

# ---- 裸颜色名覆盖填充检测(fill=浅色 之后裸写 black → 纯黑块) ----
BARE = re.compile(r"^(black|white|red|blue|green|gray|grey|cyan|magenta|yellow|orange|violet|purple|brown|teal|indigo|olive|pink|lime)(!\d+(!\w+)?)?$")
bad = 0
for m in re.finditer(r"\\node\[((?:[^\[\]]|\{[^}]*\})*)\]", tex, re.S):
    items = [i.strip() for i in m.group(1).split(",") if i.strip()]
    fi = [k for k, it in enumerate(items) if it.startswith("fill=") and not it.startswith("fill=none")]
    if not fi:
        continue
    ci = [k for k, it in enumerate(items) if "=" not in it and BARE.match(it)]
    if any(k > min(fi) for k in ci):
        bad += 1
if bad > 0:
    print(f"CRITICAL: {bad} 个 node 在 fill=<浅色> 之后裸写颜色名(如 black) — 裸色=color=会覆盖填充→整块变纯黑(黑底黑字)。修：设文字色改用 text=black，不要裸写颜色名")
    critical += 1

# ---- 每阶段不同颜色 / 彩虹原色 ----
unique_fills = len(set(re.findall(r"fill=\{rgb,255:red,\d+;green,\d+;blue,\d+\}", tex)))
if unique_fills > 4:
    print(f"CRITICAL: 发现 {unique_fills} 种不同 rgb 填充色，应统一用一套配色方案（main+sub 两色 + dashbox 灰色）")
    critical += 1
named_fills = len(set(p for p in re.findall(r"fill=\w+!?\d*", tex)
                        if p not in ("fill=none", "fill=white", "fill=gray", "fill=black")))
if named_fills > 4:
    print(f"CRITICAL: 发现 {named_fills} 种不同命名填充色 — 彩虹效果！应统一用 Template 4 的双色方案")
    critical += 1

# ---- 禁止项 ----
if has(r"\\fill\[.*rgb.*rounded corners", tex):
    print("CRITICAL: 发现灰色大背景 \\fill，必须删除")
    critical += 1
if has(r"on background layer", tex):
    print("CRITICAL: 发现 on background layer，必须删除")
    critical += 1
if has(r"fit=\(", tex):
    print("CRITICAL: 发现 fit=()，必须改用手动坐标 dashbox")
    critical += 1
if has(r"fill=(blue|red|green|black|gray![7-9]0|gray!100|dark)(?!\!)", tex):
    print("CRITICAL: 发现深色填充")
    critical += 1

# ---- 浅色文字 ----
light_gray = count(r"color=gray![3-6]0|text=gray![3-6]0|\\color\{gray![3-6]0\}|\\textcolor\{gray![3-6]0\}", tex)
bare_gray = count(r"\\color\{gray\}|text=gray[^!]|\\textcolor\{gray\}\{", tex)
note_style = count(r"note/.style", tex)
if light_gray > 0:
    print(f"CRITICAL: {light_gray} 处浅色文字(gray!30~60 各种写法)")
    critical += 1
if bare_gray > 0:
    print(f"CRITICAL: {bare_gray} 处裸 gray 文字 (无 !60+ 深度修饰)")
    critical += 1
if note_style > 0:
    print("CRITICAL: 发现 note/.style，禁止浅色注释")
    critical += 1

# ---- opacity 滥用(fill opacity 合法,排除字母前带 fill) ----
faded_any = count(r"(?<![a-z])opacity=0\.[0-5]", tex)
if faded_any > 2:
    print(f"CRITICAL: {faded_any} 处 opacity ≤ 0.5 — 文字/线条几乎隐形（公式说明、辅助标签必须 opacity >= 0.85）")
    print("         (fill opacity 用于色块填充是合法的，本检测仅抓裸 opacity)")
    critical += 1

# ---- \draw 彩虹原色 ----
draw_colors = len(set(re.findall(r"\\draw\[[^\]]*?(color=|draw=)?\b(red|orange|yellow|green|blue|cyan|magenta|violet|purple|brown|teal|indigo|olive|pink|lime)\b", tex)))
if draw_colors > 3:
    print(f"CRITICAL: \\draw 命令用了 {draw_colors} 种不同命名色 — 彩虹效果！同张图主体色 ≤ 3 种（含黑灰）")
    critical += 1

# ---- 几何图纯红标注(保留给强调/关键点) ----
red_labels = count(r"\\node\[[^\]]*(color=red|text=red)[^!]", tex)
red_short = count(r"\\node\[red[,\[\] ]", tex)
red_total = red_labels + red_short
if red_total > 2:
    print(f"WARNING: {red_total} 处文字用纯红色 — 红色应保留给\"强调/关键点\"，普通几何标注用 black 或 black!80")

# ---- 同锚点多标签聚集 ----
from collections import Counter
anchors = [m.group(1) for m in re.finditer(r"of\s+([a-zA-Z][a-zA-Z0-9_]*)", tex)]
anchor_dup = [(k, v) for k, v in Counter(anchors).items() if v >= 3]
if anchor_dup:
    print("CRITICAL: 同一锚点被相对定位引用 ≥ 3 次（标签必重叠）：")
    for k, v in anchor_dup:
        print(f"    {k} ({v}次)")
    print("  → 改用引线散射: \\draw[gray!60, thin] (P) -- ++(1.0, 0.6) node[right] {标签}")
    critical += 1

many_path_labels = count(r"\\(draw|path)[^;]*node\[[^\]]*\][^{;]*\{[^}]*\}[^;]*node\[[^\]]*\][^{;]*\{[^}]*\}[^;]*node\[", tex, re.S)
if many_path_labels > 0:
    print(f"WARNING: {many_path_labels} 条 \\draw/\\path 路径上挂 ≥ 3 个 node 标签 — 短路径密集标签易遮挡")

tiny_offset = count(r"(above|below|left|right)=[0-5](pt|\.[0-9]+pt)", tex)
if tiny_offset > 3:
    print(f"WARNING: {tiny_offset} 处 above/below/left/right=<6pt 偏移过小 — 中文标签框约 7-8pt 高，会溢出覆盖锚点")
    print("  → 改用 above=4pt 或 above=0.15cm 起步，多标签场景用 above=8pt+")

n_coords = count(r"at\s*\(\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\)", tex)
if n_coords >= 8:
    print(f"INFO: {n_coords} 个绝对坐标 \\node at(x,y) — 节点密度较高，建议人工/Vision 复查标签重叠")

# ---- 杂项 WARNING ----
if has(r"text=white", tex):
    print("WARNING: 发现白色文字")
if has(r"rotate=90", tex):
    print("WARNING: 发现 rotate=90，建议水平文字")
if not has(r"bigarrow|line width=1.8pt|line width=2pt", tex):
    print("WARNING: 没有粗箭头")
if not has(r"rounded corners", tex):
    print("WARNING: 没有圆角")

# ---- 节点重叠检测 ----
print("--- 重叠检测 ---")
BS = chr(92)


def est_wh(style, text):
    w = h = None
    wm = re.search(r"minimum width=(\d+\.?\d*)cm", style)
    hm = re.search(r"minimum height=(\d+\.?\d*)cm", style)
    sm = re.search(r"minimum size=(\d+\.?\d*)cm", style)
    twm = re.search(r"text width=(\d+\.?\d*)cm", style)
    if sm:
        w = h = float(sm.group(1))
    if wm:
        w = float(wm.group(1))
    if twm and w is None:
        w = float(twm.group(1))
    if hm:
        h = float(hm.group(1))
    t = text or ""
    lines = t.split(BS + BS) if (BS + BS) in t else [t]
    if w is None:
        maxw = 0.0
        for ln in lines:
            cn = len([c for c in ln if "\u4e00" <= c <= "\u9fff"])
            en = len([c for c in ln if c.isascii() and (c.isalnum() or c in "+-=/*(),.^_")])
            maxw = max(maxw, cn * 0.37 + en * 0.18 + 0.4)
        w = maxw if maxw > 0 else 2.0
    if h is None:
        h = 0.35 + 0.40 * len(lines)
    return w, h


NODE = re.compile(r"\\node\[([^\]]*)\]\s*(?:\(([^)]*)\))?\s*at\s*\(([^)]+)\)\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\})?")
raw = []
for m in NODE.finditer(tex):
    style = m.group(1)
    name = (m.group(2) or "").strip()
    coord = m.group(3).strip()
    text = m.group(4) or ""
    w, h = est_wh(style, text)
    raw.append({"name": name, "coord": coord, "w": w, "h": h, "box": ("dash" in style)})

NUM = re.compile(r"^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$")
centers = {}
for n in raw:
    mm = NUM.match(n["coord"])
    if mm and n["name"]:
        centers[n["name"]] = (float(mm.group(1)), float(mm.group(2)), n["w"], n["h"])


def resolve(coord):
    mm = NUM.match(coord)
    if mm:
        return float(mm.group(1)), float(mm.group(2))
    parts = coord.split(".")
    base = parts[0].strip()
    if base not in centers:
        return None
    bx, by, bw, bh = centers[base]
    if len(parts) == 1:
        return bx, by
    anch = parts[1].strip().lower()
    dx = dy = 0.0
    if "north" in anch:
        dy = bh / 2
    if "south" in anch:
        dy = -bh / 2
    if "east" in anch:
        dx = bw / 2
    if "west" in anch:
        dx = -bw / 2
    return bx + dx, by + dy


all_nodes = []
for n in raw:
    p = resolve(n["coord"])
    if p is None:
        continue
    all_nodes.append({"x": p[0], "y": p[1], "w": n["w"], "h": n["h"], "box": n["box"]})

SH = 0.12


def half(v):
    return max(0.05, v / 2 - SH)


overlaps = 0
for i in range(len(all_nodes)):
    a = all_nodes[i]
    for j in range(i + 1, len(all_nodes)):
        b = all_nodes[j]
        if a["box"] != b["box"]:
            continue
        if (a["x"] - half(a["w"]) < b["x"] + half(b["w"]) and b["x"] - half(b["w"]) < a["x"] + half(a["w"])
                and a["y"] - half(a["h"]) < b["y"] + half(b["h"]) and b["y"] - half(b["h"]) < a["y"] + half(a["h"])):
            label = "虚线框" if a["box"] else "节点/说明框"
            print(f"CRITICAL: {label}重叠! ({a['x']:.2f},{a['y']:.2f}) vs ({b['x']:.2f},{b['y']:.2f})")
            overlaps += 1
if overlaps == 0 and all_nodes:
    print(f"OK: {len(all_nodes)} 个节点无重叠")
elif not all_nodes:
    print("INFO: 未检测到节点")
else:
    critical += 1

# ---- 中文节点宽度检测 ----
print("--- 中文节点宽度检测 ---")
issues = 0
for m in re.finditer(r"\\node\[([^\]]*)\]\s*(?:\([^)]*\)\s*)?(?:at\s*\([^)]*\)\s*)?\{([^}]*)\}", tex):
    style = m.group(1)
    text = m.group(2).strip()
    if not text or text == "":
        continue
    if text.startswith("\\\\") and len(text) < 5:
        continue
    cn_chars = len([c for c in text if "\u4e00" <= c <= "\u9fff" or "\u3000" <= c <= "\u303f"])
    en_chars = len([c for c in text if c.isascii() and c.isalpha()])
    if cn_chars == 0:
        continue
    needed_w = cn_chars * 0.7 + en_chars * 0.35 + 1.0
    wm = re.search(r"minimum width=(\d+\.?\d*)cm", style)
    twm = re.search(r"text width=(\d+\.?\d*)cm", style)
    actual_w = float(wm.group(1)) if wm else (float(twm.group(1)) if twm else 2.0)
    if actual_w < needed_w - 0.3:
        clean_text = text[:20].replace("\\\\\\\\", "/").replace("\\\\", "")
        print(f"WARNING: \"{clean_text}\" ({cn_chars}中+{en_chars}英) 需要 {needed_w:.1f}cm 但只有 {actual_w:.1f}cm")
        issues += 1
if issues == 0:
    print("OK: 中文节点宽度检查通过")

# ---- 连线穿过节点检测 ----
print("--- 连线路径检测 ---")
import math
nodes = {}
for m in re.finditer(r"\\node\[([^\]]*)\]\s*\(([^)]*)\)\s*at\s*\(([^,]+),\s*([^)]+)\)", tex):
    name = m.group(2).strip()
    try:
        x, y = float(m.group(3).strip()), float(m.group(4).strip())
        style = m.group(1)
        wm = re.search(r"minimum width=(\d+\.?\d*)cm", style)
        w = float(wm.group(1)) if wm else 2.0
        nodes[name] = (x, y, w / 2)
    except Exception:
        pass
issues = 0
for m in re.finditer(r"\\draw.*?\(([^)]+)\).*?--.*?\(([^)]+)\)", tex):
    src_name = m.group(1).strip().split(".")[0]
    dst_name = m.group(2).strip().split(".")[0]
    if src_name not in nodes or dst_name not in nodes:
        continue
    sx, sy, _ = nodes[src_name]
    dx, dy, _ = nodes[dst_name]
    for name, (nx, ny, nr) in nodes.items():
        if name == src_name or name == dst_name:
            continue
        line_len = math.sqrt((dx - sx) ** 2 + (dy - sy) ** 2)
        if line_len < 0.1:
            continue
        t = max(0, min(1, ((nx - sx) * (dx - sx) + (ny - sy) * (dy - sy)) / (line_len ** 2)))
        closest_x = sx + t * (dx - sx)
        closest_y = sy + t * (dy - sy)
        dist = math.sqrt((nx - closest_x) ** 2 + (ny - closest_y) ** 2)
        if dist < nr + 0.3 and 0.1 < t < 0.9:
            print(f"CRITICAL: 连线 {src_name}→{dst_name} 可能穿过节点 {name} (距离={dist:.2f}cm)")
            issues += 1
if issues == 0 and nodes:
    print(f"OK: {len(nodes)} 个节点，连线路径无穿过")
elif not nodes:
    print("INFO: 未检测到带名称的节点")
else:
    critical += 1

# ---- Overfull 检测(figures/x.log 或 paper/main.log) ----
print("--- Overfull 检测 ---")
for lf in (tex_path.with_suffix(".log"), Path("paper/main.log")):
    if not lf.is_file():
        continue
    overfull = count(r"Overfull.*hbox|Overfull.*vbox", lf.read_text(encoding="utf-8", errors="ignore"))
    if overfull > 0:
        print(f"WARNING: {overfull} 个 Overfull 警告 (in {lf.name}) — 可能有文字溢出节点")
        for line in [ln for ln in lf.read_text(encoding="utf-8", errors="ignore").splitlines() if "Overfull" in ln][:5]:
            print("  " + line.strip())
    else:
        print(f"OK: 无 Overfull 警告 (in {lf.name})")
    break

print(f"=== 自检完成: {critical} 个 CRITICAL ===")
raise SystemExit(critical if critical < 255 else 255)
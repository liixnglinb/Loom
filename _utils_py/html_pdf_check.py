#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""html_pdf_check.py — HTML→PDF 出图质量质检(pure-stdlib 版)。

用法:
    python html_pdf_check.py figures/fig_roadmap.pdf

退出码: 0=通过(可能带 WARN,不阻塞)  1=FAIL(必修)  2=无法检查(跳过)。
4 项检查(对齐 SKILL Step 4 契约):
  ① 单页(check 最关键,多页=FAIL:LaTeX 只显示第一页会截断论文)
  ② 矢量(有字体对象/文本→非整页位图;整页位图=FAIL)
  ③ 裁切/尺寸异常(MediaBox 非法或奇大=FAIL)
  ④ 宽高比(>8:1 → WARN,不阻塞)

不依赖 pypdf 等第三方库:直接解析 PDF 结构 + zlib 解压流找文本运算符。
"""
import re
import sys
import zlib
from pathlib import Path


def w(s):
    return s * 2.54 / 72  # pt → cm(仅供人性化显示)


def main():
    pdf = Path(sys.argv[1] if len(sys.argv) > 1 else "figures/fig.pdf")
    if not pdf.is_file():
        print(f"html_pdf_check: 文件不存在 {pdf}，跳过 (exit 2)")
        return 2
    try:
        data = pdf.read_bytes()
    except OSError as e:
        print(f"html_pdf_check: 读取失败 {e}，跳过 (exit 2)")
        return 2

    if b"%PDF-" not in data[:2048]:
        print(f"html_pdf_check: {pdf.name} 不是有效 PDF（缺 %PDF 头），跳过 (exit 2)")
        return 2

    fails = []
    warns = []
    txt = data.decode("latin-1", "replace")

    # ---- 文本层:原始 + 每个流解压(xelatex/Chromium 的页树/字体/MediaBox 全在压缩对象里) ----
    layers = [txt]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = m.group(1)
        # 头尾 `\d+ 0 R` 长度行(部分写入器)剥掉
        raw2 = re.sub(rb"^.*?(?=\d)\d+\s+0\s+R\s*\r?\n", b"", raw, count=1)
        for attempt in (zlib.decompress, lambda b: b):
            try:
                layers.append(attempt(raw2).decode("latin-1", "replace"))
                break
            except Exception:
                continue

    # ---- ① 页数 ----
    # 权威计:页树 /Type /Pages 的 /Count(Chromium/xelatex 都写);兜底:直接数 /Type /Page(排除 /Pages)
    count_total, page_objs = 0, 0
    for layer in layers:
        page_objs = max(page_objs, len(re.findall(r"/Type\s*/Page(?!s)", layer)))
        for mm in re.finditer(r"/Type\s*/Pages\b(.*?)(?=/Type\b|\Z)", layer, re.S):
            mc = re.search(r"/Count\s+(\d+)", mm.group(1))
            if mc:
                count_total += int(mc.group(1))
    pages = count_total if count_total > 0 else (page_objs if page_objs > 0 else -1)
    if pages > 1:
        fails.append(f"多页 PDF ({pages} 页) — LaTeX 只显示第一页会截断，必须精简内容/拆图重出单页")
    elif pages == -1:
        warns.append("页数未知(未扫到页树 /Count，按单页放行)")

    # ---- ② 矢量/文本：字体对象或 Tf 操作符；整页位图(有 Image 无文本)=FAIL ----
    fonts = 0
    has_image = False
    has_tf = False
    for layer in layers:
        fonts += len(re.findall(r"/Type\s*/Font(?!s)", layer))
        if re.search(r"/Subtype\s*/Image|\/Image\b", layer):
            has_image = True
        if re.search(r"\b\d+\s*[\d.]+\s+Tf\b|/Tf\b|/FontFile\b", layer):
            has_tf = True
    if not has_tf and has_image:
        fails.append("整页位图(无字体/文本且含大图) — 检查 HTML 是否误用 <img>/<canvas> 代替文字，改回纯文本+CSS")
    elif not has_tf and fonts == 0:
        warns.append("无文本/字体对象(纯矢量图形图,放行)")

    # ---- ③ 尺寸异常 ----
    sizes = []
    for layer in layers:
        for m in re.finditer(r"/MediaBox\s*\[\s*([\d.\-eE]+)\s+([\d.\-eE]+)\s+([\d.\-eE]+)\s+([\d.\-eE]+)\s*\]", layer):
            try:
                a, b, c, d = (float(x) for x in m.groups())
                sizes.append((abs(c - a), abs(d - b)))
            except (ValueError, TypeError):
                continue
    if sizes:
        w0, h0 = sizes[0]
        if w0 <= 0 or h0 <= 0 or w0 > 20000 or h0 > 20000:
            fails.append(f"页面尺寸异常 ({w0:.0f}x{h0:.0f}pt) — 检查 body{{margin:0}} 与 .fig 是否有内容、display:inline-block")
        # ---- ④ 宽高比 ----
        ratio = max(w0, h0) / min(w0, h0) if min(w0, h0) > 0 else 0
        if ratio > 8:
            warns.append(f"宽高比过宽 (≈{ratio:.1f}:1, {w0:.0f}x{h0:.0f}pt) — 建议 pipeline 让阶段换行、roadmap 改窄卡片")
    else:
        warns.append("未扫到 MediaBox（尺寸未验）")

    print(f"=== html_pdf_check: {pdf.name}（{pages if pages >= 0 else '?'}页, 字体×{fonts}, 尺寸{'x'.join([f'{x:.0f}' for x in sizes[0]]) if sizes else '未知'}）===")
    if fails:
        for f in fails:
            print(f"  FAIL: {f}")
        print("  退出码 1（FAIL 必修）：按上述明细修复后重新出 PDF 再检")
        return 1
    for ww in warns:
        print(f"  WARN: {ww}")
    print("  PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
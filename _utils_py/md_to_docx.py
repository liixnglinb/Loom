#!/usr/bin/env python3
"""ModelFlow Markdown → Word (docx) 中文导出引擎。

用 python-docx 实现 Markdown → Word 核心能力：
  - Markdown 标题层级 → Word 大纲标题（黑体标题，Word 自动编号）
  - 正文 → 宋体 12pt，首行缩进 2 字符
  - 三线表（顶线/表头底线/底线）
  - 行内图片自动嵌入并缩放（>=min 宽按比例）
  - 上标引用 [n] 转 Word 上标
  - 块公式（$$..$$）保留为等宽灰色段落（Word 原生公式需 OMML，此处降级处理）
  - 列表（- / 1.）转 Word 列表

用法：
  python md_to_docx.py --source paper.md --output paper.docx [--title "论文题目"]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor, Emu
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("ERROR: 需要 python-docx，请先 pip install python-docx", file=__import__("sys").stderr)
    __import__("sys").exit(1)

import sys

HEI = "黑体"
SONG = "宋体"
BODY_SIZE = 12          # pt
FIRST_INDENT = Pt(24)   # 2 字符 × 12pt


def _set_font(run, name_cn, size_pt, bold=False, color=None):
    run.font.name = name_cn
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    r = run._element.rPr.rFonts
    r.set(qn("w:eastAsia"), name_cn)
    if color:
        run.font.color.rgb = RGBColor(*color)
    return run


def _add_paragraph(doc, text="", style=None, align=None, indent=None):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    if indent is not None:
        p.paragraph_format.first_line_indent = indent
    return p


def _add_heading(doc, text, level):
    h = doc.add_heading(level=int(min(max(level, 1), 4)))
    for r in h.runs:
        _set_font(r, HEI, max(16 - level, 12), bold=True)
    return h


def _add_body_with_inline(doc, text):
    """正文：解析行内代码/公式/加粗/上标引用/图片链接。"""
    p = _add_paragraph(doc, indent=FIRST_INDENT)
    # 提取图片 ![](path)
    img_m = re.search(r"!\[([^\]]*)\]\(([^)]+)\)", text)
    if img_m:
        caption = img_m.group(1)
        path = img_m.group(2).strip()
        # 插入图片段落
        try:
            pic_p = doc.add_paragraph()
            pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # 自适应宽度
            from docx.shared import Inches
            run = pic_p.add_run()
            run.add_picture(path, width=Inches(min(max(_guess_img_width(path), 2.0), 5.8)))
            if caption:
                cap = _add_paragraph(doc, f"{caption}", align=WD_ALIGN_PARAGRAPH.CENTER)
                for r in cap.runs:
                    _set_font(r, SONG, 10.5)
        except Exception:
            p.add_run(f"[图片无法嵌入: {path}]")
        # 处理剩余文本（若无剩余，直接返回）
        rest = text[:img_m.start()] + text[img_m.end():]
        if not rest.strip():
            return
        text = rest
    # 分块解析：行内代码 `x`、公式 $..$、**加粗**、上标 [n]
    tokens = re.split(r"(`[^`]+`|\$\$[^$]+\$\$|\$[^$]+\$|\*\*[^*]+\*\*|\[[0-9,]+\])", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("`") and tok.endswith("`"):
            r = p.add_run(tok[1:-1]); _set_font(r, "Consolas", BODY_SIZE - 1)
        elif tok.startswith("$$") and tok.endswith("$$"):
            r = p.add_run(tok); _set_font(r, "Cambria Math", BODY_SIZE - 1)
        elif tok.startswith("$") and tok.endswith("$") and len(tok) > 2:
            r = p.add_run(tok); _set_font(r, "Cambria Math", BODY_SIZE - 1)
        elif tok.startswith("**") and tok.endswith("**"):
            r = p.add_run(tok[2:-2]); _set_font(r, SONG, BODY_SIZE, bold=True)
        elif re.fullmatch(r"\[[0-9,]+\]", tok):
            r = p.add_run(tok); _set_font(r, SONG, BODY_SIZE); r.font.superscript = True
        else:
            r = p.add_run(tok); _set_font(r, SONG, BODY_SIZE)
    return p


def _guess_img_width(path: str) -> float:
    """粗略估计图片宽度（英寸），失败给默认。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            w_px, h_px = im.size
            dpi = 96
            return w_px / dpi
    except Exception:
        return 5.0


def _add_table(doc, rows):
    """标准三线表：仅顶线 1.5pt / 表头底线 0.75pt / 底线 1.5pt（booktabs 风格）。"""
    data = []
    for row in rows[:]:
        cells = [c.strip() for c in re.split(r"\s*\|\s*", row.strip().strip("|"))]
        data.append(cells)
    if not data:
        return
    ncol = max(len(r) for r in data)
    tbl = doc.add_table(rows=len(data), cols=ncol)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.style = "Table Grid"
    for ri, row in enumerate(data):
        for ci in range(ncol):
            cell = tbl.cell(ri, ci)
            cell.paragraphs[0].text = ""
            val = row[ci] if ci < len(row) else ""
            r = cell.paragraphs[0].add_run(val)
            _set_font(r, SONG, 10.5, bold=(ri == 0))
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    # 三线表：去掉 Table Grid 竖线，只留顶/表头/底线
    _apply_booktabs(tbl)
    return tbl


def _apply_booktabs(tbl):
    """把整表转成三线表：第一条边框顶线、表头行下边框、最后一行下边框。"""
    from docx.oxml.ns import qn as _qn
    tblPr = tbl._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom"):
        el = OxmlElement(f"w:{edge}")
        el.set(_qn("w:val"), "single"); el.set(_qn("w:sz"), "12"); el.set(_qn("w:color"), "000000")
        borders.append(el)
    for edge in ("left", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(_qn("w:val"), "none"); el.set(_qn("w:sz"), "0")
        borders.append(el)
    # 移除旧 borders
    for old in tblPr.findall(_qn("w:tblBorders")):
        tblPr.remove(old)
    tblPr.append(borders)
    # 表头行下框线
    if len(tbl.rows) >= 2:
        first_row = tbl.rows[0]._tr
        tcPr = first_row.tc_lst[0].get_or_add_tcPr()
        tcBorders = OxmlElement("w:tcBorders")
        bottom = OxmlElement("w:bottom")
        bottom.set(_qn("w:val"), "single"); bottom.set(_qn("w:sz"), "6"); bottom.set(_qn("w:color"), "000000")
        tcBorders.append(bottom)
        tcPr.append(tcBorders)


def convert_md_to_docx(md_text: str, out_path: str, title: str = ""):
    doc = Document()
    # 页面：A4 + 2.5cm 边距
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.5)
    sec.left_margin = sec.right_margin = Cm(2.5)
    # 默认正文样式
    normal = doc.styles["Normal"]
    normal.font.name = SONG
    normal.font.size = Pt(BODY_SIZE)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), SONG)

    if title:
        tp = _add_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
        r = tp.add_run(title); _set_font(r, HEI, 18, bold=True)

    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        # 块公式块 $$
        if line.strip().startswith("$$"):
            buf = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("$$"):
                buf.append(lines[i]); i += 1
            if i < len(lines):
                buf.append(lines[i])
            p = _add_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
            r = p.add_run("\n".join(buf)); _set_font(r, "Cambria Math", BODY_SIZE - 1)
            i += 1
            continue
        # 标题 ###### ~ #
        hm = re.match(r"^(#{1,6})\s+(.*)$", line)
        if hm:
            level = len(hm.group(1))
            _add_heading(doc, hm.group(2).strip(), level)
            i += 1
            continue
        # 表格行（| a | b |）
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[i+1]):
            rows = [line]
            i += 2  # 跳过分隔行
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i]); i += 1
            _add_table(doc, rows)
            continue
        # 分隔线
        if re.fullmatch(r"---+\s*", line):
            i += 1
            continue
        # 有序列表 1. x
        om = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
        if om:
            p = _add_paragraph(doc, indent=FIRST_INDENT)
            r = p.add_run(f"{om.group(1)}. {om.group(2)}"); _set_font(r, SONG, BODY_SIZE)
            i += 1
            continue
        # 无序列表 - x
        um = re.match(r"^\s*[-*]\s+(.*)$", line)
        if um:
            p = _add_paragraph(doc, indent=FIRST_INDENT)
            r = p.add_run("• " + um.group(1)); _set_font(r, SONG, BODY_SIZE)
            i += 1
            continue
        # 空行
        if not line.strip():
            i += 1
            continue
        # 普通正文
        _add_body_with_inline(doc, line)
        i += 1

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return str(out)


def main():
    ap = argparse.ArgumentParser(description="Markdown → Word 中文论文")
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--title", default="")
    args = ap.parse_args()
    src = Path(args.source)
    if not src.exists():
        print(f"ERROR: 源文件不存在: {src}", file=sys.stderr)
        sys.exit(1)
    md_text = src.read_text(encoding="utf-8")
    out = convert_md_to_docx(md_text, args.output, args.title)
    print(f"OK {out}")


if __name__ == "__main__":
    main()
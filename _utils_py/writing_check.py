#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""writing_check.py — Post-writing quality checks(pure-stdlib 版,对齐 _utils/writing_check.sh)。

用法:
    python writing_check.py [paper/]

退出码: 0=通过  1=失败(需修复)  2=跳过。run_check 约定 {0,2}=通过。
逻辑与 .sh 一致:图文交错/堆叠、参考文献真实性、AI 写作痕迹(列表/图表主语/相邻图号开头)、
图注超长(递归跟随 \\input)、元叙述泄露、游离图、缺失图、过度声称等。
"""
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

PAPER_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "paper")
EXIT_CODE = 0


def fail(msg):
    global EXIT_CODE
    print(msg)
    EXIT_CODE = 1


def warn(msg):
    print(msg)


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def nmatches(pat, s, flags=0):
    return len(re.findall(pat, s, flags)) if s else 0


sec_dir = PAPER_DIR / "sections"
sec_files = [f for f in sorted(sec_dir.glob("*.tex"))] if sec_dir.is_dir() else []
main_tex = PAPER_DIR / "main.tex"
# 论文产物尚不存在(paper 步未跑)→不可检查,跳过不阻断{0,2}
if not main_tex.is_file() and not sec_files:
    print(f"SKIP: {PAPER_DIR} 无任何 .tex 产物（paper 步未跑）(exit 2)")
    raise SystemExit(2)
main_content = read(main_tex) if main_tex.is_file() else ""
all_tex = [f for f in sec_files if f.is_file()] + ([main_tex] if main_tex.is_file() else [])

print(f"=== Writing quality checks ({PAPER_DIR}) ===")

# 1. Figure-text interleaving: stacking + missing analysis (awk state machines)
print("--- Figure stacking check ---")


def stacking_count(content):
    c = 0
    a = 0
    t = 0
    for line in content.splitlines():
        if re.search(r"\\end\{(figure|table)\}", line):
            a, t = 1, 0
            continue
        if a and re.search(r"\\begin\{(figure|table)\}", line):
            if t < 3:
                c += 1
            a = 0
            continue
        if a and re.search(r"[a-zA-Z\u4e00-\u9fff]{3,}", line):
            t += 1
            if t >= 3:
                a = 0
    return c


def no_analysis_count(content):
    """figure/table 之后 <3 行分析文字就出现新环境/章节。"""
    c = 0
    e = 0
    t = 0
    lines = content.splitlines()
    for line in lines:
        if re.search(r"\\end\{(figure|table)\}", line):
            e, t = 1, 0
            continue
        if e and re.search(r"[a-zA-Z\u0080-\uffff]{10,}", line):
            t += 1
            if t >= 3:
                e = 0
            continue
        if e and re.search(r"\\(section|subsection|chapter|begin\{figure|begin\{table)", line):
            if t < 3:
                c += 1
            e = 0
    if e and t < 3:
        c += 1
    return c


total_stacking = 0
total_no_analysis = 0
for f in sec_files:
    bn = f.name
    content = read(f)
    s = stacking_count(content)
    n = no_analysis_count(content)
    if s > 0:
        fail(f"  FAIL {bn}: {s} figure stacking violations")
    if n > 0:
        fail(f"  FAIL {bn}: {n} figures/tables missing analysis text")
    total_stacking += s
    total_no_analysis += n
print(f"  Total: {total_stacking} stacking, {total_no_analysis} missing analysis")
if total_stacking == 0 and total_no_analysis == 0:
    warn("  OK: figure-text interleaving passed")

# 2. References check
print("--- References check ---")
bib = PAPER_DIR / "references.bib"
if bib.is_file():
    bib_count = nmatches(r"^@", read(bib), re.M)
    print(f"  references.bib: {bib_count} entries")
    if bib_count == 0:
        fail("  FAIL: references.bib is empty")
else:
    fail("  FAIL: references.bib not found")

cited_keys = set()
for f in all_tex:
    for m in re.finditer(r"\\cite[tp]*\{([^}]*)\}", read(f)):
        for k in m.group(1).split(","):
            cited_keys.add(k.strip())
print(f"  Cited keys in text: {len(cited_keys)}")
cite_in_body = sum(nmatches(r"\\cite", read(f)) for f in all_tex)
if cite_in_body == 0:
    fail("  FAIL: no \\cite{} found in body text")

# 2b. References authenticity (bib_authenticity_check.py, hard-fail only rc==1)
if bib.is_file():
    _bibchk = Path(__file__).resolve().parent / "bib_authenticity_check.py"
    if _bibchk.is_file():
        print("--- References authenticity ---")
        try:
            r = subprocess.run([sys.executable, str(_bibchk), "--bib", str(bib)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            out = (r.stdout + r.stderr)
            if out.strip():
                print(out[-2000:])
            if r.returncode == 1:
                fail("  FAIL: 参考文献真实性核验发现疑似编造条目（见上）")
        except Exception as e:
            warn(f"  (bib_authenticity_check 运行失败: {e})")

# 3. Section character counts
print("--- Section sizes ---")
total_chars = 0
for f in sec_files:
    if not f.is_file():
        continue
    chars = f.stat().st_size
    total_chars += chars
    print(f"  {f.name}: {chars} chars")
print(f"  Total: {total_chars} chars")

# 4. Unused PDF figures (WARN only)
print("--- Unused figures ---")
figs_dir = Path("figures")
unused = 0
if figs_dir.is_dir():
    for pdf in sorted(figs_dir.glob("*.pdf")):
        bn = pdf.name
        joined = "\n".join(read(f) for f in all_tex)
        if bn not in joined:
            warn(f"  WARN: {bn} not referenced")
            unused += 1
if unused == 0:
    warn("  OK: all PDF figures referenced")

# 5. Placeholders (WARN only)
print("--- Placeholder check ---")
placeholders = 0
for f in sec_files:
    if re.search(r"PLACEHOLDER|待补充|TODO|待续写", read(f), re.I):
        warn(f"  WARN: {f.name} contains placeholder markers")
        placeholders += 1
if placeholders == 0:
    warn("  OK: no placeholders found")

# 6. Forbidden patterns
print("--- Forbidden patterns ---")
bad_input = []
for f in sec_files:
    for i, ln in enumerate(read(f).splitlines(), 1):
        if re.search(r"\\input\{[^}]*figures", ln) and not re.search(r"TABLE_[^}]*\.tex", ln):
            bad_input.append(f"{f.name}:{i}:{ln.strip()}")
if bad_input:
    for b in bad_input:
        print("  " + b)
    fail("  FAIL: \\input{figures/...} 只允许 TABLE_*.tex；图请复制 \\begin{figure} 代码块进 sections")
for f in ([main_tex] + sec_files):
    if f.is_file() and re.search(r"colorlinks=true", read(f)):
        fail(f"  FAIL: colorlinks=true found ({f.name})")

# 7. AI writing patterns (itemize/enumerate)
print("--- AI writing patterns ---")
ai_patterns = 0
for f in sec_files:
    bn = f.name
    if re.search(r"appendix|附录|code", bn, re.I):
        continue
    content = read(f)
    item_count = nmatches(r"\\begin\{itemize\}", content)
    enum_count = nmatches(r"\\begin\{enumerate\}", content)
    total_list = item_count + enum_count
    if total_list > 0:
        warn(f"  WARN {bn}: {total_list} bullet/numbered lists (itemize={item_count}, enumerate={enum_count}) — convert to flowing prose")
        ai_patterns += total_list
if ai_patterns > 3:
    fail(f"  FAIL: {ai_patterns} total lists in body text — strong AI writing signal, must convert to paragraphs")
elif ai_patterns > 0:
    warn(f"  WARN: {ai_patterns} lists found — consider converting to prose")

# 7b. Figure-as-subject detection
print("--- Figure-as-subject check ---")
fig_subject = 0
for f in sec_files:
    bn = f.name
    if re.search(r"appendix|附录|code|symbol", bn, re.I):
        continue
    content = read(f)
    hits = nmatches(r"^\s*(如图|由图|从图|图\s*\\|图\d|如表|由表|从表|表\s*\\|表\d)", content, re.M)
    hits_en = nmatches(r"^\s*(Figure|Table|Fig\.|Tab\.)\s*\\", content, re.M | re.I)
    total_hits = hits + hits_en
    if total_hits >= 3:
        warn(f"  WARN {bn}: {total_hits} 段以图/表引用开头 — 图表应作旁证融入论证，不要做段落主语")
        fig_subject += total_hits
if fig_subject >= 5:
    fail(f"  FAIL: {fig_subject} 处图表做主语 — 严重 AI 写作痕迹，需重写图文衔接")
elif fig_subject > 0:
    warn(f"  WARN: {fig_subject} 处图表做主语 — 建议改为括号旁注形式")

# 7b2. 相邻图号开头检测
print("--- 相邻图号开头检测 ---")
open_re = re.compile(r"^(图|表)\s*[\d\\]|^(Figure|Table|Fig|Tab)\b")
viol = 0
tot_open = 0
tot_ref = 0
file_pairs_total = 0
for fn in sorted(os.listdir(sec_dir)) if sec_dir.is_dir() else []:
    if not fn.endswith(".tex"):
        continue
    if re.search(r"appendix|附录|code|symbol", fn, re.I):
        continue
    content = read(sec_dir / fn).replace("\r\n", "\n")
    paras = re.split(r"\n\s*\n", content)
    flags = []
    for p in paras:
        s = p.strip()
        if not s:
            continue
        first = s[0]
        if first in "\\%{}&$#" or len(s) < 15:
            continue
        flags.append(bool(open_re.match(s)))
        if re.search(r"(图|表)\s*[\d\\]|(Figure|Table|Fig|Tab)\b", s):
            tot_ref += 1
    tot_open += sum(flags)
    file_pairs = 0
    for i in range(len(flags) - 1):
        if flags[i] and flags[i + 1]:
            file_pairs += 1
    if file_pairs > 0:
        print(f"  FAIL {fn}: {file_pairs} 处相邻段落都以图号/表号起句 — 把图号沉到句中或句末括号")
        viol += file_pairs
        file_pairs_total += file_pairs
ratio = (tot_open / tot_ref) if tot_ref else 0
if tot_ref >= 5 and ratio > 0.35:
    print(f"  FAIL 全文 {tot_open}/{tot_ref} 段以图号/表号起句（{ratio:.0%}>35%）— 通篇一个套路，即便彼此隔开也太单调")
    viol += 1
if viol > 0:
    print(f"  共 {viol} 处图号起句问题（相邻/全文普遍）— 违反图文衔接铁律，改用括号旁注/动词引导/后置印证")
    EXIT_CODE = 1
else:
    warn("  OK: 无相邻图号开头，全文起句句式多样")

# 7b3. 图注/表注超长检测(递归跟随 \\input,中文>20字/英文>14词)
print("--- 图注/表注超长检测 ---")
ZH, EN = 20, 14
bad = []


def check_caption(body_zh_en):
    cn = re.findall(r"[一-鿿]", body_zh_en)
    if cn:
        if len(cn) > ZH:
            return (len(cn), "字", "".join(cn)[:30])
    else:
        words = re.findall(r"[A-Za-z][A-Za-z-]*", body_zh_en)
        if len(words) > EN:
            return (len(words), "words", " ".join(words[:12]))
    return None


def strip_comments(s):
    out = []
    for line in s.split("\n"):
        k, cut = 0, None
        while k < len(line):
            if line[k] == "\\":
                k += 2
                continue
            if line[k] == "%":
                cut = k
                break
            k += 1
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def rel(p):
    try:
        return os.path.relpath(p, str(PAPER_DIR)).replace("\\", "/")
    except ValueError:
        return str(p)


def resolve_input(raw, cur_file):
    raw = raw.strip().strip('"')
    if not raw or raw.endswith("/"):
        return None
    names = (raw,) if raw.lower().endswith(".tex") else (raw + ".tex", raw)
    for base in (str(PAPER_DIR), os.path.dirname(cur_file), os.path.dirname(str(PAPER_DIR))):
        for name in names:
            c = os.path.normpath(os.path.join(base, name))
            if os.path.isfile(c):
                return c
    return None


def scan_captions(s, display):
    i = 0
    while True:
        m = re.search(r"\\caption\*?\s*(\[[^\]]*\]\s*)?\{", s[i:])
        if not m:
            break
        start = i + m.end()
        depth = 1
        j = start
        while j < len(s) and depth:
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
            j += 1
        inner = s[start:j - 1]
        i = j
        t = re.sub(r"\\(label|ref|cite|footnote)\{[^}]*\}", "", inner)
        t = re.sub(r"\$[^$]*\$", "", t)
        t = re.sub(r"\\[a-zA-Z]+\*?", "", t)
        r = check_caption(t)
        if r:
            bad.append((display, *r))


SKIP_RE = re.compile(r"appendix|附录|code|symbol", re.I)
MAX_DEPTH = 6
roots = []
if main_tex.is_file():
    roots.append(str(main_tex))
if sec_dir.is_dir():
    roots += [str(sec_dir / fn) for fn in sorted(os.listdir(sec_dir)) if fn.endswith(".tex")]

visited = set()
queue = [(f, 0) for f in roots]
while queue:
    f, d = queue.pop(0)
    key = os.path.normcase(os.path.abspath(f))
    if key in visited:
        continue
    visited.add(key)
    _bn = os.path.basename(f)
    _scope = "/".join(rel(f).split("/")[-2:])
    _in_appendix = re.search(r"appendix|附录", _scope, re.I)
    if _in_appendix or (SKIP_RE.search(_scope) and not _bn.upper().startswith("TABLE_")):
        continue
    try:
        s = strip_comments(open(f, encoding="utf-8", errors="ignore").read())
    except OSError:
        continue
    scan_captions(s, rel(f))
    if d < MAX_DEPTH:
        for m in re.finditer(r"\\(?:input|include)\s*\{([^{}]*)\}", s):
            nxt = resolve_input(m.group(1), f)
            if nxt:
                queue.append((nxt, d + 1))

md = os.path.join(str(PAPER_DIR), "main.md")
if os.path.isfile(md):
    try:
        text = open(md, encoding="utf-8", errors="ignore").read()
    except OSError:
        text = ""
    m2 = re.search(r"(?m)^##\s*(附录|Appendix|参考文献|References)", text)
    body = text[:m2.start()] if m2 else text
    for alt in re.findall(r"!\[([^\]]*)\]\([^)]*\)", body):
        stripped = re.sub(r"^\s*(图|表|Figure|Fig\.?|Table|Tab\.?)\s*\d+\s*[:：.．、]?\s*", "", alt, flags=re.I)
        r = check_caption(stripped)
        if r:
            bad.append(("main.md", *r))

figdir = None
for _c in (os.path.join(os.path.dirname(str(PAPER_DIR)) or ".", "figures"),
           "figures", os.path.join(str(PAPER_DIR), "..", "figures")):
    if os.path.isdir(_c):
        figdir = _c
        break
if figdir:
    try:
        _tfs = sorted(fn for fn in os.listdir(figdir) if fn.startswith("TABLE_") and fn.lower().endswith(".md"))
    except OSError:
        _tfs = []
    for fn in _tfs:
        try:
            _lines = open(os.path.join(figdir, fn), encoding="utf-8", errors="ignore").read().split("\n")
        except OSError:
            continue
        for ln in _lines:
            m3 = re.fullmatch(r"\*\*(.+?)\*\*", ln.strip())
            if not m3:
                continue
            st = re.sub(r"^\s*(表|Table|Tab\.?)\s*\d*\s*[:：.．、]?\s*", "", m3.group(1), flags=re.I)
            r = check_caption(st)
            if r:
                bad.append(("figures/" + fn, *r))
            break

if bad:
    for fn, n, unit, preview in bad:
        print(f"  FAIL {fn}: caption {n} {unit}（超上限，中文≤20字/英文≤14词）: {preview}...")
    print(f"  共 {len(bad)} 处图注/表注过长 — caption 只写简短标签，判据/参数/结论移入正文")
    if any(("figures/" in fn) or fn.startswith("../") for fn, *_ in bad):
        print("  ★ 落在 figures/ 的表注要改那个源文件本身，没有\"中间副本\"可改：")
        print("    PDF 模式它被 \\input{../figures/TABLE_*.tex} 直通成品，改 sections/ 无效；")
        print("    docx 模式它被 cat figures/TABLE_*.md 拼进 main.md，改 main.md 会被下次覆盖。")
        print("    统计口径/结论/数据来源搬进正文（docx 也可放表下方的「> 注：」行）。")
    EXIT_CODE = 1
elif not roots and not os.path.isfile(md):
    warn("  WARN: 未找到 main.tex / sections/*.tex / main.md — caption 未检查（不是合规，是没扫到）")
else:
    warn("  OK: 图注/表注长度合规（已递归跟随 \\input）")

# 7c. Meta-content leak detection
print("--- Meta-content leak check ---")
meta_leaks = 0
for f in sec_files:
    bn = f.name
    leaks = nmatches(r"RESULTS\.md|CLAUDE\.md|MODELING_REPORT|PROBLEM_ANALYSIS|figures/\*\.json|latex_includes|参赛者|参赛队伍|参赛选手", read(f), re.I)
    if leaks > 0:
        fail(f"  FAIL {bn}: {leaks} 处内部指令/文件名泄露到正文")
        meta_leaks += leaks
if meta_leaks == 0:
    warn("  OK: 无元叙述泄露")

# 8. Citation format (multi-cite WARN)
print("--- Citation format ---")
multi_cite = 0
for f in sec_files:
    bn = f.name
    mc = nmatches(r"\\cite\{[^}]*,[^}]*\}", read(f))
    if mc > 0:
        warn(f"  WARN {bn}: {mc} multi-cite instances (\\cite{{a,b,c}}) — split into separate \\cite{{a}}\\cite{{b}}\\cite{{c}}")
        multi_cite += mc
if multi_cite == 0:
    warn("  OK: all citations are single-key")

# 9. Symbol/assumptions page break (WARN only)
print("--- Symbol/assumptions page break ---")
for f in sec_files:
    bn = f.name
    content = read(f)
    lines = content.splitlines()
    section_lines = [i for i, ln in enumerate(lines) if re.search(r"\\section\{", ln)]
    is_target = bool(re.search(r"symbol|assumption", bn, re.I)) or bool(re.search(r"\\section\{符号说明\}|\\section\{模型假设\}", content))
    if not is_target:
        continue
    if re.search(r"\\section\{符号说明\}|\\section.*符号", content):
        ok = any(i >= 1 and re.search(r"\\clearpage", lines[i - 1]) for i in section_lines) if len(section_lines) > 0 else False
        warn("  OK " + bn + ": has \\clearpage before symbol section" if ok else f"  WARN {bn}: missing \\clearpage — compile_utils.sh will auto-fix")
    if re.search(r"\\section\{模型假设\}|\\section.*假设", content):
        pre_ok = any(i >= 1 and re.search(r"\\needspace|\\clearpage", lines[i - 1]) for i in section_lines) if len(section_lines) > 0 else False
        warn("  OK " + bn + ": has page break control" if pre_ok else f"  WARN {bn}: missing \\needspace — compile_utils.sh will auto-fix")

print("=== Writing checks done (exit code: {}) ===".format(0 if EXIT_CODE == 0 else 1))

# ---- 10. 图片尺寸 (WARN only) ----
print("--- 图片尺寸检查 ---")
for f in all_tex:
    content = read(f)
    for m in re.finditer(r"\\includegraphics\[([^\]]*)\]\{([^}]*)\}", content):
        opts, path = m.group(1), m.group(2)
        w = re.search(r"width\s*=\s*([\d.]+)\\textwidth", opts)
        if w:
            val = float(w.group(1))
            if val > 1.0:
                warn(f"  WARN {f.name}: {path} width={val}\\textwidth > 1.0 — 图片溢出页面")
            elif val < 0.3:
                warn(f"  WARN {f.name}: {path} width={val}\\textwidth < 0.3 — 图片可能太小")
        s = re.search(r"scale\s*=\s*([\d.]+)", opts)
        if s:
            val = float(s.group(1))
            if val > 1.2:
                warn(f"  WARN {f.name}: {path} scale={val} > 1.2 — 图片可能溢出")

# ---- 11. 图片文件存在性 (FAIL) ----
print("--- 图片文件存在性检查 ---")
missing_figs = 0
for f in all_tex:
    content = read(f)
    for m in re.finditer(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", content):
        figpath = m.group(1)
        resolved = ""
        for try_path in (PAPER_DIR / figpath, Path(figpath), figs_dir / Path(figpath).name):
            if try_path.is_file():
                resolved = try_path
                break
        if not resolved:
            fail(f"  FAIL {f.name}: 引用的图片不存在: {figpath}")
            missing_figs += 1
if missing_figs == 0:
    warn("  OK: 所有引用的图片文件都存在")

# ---- 12. 空图表环境 (print FAIL, 不 gate,faithful to .sh) ----
print("--- 空图表环境检查 ---")
for f in all_tex:
    content = read(f)
    for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", content, re.DOTALL):
        block = m.group()
        if not (("includegraphics" in block) or ("tikzpicture" in block) or ("\\input" in block)):
            cap = re.search(r"\\caption\{([^}]{0,50})", block)
            cap_text = cap.group(1) if cap else "(no caption)"
            print(f"  FAIL {f.name}: 空 figure 环境 \"{cap_text}\" — 缺少 includegraphics")
    for m in re.finditer(r"\\begin\{table\}.*?\\end\{table\}", content, re.DOTALL):
        block = m.group()
        if ("tabular" not in block and "longtable" not in block and "\\input" not in block):
            cap = re.search(r"\\caption\{([^}]{0,50})", block)
            cap_text = cap.group(1) if cap else "(no caption)"
            print(f"  FAIL {f.name}: 空 table 环境 \"{cap_text}\" — 缺少 tabular")

# ---- 13. 图表浮动位置 (WARN only) ----
print("--- 图表浮动位置检查 ---")
float_issues = 0
for f in sec_files:
    content = read(f)
    no_pos = nmatches(r"\\begin\{figure\}\s*$", content, re.M)
    if no_pos > 0:
        warn(f"  WARN {f.name}: {no_pos} 个 figure 环境没有位置参数 — 建议加 [H] 或 [htbp]")
        float_issues += no_pos
    no_pos_t = nmatches(r"\\begin\{table\}\s*$", content, re.M)
    if no_pos_t > 0:
        warn(f"  WARN {f.name}: {no_pos_t} 个 table 环境没有位置参数 — 建议加 [H] 或 [htbp]")
        float_issues += no_pos_t
if float_issues == 0:
    warn("  OK: 所有图表都有浮动位置参数")

# 15. 图文数值一致性检查 (WARN only)
print("--- 图文数值一致性检查 ---")
consistency_issues = 0
for f in sec_files:
    bn = f.name
    content = read(f)
    fig_claims = re.findall(r"\d+\.\d+", "\n".join(
        [ln for i, ln in enumerate(content.splitlines()) if re.search(r"\\ref\{fig", ln)]))[:20]
    results_joined = read(Path("RESULTS.md")) if Path("RESULTS.md").is_file() else ""
    json_files = " ".join(read(p) for p in (figs_dir.glob("*.json") if figs_dir.is_dir() else []))
    if fig_claims:
        not_found = sum(1 for num in fig_claims if num not in results_joined and num not in json_files)
        if not_found > 0:
            warn(f"  WARN {bn}: {not_found} 个数值在 \\ref{{fig}} 附近但不在 RESULTS.md/JSON 中")
            consistency_issues += not_found
if consistency_issues == 0:
    warn("  OK: 图文数值一致性通过")

# NEW: 数值一致性 (print-only)
print("--- 数值一致性检查 ---")
json_path = figs_dir / "all_results.json"
if json_path.is_file():
    try:
        import json
        results = json.loads(read(json_path))
    except Exception:
        results = None
    if results:
        def extract_numbers(obj, prefix=""):
            nums = {}
            if isinstance(obj, dict):
                for k, v in obj.items():
                    nums.update(extract_numbers(v, f"{prefix}.{k}"))
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    nums.update(extract_numbers(v, f"{prefix}[{i}]"))
            elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
                if abs(obj) > 0.001 and abs(obj) < 1e10:
                    nums[prefix] = obj
            return nums

        json_nums = extract_numbers(results)
        if json_nums:
            paper_nums = set()
            for f in sec_files:
                text = read(f)
                for m in re.finditer(r"(?<![a-zA-Z])(\d+\.?\d+)(?![a-zA-Z_{}])", text):
                    try:
                        paper_nums.add(float(m.group(1)))
                    except ValueError:
                        pass
            missing = 0
            for key, val in json_nums.items():
                found = any(abs(pn - val) < abs(val) * 0.01 + 0.001 for pn in paper_nums)
                if not found and "round" not in key.lower() and "time" not in key.lower():
                    if any(kw in key.lower() for kw in ["rmse", "r2", "mse", "accuracy", "f1", "auc", "objective", "optimal", "best", "result", "score"]):
                        print(f"  ⚠ JSON {key}={val} 未在论文中找到匹配数值")
                        missing += 1
            print(f"  共 {missing} 个关键数值可能不一致" if missing > 0 else "  ✅ 关键数值一致性检查通过")
        else:
            print("  (JSON 中无有效数值，跳过)")
    else:
        print("  (JSON 解析失败，跳过)")
else:
    print("  (figures/all_results.json 不存在，跳过)")

# NEW: 过度声称 (print-only)
print("--- 过度声称检测 ---")
OVERCLAIM = 0
for f in sec_files:
    bn = f.name
    content = read(f)
    for word in ["首次提出", "首次发现", "完美", "最优的", "最好的", "证明了", "无可比拟", "前所未有", "开创性", "革命性"]:
        count = nmatches(re.escape(word), content)
        if count > 0:
            print(f"  ⚠ {bn}: 发现过度声称 \"{word}\" ({count} 次) — 建议改为更谨慎的表述")
            OVERCLAIM += count
if OVERCLAIM == 0:
    print("  ✅ 无过度声称")

# NEW: 内容覆盖度 (info only)
print("--- 内容覆盖度检查 ---")
if Path("PROBLEM_ANALYSIS.md").is_file():
    _count_sh = Path(__file__).resolve().parent / "count_subproblems.py"
    if _count_sh.is_file():
        try:
            r = subprocess.run([sys.executable, str(_count_sh), "PROBLEM_ANALYSIS.md"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            PROB_COUNT = int((r.stdout or "0").strip().split()[-1] if (r.stdout or "").strip() else 0)
        except Exception:
            PROB_COUNT = nmatches(r"问题[一二三四五六七八九十]", read(Path("PROBLEM_ANALYSIS.md")))
    else:
        PROB_COUNT = nmatches(r"问题[一二三四五六七八九十]", read(Path("PROBLEM_ANALYSIS.md")))
    CHAPTER_COUNT = 0
    for f in sec_files:
        if re.search(r"\\section\{.*问题[一二三四五六七八九十0-9]|\\section\{.*Problem", read(f)):
            CHAPTER_COUNT += 1
    print(f"  赛题子问题数: {PROB_COUNT}, 字面含【问题N】的章节数: {CHAPTER_COUNT}（描述性标题不计入属正常，不阻断）")
    if CHAPTER_COUNT < PROB_COUNT:
        print("  ℹ 提示：字面含'问题N'的章节少于子问题数——若用了描述性标题属正常；请自查每个子问题都有对应章节（硬核对见 capability_check）")

# NEW: 引用完整性 (print-only)
print("--- 引用完整性检查 ---")
if bib.is_file():
    CITED = set()
    for f in all_tex:
        for m in re.finditer(r"\\cite\{([^}]*)\}", read(f)):
            for k in m.group(1).split(","):
                CITED.add(k.strip())
    BIB_KEYS = set(re.findall(r"^\s*@\w+\{([^,]+)", read(bib), re.M))
    MISSING_BIB = [k for k in CITED if k not in BIB_KEYS]
    if MISSING_BIB:
        for k in MISSING_BIB:
            print(f"  ⚠ \\cite{{{k}}} 在 references.bib 中无对应条目")
    else:
        print("  ✅ 所有引用都有对应 bib 条目")
elif main_tex.is_file() and re.search(r"thebibliography", main_content):
    print("  (使用 thebibliography 环境，跳过 bib 文件检查)")
else:
    print("  ⚠ 未找到 references.bib")

print("")
print(f"=== Writing check complete (exit={EXIT_CODE if EXIT_CODE in (0, 1) else 1}) ===")
raise SystemExit(EXIT_CODE if EXIT_CODE in (0, 1) else 1)
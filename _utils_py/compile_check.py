#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""compile_check.py — Post-compilation quality checks(pure-stdlib 版,对齐 _utils/compile_check.sh)。

用法:
    python compile_check.py [paper/]

退出码: 0=通过  1=失败(需修复)  2=跳过。run_check 约定 {0,2}=通过。
逻辑与 .sh 一致:PDF 存在/质量、未定义引用、LaTeX 错误、模板完整性、文献、
引用顺序/合并、图引用、堆叠、重复 label、禁 \\cref 等。
"""
import re
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


sec_files = list(sorted((PAPER_DIR / "sections").glob("*.tex"))) if (PAPER_DIR / "sections").is_dir() else []
main_tex = PAPER_DIR / "main.tex"
main_log = PAPER_DIR / "main.log"
# 论文产物尚不存在(paper 步未跑)→不可检查,跳过不阻断{0,2}
if not main_tex.is_file() and not sec_files:
    print(f"SKIP: {PAPER_DIR} 无任何 .tex 产物（paper 步未跑）(exit 2)")
    raise SystemExit(2)
all_tex = sec_files + ([main_tex] if main_tex.is_file() else [])

print(f"=== Post-compile checks ({PAPER_DIR}) ===")

# 1. PDF existence and size
pdf = PAPER_DIR / "main.pdf"
if pdf.is_file():
    pdf_size = pdf.stat().st_size
    print(f"  OK: main.pdf exists ({pdf_size} bytes)")
    if pdf_size < 100000:
        fail("  FAIL: PDF is small (<100KB), compilation likely failed")
else:
    fail("  FAIL: main.pdf not found")

log = read(main_log)

# 2. Undefined references
undef_refs = nmatches(r"\['?'\]", log)
print(f"  Undefined references: {undef_refs}")
if undef_refs > 0:
    fail(f"  FAIL: {undef_refs} undefined references — PDF shows [?]")

# 2.5 LaTeX compilation errors (CRITICAL — must fix before accepting)
print("--- LaTeX errors ---")
LATEX_ERRORS = 0
if log:
    bad_math = nmatches(r"Bad math environment delimiter|Missing \$ inserted|Display math should end|begin\{document\} ended by", log)
    warn(f"  CRITICAL: {bad_math} math environment errors — fix $...$ delimiters in .tex files"); LATEX_ERRORS += bad_math
    lr_mode = nmatches(r"Not allowed in LR mode|Not in outer par mode", log)
    warn(f"  CRITICAL: {lr_mode} LR mode errors — check math/float placement"); LATEX_ERRORS += lr_mode
    undef_cs = nmatches(r"Undefined control sequence", log)
    warn(f"  WARN: {undef_cs} undefined control sequences")
    missing_pkg = re.findall(r"File .* not found\.|LaTeX Error: File .* not found", log)[:5]
    if missing_pkg:
        warn("  CRITICAL: missing packages:")
        for m in missing_pkg[:5]:
            warn("    " + m)
        LATEX_ERRORS += 1
    font_err = nmatches(r"Font.*not found|cannot find font", log)
    warn(f"  WARN: {font_err} font errors (check fc-list)")
    if LATEX_ERRORS > 0:
        print("")
        warn("  ============================================================")
        warn(f"  CRITICAL: {LATEX_ERRORS} LaTeX errors found — MUST FIX")
        warn("  ============================================================")
        warn("  Error locations (from main.log):")
        lines = log.splitlines()
        for i, ln in enumerate(lines):
            if re.search(r"Bad math|Missing \$ inserted|begin\{document\} ended|Not allowed in LR mode", ln):
                for j in range(max(0, i - 1), min(len(lines), i + 2)):
                    if re.match(r"^\./|^l\.", lines[j]):
                        warn("    " + lines[j].strip())
        warn("  ============================================================")
        print("")
        EXIT_CODE = 1

# 3. Overfull hbox
overfull = nmatches(r"Overfull.*hbox", log)
print(f"  Overfull hbox: {overfull}")

# 3.5 Overfull vbox
overfull_v = nmatches(r"Overfull.*vbox", log)
if overfull_v > 0:
    fail(f"  FAIL: {overfull_v} overfull vbox — tables/figures cut off at page bottom")
    warn("  Fix: use longtable for tall tables, or split into smaller tables")

# 3.6 Tall table detection
print("--- Tall table check ---")
for f in (sec_files + [main_tex]):
    if not f.is_file():
        continue
    bn = f.name
    if re.search(r"appendix|附录|A_code", bn, re.I):
        continue
    content = read(f)
    tt = False
    for m in re.finditer(r"\\begin\{tabular\}.*?\\end\{tabular\}", content, re.DOTALL):
        block = m.group()
        rows = block.count(r"\\")
        if rows > 20:
            start = max(0, m.start() - 200)
            before = content[start:m.start()]
            cap = re.search(r"\\caption\{([^}]{0,50})", before)
            cap_text = cap.group(1) if cap else "(unknown)"
            fail(f'  FAIL: {bn} has {rows}-row table "{cap_text}" — must truncate to top5+bottom3, full table in appendix')
            tt = True

# 4. TOC generation
if main_tex.is_file() and re.search(r"tableofcontents", read(main_tex)):
    toc = PAPER_DIR / "main.toc"
    if toc.is_file() and toc.stat().st_size > 0:
        print("  OK: TOC generated")
    else:
        fail("  FAIL: TOC empty or missing")

# 6. Bibliography + template integrity
if main_tex.is_file():
    main_content = read(main_tex)
    print("--- Template integrity (auto-detect) ---")
    TMPL_TYPE = "unknown"
    if re.search(r"cumcmthesis", main_content):
        TMPL_TYPE = "cumcm"
    if re.search(r"gmcmthesis", main_content):
        TMPL_TYPE = "huawei"
    if re.search(r"MathorCupmodeling", main_content):
        TMPL_TYPE = "mathorcup"
    if re.search(r"JXUSTmodeling", main_content):
        TMPL_TYPE = "huashubei"
    if re.search(r"yrdmcm", main_content):
        TMPL_TYPE = "changsanjiao"
    if re.search(r"neepumcm", main_content):
        TMPL_TYPE = "diangongbei"
    if re.search(r"nemcmthesis", main_content):
        TMPL_TYPE = "dongsansheng"
    if re.search(r"mcmthesis", main_content) and TMPL_TYPE == "unknown":
        TMPL_TYPE = "mcm"
    if re.search(r"apmcmthesis", main_content):
        TMPL_TYPE = "apmcm"
    if re.search(r"统计建模|natbib.*numbers.*square.*super|listoftables", main_content, re.I):
        TMPL_TYPE = "stats"
    if TMPL_TYPE == "cumcm" and re.search(r"withoutpreface", main_content) and re.search(r"五一", main_content):
        TMPL_TYPE = "wuyi"
    if TMPL_TYPE == "cumcm" and re.search(r"withoutpreface", main_content) and not re.search(r"五一", main_content):
        TMPL_TYPE = "huazhong"
    print(f"  Detected template: {TMPL_TYPE}")

    # Package conflict check (all templates)
    print("--- Package conflict check ---")
    if re.search(r"\\usepackage\{cite\}", main_content) and re.search(r"\\usepackage.*\{natbib\}", main_content):
        fail("  CRITICAL: cite + natbib both loaded — these packages CONFLICT, remove \\usepackage{cite}")
    for pkg in ("subcaption", "float", "graphicx", "booktabs", "caption"):
        if re.search(r"\\usepackage.*\{.*" + pkg + r".*\}", main_content):
            if TMPL_TYPE in ("cumcm", "wuyi", "huazhong") and pkg in ("subcaption", "float", "graphicx", "booktabs"):
                warn(f"  WARN: {pkg} duplicated (cls already loads it)")
            elif TMPL_TYPE == "huashubei" and pkg in ("subcaption", "caption", "booktabs", "graphicx"):
                warn(f"  WARN: {pkg} duplicated (cls already loads it)")
            elif TMPL_TYPE in ("changsanjiao", "diangongbei") and pkg in ("graphicx", "booktabs"):
                warn(f"  WARN: {pkg} duplicated (cls already loads it)")

    # Per-template specific checks
    wuyi = TMPL_TYPE == "wuyi"
    if wuyi:
        print("--- 五一杯 specific checks ---")
        if re.search(r"承诺书", main_content):
            warn("  OK: 承诺书页存在")
        else:
            fail("  CRITICAL: 五一杯缺少承诺书页")
        if re.search(r"image2", main_content):
            warn("  OK: 封面 logo (image2) 存在")
        else:
            fail("  CRITICAL: 五一杯缺少封面 logo")
        if re.search(r"关键词", main_content):
            warn("  OK: 关键词位置存在")
        else:
            fail("  CRITICAL: 五一杯缺少关键词")
        if re.search(r"withoutpreface", main_content):
            warn("  OK: withoutpreface 选项存在")
        else:
            fail("  CRITICAL: 缺少 withoutpreface（会出现国赛承诺书）")
        if re.search(r"\\maketitle", main_content):
            fail("  CRITICAL: 五一杯不应有 \\maketitle（会和手写承诺书冲突）")
        else:
            warn("  OK: 无 \\maketitle")
        if re.search(r"五一数学建模竞赛", main_content):
            warn("  OK: 五一杯标题存在")
        else:
            fail("  CRITICAL: 缺少'五一数学建模竞赛'标题 — main.tex 可能被重写了")
        if any((PAPER_DIR / "image2.png").is_file(), (PAPER_DIR / "image2.jpg").is_file(), Path("figures/image2.png").is_file()):
            warn("  OK: image2 图片文件存在")
        else:
            fail("  CRITICAL: image2 图片文件不存在 — 封面 logo 会显示为空")
    elif TMPL_TYPE == "huazhong":
        print("--- 华中杯 specific checks ---")
        if re.search(r"cumcmthesis", main_content):
            warn("  OK: 使用 cumcmthesis cls")
        else:
            fail("  CRITICAL: 华中杯未使用 cumcmthesis")
        if re.search(r"withoutpreface", main_content):
            warn("  OK: withoutpreface 选项存在")
        else:
            fail("  CRITICAL: 缺少 withoutpreface")
        if re.search(r"\\begin\{abstract\}", main_content):
            warn("  OK: 使用 abstract 环境")
        else:
            warn("  WARN: 华中杯应使用 \\begin{abstract} 环境")
        if re.search(r"thebibliography", main_content):
            warn("  OK: 使用 thebibliography")
        else:
            warn("  WARN: 华中杯应使用 thebibliography 环境")
    elif TMPL_TYPE == "mathorcup":
        print("--- MathorCup specific checks ---")
        if re.search(r"MathorCupmodeling", main_content):
            warn("  OK: 使用 MathorCupmodeling cls")
        else:
            fail("  CRITICAL: MathorCup 未使用正确 cls")
        if re.search(r"\\bianhao|\\tihao|\\timu", main_content):
            warn("  OK: 队伍信息命令存在")
        else:
            fail("  CRITICAL: MathorCup 缺少队伍信息")
        if re.search(r"\\maketitle", main_content):
            fail("  CRITICAL: MathorCup 不应有独立封面 \\maketitle")
        else:
            warn("  OK: 无独立封面")
    elif TMPL_TYPE == "stats":
        print("--- 统计建模 specific checks ---")
        if re.search(r"listoftables", main_content):
            warn("  OK: \\listoftables present")
        else:
            fail("  CRITICAL: \\listoftables missing — template was rewritten!")
        if re.search(r"listoffigures", main_content):
            warn("  OK: \\listoffigures present")
        else:
            fail("  CRITICAL: \\listoffigures missing — template was rewritten!")
        if re.search(r"cline\{2-2\}", main_content):
            warn("  OK: cover page \\cline present")
        else:
            warn("  WARN: cover page \\cline missing")
        if re.search(r"^(表|图)\d+\.", main_content, re.M)[:3] and len(re.findall(r"^(表|图)\d+\.", main_content, re.M)) > 0:
            fail("  CRITICAL: hand-written figure/table list detected — must use \\listoftables/\\listoffigures")
    elif TMPL_TYPE == "dongsansheng":
        print("--- 东三省 specific checks ---")
        if re.search(r"nemcmthesis", main_content):
            warn("  OK: 使用 nemcmthesis cls")
        else:
            fail("  CRITICAL: 未使用 nemcmthesis")
        if re.search(r"\\ttle|\\title", main_content):
            warn("  OK: 标题命令存在")
        else:
            warn("  WARN: 缺少标题")
        if re.search(r"\\makecoverpage", main_content):
            warn("  OK: 封面生成命令存在")
        else:
            warn("  WARN: 缺少 \\makecoverpage")
    elif TMPL_TYPE == "huawei":
        print("--- 华为杯 specific checks ---")
        if re.search(r"gmcmthesis", main_content):
            warn("  OK: 使用 gmcmthesis cls")
        else:
            fail("  CRITICAL: 华为杯未使用 gmcmthesis")
    else:
        warn(f"  (no template-specific checks for {TMPL_TYPE})")

    # Bibliography: \bibliography OR inline thebibliography
    if re.search(r"\\bibliography\{|\\begin\{thebibliography\}", main_content):
        warn("  OK: bibliography present (\\bibliography 或 thebibliography)")
    else:
        fail("  FAIL: no \\bibliography / thebibliography in main.tex")
    if re.search(r"\\begin\{thebibliography\}", main_content):
        inline_items = nmatches(r"\\bibitem", main_content)
        if inline_items > 0:
            warn(f"  OK: inline thebibliography ({inline_items} entries)")
        else:
            fail("  FAIL: inline thebibliography 为空（无 \\bibitem）")
    else:
        bib = PAPER_DIR / "references.bib"
        if bib.is_file():
            bib_entries = nmatches(r"^@", read(bib), re.M)
            warn(f"  OK: references.bib ({bib_entries} entries)")
        else:
            fail("  FAIL: references.bib not found")
        bbl_entries = nmatches(r"\\bibitem", read(PAPER_DIR / "main.bbl"))
        print(f"  Bibliography entries in PDF: {bbl_entries}")
        if bbl_entries == 0:
            fail("  FAIL: bibliography is empty in compiled PDF")

# 7. Citation count in body
cite_count = 0
for f in all_tex:
    cite_count += nmatches(r"\\[a-z]*cite[a-z]*\{", read(f))
print(f"  Citations in body: {cite_count}")
if cite_count == 0:
    fail("  FAIL: no citations in body text")

# 7.5 Citation format check
print("--- Citation format check ---")
if main_tex.is_file():
    main_content = read(main_tex)
    if re.search(r"\\bibliographystyle\{gbt7714|plainnat.*super|natbib.*super", main_content):
        warn("  OK: 使用上标引用样式 (gbt7714-numerical / natbib super)")
    elif re.search(r"\\bibliographystyle\{plainnat\}|\\bibliographystyle\{plain\}|\\bibliographystyle\{unsrt\}", main_content):
        upcite_count = sum(nmatches(r"\\upcite\{|\\textsuperscript\{\\cite", read(f)) for f in all_tex)
        plain_cite_count = sum(nmatches(r"[^t]\\cite\{", read(f)) for f in all_tex)
        if upcite_count == 0 and plain_cite_count > 0:
            fail(f"  FAIL: {plain_cite_count} citations not using superscript format")
            warn("  Fix: 改用 \\bibliographystyle{gbt7714-numerical} 或把 \\cite{x} 改为 \\upcite{x} / \\textsuperscript{\\cite{x}}")
        else:
            warn(f"  OK: citations use superscript ({upcite_count} superscript, {plain_cite_count} plain)")

# 7.5.2 Citation order and merging
print("--- Citation order and merging ---")
cite_order_global = []
all_errors = []
cite_warns = []
prev_max_num = 0
for f in all_tex:
    if not f.is_file():
        continue
    content = read(f)
    for m in re.finditer(r"\\(up)?cite\{([^}]+)\}", content):
        keys = [k.strip() for k in m.group(2).split(",")]
        for k in keys:
            if k not in cite_order_global:
                cite_order_global.append(k)
for f in all_tex:
    if not f.is_file():
        continue
    content = read(f)
    for m in re.finditer(r"\\(up)?cite\{([^}]+)\}", content):
        keys = [k.strip() for k in m.group(2).split(",")]
        nums = [cite_order_global.index(k) + 1 if k in cite_order_global else 999 for k in keys]
        line_num = content[:m.start()].count("\n") + 1
        snippet = m.group(0)
        if len(nums) > 1 and nums != sorted(nums):
            all_errors.append(f'  FAIL {f.name}:{line_num}: 多引用编号不是升序 {nums}: {snippet}')
        cur_max = max(nums) if nums else 0
        new_nums = [n for n in nums if n > prev_max_num]
        if new_nums and min(new_nums) > prev_max_num + 1:
            cite_warns.append(f'  WARN {f.name}:{line_num}: 引用编号跳跃 (之前最大={prev_max_num}, 新引用最小={min(new_nums)}): {snippet}')
        prev_max_num = max(prev_max_num, cur_max)
if cite_warns:
    print("\n".join(cite_warns[:10]))
if all_errors:
    print("\n".join(all_errors[:15]))
    if len(all_errors) > 15:
        print(f"  ... and {len(all_errors)-15} more")
    EXIT_CODE = 1
else:
    warn("  OK: 引用编号全局递增且多引用内部升序")

# 7.5.3 Consecutive citation merging (WARN only)
print("--- Consecutive citation merging ---")
for f in sec_files:
    content = read(f)
    consec = nmatches(r"\\(up)?cite\{[^}]+\}[\s]*\\(up)?cite\{[^}]+\}", content)
    if consec > 0:
        warn(f"  WARN {f.name}: {consec} consecutive \\cite{{}} should merge to \\cite{{a,b}}")

# 8. Unused PDF figures (WARN only)
print("--- Unused figures ---")
unused = 0
figs_dir = Path("figures")
if figs_dir.is_dir():
    for pdf in sorted(figs_dir.glob("*.pdf")):
        bn = pdf.name
        joined = "\n".join(read(f) for f in all_tex)
        if bn not in joined:
            warn(f"  WARN: {bn} not referenced")
            unused += 1
if unused == 0:
    warn("  OK: all figures referenced")

# 8.5 Missing figure files (referenced but not found)
print("--- Missing figure files ---")
missing = 0
for f in all_tex:
    if not f.is_file():
        continue
    content = read(f)
    for m in re.finditer(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", content):
        figpath = m.group(1)
        resolved = ""
        for try_path in (PAPER_DIR / figpath, Path(figpath), figs_dir / Path(figpath).name):
            if try_path.is_file():
                resolved = try_path
                break
        if not resolved:
            fail(f"  FAIL {f.name}: missing figure: {figpath}")
            missing += 1
if missing == 0:
    warn("  OK: all referenced figures exist")

# 8.6 Empty figure/table environments (print but non-blocking, faithful to .sh)
print("--- Empty figure/table environments ---")
for f in all_tex:
    if not f.is_file():
        continue
    content = read(f)
    for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", content, re.DOTALL):
        block = m.group()
        if "includegraphics" not in block and "tikzpicture" not in block and "\\input" not in block:
            cap = re.search(r"\\caption\{([^}]{0,50})", block)
            cap_text = cap.group(1) if cap else "(no caption)"
            print(f'  FAIL {f.name}: empty figure "{cap_text}"')
    for m in re.finditer(r"\\begin\{table\}.*?\\end\{table\}", content, re.DOTALL):
        block = m.group()
        if "tabular" not in block and "longtable" not in block and "\\input" not in block:
            cap = re.search(r"\\caption\{([^}]{0,50})", block)
            cap_text = cap.group(1) if cap else "(no caption)"
            print(f'  FAIL {f.name}: empty table "{cap_text}"')

# 9. Figure stacking (awk state machine)
print("--- Figure stacking ---")


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
        if a and t >= 3:
            a = 0
    return c


total_stacking = 0
for f in sec_files:
    bn = f.name
    count = stacking_count(read(f))
    if count > 0:
        fail(f"  FAIL: {bn} has {count} figure stacking violations — add analysis text between figures")
    total_stacking += count
if total_stacking == 0:
    warn("  OK: no figure stacking")

# 9.5 Subfigure abuse and small figure width
print("--- Subfigure / small figure check ---")
subfig_abuse = 0
small_width = 0
for f in sec_files:
    bn = f.name
    content = read(f)
    sf_count = nmatches(r"\\begin\{subfigure\}", content)
    if sf_count > 0:
        fail(f"  FAIL: {bn} uses subfigure ({sf_count} times) — competition papers must use independent figure environments, not subfigure")
        subfig_abuse += sf_count
    small = [float(x) for x in re.findall(r"width\s*=\s*(\d+\.\d+)\\textwidth", content) if float(x) < 0.7]
    if small:
        fail(f"  FAIL: {bn} has {len(small)} figures with width < 0.7\\textwidth — figures too small, use ≥ 0.85\\textwidth")
        small_width += len(small)
if subfig_abuse == 0 and small_width == 0:
    warn("  OK: no subfigure abuse or small figures")

# 10. TikZ architecture diagram check (against plan)
tikz_exists = "YES" if (figs_dir / "tikz_architecture_examples.tex").is_file() and (figs_dir / "tikz_architecture_examples.tex").stat().st_size > 0 else "NO"
print(f"  TikZ architecture diagram: {tikz_exists}")
if tikz_exists == "NO":
    for plan in ("PAPER_PLAN.md", "PROBLEM_ANALYSIS.md", "TOPIC_PLAN.md"):
        p = Path(plan)
        if p.is_file() and re.search(r"tikz|架构图|技术路线|研究框架|流程图|关系图|architecture.*diagram|roadmap|framework.*diagram", read(p), re.I):
            warn("  WARN: plan mentions TikZ diagrams but figures/tikz_architecture_examples.tex not found")
            break

# 11. Title existence check
print("--- Title check ---")
if main_tex.is_file():
    main_content = read(main_tex)
    if re.search(r"\\title\{", main_content):
        title = re.search(r"\\title\{(.*?)\}", main_content, re.S)
        title_content = title.group(1) if title else ""
        title_clean = re.sub(r"\\[a-zA-Z]*\{[^}]*\}", "", title_content)
        title_clean = re.sub(r"\\[a-zA-Z]*", "", title_clean)
        title_clean = re.sub(r"\s", "", title_clean)
        if not title_clean:
            fail("  FAIL: \\title{} is empty — PDF has no title")
        else:
            warn("  OK: title present")
    elif re.search(r"\\timu\{|\\ttle\{|\\biaoti\{", main_content):
        warn("  OK: title present (non-standard command)")
    elif re.search(r"MathorCup|nemcmthesis|JXUSTmodeling|neepumcm", main_content):
        warn("  OK: special template (title in cls-specific command)")
    else:
        fail("  FAIL: no \\title command found — PDF has no title")

# 12. Symbol/assumptions page break (WARN only)
print("--- Symbol/assumptions page break ---")
for f in sec_files:
    bn = f.name
    content = read(f)
    is_target = bool(re.search(r"symbol|assumption", bn, re.I)) or bool(re.search(r"\\section\{符号说明\}|\\section\{模型假设\}", content))
    if not is_target:
        continue
    lines = content.splitlines()
    section_lines = [i for i, ln in enumerate(lines) if re.search(r"\\section\{", ln)]
    if re.search(r"\\section\{符号说明\}|\\section.*符号", content):
        ok = any(i >= 1 and re.search(r"\\clearpage", lines[i - 1]) for i in section_lines)
        warn(f"  OK: {bn} has \\clearpage before \\section" if ok else f"  WARN {bn}: missing \\clearpage before symbol section — title and table may split. Re-run compile_utils.sh.")
        if re.search(r"\\begin\{table\}\[H\]", content):
            warn(f"  WARN {bn}: table uses [H] — may cause title-table split. Should be [htbp].")
    if re.search(r"\\section\{模型假设\}|\\section.*假设", content):
        pre_ok = any(i >= 1 and re.search(r"\\needspace|\\clearpage", content.splitlines()[i - 1]) for i in section_lines)
        post_ok = any(i + 1 < len(content.splitlines()) and re.search(r"\\nopagebreak", content.splitlines()[i + 1]) for i in section_lines)
        warn(f"  OK: {bn} has page break control before \\section" if pre_ok else f"  WARN {bn}: missing \\needspace before assumption section. Re-run compile_utils.sh.")
        warn(f"  OK: {bn} has \\nopagebreak after \\section" if post_ok else f"  WARN {bn}: missing \\nopagebreak after assumption section.")

# N. Duplicate labels — hard FAIL (silent misnumbering root cause)
print("--- 重复 label 检测 ---")
labels = []
for f in all_tex:
    labels += re.findall(r"\\label\s*\{([^}]*)\}", read(f))
dups = Counter(labels)
dup_hits = {k: v for k, v in dups.items() if v >= 2}
if dup_hits:
    print("  FAIL: 重复 label（同一个 \\label 贴了多次，会导致图/表号静默错乱）:")
    for name, c in sorted(dup_hits.items()):
        print(f"    {name} (x{c})")
    warn("    修复：每个图/表块只嵌入一次，删掉重复的 \\begin{figure}/\\begin{table} 块。")
    EXIT_CODE = 1
else:
    warn("  OK: 无重复 label")

# N+1. \cref/\Cref/\autoref forbidden (duplicates "图" prefix)
print("--- 禁用 \\cref（防\"图 图1\"前缀重复）---")
cref_hits = []
for f in all_tex:
    for m in re.finditer(r"\\(cref|Cref|autoref)\{", read(f)):
        cref_hits.append(f"{f.name}:{read(f)[:m.start()].count(chr(10)) + 1}:{m.group(0)}")
if cref_hits:
    print("  FAIL: 正文用了 \\cref/\\Cref/\\autoref（模板会自动补\"图\"字 → 输出\"图 图1\"）:")
    for h in cref_hits:
        print("    " + h)
    warn('    修复：全部改成 \\ref{}，"图/表"字手写在前面（如 图~\\ref{fig:x}）。')
    EXIT_CODE = 1
else:
    warn('  OK: 正文未使用 \\cref（前缀由手写"图/表"+\\ref 保证，无重复）')

print(f"=== All checks done (exit code: {EXIT_CODE}) ===")
raise SystemExit(EXIT_CODE if EXIT_CODE in (0, 1) else 1)
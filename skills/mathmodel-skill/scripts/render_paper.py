"""
render_paper.py — markdown 中间产物 → 最终 PDF (v3.1 国赛版)

功能:
1. 读 stage 8 各节 markdown 产出 (<cwd>/paper_workspace/)
2. 按 competition 选择 LaTeX 模板与编译器:
   - mathmodel:    templates/latex/mathmodel/main.tex      + xelatex
3. md → tex (正式编译使用 Pandoc；手工正则只供 structural dry-run)
4. 三编生成 PDF

用法:
    python <skill>/scripts/render_paper.py --competition mathmodel --workspace paper_workspace/
    python scripts/render_paper.py --competition mathmodel --workspace ws/ --output-dir out/ \
      --title "Paper Title" \
      --keywords "optimization, robustness, simulation"
    python scripts/render_paper.py --competition mathmodel --workspace ws/ --no-compile  (dry-run)
"""

import argparse
import json
import os
import re
import subprocess
import shutil
from pathlib import Path


_SKILL_ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_MAP = {
    "mathmodel": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "mathmodel",
        "engine": "xelatex",
        "main_filename": "main.tex",
        "mode": "main_template",
        "_doc": "mathmodel 使用仓库原创 ctexart 电子论文模板与 section marker 装配",
    },
}


SECTION_TO_FILE = {
    "abstract": "01_abstract.md",
    "1_problem_restate": "02_problem_restate.md",
    "2_problem_analysis": "03_analysis.md",
    "3_assumptions": "04_assumptions.md",
    "4_notation": "05_notation.md",
    "5_models": "06_models.md",
    "6_sensitivity": "07_sensitivity.md",
    "7_evaluation": "08_evaluation.md",
    "8_references": "09_references.md",
    "appendix_code": "10_appendix.md",
}

MATHMODEL_NO_AI_FILENAME = "AI工具未使用声明.md"
OPTIONAL_SECTION_TO_FILE = {
    "mathmodel_no_ai_statement": MATHMODEL_NO_AI_FILENAME,
}

SECTION_MARKER_RE = re.compile(r"^\s*%\s*MATHMODEL:SECTION\s+([A-Za-z0-9_]+)\s*$", re.MULTILINE)
OPTIONAL_BLOCK_RE = re.compile(
    r"^[ \t]*%\s*MATHMODEL:OPTIONAL\s+(?P<name>[A-Za-z0-9_]+)\s+BEGIN\s*$\n"
    r"(?P<body>.*?)"
    r"^[ \t]*%\s*MATHMODEL:OPTIONAL\s+(?P=name)\s+END\s*$\n?",
    re.MULTILINE | re.DOTALL,
)

PAPER_FIELD_TOKENS = {
    "mathmodel": {
        "title": "MATHMODEL_TITLE",
        "keywords": "MATHMODEL_KEYWORDS",
    },
}

PAPER_FIELD_LABELS = {
    "problem": "problem/题号",
    "title": "title/论文题目",
    "keywords": "keywords/关键词",
}

_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


# ============================================================================
# 路径与配置
# ============================================================================

def resolve_competition(cli_arg: str = None, decision_log_path: Path = None) -> str:
    """优先级: CLI > env MATHMODEL_COMPETITION > decision_log.competition > 'mathmodel'"""
    if cli_arg:
        return cli_arg
    env = os.environ.get("MATHMODEL_COMPETITION")
    if env:
        return env
    if decision_log_path and decision_log_path.exists():
        try:
            with open(decision_log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
            if log.get("competition"):
                return log["competition"]
        except (json.JSONDecodeError, KeyError):
            pass
    return "mathmodel"


def resolve_decision_log_path(workspace: Path, explicit_path: str = None) -> Path:
    """Bind state to the user's workspace before falling back to the process cwd."""
    if explicit_path:
        return Path(explicit_path)
    candidates = (
        workspace.resolve().parent / "state" / "decision_log.json",
        Path.cwd() / "state" / "decision_log.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def load_decision_log(path: Path, required: bool = False) -> dict:
    """Load render state strictly; an existing but malformed state is never ignored."""
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"decision log {path} 不存在")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"decision log {path} 无法读取或不是合法 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"decision log {path} 根节点必须是 object")
    return value


def resolve_paper_metadata(decision_log: dict = None, overrides: dict = None) -> dict:
    """Resolve final-paper metadata with explicit CLI values taking precedence."""
    decision_log = decision_log or {}
    overrides = overrides or {}
    paper_metadata = decision_log.get("paper_metadata") or {}
    if not isinstance(paper_metadata, dict):
        raise ValueError("decision_log.paper_metadata 必须是 object")
    problem_meta = decision_log.get("problem_meta") or {}
    if not isinstance(problem_meta, dict):
        raise ValueError("decision_log.problem_meta 必须是 object")

    def choose(key: str, *fallbacks):
        if key in overrides and overrides[key] is not None:
            return overrides[key]
        if key in paper_metadata and paper_metadata[key] is not None:
            return paper_metadata[key]
        return next((value for value in fallbacks if value is not None), None)

    return {
        "problem": choose(
            "problem", problem_meta.get("letter"), decision_log.get("problem")
        ),
        # A paper title and final keyword set are submission-facing fields. Do
        # not silently substitute the problem statement title or scan keywords.
        "title": choose("title"),
        "keywords": choose("keywords"),
    }


def _normalize_scalar(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    normalized = " ".join(str(value).split())
    return normalized or None


def _normalize_keywords(value) -> list[str] | None:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = re.split(r"[,;；\n]+", value)
    elif isinstance(value, (list, tuple)):
        raw_items = list(value)
    else:
        return None
    items = []
    for item in raw_items:
        if not isinstance(item, str):
            return None
        normalized = _normalize_scalar(item)
        if normalized:
            items.append(normalized)
        elif item not in (None, ""):
            return None
    return items


def _is_placeholder(field: str, value: str) -> bool:
    compact = " ".join(value.strip().split())
    folded = compact.casefold()
    if folded.startswith("mathmodel_"):
        return True
    if re.fullmatch(r"x+", folded):
        return True
    if folded in {"todo", "tbd", "待定", "待填写", "placeholder"}:
        return True
    if field == "title" and folded in {
        "title of your paper",
        "paper title",
        "untitled",
        "赛题论文题目",
        "论文标题",
    }:
        return True
    if field == "keywords":
        if re.fullmatch(r"keyword\s*\d*", folded):
            return True
        if re.fullmatch(r"关键词\s*\d*", compact):
            return True
    return False


def prepare_paper_metadata(
    competition: str,
    metadata: dict = None,
    allow_placeholders: bool = False,
) -> tuple[dict, list[str]]:
    """Normalize required fields and fail closed on missing/template values."""
    tokens = PAPER_FIELD_TOKENS.get(competition)
    if tokens is None:
        return {}, []
    metadata = metadata or {}
    normalized = {}
    issues = []
    for field in tokens:
        raw_value = metadata.get(field)
        if field == "keywords":
            value = _normalize_keywords(raw_value)
            if value is None:
                issues.append(f"{PAPER_FIELD_LABELS[field]} 类型无效")
                continue
            if not value:
                issues.append(f"缺少 {PAPER_FIELD_LABELS[field]}")
                continue
            placeholders = [item for item in value if _is_placeholder(field, item)]
            if placeholders:
                issues.append(
                    f"{PAPER_FIELD_LABELS[field]} 仍含占位符: "
                    + ", ".join(placeholders)
                )
                continue
            normalized[field] = value
            continue

        value = _normalize_scalar(raw_value)
        if value is None:
            issues.append(f"缺少 {PAPER_FIELD_LABELS[field]}")
        elif _is_placeholder(field, value):
            issues.append(f"{PAPER_FIELD_LABELS[field]} 仍是占位符: {value}")
        else:
            normalized[field] = value

    if issues and not allow_placeholders:
        source_hint = (
            "请填写 state/decision_log.json 的 paper_metadata，或使用 "
            "--control-number/--registration-number、--problem、--title、--keywords。"
        )
        raise ValueError(
            f"{competition} 正式渲染已停止：" + "；".join(issues) + "。" + source_hint
        )
    return normalized, issues


def _latex_escape(value: str) -> str:
    return "".join(_LATEX_ESCAPES.get(char, char) for char in value)


def fill_paper_metadata(
    template_text: str,
    competition: str,
    metadata: dict = None,
    allow_placeholders: bool = False,
) -> str:
    """Replace every front-matter token, leaving obvious tokens only in preview mode."""
    tokens = PAPER_FIELD_TOKENS.get(competition)
    if tokens is None:
        return template_text
    missing_template_tokens = [
        token for token in tokens.values() if token not in template_text
    ]
    if missing_template_tokens:
        raise ValueError(
            "模板缺少提交元数据 token: " + ", ".join(missing_template_tokens)
        )

    normalized, issues = prepare_paper_metadata(
        competition, metadata, allow_placeholders=allow_placeholders
    )
    separator = "；"
    for field, value in normalized.items():
        if field == "keywords":
            rendered = separator.join(_latex_escape(item) for item in value)
        else:
            rendered = _latex_escape(value)
        template_text = template_text.replace(tokens[field], rendered)

    if issues:
        print(
            "[WARN] 模板预览保留显式 MATHMODEL_* token: " + "；".join(issues)
        )
    return template_text


def find_unresolved_front_matter_placeholders(tex_text: str) -> list[str]:
    """Detect both current fail-closed tokens and placeholders in older outputs."""
    unresolved = []
    for competition, fields in PAPER_FIELD_TOKENS.items():
        for field, token in fields.items():
            if token in tex_text:
                unresolved.append(f"{competition}:{PAPER_FIELD_LABELS[field]}")

    return sorted(set(unresolved))


# ============================================================================
# md → tex 转换
# ============================================================================

def has_pandoc() -> bool:
    try:
        r = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def md_to_tex_pandoc(md_text: str) -> str:
    r = subprocess.run(
        ["pandoc", "-f", "markdown+tex_math_dollars+pipe_tables+raw_tex",
         "-t", "latex", "--no-highlight"],
        input=md_text, capture_output=True, text=True, encoding="utf-8"
    )
    if r.returncode != 0:
        raise RuntimeError(f"pandoc 失败: {r.stderr}")
    return r.stdout


def md_to_tex_fallback(md_text: str) -> str:
    """5 类 markdown → LaTeX 手工正则 (代码块 / 公式块 / 图片 / 表格 / 列表 / 标题 / 行内)"""
    tex = md_text

    def replace_code_block(m):
        lang = m.group(1) or "text"
        body = m.group(2)
        return f"\\begin{{lstlisting}}[language={lang}]\n{body}\n\\end{{lstlisting}}"
    tex = re.sub(r"```(\w+)?\n(.*?)\n```", replace_code_block, tex, flags=re.DOTALL)

    def replace_eq(m):
        body = m.group(1).strip()
        if "\\\\" in body or "&" in body:
            return f"\\begin{{align}}\n{body}\n\\end{{align}}"
        return f"\\begin{{equation}}\n{body}\n\\end{{equation}}"
    tex = re.sub(r"\$\$(.+?)\$\$", replace_eq, tex, flags=re.DOTALL)

    # 行内公式 $...$ -> \(...\)（块级 $$ 已替换为 equation 环境，互不冲突）
    def replace_inline_eq(m):
        return rf"\({m.group(1)}\)"
    tex = re.sub(r"(?<!\$)\$([^$\n]+?)\$(?!\$)", replace_inline_eq, tex)

    def replace_img(m):
        alt = m.group(1)
        path = _latex_escape(m.group(2))
        return (f"\\begin{{figure}}[H]\n\\centering\n"
                f"\\includegraphics[width=0.8\\textwidth]{{{path}}}\n"
                f"\\caption{{{alt}}}\n\\end{{figure}}")
    tex = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_img, tex)

    def replace_table(m):
        rows = [r.strip() for r in m.group(0).splitlines() if r.strip()]
        if len(rows) < 2:
            return m.group(0)
        cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
        header = cells[0]
        data = cells[2:] if len(cells) > 2 else []
        n_cols = len(header)
        col_spec = "l" * n_cols
        out = [f"\\begin{{table}}[H]\n\\centering",
               f"\\begin{{tabular}}{{{col_spec}}}\n\\toprule",
               " & ".join(header) + " \\\\",
               "\\midrule"]
        for row in data:
            out.append(" & ".join(row) + " \\\\")
        out.append("\\bottomrule\n\\end{tabular}\n\\end{table}")
        return "\n".join(out)
    tex = re.sub(r"^\|.+\|\s*$\n^\|[-:\s|]+\|\s*$\n(?:^\|.+\|\s*$\n?)+",
                  replace_table, tex, flags=re.MULTILINE)

    def replace_ol(m):
        items = re.findall(r"^\s*\d+\.\s+(.+)$", m.group(0), re.MULTILINE)
        if not items:
            return m.group(0)
        body = "\n".join(f"\\item {it}" for it in items)
        return f"\\begin{{enumerate}}\n{body}\n\\end{{enumerate}}"
    tex = re.sub(r"(?:^\s*\d+\.\s+.+\n?){2,}", replace_ol, tex, flags=re.MULTILINE)

    def replace_ul(m):
        items = re.findall(r"^\s*-\s+(.+)$", m.group(0), re.MULTILINE)
        if not items:
            return m.group(0)
        body = "\n".join(f"\\item {it}" for it in items)
        return f"\\begin{{itemize}}\n{body}\n\\end{{itemize}}"
    tex = re.sub(r"(?:^\s*-\s+.+\n?){2,}", replace_ul, tex, flags=re.MULTILINE)

    tex = re.sub(r"^# (.+)$", r"\\section{\1}", tex, flags=re.MULTILINE)
    tex = re.sub(r"^## (.+)$", r"\\subsection{\1}", tex, flags=re.MULTILINE)
    tex = re.sub(r"^### (.+)$", r"\\subsubsection{\1}", tex, flags=re.MULTILINE)

    tex = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", tex)
    tex = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\\textit{\1}", tex)
    tex = re.sub(r"`([^`]+?)`", r"\\texttt{\1}", tex)
    tex = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", tex)

    return tex


def expand_narrow_tables(tex: str) -> str:
    """把 Pandoc 从 pipe 表生成的窄自然宽度 `l` 列，扩展为铺满版心的 `p{}` 列。

    Pandoc 对 pipe 表（``|---|---|``）输出 ``@{}l...l@{}``：不换行、窄于版心，
    导致三线（toprule/midrule/bottomrule）只铺到内容自然宽度、长文本溢出；
    而 grid 表输出 ``p{(linewidth-…) * real{…}}`` 铺满版心。这里把前者等价转换为
    后者的等宽版本，保证三线铺满、内容自动换行（公式与 Pandoc grid 表一致，
    需 array/calc 包，模板已加载）。
    """
    def repl(m):
        cols = m.group(1)
        n = len(cols)
        if n < 1:
            return m.group(0)
        frac = 1.0 / n
        pad = 2 * (n - 1)  # 两端 @{} 各去掉一个 tabcolsep，剩 2(n-1) 个
        spec = "@{}" + "@{}".join(
            f">{{\\raggedright\\arraybackslash}}p{{(\\linewidth - {pad}\\tabcolsep) "
            f"* \\real{{{frac:.5g}}}}}"
            for _ in range(n)
        ) + "@{}"
        return "\\begin{longtable}{" + spec + "}"

    return re.sub(r"\\begin\{longtable\}\[\]\{@\{\}(l+)@\{\}\}", repl, tex)


def md_to_tex(md_text: str, prefer_pandoc: bool = True) -> str:
    if prefer_pandoc:
        if not has_pandoc():
            raise RuntimeError("Pandoc 未安装，正式论文转换已停止")
        return expand_narrow_tables(md_to_tex_pandoc(md_text))
    return md_to_tex_fallback(md_text)


def validate_workspace_sections(workspace: Path) -> None:
    """Require every 01–10 workspace input to exist and contain content."""
    missing = []
    empty = []
    for filename in SECTION_TO_FILE.values():
        path = workspace / filename
        if not path.is_file():
            missing.append(filename)
        elif not path.read_text(encoding="utf-8").strip():
            empty.append(filename)
    problems = []
    if missing:
        problems.append(f"缺失: {', '.join(missing)}")
    if empty:
        problems.append(f"空文件: {', '.join(empty)}")
    if problems:
        raise FileNotFoundError(
            "paper workspace 不完整（" + "；".join(problems) + "）。"
            "为避免生成正文缺失但看似成功的 PDF，已停止。"
        )


# ============================================================================
# 模板填充: 统一 marker 装配
# ============================================================================


def fill_template_main(
    workspace: Path,
    template_dir: Path,
    output_dir: Path,
    main_filename: str,
    prefer_pandoc: bool = True,
    competition: str = None,
    paper_metadata: dict = None,
    allow_placeholders: bool = False,
) -> Path:
    """Render section files and wire them into a competition main.tex template."""
    validate_workspace_sections(workspace)
    main_src = template_dir / main_filename
    if not main_src.exists():
        raise FileNotFoundError(f"模板 {main_src} 不存在")
    main_text = fill_paper_metadata(
        main_src.read_text(encoding="utf-8"),
        competition,
        metadata=paper_metadata,
        allow_placeholders=allow_placeholders,
    )

    # Validate submission metadata before creating an output that could be
    # mistaken for a ready paper.
    output_dir.mkdir(parents=True, exist_ok=True)
    sections_dir = output_dir / "sections"
    sections_dir.mkdir(exist_ok=True)
    main_dst = output_dir / main_filename

    # 复制其他 sty / cls 文件
    for ext in ("*.cls", "*.sty", "*.bib"):
        for f in template_dir.glob(ext):
            shutil.copy(f, output_dir)

    # 复制 figures
    if (template_dir / "figures").exists():
        shutil.copytree(template_dir / "figures", output_dir / "figures",
                         dirs_exist_ok=True)
    if (workspace.parent / "figures").exists():
        shutil.copytree(workspace.parent / "figures", output_dir / "figures",
                         dirs_exist_ok=True)

    optional_included = set()

    def resolve_optional_block(match: re.Match) -> str:
        name = match.group("name")
        if name not in OPTIONAL_SECTION_TO_FILE:
            raise ValueError(f"模板包含未知 optional block: {name}")
        path = workspace / OPTIONAL_SECTION_TO_FILE[name]
        if not path.is_file():
            return ""
        if not path.read_text(encoding="utf-8").strip():
            raise ValueError(f"可选节 {path.name} 存在但为空")
        optional_included.add(name)
        return match.group("body")

    main_text = OPTIONAL_BLOCK_RE.sub(resolve_optional_block, main_text)
    markers = SECTION_MARKER_RE.findall(main_text)
    duplicate_markers = sorted({name for name in markers if markers.count(name) > 1})
    if duplicate_markers:
        raise ValueError(f"模板包含重复 section marker: {duplicate_markers}")
    unknown_markers = sorted(
        set(markers) - set(SECTION_TO_FILE) - set(OPTIONAL_SECTION_TO_FILE)
    )
    if unknown_markers:
        raise ValueError(f"模板包含未知 section marker: {unknown_markers}")
    orphan_optional = sorted(
        set(markers).intersection(OPTIONAL_SECTION_TO_FILE) - optional_included
    )
    if orphan_optional:
        raise ValueError(
            f"可选 section marker 必须位于同名 OPTIONAL block 内: {orphan_optional}"
        )

    missing_markers = sorted(set(SECTION_TO_FILE) - set(markers))
    if missing_markers:
        raise ValueError(
            f"模板缺少 MATHMODEL section marker: {missing_markers}; "
            "为避免生成看似成功但正文为空的 PDF, 已停止"
        )

    section_files = dict(SECTION_TO_FILE)
    section_files.update({
        marker: OPTIONAL_SECTION_TO_FILE[marker]
        for marker in markers if marker in optional_included
    })

    # md → sections/<sec>.tex
    for sec, fname in section_files.items():
        md_path = workspace / fname
        sec_tex_path = sections_dir / f"{sec}.tex"
        tex = md_to_tex(md_path.read_text(encoding="utf-8"), prefer_pandoc)
        sec_tex_path.write_text(tex, encoding="utf-8")

    main_text = SECTION_MARKER_RE.sub(
        lambda m: f"\\input{{sections/{m.group(1)}}}",
        main_text,
    )
    main_dst.write_text(main_text, encoding="utf-8")

    print(
        f"[OK] 已生成 {main_dst}, 渲染并自动连接 "
        f"{len(section_files)} 个 sections/*.tex"
    )
    return main_dst


def fill_template(
    competition: str,
    workspace: Path,
    output_dir: Path,
    prefer_pandoc: bool = True,
    paper_metadata: dict = None,
    allow_placeholders: bool = None,
) -> tuple[Path, str]:
    """竞赛分发: 返回 (main_tex_path, engine)"""
    cfg = TEMPLATE_MAP.get(competition)
    if cfg is None:
        raise ValueError(f"未知 competition: {competition}; 支持 {list(TEMPLATE_MAP.keys())}")

    template_dir = cfg["template_dir"]
    if not template_dir.exists():
        raise FileNotFoundError(f"模板目录 {template_dir} 不存在")

    if cfg["mode"] == "main_template":
        # Backward-compatible programmatic structural preview: callers that
        # explicitly select the fallback converter already opted out of formal
        # rendering. CLI callers always pass an explicit boolean instead.
        if allow_placeholders is None:
            allow_placeholders = not prefer_pandoc
        main_tex_path = fill_template_main(workspace, template_dir, output_dir,
                                            cfg["main_filename"], prefer_pandoc,
                                            competition=competition,
                                            paper_metadata=paper_metadata,
                                            allow_placeholders=allow_placeholders)
    else:
        raise ValueError(f"未知 template mode: {cfg['mode']}")

    return main_tex_path, cfg["engine"]


# ============================================================================
# 编译
# ============================================================================

_IDENTITY_PATTERNS = [
    (r"[\u4e00-\u9fff]{0,8}(?:大学|学院|学校|职业技术|师范)", "疑似校名/机构名"),
    (r"(?:指导|带队)老师", "指导教师字段"),
    (r"\b(?:University|College|Institute|School)\b", "英文机构名"),
]


def scan_identity_leak(workdir: Path) -> list[str]:
    """扫描输出目录所有 tex 中的疑似身份信息（跳过参考文献节）。"""
    hits = []
    for tex in workdir.rglob("*.tex"):
        if tex.name == "8_references.tex":
            continue
        try:
            text = tex.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat, label in _IDENTITY_PATTERNS:
            for m in re.findall(pat, text):
                hits.append(f"{tex.name}: {label} -> {m}")
    return hits


def check_figure_refs(workdir: Path) -> list[str]:
    """核对正文 \\includegraphics 引用的图是否都存在于 figures 目录。"""
    figdir = workdir / "figures"
    missing = []
    for tex in workdir.rglob("*.tex"):
        try:
            text = tex.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
            fname = Path(m).name
            if not (figdir / fname).is_file():
                missing.append(f"{tex.name}: {m}")
    return missing


def scan_missing_glyphs(workdir: Path) -> list[str]:
    """扫描输出目录 tex 中的缺字字符（圈数字等），命中提示改半角括号。"""
    glyph_re = re.compile(r"[\u2460-\u24ff\u2776-\u2793]")
    missing = []
    for tex in workdir.rglob("*.tex"):
        try:
            text = tex.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in glyph_re.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            missing.append(f"{tex.name}:{line_no}: U+{ord(m.group()):04X} {m.group(0)}")
    return missing


def compile_pdf(tex_path: Path, engine: str = "xelatex", runs: int = 3) -> bool:
    try:
        unresolved = find_unresolved_front_matter_placeholders(
            tex_path.read_text(encoding="utf-8")
        )
    except OSError as exc:
        print(f"[FAIL] 无法读取待编译 TeX: {exc}")
        return False
    if unresolved:
        print(
            "[FAIL] 正式编译已停止，封面/摘要页仍含提交占位符: "
            + ", ".join(unresolved)
        )
        return False

    workdir = tex_path.parent

    # D9: 编译前核对正文引用的图是否都存在
    missing_figs = check_figure_refs(workdir)
    if missing_figs:
        print("[FAIL] 正文引用了不存在的图文件，请补齐或修正引用：")
        for item in missing_figs:
            print("   - " + item)
        return False

    # D3: 编译前扫描疑似身份信息（学校/指导老师等），命中仅告警需人工确认
    identity_hits = scan_identity_leak(workdir)
    if identity_hits:
        print("[WARN] 检测到疑似身份/机构信息（可能命中匿名违规，请人工确认并移除）：")
        for item in identity_hits:
            print("   - " + item)

    missing_glyphs = scan_missing_glyphs(workdir)
    if missing_glyphs:
        print("[WARN] 检测到可能缺字的字符（圈数字等），建议改半角括号：")
        for item in missing_glyphs:
            print("   - " + item)

    for i in range(runs):
        print(f"\n--- {engine} 第 {i+1}/{runs} 次 ---")
        result = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", str(tex_path.name)],
            cwd=workdir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        if result.returncode != 0:
            print(f"[FAIL] {engine} 失败 (返回码 {result.returncode})")
            print(result.stdout[-2000:])
            print("--- stderr ---")
            print(result.stderr[-1000:])
            return False
    pdf_path = tex_path.with_suffix(".pdf")
    if pdf_path.exists():
        print(f"\n[OK] PDF 已生成: {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")
        return True
    print(f"[FAIL] PDF 未生成")
    return False


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=str, required=True,
                        help="<cwd>/paper_workspace/ 目录, 含 01..10_*.md 节文件")
    parser.add_argument("--competition", type=str, default=None,
                        help="mathmodel (默认从 decision_log 读, 缺失则 mathmodel)")
    parser.add_argument("--decision-log", type=str, default=None,
                        help="可选: 指定 decision_log.json 路径用于自动检测 competition")
    parser.add_argument("--problem", default=None,
                        help="题号/Problem Chosen（覆盖 decision log）")
    parser.add_argument("--title", default=None,
                        help="最终论文题目（覆盖 decision log）")
    parser.add_argument("--keywords", default=None,
                        help="最终关键词，以逗号、分号或中文分号分隔（覆盖 decision log）")
    parser.add_argument("--output-dir", type=str, default="paper_output")
    parser.add_argument("--no-pandoc", action="store_true",
                        help="禁用 pandoc, 直接用手工正则 (调试用)")
    parser.add_argument("--no-compile", action="store_true",
                        help="只填充模板, 不调用 LaTeX 引擎 (dry-run)")
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="仅模板预览: 允许保留醒目的 MATHMODEL_* token；必须与 --no-compile 同用",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace)
    output_dir = Path(args.output_dir)

    if not workspace.exists():
        print(f"[FAIL] workspace {workspace} 不存在")
        return 1

    if args.allow_placeholders and not args.no_compile:
        print("[FAIL] --allow-placeholders 只能与 --no-compile 一起使用，禁止生成占位 PDF")
        return 1

    decision_log_path = resolve_decision_log_path(workspace, args.decision_log)
    try:
        decision_log = load_decision_log(
            decision_log_path, required=bool(args.decision_log)
        )
        paper_metadata = resolve_paper_metadata(
            decision_log,
            {
                "problem": args.problem,
                "title": args.title,
                "keywords": args.keywords,
            },
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"[FAIL] {e}")
        return 1

    competition = resolve_competition(args.competition, decision_log_path)
    print(f"competition: {competition}")

    prefer_pandoc = not args.no_pandoc
    if args.no_pandoc and not args.no_compile:
        print("[FAIL] --no-pandoc 仅用于 --no-compile structural dry-run；正式编译必须使用 Pandoc")
        return 1
    if prefer_pandoc and not has_pandoc():
        if not args.no_compile:
            print("[FAIL] 正式论文转换需要 Pandoc: https://pandoc.org/installing.html")
            return 1
        print("[WARN] Pandoc 未安装；本次 --no-compile 仅检查结构，使用简化转换器")
        prefer_pandoc = False

    try:
        tex_path, engine = fill_template(
            competition,
            workspace,
            output_dir,
            prefer_pandoc,
            paper_metadata=paper_metadata,
            allow_placeholders=args.allow_placeholders,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"[FAIL] {e}")
        return 1

    if args.no_compile:
        print(f"[OK] dry-run 完成 (--no-compile). engine={engine}, tex={tex_path}")
        return 0

    return 0 if compile_pdf(tex_path, engine=engine, runs=3) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

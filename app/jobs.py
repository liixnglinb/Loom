# -*- coding: utf-8 -*-
"""竞赛工作流作业执行引擎。
逐步：问题分析 → 建模 → 代码 → 论文 → 编译 → 审查改进。
每个步骤：加载对应 skill 的 SKILL.md 作为 system，拼接用户提供的赛题/配置，调 LLM，
产出的 .md/.tex/.json 落盘到 workspace/user_data + workspace 根，并通过 _utils 脚本自检。
"""
import json, threading, time, shutil, subprocess, sys, re, os
from pathlib import Path
from . import db, paths
from .llm import LLMError

# Windows GUI 子系统下子进程默认会弹黑窗（ffmpeg/xelatex/python/winget 等），
# 统一加 CREATE_NO_WINDOW 抑制；非 Windows 平台该值为 0（subprocess 忽略）。
_CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ---------------- 暂停/恢复（修复4：线程事件实现真暂停） ----------------
_PAUSE_EVENTS: dict = {}          # wid -> threading.Event（set=可运行，clear=暂停）
_PAUSE_LOCK = threading.Lock()
_JOB_START_LOCK = threading.Lock()   # 防同一工作流重复启动（P2-10）


def _pause_event(wid):
    with _PAUSE_LOCK:
        ev = _PAUSE_EVENTS.get(wid)
        if ev is None:
            ev = threading.Event()
            ev.set()
            _PAUSE_EVENTS[wid] = ev
        return ev


def pause_job(wid):
    """真暂停：清除事件，execute_job 在步骤边界阻塞等待。"""
    _pause_event(wid).clear()


def resume_job(wid):
    """真恢复：置位事件，被阻塞的 execute_job 线程继续。"""
    _pause_event(wid).set()


def _clear_pause(wid):
    """工作流结束时清理暂停事件，避免泄漏。"""
    with _PAUSE_LOCK:
        _PAUSE_EVENTS.pop(wid, None)


def _push(wid, payload):
    """向工作流的 WebSocket 订阅者推送状态（失败静默，不影响流水线）。"""
    try:
        from .ws import push_sync
        push_sync(wid, payload)
    except Exception:
        pass

WS_ROOT = paths.WS_ROOT
WS_ROOT.mkdir(exist_ok=True)
# 项目内 python 等价自检脚本目录（Windows 无 bash，故把 shell 脚本翻译为 py，随包一起分发）
PROJECT_UTILS = paths.BASE / "_utils_py"
PROJECT_UTILS.mkdir(exist_ok=True)


def _setting_dir(key, env_key):
    """从 settings 表 / 环境变量读一个可选目录覆盖（存在才返回）。"""
    import os as _os
    for v in (_os.environ.get(env_key), db.get_setting(key, "")):
        if v and v.strip():
            p = Path(v.strip())
            if p.exists():
                return p
    return None


# ---------------- skill / utils 资产路径解析（机器无关，随包分发） ----------------
# 设计原则：随包内置的 skills/ 与 _utils_py/ 是唯一可靠来源，换机器、打包分发均可用。
# 如需定制，通过环境变量或 settings 表指向外部目录覆盖（目录不存在则自动回退内置），
# 绝不写死任何用户机器路径。
BUNDLED_SKILLS_DIR = paths.BASE / "skills"      # 随包内置全量 skill（spec --add-data 分发）
BUNDLED_UTILS_DIR = PROJECT_UTILS               # 随包内置自检/工具脚本

# 外部覆盖：环境变量 MODELFLOW_SKILLS_DIR / MODELFLOW_UTILS_DIR，或 settings 表
# skills_dir / utils_dir。仅当指向的目录真实存在时才生效，否则静默回退内置副本。
SKILLS_DIR = _setting_dir("skills_dir", "MODELFLOW_SKILLS_DIR") or BUNDLED_SKILLS_DIR
UTILS_DIR = _setting_dir("utils_dir", "MODELFLOW_UTILS_DIR") or BUNDLED_UTILS_DIR

# 竞赛工作流步骤编排（ModelFlow 智模流水线 9 步）
COMPETITION_STEPS = [
    {"key": "analysis", "label": "赛题分析", "skill": "comp-prob-analysis",
     "out": "PROBLEM_ANALYSIS.md", "checkpoint": True,
     "role": "executor",
     "check": "step_audit.py prob"},
    {"key": "modeling", "label": "建模求解", "skill": "comp-modeling",
     "out": "MODELING_REPORT.md", "checkpoint": True,
     "role": "executor",
     "check": "step_audit.py modeling"},
    {"key": "code", "label": "编程实现", "skill": "comp-code",
     "out": "RESULTS.md", "checkpoint": True,
     "role": "executor",
     "check": "step_audit.py code"},
    {"key": "figure", "label": "图表生成", "skill": "paper-figure",
     "out": "FIGURES.md", "checkpoint": False,
     "role": "executor",
     "check": "step_audit.py figure"},
    {"key": "arch", "label": "流程与架构图绘制", "skill": "paper-figure-html diagram-design",
     "out": "ARCHITECTURE.md", "checkpoint": False,
     "role": "executor",
     "check": "step_audit.py arch"},
    {"key": "review", "label": "逻辑对抗复核", "skill": "comp-review",
     "out": "LOGIC_REVIEW.md", "checkpoint": False,
     "role": "reviewer",
     "check": "step_audit.py review"},
    {"key": "paper", "label": "竞赛论文撰写", "skill": "comp-paper-zh",
     "out": "main.tex", "checkpoint": True,
     "role": "editor",
     "check": "step_audit.py paper"},
    {"key": "compile", "label": "编译与合规检查", "skill": "comp-compile-zh",
     "out": "main.pdf", "checkpoint": False,
     "role": "executor",
     "check": "step_audit.py compile"},
    {"key": "improve", "label": "论文改进循环", "skill": "auto-paper-improvement-loop",
     "out": "IMPROVED_PAPER.md", "checkpoint": False,
     "role": "executor",
     "check": "step_audit.py improve"},
]

# ---------------- 非竞赛流水线（10 套） ----------------
# 每步：skill 对应桌面 skills/<skill>/SKILL.md；out 为该步主产物文件；
# role∈executor/reviewer/editor，映射到设置页角色模型；check 为空则跳过自检。
NON_COMPETITION_STEPS = {
    "idea_discovery": [
        {"key": "lit", "label": "文献调研", "skill": "research-lit",
         "out": "LITERATURE_REVIEW.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "idea", "label": "头脑风暴", "skill": "idea-creator",
         "out": "IDEA_SHORTLIST.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "novelty", "label": "验新颖性", "skill": "novelty-check",
         "out": "NOVELTY_CHECK.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "review", "label": "方案评审", "skill": "research-review",
         "out": "REVIEW.md", "checkpoint": False, "role": "reviewer", "check": ""},
        {"key": "refine", "label": "方案细化", "skill": "research-refine",
         "out": "IDEA_REPORT.md", "checkpoint": True, "role": "executor", "check": ""},
    ],
    "experiment_bridge": [
        {"key": "plan", "label": "实验方案", "skill": "experiment-plan",
         "out": "EXPERIMENT_PLAN.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "run", "label": "跑实验", "skill": "run-experiment",
         "out": "RESULTS.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "monitor", "label": "监测实验", "skill": "monitor-experiment",
         "out": "EXPERIMENT_LOG.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "analyze", "label": "结果分析", "skill": "analyze-results",
         "out": "ANALYSIS.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "figure", "label": "论文图表", "skill": "paper-figure",
         "out": "FIGURES.md", "checkpoint": True, "role": "executor", "check": ""},
    ],
    "auto_review": [
        {"key": "analyze", "label": "论文分析", "skill": "paper-analysis",
         "out": "ANALYSIS.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "quality", "label": "质量审查", "skill": "quality-check",
         "out": "QUALITY_REVIEW.md", "checkpoint": False, "role": "reviewer", "check": ""},
        {"key": "loop", "label": "自动评审循环", "skill": "auto-review-loop",
         "out": "AUTO_REVIEW.md", "checkpoint": True, "role": "reviewer", "check": ""},
        {"key": "rebuttal", "label": "审稿回应", "skill": "rebuttal",
         "out": "REBUTTAL.md", "checkpoint": False, "role": "executor", "check": ""},
    ],
    "paper_writing": [
        {"key": "plan", "label": "大纲规划", "skill": "paper-plan",
         "out": "PAPER_PLAN.md", "checkpoint": True, "role": "executor", "check": ""},
        {"key": "analyze", "label": "数据分析", "skill": "paper-analysis",
         "out": "RESULTS.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "figure", "label": "图表生成", "skill": "paper-figure",
         "out": "FIGURES.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "paper", "label": "正文撰写", "skill": "paper-write",
         "out": "paper/main.md", "checkpoint": True, "role": "editor", "check": ""},
        {"key": "compile", "label": "编译 PDF", "skill": "paper-compile",
         "out": "paper/main.pdf", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "improve", "label": "论文改进循环", "skill": "auto-paper-improvement-loop",
         "out": "IMPROVED_PAPER.md", "checkpoint": False, "role": "executor", "check": ""},
    ],
    "full_pipeline": [
        {"key": "lit", "label": "文献调研", "skill": "research-lit",
         "out": "LITERATURE_REVIEW.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "refine", "label": "方案细化", "skill": "research-refine",
         "out": "METHOD_PLAN.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "review", "label": "评审改进", "skill": "auto-review-loop",
         "out": "AUTO_REVIEW.md", "checkpoint": True, "role": "reviewer", "check": ""},
        {"key": "paper", "label": "正文撰写", "skill": "paper-write",
         "out": "paper/main.md", "checkpoint": True, "role": "editor", "check": ""},
        {"key": "compile", "label": "编译 PDF", "skill": "paper-compile",
         "out": "paper/main.pdf", "checkpoint": False, "role": "executor", "check": ""},
    ],
    "thesis_proposal": [
        {"key": "lit", "label": "文献调研", "skill": "literature-review",
         "out": "LITERATURE_REVIEW.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "proposal", "label": "开题撰写", "skill": "thesis-proposal",
         "out": "THESIS_PROPOSAL.md", "checkpoint": True, "role": "editor", "check": ""},
        {"key": "format", "label": "格式优化", "skill": "format-profile",
         "out": "FORMAT_PROFILE.json", "checkpoint": False, "role": "executor", "check": ""},
    ],
    "literature_review": [
        {"key": "search", "label": "文献检索", "skill": "literature-review",
         "out": "LITERATURE_REVIEW.md", "checkpoint": True, "role": "executor", "check": ""},
        {"key": "quality", "label": "质量审查", "skill": "quality-check",
         "out": "QUALITY_REVIEW.md", "checkpoint": False, "role": "reviewer", "check": ""},
    ],
    "course_paper": [
        {"key": "plan", "label": "大纲规划", "skill": "course-plan",
         "out": "OUTLINE.md", "checkpoint": True, "role": "executor", "check": ""},
        {"key": "analyze", "label": "数据分析", "skill": "paper-analysis",
         "out": "RESULTS.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "figure", "label": "图表生成", "skill": "paper-figure",
         "out": "FIGURES.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "paper", "label": "正文撰写", "skill": "course-paper",
         "out": "COURSE_PAPER.md", "checkpoint": True, "role": "editor", "check": ""},
        {"key": "format", "label": "格式优化", "skill": "format-profile",
         "out": "FORMAT_PROFILE.json", "checkpoint": False, "role": "executor", "check": ""},
    ],
    "course_report": [
        {"key": "plan", "label": "事实提取+大纲", "skill": "course-report-plan",
         "out": "OUTLINE.md", "checkpoint": True, "role": "executor", "check": ""},
        {"key": "figure", "label": "图表生成", "skill": "paper-figure",
         "out": "FIGURES.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "arch", "label": "架构/流程图", "skill": "mermaid-diagram diagram-design",
         "out": "ARCHITECTURE.md", "checkpoint": False, "role": "executor", "check": ""},
        {"key": "paper", "label": "正文撰写", "skill": "course-report",
         "out": "COURSE_REPORT.md", "checkpoint": True, "role": "editor", "check": ""},
        {"key": "format", "label": "格式优化", "skill": "format-profile",
         "out": "FORMAT_PROFILE.json", "checkpoint": False, "role": "executor", "check": ""},
    ],
    "humanities_paper": [
        {"key": "plan", "label": "论文规划", "skill": "humanities-plan",
         "out": "OUTLINE.md", "checkpoint": True, "role": "executor", "check": ""},
        {"key": "paper", "label": "正文撰写", "skill": "humanities-write",
         "out": "HUMANITIES_PAPER.md", "checkpoint": True, "role": "editor", "check": ""},
        {"key": "format", "label": "格式优化", "skill": "format-profile",
         "out": "FORMAT_PROFILE.json", "checkpoint": False, "role": "executor", "check": ""},
    ],
}

# 全部流水线：竞赛 + 10 套非竞赛
PIPELINES = {"competition": COMPETITION_STEPS}
PIPELINES.update(NON_COMPETITION_STEPS)

# ---------------- 第二套国赛流程：BZD 双审精制流（cumcm-bzd-2026） ----------------
# 与「极速全自动流」(competition) 并存，新建竞赛时二选一。9 阶段=题面解析→策略→执行→稳健→
# 写作→摘要→全面审查I(章节自查)→全面审查II(综合评审)→终稿合规出库，含 BZD 2026 模板与双审查。
COMPETITION_STEPS_BZD = [
    {"key": "stage01_kickoff", "label": "启动与题面解析", "skill": "bzd-2026-stage-01 diagram-design",
     "out": "PROBLEM_TRANSLATION.md", "checkpoint": False, "role": "executor", "check": ""},
    {"key": "stage02_strategy", "label": "建模策略与模型选型", "skill": "bzd-2026-stage-02 diagram-design",
     "out": "TECH_ROUTE.md", "checkpoint": False, "role": "executor", "check": ""},
    {"key": "stage03_solving", "label": "建模执行", "skill": "bzd-2026-stage-03 diagram-design",
     "out": "SOLVING_RESULTS.md", "checkpoint": True, "role": "executor", "check": ""},
    {"key": "stage04_robust", "label": "稳健性总检验", "skill": "bzd-2026-stage-04 diagram-design",
     "out": "ROBUST_REPORT.md", "checkpoint": False, "role": "executor", "check": ""},
    {"key": "stage05_writing", "label": "章节写作", "skill": "bzd-2026-stage-05 diagram-design",
     "out": "PAPER_SECTIONS.md", "checkpoint": True, "role": "editor", "check": ""},
    {"key": "stage06_abstract", "label": "摘要与首页", "skill": "bzd-2026-stage-06 diagram-design",
     "out": "ABSTRACT.md", "checkpoint": False, "role": "editor", "check": ""},
    {"key": "stage07_review1", "label": "全面审查 I：章节自查", "skill": "bzd-2026-stage-07 diagram-design",
     "out": "REVIEW1_CHAPTERS.md", "checkpoint": True, "role": "reviewer", "check": ""},
    {"key": "stage08_review2", "label": "全面审查 II：综合评审", "skill": "bzd-2026-stage-08 diagram-design",
     "out": "REVIEW2_PANEL.md", "checkpoint": True, "role": "reviewer", "check": ""},
    {"key": "stage09_release", "label": "终稿装配与合规出库", "skill": "bzd-2026-stage-09 diagram-design",
     "out": "SUBMISSION.md", "checkpoint": False, "role": "executor", "check": ""},
]
PIPELINES["competition_bzd"] = COMPETITION_STEPS_BZD

# 是否为竞赛类
def is_competition_template(template):
    t = template or ""
    return t == "competition" or t.startswith("comp_") or t == "competition_bzd"

# 步骤索引映射（供 data_fig 等配置读取，以竞赛为基准）
STEP_INDEX = {s["key"]: i for i, s in enumerate(COMPETITION_STEPS)}

def compose_skill_prompt(skill, template, step_key):
    """原版 SKILL.md + 用户定制（replace 优先，其次 extra 追加）。

    CLI 模式下 SKILL 全文经 CLAUDE.md 注入，同样走本函数，保证双引擎一致。
    """
    base = load_skill_prompt(skill)
    ov = db.get_skill_override(template, step_key)
    if not ov:
        return base
    if (ov.get("replace_prompt") or "").strip():
        return ov["replace_prompt"] if not base else \
            f"{ov['replace_prompt']}\n\n---\n【原版 skill 参考（如与上方定制冲突以定制为准）】\n{base[:6000]}"
    if (ov.get("extra_prompt") or "").strip():
        return f"{base}\n\n---\n【用户补充要求（最高优先级）】\n{ov['extra_prompt']}" if base \
            else ov["extra_prompt"]
    return base

def _sanitize_skill_prompt(text: str) -> str:
    """移除 SKILL.md 中由旧工作区导出时误带入的运行时快照块。

    部分原始 skill 尾部混入 `Additional Parameters / Workspace Context /
    Previous Steps Output Summary / Pipeline Context`，其中包含历史模型预设 ID、
    step_models 和旧附件路径。它们不是技能规则，却会污染新工作区并让 CLI 误选
    旧模型。只保留这些标题之前的稳定技能正文。
    """
    if not text:
        return text
    markers = ("\n## Additional Parameters", "\n## Workspace Context",
               "\n## Previous Steps Output Summary", "\n## Pipeline Context")
    cuts = [text.find(m) for m in markers if text.find(m) >= 0]
    return text[:min(cuts)].rstrip() + "\n" if cuts else text


def load_skill_prompt(skill):
    """读取并净化 skill 的 SKILL.md 作为 system prompt。

    支持「skill_a skill_b」空格分隔的多技能叠加：按序读取并拼接，先注入的是执行主技能，
    后注入的是配套规范（如 paper-figure-html diagram-design）。
    优先读外部覆盖目录（环境变量 MODELFLOW_SKILLS_DIR 或 settings.skills_dir，
    存在才生效）；否则读随包内置 skills/（与 _utils_py 一并随包分发，机器无关）。
    均未命中返回空串，由上层兜底。
    """
    names = [n for n in str(skill or "").split() if n.strip()]
    parts = []
    for name in names:
        for base in (SKILLS_DIR, BUNDLED_SKILLS_DIR):
            try:
                p = base / name / "SKILL.md"
                if p.exists():
                    parts.append(_sanitize_skill_prompt(p.read_text(encoding="utf-8")))
                    break
            except Exception:
                continue
    return "\n\n---\n".join(parts)

def ws_path(wid):
    p = WS_ROOT / f"job_{wid}"
    (p / "user_data").mkdir(parents=True, exist_ok=True)
    return p

def _extract_text(dest: Path) -> str:
    """把上传的 PDF/docx/xlsx 抽取成纯文本，写入 <stem>_extracted.txt。

    skill 约定：赛题/资料优先读 *_extracted.txt（PDF 公式直接用 Read 会乱码）。
    返回抽取文本路径（相对 workspace）或空串。失败静默返回空，不阻断流水线。
    """
    suffix = dest.suffix.lower()
    try:
        txt = ""
        if suffix == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(str(dest)) as pdf:
                    pages = []
                    for pg in pdf.pages:
                        pages.append(pg.extract_text() or "")
                txt = "\n\n".join(pages)
            except Exception:
                # PyPDF2 兜底
                try:
                    import pypdf
                    r = pypdf.PdfReader(str(dest))
                    txt = "\n\n".join((p.extract_text() or "") for p in r.pages)
                except Exception:
                    return ""
        elif suffix == ".docx":
            try:
                import docx
                d = docx.Document(str(dest))
                txt = "\n".join(p.text for p in d.paragraphs)
                for tb in d.tables:
                    for row in tb.rows:
                        txt += "\n" + " | ".join(c.text for c in row.cells)
            except Exception:
                return ""
        elif suffix in (".xlsx", ".xls", ".csv"):
            try:
                import pandas as pd
                if suffix == ".csv":
                    df = pd.read_csv(str(dest))
                else:
                    df = pd.read_excel(str(dest))
                txt = df.to_csv(index=False)
            except Exception:
                return ""
        elif suffix == ".pptx":
            try:
                from pptx import Presentation
                prs = Presentation(str(dest))
                parts = []
                for i, slide in enumerate(prs.slides, 1):
                    parts.append(f"\n--- 第 {i} 页 ---")
                    for shape in slide.shapes:
                        if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip():
                            parts.append(shape.text_frame.text)
                        elif getattr(shape, "has_table", False):
                            for row in shape.table.rows:
                                parts.append(" | ".join(c.text for c in row.cells))
                txt = "\n".join(parts)
            except Exception:
                return ""
        elif suffix == ".doc":
            # 老 .doc 无原生活取层：返回空串（AI 会读原文件；转 .docx 需 Office/WPS）
            return ""
        else:
            return ""
        if not txt or not txt.strip():
            return ""
        out = dest.with_name(dest.stem + "_extracted.txt")
        out.write_text(txt, encoding="utf-8")
        return str(out)
    except Exception:
        return ""


_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".ts", ".mts", ".mpg", ".mpeg"}


def _find_ff_bin(name):
    """定位 ffmpeg/ffprobe：PATH → WinGet Links → WinGet Packages（按环境变量推导，不写死用户名）。"""
    p = shutil.which(name)
    if p:
        return p
    local = os.environ.get("LOCALAPPDATA")
    if local:
        links = Path(local) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe"
        if links.exists():
            return str(links)
        pkgs = Path(local) / "Microsoft" / "WinGet" / "Packages"
        if pkgs.is_dir():
            try:
                for d in pkgs.iterdir():
                    if "ffmpeg" in d.name.lower():
                        for exe in d.rglob(f"{name}.exe"):
                            return str(exe)
            except OSError:
                pass
    return ""


def _probe_video(dest: Path):
    """ffprobe 读视频元信息，返回 (info_text, duration, has_audio) 或 None。"""
    ffprobe = _find_ff_bin("ffprobe")
    if not ffprobe:
        return None
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(dest)],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace", creationflags=_CNW)
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout or "{}")
    except Exception:
        return None
    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    vstream = next((s for s in streams if s.get("codec_type") == "video"), {})
    astream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    try:
        dur = float(fmt.get("duration") or vstream.get("duration") or 0)
    except (TypeError, ValueError):
        dur = 0.0
    w = vstream.get("width") or "?"
    h = vstream.get("height") or "?"
    fps = "?"
    try:
        num, den = vstream.get("avg_frame_rate", "").split("/")
        if den and den != "0":
            fps = f"{float(num) / float(den):.2f}"
    except Exception:
        try:
            fps = str(round(float(vstream.get("r_frame_rate") or 0), 2))
        except Exception:
            pass
    has_audio = bool(astream)
    acodec = astream.get("codec_name") or "?"
    lines = [
        f"视频文件：{dest.name}",
        f"时长：{dur:.2f} 秒（{int(dur // 60)} 分 {dur % 60:.0f} 秒）",
        f"分辨率：{w}x{h}",
        f"帧率：{fps} fps",
        f"音频轨：{'有（' + acodec + '）' if has_audio else '无'}",
    ]
    return "\n".join(lines), dur, has_audio


def _extract_video(dest: Path):
    """把上传的视频解析成可被 AI 读取的产物：
      - *_video_info.txt   ffprobe 时长/分辨率/帧率（最小闭环，无 ffmpeg 也能出）
      - *_frames/          均匀抽关键帧 JPG（vision LLM 读画面）
      - *_audio.mp3/.wav   抽取音轨（供 ASR 转写，未配置转写时 skill 自行决定）
    任一环节失败静默降级，不阻断流水线；返回产物相对路径列表。
    """
    info = _probe_video(dest)
    rel = []
    if info:
        info_txt, dur, has_audio = info
        try:
            ip = dest.with_name(dest.stem + "_video_info.txt")
            ip.write_text(info_txt + "\n", encoding="utf-8")
            rel.append(str(ip))
        except OSError:
            pass
    else:
        dur, has_audio = 0.0, False
        # 无 ffprobe 时也给出最小提示（不报时长/分辨率）
        try:
            ip = dest.with_name(dest.stem + "_video_info.txt")
            ip.write_text(
                f"视频文件：{dest.name}\n（未检测到 ffprobe，无法解析时长/分辨率；"
                "可在设置页「本地运行时」一键安装 ffmpeg）\n", encoding="utf-8")
            rel.append(str(ip))
        except OSError:
            pass
    ffmpeg = _find_ff_bin("ffmpeg")
    if not ffmpeg:
        return rel
    # 1) 均匀抽帧（约每 dur/12 秒一帧，最多 12 张），供 vision LLM 读画面
    fdir = dest.with_name(dest.stem + "_frames")
    try:
        interval = max(1, int(round(dur / 12))) if dur > 12 else 1
        fdir.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [ffmpeg, "-y", "-i", str(dest),
             "-vf", f"fps=1/{interval}", "-frames:v", "12",
             str(fdir / "frame_%03d.jpg")],
            capture_output=True, text=True, timeout=600,
            encoding="utf-8", errors="replace", creationflags=_CNW)
        if r.returncode == 0 and any(fdir.iterdir()):
            rel.append(str(fdir))
    except Exception:
        pass
    # 2) 抽音轨（优先 mp3，失败退 wav）
    if has_audio:
        for ext, acodec in ((".mp3", "libmp3lame"), (".wav", "pcm_s16le")):
            ap = dest.with_name(dest.stem + "_audio" + ext)
            try:
                r = subprocess.run(
                    [ffmpeg, "-y", "-i", str(dest), "-vn",
                     "-acodec", acodec, "-ac", "1", "-ar", "16000", str(ap)],
                    capture_output=True, text=True, timeout=900,
                    encoding="utf-8", errors="replace", creationflags=_CNW)
                if r.returncode == 0 and ap.exists() and ap.stat().st_size > 0:
                    rel.append(str(ap))
                    break
            except Exception:
                continue
    return rel


def _resolve_vision_cred():
    """统一解析视觉模型的 (provider, api_base, api_key, model)。

    视觉质检脚本（data_fig_vision_check / tikz_vision_check）约定读
    EDITOR_AI_*（多模态）→ OPENAI_*（openai 兼容）→ 旧 gpt_image_key。
    此处与之一致，供图片 OCR 复用；无可用 key 时 api_key 为空。
    """
    # 1) 图片预设（多模态视觉模型，run_step_via_cli 注入 EDITOR_AI_* 的同源）
    img = db.get_default_image_preset()
    if img and (img.get("api_key") or "").strip():
        return ("openai", (img.get("api_base") or "").strip(),
                img["api_key"].strip(), (img.get("model") or "gpt-4o").strip())
    # 2) 默认 API 预设（openai 兼容，run_step_via_cli 注入 OPENAI_* 的同源）
    d = db.get_default_preset()
    if d and (d.get("api_key") or "").strip() \
            and (d.get("provider") or "openai").lower() in ("openai", ""):
        return ("openai", (d.get("api_base") or "").strip(),
                d["api_key"].strip(), (d.get("model") or "gpt-4o").strip())
    # 3) 旧 settings 字段（向后兼容）
    k = (db.get_setting("gpt_image_key", "") or "").strip()
    if k:
        return ("openai", (db.get_setting("gpt_image_base", "") or "").strip(),
                k, (db.get_setting("gpt_image_model", "") or "gpt-4o").strip())
    return ("openai", "", "", "")


_OCR_PROMPT = ("请识别这张数学建模赛题图片里的全部内容，原样输出文字与公式："
               "数学公式用 LaTeX 记法（行内 $...$，独立公式 $$...$$），"
               "表格按行输出、单元格用 | 分隔，图表里的坐标轴标签/图例文字也一并给出。"
               "只输出识别结果，不要解释。")


def _ocr_bytes(data: bytes, mime: str, prompt: str = "", cred=None) -> str:
    """对单张图片字节做视觉识别，返回文本；失败返回空串。"""
    prov, base, key, model = cred if cred else _resolve_vision_cred()
    if not key:
        return ""
    import base64
    try:
        b64 = base64.b64encode(data).decode("ascii")
    except Exception:
        return ""
    messages = [{"role": "user", "content": [
        {"type": "text", "text": prompt or _OCR_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
    ]}]
    try:
        from .llm import chat
        return (chat(prov, base, key, model, messages, temperature=0, max_tokens=3000) or "").strip()
    except Exception:
        return ""


def _ocr_image(dest: Path) -> str:
    """对上传图片做视觉 OCR/公式提取，写 <stem>_ocr.txt。

    复用视觉模型（与视觉质检脚本同一套 key 解析），把题面图片里的文字与公式
    转成文本（公式尽量 LaTeX 化）供 skill 优先读。未配置 key 或识别失败时静默
    返回空串，不阻断流水线（AI 仍可 Read 原图）。
    """
    if dest.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        return ""
    try:
        data = dest.read_bytes()
        ext = dest.suffix.lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg",
                "jpeg": "image/jpeg", "webp": "image/webp",
                "bmp": "image/bmp"}.get(ext, "image/png")
    except Exception:
        return ""
    txt = _ocr_bytes(data, mime)
    if not txt:
        return ""
    out = dest.with_name(dest.stem + "_ocr.txt")
    out.write_text(f"# 图片 OCR（Vision AI 自动识别）\n\n{txt}\n", encoding="utf-8")
    return str(out)


def _ocr_pdf_pages(dest: Path, text_len_threshold: int = 120) -> str:
    """PDF 公式图/扫描页兜底：把文字层缺失/稀少的页用 PyMuPDF 渲染成 PNG 再 OCR。

    写 <stem>_pages_ocr.txt（与 _extract_text 产出的 <stem>_extracted.txt 互补：
    前者覆盖文字层为空/几乎为空的扫描页、公式截图页）。fitz(PyMuPDF) 缺失或未配置
    视觉 key 时静默跳过，不阻断流水线。
    """
    if dest.suffix.lower() != ".pdf":
        return ""
    cred = _resolve_vision_cred()
    if not cred[2]:
        return ""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ""
    try:
        doc = fitz.open(str(dest))
    except Exception:
        return ""
    out_lines = []
    try:
        for i, page in enumerate(doc):
            text = (page.get_text() or "").strip()
            # 文字层足够丰富的页走 _extracted.txt，不重复 OCR；只兜底扫描/图片页
            if len(text) >= text_len_threshold:
                continue
            try:
                pix = page.get_pixmap(dpi=150)
                data = pix.tobytes("png")
            except Exception:
                continue
            txt = _ocr_bytes(data, "image/png", cred=cred)
            if txt:
                out_lines.append(f"## 第 {i + 1} 页（位图 OCR 兜底）\n{txt}")
    finally:
        try:
            doc.close()
        except Exception:
            pass
    if not out_lines:
        return ""
    out = dest.with_name(dest.stem + "_pages_ocr.txt")
    out.write_text(
        "# PDF 扫描页/公式图 OCR（Vision AI 位图兜底）\n\n"
        + "\n\n".join(out_lines) + "\n", encoding="utf-8")
    return str(out)


def _save_assets(workspace, config):
    """把前端上传的资料文件写进 workspace。

    config['files'] 形如：[{name, path(绝对路径), cat}]
    cat ∈ problem / prob_img / data / template / outline
    落盘约定：
      user_data/problem/    赛题正文/文档
      user_data/prob_img/   赛题图片
      user_data/data/       数据附件（csv/xlsx/json…）
      user_data/template/   格式模板（tex/cls/docx…）
      user_data/outline/    解题思路/大纲文档
    返回落盘文件索引（相对 workspace 的路径列表，供 prompt 引用）。
    """
    ud = workspace / "user_data"
    rel = []
    for f in config.get("files", []) or []:
        src = Path(f.get("path", ""))
        if not src.exists():
            continue
        cat = f.get("cat", "data")
        # 前端 cat 前缀 cf 与后端目录映射对齐
        dir_map = {"problem": "problem", "cfProblem": "problem",
                   "prob_img": "prob_img", "cfProbImg": "prob_img", "cfImg": "prob_img",
                   "data": "data", "cfData": "data",
                   "template": "template", "cfTemplate": "template",
                   "outline": "outline", "cfOutline": "outline"}
        sub = dir_map.get(cat, "data")
        dest_dir = ud / sub
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            dest = dest_dir / src.name
            dest.write_bytes(src.read_bytes())
            rel.append(str(dest.relative_to(workspace)).replace("\\", "/"))
            # PDF/docx/xlsx 自动抽取文本，供 skill 优先读取（赛题公式不丢）
            if cat in ("problem", "cfProblem", "data", "cfData", "outline", "cfOutline"):
                ext = _extract_text(dest)
                if ext:
                    rel.append(str(Path(ext).relative_to(workspace)).replace("\\", "/"))
                # PDF 扫描页/公式图兜底：文字层缺失页 → PyMuPDF 转 PNG → 视觉 OCR
                if dest.suffix.lower() == ".pdf":
                    poc = _ocr_pdf_pages(dest)
                    if poc:
                        rel.append(str(Path(poc).relative_to(workspace)).replace("\\", "/"))
                # 视频：ffprobe 元信息 + 关键帧 + 音轨（AI 可读画面/转写音频）
                if dest.suffix.lower() in _VIDEO_EXTS:
                    for vp in _extract_video(dest):
                        try:
                            rel.append(str(Path(vp).relative_to(workspace)).replace("\\", "/"))
                        except ValueError:
                            rel.append(str(vp).replace("\\", "/"))
            # 图片：视觉 OCR/公式提取（写 <stem>_ocr.txt 供 skill 优先读）
            if dest.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                ocr = _ocr_image(dest)
                if ocr:
                    rel.append(str(Path(ocr).relative_to(workspace)).replace("\\", "/"))
        except Exception:
            continue
    return rel

def _save_question(workspace, config):
    """把纯文本赛题/补充说明写盘。"""
    q = (config.get("question") or "").strip()
    supp = (config.get("supplement") or "").strip()
    if q or supp:
        ud = workspace / "user_data"
        ud.mkdir(parents=True, exist_ok=True)
        text = ""
        if q:
            text += f"# 赛题正文\n{q}\n"
        if supp:
            text += f"\n# 赛题补充说明\n{supp}\n"
        (ud / "PROBLEM.md").write_text(text, encoding="utf-8")
        return "user_data/PROBLEM.md"
    return ""

def build_user_message(step, config, file_index, template="competition"):
    """按步骤构造单行用户消息：主题 + 自定义要求 + 文件索引 + 表单参数。

    火山方舟 Agent Plan 的 Anthropic 兼容层会把包含换行的 prompt 误路由到账号旧模型
    （已实测变成 sensenova/deepseek），而相同内容压成单行会稳定使用 ark-code-latest。
    SKILL 全文已经通过 --append-system-prompt-file / CLAUDE.md 注入，因此用户消息可安全
    单行化，不影响 Markdown 产物格式。
    """
    agent_role = ("你是数学建模竞赛全自动求解智能体。"
                  if is_competition_template(template)
                  else "你是一名严谨的科研与学术写作智能体，按 skill 流程逐步完成本工作流。")
    lines = [agent_role]
    head = [
        ("question", "【赛题/研究内容/主题】") if is_competition_template(template)
        else ("question", "【研究主题/待办内容】"),
        ("custom_require", "【自定义要求（最高优先级，冲突时以此为准）】"),
        ("outline", "【解题思路/大纲】"),
    ]
    for key, label in head:
        v = (config.get(key) or "").strip()
        if v:
            lines.append(f"\n{label}\n{v}")
    # 已上传且已落盘的文件索引
    if file_index:
        lines.append("\n【本工作流的已有资料（已落盘到 user_data 目录，可读取）】\n" +
                     "\n".join(f"- {p}" for p in file_index))
    # 竞赛级表单参数：注入到上下文让 skill 按需遵守
    params = _fmt_config_params(config)
    if params:
        lines.append(f"\n【本工作流表单配置（供参考，具体以 skill 为准）】\n{params}")
    lines.append(f"请严格按上方 skill 的流程完成本步骤（{step['label']}），并把产出写为对应文件。")
    # 火山 Agent Plan /api/plan 对包含换行的 Claude CLI prompt 存在路由歧义：
    # 同一 ark-code-latest 在单行时正常，多行时会被服务端切到账号旧模型。
    # 将用户消息压成单行；完整多行规则仍在 CLAUDE.md 与 system prompt，不损失语义。
    return " ； ".join(" ".join(str(x).split()) for x in lines if str(x).strip())

# 角色 -> settings 键映射
# 兼容旧式 model 字段的兜底默认（无任何预设/未指定时的最后回退）
_LEGACY_DEFAULT_MODEL = "gpt-4o-mini"

def _default_model_for(provider):
    """按协议回退默认模型：Anthropic Messages 网关会把 claude-* 映射到自家模型；
    此前空模型一律回退 gpt-4o-mini，会让 Anthropic 预设（DeepSeek/GLM/MiniMax 等）
    在第一步就被网关以「模型不存在」拒绝（配置了 key 也跑不动的元凶）。"""
    return "claude-sonnet-4-5" if (provider or "").lower() == "anthropic" \
        else "gpt-4o-mini"

def resolve_model(role, config=None):
    """解析某步骤实际使用的 API，返回 (provider, api_base, api_key, model)。

    数据源：api_presets 预设库。
    优先级：
      0. config['step_models'][role] 若命中「预设名」→ 用该预设（按步骤覆盖）；
         config['step_models'][role] 为非空非预设名 → 视为真实 model id，套默认连接；
      0.5) 角色专用模型（设置页三下拉接线）：
         role=review 命中 reviewer_model → 套默认预设连接换该 model（跨模型复核）；
         role=improve/paper 命中 editor_model → 同上（编辑改稿轻量模型）。
         仅在 step_models 未覆盖该步时生效，比步骤级覆盖优先级低；
      1. config['model'] 若命中「预设名」→ 用该预设；
      2. config['model'] 是非空且非预设名 → 视为真实 model id，用默认预设的 base/key 覆盖 model；
      3. 否则直接用「全局默认预设」；若预设 extra 含 model_map 且命中当前角色，
         换成映射后的实际模型（fallback_model 作未命中角色时的兜底）；
      4. 没有默认预设 → 回退到旧的 executor_model 设置（兼容旧数据），再没有则抛错。
    """
    presets = db.list_presets()
    preset_map = {p["name"]: p for p in presets if p.get("name")}
    default = db.get_default_preset()

    def pick(p):
        _prov = (p.get("provider") or "openai").strip()
        return (_prov, p.get("api_base") or "",
                p.get("api_key") or "", p.get("model") or _default_model_for(_prov))

    def via_model(uni, fallback_pick):
        """根据给定的 model 选择：命中预设用预设，否则套默认连接。"""
        m = (uni or "").strip()
        if not m:
            return fallback_pick
        hit = preset_map.get(m)
        if hit:
            return pick(hit)
        if default:
            return (default.get("provider") or "openai", default.get("api_base") or "",
                    default.get("api_key") or "", m)
        return ("openai", "", "", m)

    # 0) 按步骤覆盖（前端「每步指定」）
    step_models = (config or {}).get("step_models") or {}
    if isinstance(step_models, dict) and (step_models.get(role) or "").strip():
        return via_model(step_models.get(role), None)

    # 0.5) 角色专用模型（设置页「审稿者 / 编辑器 AI」下拉接线）
    #      值语义：存预设名或裸 model id；连接走默认预设（跨模型复核用别家 key 时
    #      请直接建预设并把 step_models 指向它，角色字段只切模型不切连接）。
    if not isinstance(step_models, dict) or not (step_models.get(role) or "").strip():
        role_setting = ""
        if role == "review":
            role_setting = db.get_setting("reviewer_model", "") or ""
        elif role in ("improve", "paper"):
            role_setting = db.get_setting("editor_model", "") or ""
        role_setting = (role_setting or "").strip()
        if role_setting and not preset_map.get(role_setting):
            # 非预设名：套默认连接换模型；默认连接不存在则忽略角色字段
            if default:
                return (default.get("provider") or "openai", default.get("api_base") or "",
                        default.get("api_key") or "", role_setting)
        elif role_setting:
            return pick(preset_map[role_setting])

    uni = ((config or {}).get("model") or "").strip()
    if uni:
        hit = preset_map.get(uni)
        if hit:
            return pick(hit)
        # 指定了具体模型 id：套用默认预设的连接，但用该 model
        if default:
            return (default.get("provider") or "openai", default.get("api_base") or "",
                    default.get("api_key") or "", uni)
        return ("openai", "", "", uni)
    if default:
        if default:

            prov, base, key, mdl = pick(default)

            # 高级选项：模型映射 / 默认兜底（extra.model_map / extra.fallback_model）

            try:

                extra = default.get("extra") or {}

                mmap = extra.get("model_map") or {}

                if isinstance(mmap, dict) and mmap.get(role):

                    mdl = mmap[role]

                elif extra.get("fallback_model"):

                    mdl = extra["fallback_model"]

            except Exception:

                pass

            return (prov, base, key, mdl)

        return pick(default)
    # 兼容旧数据：旧 executor_model 设置
    legacy = db.get_setting("executor_model") or ""
    if legacy:
        hit = preset_map.get(legacy)
        if hit:
            return pick(hit)
        return ("openai", "", "", legacy)
    raise LLMError("未配置任何 API 预设，请在「设置」页新增并设为默认")

def _fmt_config_params(config):
    """把前端开关/数量/风格等参数整理成一行行描述，供 skill 感知。"""
    maps = {
        "contest": "赛项",
        "qiHao": "题号",
        "out_format": "输出格式",
        "review_mode": "审查模式",
        "page_limit": "页数限制",
        "rich_mode": "丰满模式",
        "logic_review": "逻辑对抗复核",
        "flow_engine": "流程图引擎",
        "color_scheme": "图表配色",
        "chart_style": "图表风格",
        "data_palette": "数据图配色方案",
        "data_layout": "图表版式",
        "img_count": "图片数量",
        "tbl_count": "表格数量",
        "model_count": "模型数量",
        "data_fig_check": "数据图视觉质检",
        "per_flow": "每个问题都画求解流程图",
        "only_total": "只画总图",
        "flow_fig_check": "流程图/架构图视觉质检",
        "ai_declare": "AI工具使用声明",
        "manual_checkpoint": "人工检查点",
        "improve_loop": "论文改进循环",
        "model_alloc": "模型分配方式",
    }
    out = []
    for k, label in maps.items():
        v = config.get(k)
        if v is None or v == "":
            continue
        if isinstance(v, bool):
            out.append(f"{label}: {'开启' if v else '关闭'}")
        else:
            out.append(f"{label}: {v}")
    return "\n".join(out)

def run_check(ws, wid, key, step):
    """运行步骤的自检脚本（如存在且可运行）。返回 (ok, detail)。

    优先使用项目内 Python 等价脚本（_utils_py），保证 Windows 无 bash 也能跑；
    否则回退到桌面共享脚本目录。.py 用当前解释器，.sh 若无 bash 则跳过并说明。
    """
    script = step.get("check")
    if not script:
        return True, "无自检脚本"
    # 解释器：源码模式 sys.executable；打包(frozen)后用独立 Python（step_audit 必须真跑）
    py = sys.executable
    if paths.FROZEN:
        _py = resolve_python()
        if not _py:
            return True, "未找到独立 Python，跳过子进程自检"
        py = _py
    parts = script.split()
    prog = parts[0]
    args = parts[1:]
    # 项目内 python 等价脚本优先（Windows 无 bash：.sh 自动映射同名 .py）
    local = PROJECT_UTILS / (prog[:-3] + ".py") if prog.endswith(".sh") else PROJECT_UTILS / prog
    candidates = ([local] if local.exists() else []) + [UTILS_DIR / prog]
    spath = next((p for p in candidates if p.exists()), None)
    if not spath:
        return True, f"自检脚本 {prog} 不存在，跳过"
    # .sh 脚本在 Windows 优先找对应 .py 或 python 等价名
    if spath.suffix.lower() == ".sh":
        pyp = PROJECT_UTILS / (spath.with_suffix(".py").name)
        if pyp.exists():
            spath = pyp
        else:
            return True, f"自检脚本 {prog} 为 shell 脚本，本机无 bash，跳过"
    try:
        # 外层超时:默认 900s(step_audit 套件内部子审计各带 60-180s 超时逐项兜底,
        # 外层只防整套悬挂;120s 会误杀死多子审计的 code/compile 套件判假阻断)
        timeout = step.get("check_timeout", 900)
        import os as _os
        _env = dict(_os.environ)
        _env.setdefault("PYTHONIOENCODING", "utf-8")
        if paths.FROZEN:
            _mei = _os.environ.get("_MEIPASS") or getattr(sys, "_MEIPASS", None)
            if _mei:
                _pp = _env.get("PYTHONPATH", "")
                _env["PYTHONPATH"] = _mei + (";" + _pp if _pp else "")
        r = subprocess.run([py, str(spath), *args],
                           cwd=str(ws), capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", env=_env, creationflags=_CNW)
        # 约定：0=通过 1=失败(阻断) 2=无清单/跳过(不阻断)。rc∈{0,2} 视为通过
        ok = r.returncode in (0, 2)
        return ok, (r.stdout + r.stderr)[-500:]
    except Exception as e:
        return False, str(e)

# ---------------- PDF 编译（修复：compile/improve 步骤真实调用 xelatex） ----------------
_XELATEX_CANDIDATES = [
    shutil.which("xelatex"),
    r"C:\texlive\2026\bin\windows\xelatex.exe",
    r"C:\texlive\2025\bin\windows\xelatex.exe",
    r"C:\texlive\2024\bin\windows\xelatex.exe",
]

def find_xelatex():
    """定位 xelatex：PATH → 常见 TeXLive 安装路径。找不到返回 None。"""
    for c in _XELATEX_CANDIDATES:
        if c and Path(c).exists():
            return c
    return None

# ---------------- 竞赛模板资产（cls/sty 等，供 xelatex 找到文档类） ----------------
# 素材来源：随包分发的 _templates/<contest>/（字体走系统自带，模板骨架随包分发）
TEMPLATE_DIR_CANDIDATES = [
    paths.BASE / "_templates",
]
_CLASS_TEMPLATE_HINTS = [          # 文档类名 → 模板目录名（子串匹配，命中即用）
    ("cumcmthesis", ["cumcm", "huazhong"]),
    ("mathorcupmodeling", ["mathorcup"]),
]

def _template_base():
    """定位竞赛模板库根目录：settings/templates_dir → 项目 _templates → 旧版遗留路径。"""
    custom = _setting_dir("templates_dir", "MODELFLOW_TEMPLATES_DIR")
    if custom:
        return custom
    for p in TEMPLATE_DIR_CANDIDATES:
        if p.exists():
            return p
    return None

def ensure_template_assets(ws):
    """在编译前把 main.tex 所用文档类的模板文件补到同目录。

    读 paper/main.tex（或 ws/main.tex）的 \\documentclass{Name}，
    在模板库各竞赛目录里找 <Name>.cls；找到就把该目录下所有 ≤512KB 的文件
    （cls/sty/bst/tex/图片等）复制进 tex 所在目录。大字体不复制的理由：
    中文 Windows 自带宋体/楷体，实际编译时也没把这些字体放进 paper/。
    """
    base = _template_base()
    if not base or not base.is_dir():
        return ""
    tex = None
    for cand in (ws / "paper" / "main.tex", ws / "main.tex"):
        if cand.is_file():
            tex = cand
            break
    if not tex:
        return ""
    try:
        head = tex.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return ""
    m = re.search(r"\\documentclass(?:\[[^\]]*\])?\s*\{([A-Za-z][\w.-]*)\}", head)
    if not m:
        return ""
    cls_name = m.group(1)
    # 目录优先级：按文档类名提示的竞赛目录在前，其余兜底
    hinted = []
    for frag, dirs in _CLASS_TEMPLATE_HINTS:
        if frag.lower() == cls_name.lower():
            hinted = dirs
            break
    order = hinted + [d.name for d in base.iterdir()
                      if d.is_dir() and d.name not in hinted]
    for dname in order:
        tdir = base / dname
        cls = next(tdir.rglob(cls_name + ".cls"), None) if tdir.is_dir() else None
        if not cls:
            continue
        dest = tex.parent
        copied = []
        try:
            for f in cls.parent.rglob("*"):
                if f.is_file() and f.stat().st_size <= 512 * 1024 \
                        and f.suffix.lower() not in (".ttf", ".ttc", ".otf"):
                    target = dest / f.name
                    if not target.exists():
                        shutil.copy2(f, target)
                        copied.append(f.name)
            if copied:
                shutil.copy2(cls, dest / cls.name)
                copied.append(cls.name)
        except OSError:
            pass
        return f"已注入模板 {dname}/{cls.name}（+{len(copied)} 个辅助文件）"
    return ""

def compile_pdf(ws, rounds=3, timeout=300):
    """在工作区内真编译 main.tex → main.pdf（xelatex 子进程，回收日志）。

    查找顺序：workspace/paper/main.tex → workspace/main.tex。
    每遍编译输出末 800 字符累积进 compile_log.txt；若失败，摘要一并给出。
    返回 (ok, 摘要)。ok=False 表示找不到 xelatex / 无 main.tex / 编译失败 / 未产出 PDF。
    """
    xelatex = find_xelatex()
    if not xelatex:
        return False, "未找到 xelatex（PATH 与 TeXLive 2024-2026 默认路径均无），无法编译"
    tex = ws / "paper" / "main.tex"
    if not tex.is_file():
        tex = ws / "main.tex"
    if not tex.is_file():
        return False, "未找到 main.tex（paper/main.tex 与 workspace 根均无），无法编译"
    tpl_note = ensure_template_assets(ws)
    # 追加式日志：保留每次调用（含修复循环多轮重编译）的完整证据链
    logs = ([f"--- 模板资产 ---\n{tpl_note}"] if tpl_note else [])
    ok = True
    for i in range(rounds):
        try:
            r = subprocess.run([xelatex, "-interaction=nonstopmode", "-synctex=1", tex.name],
                               cwd=str(tex.parent), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout, creationflags=_CNW)
        except subprocess.TimeoutExpired:
            logs.append(f"--- 第 {i+1}/{rounds} 遍 xelatex 超时({timeout}s)，中止 ---")
            ok = False
            break
        tail = (r.stdout + r.stderr)[-800:]
        logs.append(f"--- 第 {i+1}/{rounds} 遍 xelatex (rc={r.returncode}) ---\n{tail}")
        if r.returncode != 0:
            ok = False
            break
    try:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(ws / "compile_log.txt", "a", encoding="utf-8") as fh:
            fh.write(f"\n===== 会话 {stamp} =====\n" + "\n".join(logs) + "\n")
    except OSError:
        pass
    pdf = tex.parent / "main.pdf"
    if not pdf.is_file() or pdf.stat().st_size == 0:
        return False, "xelatex 未产出 main.pdf（详见 compile_log.txt）\n" + "\n".join(logs)
    return ok, f"xelatex 编译完成，main.pdf {pdf.stat().st_size} bytes，日志见 compile_log.txt"





# ---------------- CLI 执行器（claude CLI agent 会话） ----------------
# 每步以工作区为 cwd 启动 Claude Code，几十轮工具往返真实读写执行。
# 执行方式：claude -p --output-format stream-json，凭据经环境变量透传给网关。

CONTEST_TEMPLATE_MAP = [          # 赛项关键词 → 模板目录（_templates/<name>/）
    ("国赛", "cumcm"), ("cumcm", "cumcm"),
    ("华中杯", "huazhong"), ("mathorcup", "mathorcup"), ("mathorcups", "mathorcup"),
    ("华为杯", "huawei"), ("美赛", "mcm"), ("mcm", "mcm"), ("icm", "mcm"),
    ("电工杯", "diangongbei"), ("东三省", "dongsansheng"), ("辽宁省", "dongsansheng"),
    ("数维杯", "shuweibei"), ("华数杯", "huashubei"), ("五一杯", "wuyi"),
    ("长三角", "changsanjiao"), ("统计建模", "stats"), ("亚太", "apmcm_zh"),
    ("apmcm", "apmcm"),
]

def _contest_template_names(config):
    """根据表单赛项名推断要注入工作区的模板目录列表（匹配 + cumcm 兜底）。"""
    contest = str((config or {}).get("contest") or "")
    low = contest.lower()
    hits = []
    for kw, d in CONTEST_TEMPLATE_MAP:
        if kw.lower() in low or kw in contest:
            if d not in hits:
                hits.append(d)
            break                      # 首个命中即止，避免 apmcm 连带 apmcm_zh
    return hits or ["cumcm"]


# ---------------- 图表风格标记映射（前端选择 → skill 自动读取的环境变量） ----------------
# 1) 图表配色 color_scheme（纯黑白/朴素竞赛/现代精致）→ paper-figure-html 的 MH_DIAGRAM_STYLE
_DIAGRAM_STYLE = {"bw": "2", "plain": "0", "modern": "1"}
# 2) 数据图配色 data_palette（中文名）→ plot_utils.PALETTES 键
_DATA_PALETTE = {
    "经典柔和（原默认）": "soft", "Okabe-Ito 经典": "okabe_ito", "Tol 柔和": "tol_muted",
    "Tol 明快": "tol_vibrant", "北欧 Nord": "nord",
    "日暮渐变": "sunburst", "海洋青蓝": "ocean", "珊瑚": "coral", "明快春日": "spring",
    # —— 期刊 / 顶刊风 ——
    "期刊顶刊（SCI）": "journal", "Nature 顶刊": "nature", "NEJM 医学": "nejm",
    "Science 学术": "science", "Tableau 专业": "tableau", "NPG 自然": "npg",
    "色盲友好（Wong）": "colorblind",
    # —— 气质风格 ——
    "优雅 Elegant": "elegant", "柔和粉彩": "pastel", "薄荷薰衣草": "mint_lav",
    "鼠尾草玫瑰": "sage_rose", "大地森林": "earth_forest", "孔雀青": "peacock",
    "沙漠暖沙": "desert", "钴蓝珊瑚": "cobalt_coral", "星空紫金": "plum_gold",
    # —— 复古 / 个性 ——
    "火烈鸟": "flamingo", "复古霓虹": "retro", "荷兰田野": "dutch_field",
    "红酒": "wine", "苔藓陶土": "moss_clay", "青橙": "teal_orange",
    # —— 知名配色库（GitHub 公认） ——
    "现代明亮（Urban）": "urban", "科研经典（SCI）": "sci_std",
    "Kelly 对比": "kelly", "材质亮色": "plasma_bright",
}
# 3) 图表版式 data_layout（中文名）→ plot_utils.STYLE_FAMILIES 键
_DATA_LAYOUT = {
    "清爽开放": "clean_open", "柔和网格": "soft_grid", "框线期刊": "framed_journal",
    "极简无框": "minimal_bare", "粗描边": "bold_edge", "清晰深轴": "crisp_dark",
    "SCI 期刊框线": "sci_frame", "柔和细网格": "soft_mesh", "加粗面板": "bold_panel",
    "通透留白": "airy_open", "点状网格": "dotted_grid", "紧凑期刊": "journal_compact",
}
# 4) 图表风格 chart_style（默认柔和学术 soft / Nature）——仅在用户未手选具体配色时，
#    Nature 才强制锁定 nature 配色；soft 视为默认（不强制，保留种子随机去指纹）。
_CUSTOM_FALLBACK_COLORS = "#5B9BD5,#ED7D7D,#7BC8A4,#B0B0B0,#9B8EC4,#F4A261"


def _fig_markers(config):
    """把前端图表相关选择翻译成 skill 会读取的 CLAUDE.md 标记行。

    返回 marker 字符串列表（无对应选择时留空项）。所有 skill 都是 grep CLAUDE.md
    的 `MH_*` 标记，故这里直接产出可被 grep 命中的行，保证选项真正生效。
    """
    cfg = config or {}
    markers = []
    # 图表配色 → 流程图/架构图风格族（paper-figure-html 读 MH_DIAGRAM_STYLE）
    cs = (cfg.get("color_scheme") or "bw")
    dg = _DIAGRAM_STYLE.get(cs, "2")
    markers.append(f"MH_DIAGRAM_STYLE={dg}")
    # 数据图配色（优先手选 data_palette，其次 chart_style=Nature）
    pal = (cfg.get("data_palette") or "").strip()
    chart_style = (cfg.get("chart_style") or "soft").strip()
    if pal in _DATA_PALETTE:
        markers.append(f"MH_DATA_FIG_PALETTE={_DATA_PALETTE[pal]}")
    elif pal == "自定义":
        markers.append("MH_DATA_FIG_PALETTE=custom")
        markers.append(f"MH_DATA_FIG_COLORS={_CUSTOM_FALLBACK_COLORS}")
    elif chart_style == "nature":
        markers.append("MH_DATA_FIG_PALETTE=nature")
    # 图表版式（data_layout）
    lay = (cfg.get("data_layout") or "").strip()
    if lay in _DATA_LAYOUT:
        markers.append(f"MH_DATA_FIG_STYLE={_DATA_LAYOUT[lay]}")
    # 数据图视觉质检（paper-figure 读 MH_DATA_FIG_VISION=1）
    if cfg.get("data_fig_check"):
        markers.append("MH_DATA_FIG_VISION=1")
    # 流程图/架构图/TikZ 视觉质检：skill 读 MH_SKIP_DIAGRAM_VISION=1 表示「关闭/跳过」。
    # 默认关闭（省额度）：不勾选 → 输出跳过标记；勾选开启 → 不输出，skill 照常跑 vision。
    if not cfg.get("flow_fig_check"):
        markers.append("MH_SKIP_DIAGRAM_VISION=1")
    # 审查模式：快速 → skill 读 MH_FAST_MODE=1 跳过/降级昂贵步骤（comp-review/vision/改进等）
    if (cfg.get("review_mode") or "").strip().lower() == "fast":
        markers.append("MH_FAST_MODE=1")
    # 每个问题都画求解流程图（comp-prob-analysis 读 MH_FLOW_PER_PROBLEM=1）
    if cfg.get("per_flow"):
        markers.append("MH_FLOW_PER_PROBLEM=1")
    # 丰满模式（comp-paper-zh 读「丰满模式」关键词；显式给出更可靠）
    if cfg.get("rich_mode"):
        markers.append("MH_RICH_MODE=1")
    return markers


def _write_env_skill(ws, config):
    """把前端数值参数写成工作区 `.env_skill`，供 skill 内 `source .env_skill` 读取。

    skill 里的硬目标自检（MIN_FIGURES/MIN_TABLES/MIN_MODELS/MAX_PAGES）约定：
    `source .env_skill 2>/dev/null || true` 后按 shell 变量读取，仅在数值 > 0 时
    触发硬阻塞（否则走 skill 默认自动行为）。此处只翻译用户显式手填的数值：
      img_count   -> MIN_FIGURES   （「高级选项」数据图最低张数）
      tbl_count   -> MIN_TABLES
      model_count -> MIN_MODELS
      page_limit  -> MAX_PAGES     （正文页数上限）
    值为 auto/空/非法时省略对应行；全部 auto 则不生成文件（skill 自行绕过）。
    """
    cfg = config or {}

    def _num(v):
        try:
            n = int(str(v).strip())
            return n if n > 0 else None
        except (ValueError, AttributeError):
            return None

    pairs = (
        ("MIN_FIGURES", _num(cfg.get("img_count"))),
        ("MIN_TABLES", _num(cfg.get("tbl_count"))),
        ("MIN_MODELS", _num(cfg.get("model_count"))),
        ("MAX_PAGES", _num(cfg.get("page_limit"))),
    )
    lines = [f"{k}={v}" for k, v in pairs if v is not None]
    if not lines:
        return
    try:
        (ws / ".env_skill").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def _env_anchor(step, ws):
    """按步骤生成「环境锚点」——只写本步真正会调用的工具入口，不注入无关内容。

    上下文过长或换目录后，AI 据此恢复确定性入口，不靠猜路径；每个位置的锚点不同，
    用不到的工具（如 xelatex/vision）不写，避免徒增读取负担。
    """
    key = (step or {}).get("key") or ""
    _py = resolve_python() or "（未检测到，请用 `py -3` 或安装 Python 3.12）"
    _tools = str((ws / "_utils").resolve())
    lines = [
        "## 环境锚点（本步专用，换目录/上下文过长后据此恢复工具入口）",
        f"- Python 解释器：`{_py}`（优先用 `$MH_PYTHON`，未注入时用此绝对路径，不要猜 python/python3）",
        f"- 工具链目录：`{_tools}`（`bash _utils/*.sh` / `$MH_PYTHON _utils/*.py` / `cat _utils/*.md` 都相对此目录）",
    ]
    # BZD 双审精制流：cumcm-bzd-2026 资产注入目录（脚本/状态模板/模板库），环境变量 MH_BZD_DIR
    _bzd = ws / "_bzd"
    if (_bzd / "scripts").is_dir():
        lines.append(f"- BZD 资源目录：`${{MH_BZD_DIR}}` = `{_bzd.resolve()}`（评分脚本 `${{MH_BZD_DIR}}/scripts/score_artifact.py`、环境自检 `doctor.py`、数模字典 `query_model_dict.py`；状态模板 `${{MH_BZD_DIR}}/templates/shared/decision_log.json`；规则与成稿模板 `${{MH_BZD_DIR}}/references/...`）")
    # 涉及数据读写/画图/论文的步 → 核心库
    if key in ("analysis", "modeling", "code", "figure", "arch", "paper"):
        lines.append("- matplotlib/numpy/pandas/scipy 已装于此 Python，直接 import 即可（画数据图/读写数据）")
    # 视觉质检步 → vision API 入口（未配置时脚本自动跳过，不阻塞）
    if key in ("figure", "arch"):
        lines.append("- 视觉质检脚本读环境变量 EDITOR_AI_API_KEY/EDITOR_AI_BASE_URL（或 OPENAI_API_KEY/OPENAI_BASE_URL）；未配置时脚本自动降级跳过，不阻塞")
    # 流程/架构图步 → 出图内核
    if key == "arch":
        lines.append("- HTML→PDF 出图用 `_utils/screenshot_capture.py --file … --out … --format pdf`；无 Electron 时自动降级，不阻塞")
    # 编译/改进步 → LaTeX
    if key in ("compile", "improve"):
        lines.append("- LaTeX 编译用 xelatex/latexmk（未安装 `winget install MiKTeX.MiKTeX`）")
    return "\n".join(lines)


def prepare_cli_workspace(ws, config, file_index, step_list=None, current=None, template="competition"):
    """工作区布局：写 CLAUDE.md（流水线规则+当前步骤指令）+ 注入赛项模板。

    claude CLI 会自动读取 cwd 下 CLAUDE.md 作为项目级指令——SKILL.md 内容经由
    它进入上下文，规避 Windows 命令行 32K 长度上限。
    """
    # 1) 模板库整体搬进工作区（workspace/_templates），≤4MB 文件、跳过字体包
    base = _template_base()
    copied_dirs = []
    if base and base.is_dir():
        for tname in _contest_template_names(config):
            tdir = base / tname
            dest = ws / "_templates" / tname
            if not tdir.is_dir():
                continue
            dest.mkdir(parents=True, exist_ok=True)
            n = 0
            for f in tdir.rglob("*"):
                if f.is_file() and f.stat().st_size <= 4 * 1024 * 1024 \
                        and f.suffix.lower() not in (".ttf", ".ttc", ".otf"):
                    rel = f.relative_to(tdir)
                    (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(f, dest / rel)
                        n += 1
                    except OSError:
                        pass
            copied_dirs.append(f"{tname}({n})")
    # 1.5) _utils 工具链注入：SKILL 提示词里 `bash _utils/….sh` / `$PYTHON _utils/….py`
    #      / `cat _utils/….md` 全部真实可达（此前只搬
    #      _templates/，CLI 引擎里这些命令静默失败）。全量拷 _utils_py -> ws/_utils。
    utils_src = PROJECT_UTILS
    if utils_src.is_dir():
        dest = ws / "_utils"
        dest.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in utils_src.rglob("*"):
            if f.is_file() and f.stat().st_size <= 8 * 1024 * 1024:
                rel = f.relative_to(utils_src)
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(f, dest / rel)
                    n += 1
                except OSError:
                    pass
        if n:
            copied_dirs.append(f"_utils({n})")
    # 1.6) BZD 双审精制流资产注入：把 cumcm-bzd-2026（scripts/config/templates/references）
    #      整体拷入 ws/_bzd，使 CLI agent 能按环境变量 MH_BZD_DIR 确定性调用
    #      doctor.py / score_artifact.py / query_model_dict.py 与读取状态模板、模板库。
    #      （否则 stage-01 等入口 SKILL 里写的"随包 xxx"在 cwd=workspace 下不可达，模型会
    #       用文本模拟替代脚本，评分闸门落不到代码上。）
    if (is_competition_template(template) and template == "competition_bzd") or \
            (current and (current.get("skill") or "").startswith("bzd-2026-")):
        bzd_src = SKILLS_DIR / "cumcm-bzd-2026"
        if bzd_src.is_dir():
            bzd_dest = ws / "_bzd"
            if not bzd_dest.exists():
                try:
                    shutil.copytree(bzd_src, bzd_dest,
                                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                    copied_dirs.append(f"_bzd(cumcm-bzd-2026)")
                except OSError:
                    pass
    # 2) CLAUDE.md：流水线概览 + 规则 + 上传文件清单 + 当前步骤的 SKILL 全文
    labels = " > ".join(s["label"] for s in (step_list or COMPETITION_STEPS))
    cur_block = ""
    if current:
        skill_txt = compose_skill_prompt(current.get("skill") or "", template or "competition", current.get("key") or "")
        cur_block = ("\n## ⛔ 当前步骤指令（最高优先级，严格遵循）\n\n"
                     f"步骤：{current.get('label')}（skill: {current.get('skill')}）\n"
                     "产出主文件：" + str(current.get("out") or "") + "\n\n"
                     "--- SKILL 全文开始 ---\n" + skill_txt + "\n--- SKILL 全文结束 ---\n")
    files_block = ""
    if file_index:
        files_block = "\n## 用户上传的文件（已落盘，可直接读取）\n" + \
            "\n".join(f"- {p}" for p in file_index) + "\n"
    # 能力清单契约摘要（分析步产出的 CAPABILITY_CHECKLIST.json 是跨步骤
    # 契约，建模/论文步必须逐项对应）。存在时注入精要区块，显式化跨步依赖。
    cap_block = ""
    try:
        cap_file = ws / "CAPABILITY_CHECKLIST.json"
        if cap_file.is_file():
            _cd = json.loads(cap_file.read_text(encoding="utf-8"))
            _caps = _cd.get("capabilities") or []
            _nsp = _cd.get("n_subproblems") or len(_cd.get("subproblems") or [])
            if _caps:
                _lines = [f"- 共 {_nsp} 个子问题 / {len(_caps)} 条能力项（摘录前 12 条）："]
                for _c in _caps[:12]:
                    _name = (_c.get("name") or _c.get("capability") or "?")[:40]
                    _lines.append(f"  · {_name}")
                cap_block = ("\n## 上一步能力清单契约（CAPABILITY_CHECKLIST.json，工作区内有全文）\n"
                             "本步产出必须逐项覆盖/引用这些能力项编号，不得遗漏或另起炉灶：\n"
                             + "\n".join(_lines) + "\n")
    except Exception:
        cap_block = ""
    # 全程遵守条款区（CLAUDE.md 规则区：表单选择硬编码为强制条款）
    comp = is_competition_template(template)
    rules = []
    if comp:
        rules.append("- 使用中文撰写论文（除非是 LaTeX 代码）；国赛 CUMCM 只需要中文摘要，不要英文摘要")
        _cname = (config or {}).get("contest") or ""
        if _cname:
            rules.append(f"- 赛项：{_cname}   （模板选择与排版以本行为准，勿按旧赛题推断）")
        fe = (config or {}).get("flow_engine") or "html"
        rules.append(f"- 流程图/架构图引擎 = {fe.upper()}（用户选定，全程遵守，不得擅自换引擎）")
        cs = (config or {}).get("color_scheme") or "bw"
        cs_name = {"bw": "纯黑白线稿", "plain": "朴素竞赛", "modern": "现代精致"}.get(cs, cs)
        rules.append(f"- 图表配色风格族 = {cs_name}（用户手选，全程遵守）")
        pl = (config or {}).get("page_limit")
        if pl:
            rules.append(f"- 论文正文页数 ≤ {pl} 页（不含附录与参考文献）")
        if (config or {}).get("ai_declare"):
            rules.append("- 按竞赛规范在参考文献前生成「AI 工具使用声明」章节")
        if (config or {}).get("only_total") and not (config or {}).get("per_flow"):
            rules.append("- 只画一张总体技术路线图，不要为每个子问题单独画求解流程图")
    else:
        rules.append("- 使用中文撰写论文（除非是 LaTeX 代码）")
    # 图表配置标记（skill 按 MH_* 关键字 grep 本文件读取，勿删；无选择时默认黑白/随机）
    fig_markers = _fig_markers(config)
    # 环境锚点：按步骤生成，只写本步真正会调用的工具入口（防上下文过长/换目录后忘记；
    # 每个位置锚点不同，用不到的工具不写，避免徒增读取负担）。
    anchor_block = _env_anchor(current, ws)
    md = f"""# 研究项目: {(config or {}).get('title') or '自动化科研工作流'}

## 项目说明
这是一个自动化研究管理的工作流引擎，正在执行「{labels}」流水线。

## 重要规则
- 所有产出文件都写入当前工作目录（不要写到其他位置）
- 每个步骤完成后至少产出一个文件；前一步产物已存在于工作区时在其基础上继续
- 工作区内有 _templates/ 模板库可供 LaTeX 编译使用
- 工作区内有 _utils/ 工具链（确定性审计脚本与规则文档），SKILL 里的 `bash _utils/….sh` / `$PYTHON _utils/….py` / `cat _utils/….md` 均可直接调用

## 图表配置标记（数据图配色/版式由绘图库读取，流程图风格由 paper-figure-html 读取）
{chr(10).join(fig_markers)}

{anchor_block}

## 全程遵守条款（用户选定，全程有效）
{chr(10).join(rules)}

## 工程防呆条款（每步结束前自检）
- 核心原则：发现问题必须修正（不能只解释）
- 数学正确 ≠ 物理合理：数值解超出物理边界（负浓度/概率>1/能量发散等）时必须修模型或加约束，不得带病交付
- 引用前步结论时以其落盘文件为准，不得凭记忆转述；发现上下游不一致时在产出文件中显式标注
- 产出不确定的内容时如实标注置信度与局限，不得掩盖
{cap_block}
{files_block}
{cur_block}
"""
    # 数值参数硬目标落盘 .env_skill：skill 的 `source .env_skill` 据此读到
    # MIN_FIGURES/MIN_TABLES/MIN_MODELS/MAX_PAGES（此前从未生成 → 这些自检是死代码）。
    _write_env_skill(ws, config)
    try:
        (ws / "CLAUDE.md").write_text(md, encoding="utf-8")
    except OSError:
        pass
    return copied_dirs


def resolve_python():
    """定位 AI（CLI agent）可用的 Python 解释器 —— 确定性入口，AI 不靠猜。

    打包(frozen)后 sys.executable 是 ModelFlow.exe 而非 Python，故必须独立探测：
    1) settings 显式覆盖（启动自检写入）
    2) 环境变量 MODELFLOW_PYTHON
    3) Windows py launcher（py -3，最稳，走注册表）
    4) PATH 里的 python/python3
    5) 常见安装位置（AppData/Local/Programs/Python/…）
    返回 str 路径或 None。
    """
    import os as _os
    # 1) settings / env 显式覆盖
    for p in (db.get_setting("python_path", ""), _os.environ.get("MODELFLOW_PYTHON", "")):
        p = (p or "").strip()
        if p and Path(p).exists():
            return p
    # 2) 常见安装位置优先（AppData Python 常带 matplotlib/numpy/pandas 全套，是 AI 画图首选）
    cands = []
    local = _os.environ.get("LOCALAPPDATA")
    if local:
        pybase = Path(local) / "Programs" / "Python"
        if pybase.is_dir():
            cands += sorted(pybase.glob("Python*/python.exe"), reverse=True)
    cands += [Path("C:/Python312/python.exe"), Path("C:/Python311/python.exe"),
              Path("C:/Python310/python.exe")]
    for c in cands:
        try:
            if c.exists():
                return str(c)
        except OSError:
            continue
    # 3) py launcher（Windows 注册表驱动，多版本共存时可靠）
    py_launcher = shutil.which("py")
    if py_launcher:
        for ver in ("", "-3"):
            try:
                r = subprocess.run([py_launcher, *(([ver]) if ver else []), "-c",
                                    "import sys; print(sys.executable)"],
                                   capture_output=True, text=True, timeout=20, creationflags=_CNW)
                out = (r.stdout or "").strip()
                if r.returncode == 0 and out and Path(out).exists():
                    return out
            except Exception:
                continue
    # 4) PATH
    for name in ("python", "python3"):
        p = shutil.which(name)
        if p:
            return p
    return None


def find_claude_cli():
    """稳健定位本机 claude CLI（.cmd/.exe 均可）；找不到返回 None。
    探测顺序：settings 显式路径 → PATH → npm 全局目录 → 常见安装目录。
    全部按环境变量推导，不写死任何用户名，换机/换用户也能命中。
    """
    # 1) settings 显式覆盖（app_launch 启动时探测后写入）
    try:
        p = (db.get_setting("claude_cli_path", "") or "").strip()
    except Exception:
        p = ""
    if p and Path(p).exists():
        return p
    # 2) PATH（npm 全局目录常在 PATH 中，但部分环境未加入）
    p = shutil.which("claude")
    if p:
        return p
    # 3) 常见位置（按环境变量推导）
    cands = []
    appdata = os.environ.get("APPDATA")
    local = os.environ.get("LOCALAPPDATA")
    userprofile = os.environ.get("USERPROFILE")
    home = Path.home()
    if appdata:
        cands += [Path(appdata) / "npm" / "claude.cmd",
                  Path(appdata) / "npm" / "claude.exe",
                  Path(appdata) / "npm" / "claude"]
    if local:
        cands += [Path(local) / "Programs" / "claude" / "claude.exe",
                  Path(local) / "Programs" / "Claude" / "claude.exe"]
    if userprofile:
        cands += [Path(userprofile) / ".local" / "bin" / "claude",
                  Path(userprofile) / ".local" / "bin" / "claude.exe",
                  Path(userprofile) / ".claude" / "local" / "claude.exe"]
    cands += [home / ".local" / "bin" / "claude",
              home / ".local" / "bin" / "claude.exe"]
    for c in cands:
        try:
            if c.exists():
                return str(c)
        except OSError:
            continue
    return None


def auto_configure_cli():
    """启动时探测本机 Claude Code CLI / Python 运行时，命中则写入 settings。

    返回 (found: bool, path: str)。不抛异常：探测失败只记录，由执行时报错兜底。
    """
    try:
        # Python 运行时（AI 画图/跑码/自检的解释器）
        py = resolve_python()
        if py:
            db.set_setting("python_path", str(py))
        # Claude Code CLI
        p = find_claude_cli()
        if p:
            db.set_setting("claude_cli_path", str(p))
            db.set_setting("executor_mode", "cli")
            return True, str(p)
        return False, ""
    except Exception:
        return False, ""


def detect_runtimes():
    """检测流水线所需的本地运行时，返回 {name: {ok, path, hint}} 供启动遮罩展示。

    AI 好调用原则：每一项都给明确的安装指引（国内镜像），缺哪个启动时引导装哪个。
    """
    import os as _os

    def _which(*names):
        for n in names:
            p = shutil.which(n)
            if p:
                return p
        return ""

    py = resolve_python()
    # Python 是否带画图/数据核心库
    py_libs_ok = False
    if py:
        try:
            r = subprocess.run([py, "-c",
                                "import matplotlib,numpy,pandas;print('ok')"],
                               capture_output=True, text=True, timeout=30, creationflags=_CNW)
            py_libs_ok = (r.returncode == 0)
        except Exception:
            py_libs_ok = False

    return {
        "claude_cli": {
            "ok": bool(find_claude_cli()),
            "path": find_claude_cli() or "",
            "hint": "npm install -g @anthropic-ai/claude-code --registry=https://registry.npmmirror.com",
        },
        "node": {"ok": bool(_which("node")), "path": _which("node") or "",
                 "hint": "winget install OpenJS.NodeJS.LTS"},
        "git": {"ok": bool(_which("git")), "path": _which("git") or "",
                "hint": "winget install Git.Git"},
        "python": {"ok": bool(py), "path": py or "",
                   "hint": "winget install Python.Python.3.12"},
        "python_libs": {"ok": py_libs_ok, "path": py or "",
                        "hint": "pip install matplotlib numpy pandas scipy pdfplumber python-docx pypdf openpyxl PyMuPDF Pillow python-pptx"},
        "xelatex": {"ok": bool(_which("xelatex")), "path": _which("xelatex") or "",
                    "hint": "winget install MiKTeX.MiKTeX"},
        "ffmpeg": {"ok": bool(_find_ff_bin("ffmpeg")), "path": _find_ff_bin("ffmpeg") or "",
                   "hint": "winget install Gyan.FFmpeg"},
    }


# 可一键静默安装的运行时（winget 包名）。大体积/需交互授权的组件不在静默列表内，
# 只返回指引（用户手动确认后安装），避免未经确认的全局软件变更。
_INSTALLABLE = {
    "node": "OpenJS.NodeJS.LTS",
    "git": "Git.Git",
    "python": "Python.Python.3.12",
    "xelatex": "MiKTeX.MiKTeX",
    "ffmpeg": "Gyan.FFmpeg",
}


def install_runtime(name: str):
    """用 winget 静默安装一个运行时。返回 {ok, msg}。

    仅允许 _INSTALLABLE 白名单内的组件；claude_cli 用 npm（国内镜像）；
    python_libs 用 pip。安装是外部副作用，前端需显式点击「安装」才触发。
    """
    import os as _os
    name = (name or "").strip().lower()

    if name == "claude_cli":
        npm = shutil.which("npm")
        if not npm:
            return {"ok": False, "msg": "未找到 npm，请先安装 Node.js（winget install OpenJS.NodeJS.LTS）"}
        try:
            r = subprocess.run(
                [npm, "install", "-g", "@anthropic-ai/claude-code",
                 "--registry=https://registry.npmmirror.com"],
                capture_output=True, text=True, timeout=600, creationflags=_CNW)
            if r.returncode == 0:
                auto_configure_cli()
                return {"ok": True, "msg": "Claude Code CLI 已安装"}
            return {"ok": False, "msg": (r.stderr or r.stdout or "")[-300:]}
        except Exception as e:
            return {"ok": False, "msg": str(e)[:200]}

    if name == "python_libs":
        py = resolve_python()
        if not py:
            return {"ok": False, "msg": "未找到 Python"}
        try:
            r = subprocess.run(
                [py, "-m", "pip", "install", "-q",
                 "matplotlib", "numpy", "pandas", "scipy", "pdfplumber",
                 "python-docx", "pypdf", "openpyxl",
                 "PyMuPDF", "Pillow", "python-pptx"],
                capture_output=True, text=True, timeout=900, creationflags=_CNW)
            if r.returncode == 0:
                return {"ok": True, "msg": "核心库已安装（含 PyMuPDF/Pillow/python-pptx）"}
            return {"ok": False, "msg": (r.stderr or r.stdout or "")[-300:]}
        except Exception as e:
            return {"ok": False, "msg": str(e)[:200]}

    pkg = _INSTALLABLE.get(name)
    if not pkg:
        return {"ok": False, "msg": f"未知组件：{name}"}
    winget = shutil.which("winget")
    if not winget:
        return {"ok": False, "msg": "未找到 winget，请手动安装 " + pkg}
    try:
        r = subprocess.run(
            [winget, "install", "--id", pkg, "-e", "--silent",
             "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, text=True, timeout=1800, creationflags=_CNW)
        if r.returncode in (0, -1978335189):  # 已安装也返回成功
            auto_configure_cli()
            return {"ok": True, "msg": f"{name} 已就绪"}
        return {"ok": False, "msg": (r.stderr or r.stdout or "")[-300:]}
    except Exception as e:
        return {"ok": False, "msg": str(e)[:200]}


def _kill_tree(pid):
    """Windows 进程树强杀（防 CLI 卡死拖垮流水线）。"""
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)],
                   capture_output=True, timeout=15, creationflags=_CNW)

def run_step_via_cli(ws, prompt, system_text="", provider="anthropic",
                     api_base="", api_key="", model="", wid=0, step_key="",
                     timeout=None, cli_path=None):
    """以工作区为 cwd 启动一次 claude CLI agent 会话。

    流式解析 stream-json：工具调用实时推送 WS 进度；最终取 result 事件文本。
    返回 (final_text, meta)；meta 含 num_turns/duration_ms/cost/tool_calls/rc/is_error。
    异常统一抛 LLMError，由上层按失败处理。
    """
    import os as _os
    cli = cli_path or find_claude_cli()
    # Popen 会把 cwd 切到工作区：相对路径的 CLI 将失效，必须先转绝对路径
    cli = str(Path(cli).resolve()) if cli else cli
    if not cli:
        raise LLMError("未找到 Claude Code CLI，无法执行。请先运行 `npm install -g @anthropic-ai/claude-code` 安装并登录后重试")
    # ⛔ 执行引擎固定为 Claude Code CLI（Anthropic Messages 协议）。本项目没有本地路由转换
    # 服务，openai/gemini/bedrock 等协议的预设（设置页上游格式选了「需路由转换」的那几项）
    # 直连必失败。这里提前报出清晰错误，而不是把用户 key 塞进 ANTHROPIC_* 后收到莫名 HTTP 错误。
    # 兼容历史数据：provider 标成 openai 但 api_base 明显是 Anthropic 兼容网关的，仍放行。
    _proto = (provider or "").strip().lower()
    _base_l = (api_base or "").lower()
    _anthropic_hints = ("/anthropic", "/apps/anthropic", "/claudecode",
                        "/api/coding", "/api/anthropic", "/coding", "/tokenplan/personal")
    _compat = _proto in ("anthropic", "anthropic-messages", "") or \
        any(h in _base_l for h in _anthropic_hints)
    if not _compat:
        raise LLMError(
            f"当前预设协议为「{_proto}」，而流水线执行引擎（Claude Code CLI）只支持 Anthropic 兼容端点。"
            "请在设置页把该预设的上游格式改为 Anthropic Messages，并填写网关提供的 Anthropic 兼容地址"
            "（如 https://api.deepseek.com/anthropic、https://open.bigmodel.cn/api/anthropic）。")
    if timeout is None:
        try:
            timeout = int(_os.environ.get("MODELFLOW_CLI_TIMEOUT", "2700"))
        except ValueError:
            timeout = 2700
    # 凭据透传：Anthropic 官方与各类网关的双 header 兼容
    env = dict(_os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")     # AI 在 CLI 里跑 python 子进程输出 UTF-8，防 GBK 报错
    if (api_key or "").strip():
        env.setdefault("ANTHROPIC_API_KEY", api_key.strip())
        env["ANTHROPIC_AUTH_TOKEN"] = api_key.strip()      # 三方网关惯用
    else:
        env.pop("ANTHROPIC_API_KEY", None)
    if (api_base or "").strip():
        b = api_base.strip().rstrip("/")
        env["ANTHROPIC_BASE_URL"] = b                       # CLI 自行补 /v1 语义
    else:
        env.pop("ANTHROPIC_BASE_URL", None)
    # 确定性入口：AI 画图/跑码/自检用的 Python 与工具目录（skill 读 $MH_PYTHON / $MH_TOOLS_DIR）
    _py = resolve_python()
    if _py:
        env["MH_PYTHON"] = _py
    _utils = ws / "_utils"
    if _utils.is_dir():
        env["MH_TOOLS_DIR"] = str(_utils.resolve())
    # BZD 双审精制流资产目录（cumcm-bzd-2026 的 scripts/config/templates/references 注入处）
    _bzd = ws / "_bzd"
    if _bzd.is_dir():
        env["MH_BZD_DIR"] = str(_bzd.resolve())
    # 随包内置的 numpy/matplotlib 等库，确保 AI 的 python 能 import（PyInstaller 解包路径）
    _mei = _os.environ.get("_MEIPASS") or getattr(sys, "_MEIPASS", None)
    if _mei:
        env.setdefault("PYTHONPATH", _mei)
    # 视觉质检脚本（data_fig_vision_check / tikz_vision_check）读的环境变量：
    # EDITOR_AI_* 优先，OPENAI_* 兜底。统一走 _resolve_vision_cred()（与图片 OCR 同源），
    # 消除 REST(tools.py) 与 CLI(skill) 两套 key 解析漂移；未配置时脚本自身降级跳过(exit 2)。
    try:
        _vprov, _vbase, _vkey, _vmodel = _resolve_vision_cred()
        if _vkey:
            env.setdefault("EDITOR_AI_API_KEY", _vkey)
            if _vbase:
                env.setdefault("EDITOR_AI_BASE_URL", _vbase.rstrip("/"))
            env.setdefault("EDITOR_AI_MODEL_ID", _vmodel or "gpt-4o")
        _def = db.get_default_preset()
        if _def and ((_def.get("provider") or "openai").lower() in ("openai", "") or (_def.get("api_base") or "")):
            if (_def.get("api_key") or "").strip():
                env.setdefault("OPENAI_API_KEY", _def["api_key"].strip())
            if (_def.get("api_base") or "").strip():
                env.setdefault("OPENAI_BASE_URL", _def["api_base"].strip().rstrip("/"))
    except Exception:
        pass

    sys_file = ws / "_step_system.txt"
    if system_text:
        try:
            sys_file.write_text(system_text, encoding="utf-8")
        except OSError:
            sys_file = None
    # 火山方舟 Agent Plan 的 /api/plan 端点与 Windows claude.cmd 存在已实测的参数传递兼容问题：
    # 多行 prompt 作为 `-p <参数>` 传入会被 CLI 错误路由到账号旧模型；同一原始多行 prompt
    # 经 stdin 输入时稳定使用 ark-code-latest。故统一从 stdin 传用户消息，既保留完整换行语义，
    # 也避免 shell/cmd 参数解析污染；Popen 下方的 communicate 线程负责一次性写入并关闭 stdin。
    cli_prompt = str(prompt)
    args = [cli, "-p",
            "--output-format", "stream-json", "--verbose",
            "--dangerously-skip-permissions",
            # 只加载工作区 project 指令，隔离用户 ~/.claude/settings.json 中的旧模型映射、
            # 状态栏标题模型等全局配置；否则 ark-code-latest 会被旧 user 配置提前拦成
            # unrecognized_model，而直连 API 本身实际可用。
            "--setting-sources", "project"]
    if sys_file:
        args += ["--append-system-prompt-file", str(sys_file.resolve())]  # CLI 相对 cwd 二次解析，必须绝对路径
    if (model or "").strip():
        args += ["--model", model]
    logs = []                    # WS 推送用的摘要行
    raw_lines = []
    tool_calls = 0
    final_text, is_err, turns, dur_ms, cost = "", False, None, None, None
    # 逐轮日志（逐条 assistant/user 落库）：每事件一行 JSON
    turn_dir = ws / "_turn_logs"
    stamp = time.strftime("%H%M%S")
    turn_file = turn_dir / f"{step_key}_{stamp}.jsonl"
    try:
        turn_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        turn_file = None
    started = time.time()
    proc = subprocess.Popen(args, cwd=str(ws), env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace",
                            creationflags=_CNW)
    # prompt 必须通过 stdin，而不是作为 Windows 命令行参数传给 `-p`。火山 Agent Plan
    # 对多行 argv 会错误选中账号旧模型；stdin 可稳定保持 ark-code-latest。
    try:
        proc.stdin.write(cli_prompt)
        proc.stdin.close()
    except Exception:
        _kill_tree(proc.pid)
        raise LLMError("无法向 Claude CLI 写入用户消息")
    rc = None
    # ⛔ 修复：阻塞式 `for line in proc.stdout` 在 CLI 静默挂起（无输出、进程不退）时
    # 永远到不了超时判断，会把整条流水线拖死。改为后台读线程 + 队列 5s 轮询后超时真正生效。
    import queue as _queue
    _Q = _queue.Queue()              # stdout 行队列
    _SENT = object()                 # 流结束哨兵

    def _stdout_reader():
        try:
            for _l in proc.stdout:
                _Q.put(_l)
        finally:
            _Q.put(_SENT)

    threading.Thread(target=_stdout_reader, daemon=True).start()

    def _pump():
        """取一行（最长阻塞 5s）。返回 ('line', 数据) / ('sent', None) / ('empty', None)。"""
        try:
            _it = _Q.get(timeout=5)
        except _queue.Empty:
            return ("empty", None)
        if _it is _SENT:
            return ("sent", None)
        return ("line", _it)

    try:
        while True:
            _kind, _data = _pump()
            if _kind == "sent":
                break
            if _kind == "empty":
                # 超时窗口内没有任何新输出 → 判定挂起，强杀进程树
                if time.time() - started > timeout:
                    _kill_tree(proc.pid)
                    raise LLMError(f"CLI 步骤超时（>{timeout}s），已中止")
                continue
            line = (_data or "").strip()
            if not line:
                continue
            if time.time() - started > timeout:
                _kill_tree(proc.pid)
                raise LLMError(f"CLI 步骤超时（>{timeout}s），已中止")
            raw_lines.append(line[:4000])
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue                                  # 非事件行（横幅等）
            et = ev.get("type")
            # 逐轮日志：assistant/user/system/result 每事件一行精要
            if turn_file is not None and et in ("assistant", "user", "system", "result"):
                try:
                    brief = {"#ts": time.strftime("%H:%M:%S"), "type": et,
                             "subtype": ev.get("subtype")}
                    if et == "assistant":
                        kinds = []
                        for blk in ((ev.get("message") or {}).get("content") or []):
                            bt = blk.get("type")
                            if bt == "tool_use":
                                inp = blk.get("input") or {}
                                preview = json.dumps({k: inp[k] for k in list(inp)[:1]},
                                                     ensure_ascii=False)[:80]
                                kinds.append({"tool": blk.get("name"), "arg": preview})
                            elif bt == "text":
                                kinds.append({"text": (blk.get("text") or "")[:160]})
                        brief["blocks"] = kinds
                    elif et == "user":
                        c = (ev.get("message") or {}).get("content")
                        if isinstance(c, list):
                            brief["tool_results"] = sum(
                                1 for b in c if isinstance(b, dict) and b.get("type") == "tool_result")
                        elif isinstance(c, str):
                            brief["text"] = c[:160]
                    elif et == "result":
                        brief.update({"is_error": ev.get("is_error"),
                                      "num_turns": ev.get("num_turns"),
                                      "duration_ms": ev.get("duration_ms"),
                                      "cost": ev.get("total_cost_usd"),
                                      "result": (ev.get("result") or "")[:200]})
                    with open(turn_file, "a", encoding="utf-8") as tf:
                        tf.write(json.dumps(brief, ensure_ascii=False) + "\n")
                except Exception:
                    pass
            if et == "assistant":
                for blk in ((ev.get("message") or {}).get("content") or []):
                    bt = blk.get("type")
                    if bt == "tool_use":
                        tool_calls += 1
                        inp = blk.get("input") or {}
                        prev = json.dumps({k: inp[k] for k in list(inp)[:1]},
                                          ensure_ascii=False)[:90]
                        msg = f"🔧 工具#{tool_calls} {blk.get('name')}: {prev}"
                        logs.append(msg)
                        if wid:
                            _push(wid, {"type": "log", "step": step_key, "msg": msg})
                    elif bt == "text":
                        final_text += (blk.get("text") or "")
                        txt = (blk.get("text") or "").strip()
                        if txt and wid:
                            _push(wid, {"type": "log", "step": step_key,
                                        "msg": "AI: " + txt[:200]})
            elif et == "result":
                final_text = ev.get("result") or final_text
                is_err = bool(ev.get("is_error"))
                turns = ev.get("num_turns")
                dur_ms = ev.get("duration_ms")
                cost = ev.get("total_cost_usd")
                if wid:
                    _push(wid, {"type": "log", "step": step_key,
                                "msg": f"会话结束：{turns or '?'} 轮 · {round((dur_ms or 0)/1000)}s · {'失败' if is_err else '成功'}"})
        rc = proc.wait(timeout=30)
    except LLMError:
        raise
    except Exception as e:
        _kill_tree(proc.pid)
        raise LLMError(f"CLI 会话异常中断: {str(e)[:150]}")
    finally:
        try:
            sys_file and sys_file.exists() and sys_file.unlink()
        except OSError:
            pass
    # 逐轮日志收尾：轮次/耗时/成本汇总追加为最后一行
    if turn_file is not None and turn_file.exists():
        try:
            with open(turn_file, "a", encoding="utf-8") as tf:
                tf.write(json.dumps({"#ts": time.strftime("%H:%M:%S"), "type": "session_end",
                                     "rc": rc, "is_error": is_err, "num_turns": turns,
                                     "duration_ms": dur_ms, "cost": cost,
                                     "tool_calls": tool_calls}, ensure_ascii=False) + "\n")
        except OSError:
            pass
    # 会话留痕：完整 JSONL 落盘
    try:
        sdir = ws / "_sessions"
        sdir.mkdir(exist_ok=True)
        stamp = time.strftime("%H%M%S")
        (sdir / f"{step_key}_{stamp}.jsonl").write_text("\n".join(raw_lines), encoding="utf-8")
    except OSError:
        pass
    meta = {"rc": rc, "is_error": is_err, "num_turns": turns,
            "duration_ms": dur_ms, "cost": cost, "tool_calls": tool_calls}
    if rc not in (0, None) or is_err:
        raise LLMError(f"CLI 步骤失败 rc={rc} is_error={is_err}（turns={turns}，详见 _sessions/）")
    if not final_text.strip() and not tool_calls:
        raise LLMError("CLI 无输出且无工具调用（会话异常），请检查 claude 登录状态")
    return final_text, meta


def execute_job(wid):
    """后台运行：按模板路由到对应流水线，顺序执行全部步骤，更新数据库进度。"""
    w = db.get_workflow(wid)
    if not w:
        return
    config = w["config"]
    steps = w["steps"] if isinstance(w["steps"], dict) else {}
    template = w["template"] or "competition"
    step_list = [dict(s) for s in (PIPELINES.get(template, COMPETITION_STEPS))]
    # 开关门控：logic_review 未开启 → 跳过「逻辑对抗复核」步骤（review）
    if not config.get("logic_review"):
        step_list = [s for s in step_list if s.get("key") != "review"]
    # 续跑（修复4）：跳过已 done 的步骤，支持中断/重启后 resume 不重跑
    step_list = [s for s in step_list
                 if (steps.get(s["key"]) or {}).get("status") != "done"]
    db.update_workflow(wid, status="running")
    ws = ws_path(wid)
    # 落盘上传文件 + 纯文本主题/赛题
    file_index = _save_assets(ws, config)
    _save_question(ws, config)

    total = len(step_list)

    for idx, step in enumerate(step_list):
        # 暂停检查（修复4）：DB 状态为 paused 时阻塞等待 resume 置位
        if db.get_workflow(wid).get("status") == "paused":
            ev = _pause_event(wid)
            steps[step["key"]] = {"status": "paused", "label": step["label"],
                                  "skill": step["skill"], "msg": "已暂停，等待恢复"}
            db.update_workflow(wid, steps=steps)
            _push(wid, {"type": "step", "step": step["key"], "status": "paused",
                        "label": step["label"], "msg": "已暂停，等待恢复"})
            ev.wait()  # 阻塞直到 resume 置位
            db.update_workflow(wid, status="running")
            _push(wid, {"type": "status", "status": "running", "msg": "已恢复"})
        # 按步骤解析本次调用所用的模型与密钥（role=步骤 key，支持「每步指定」覆盖）
        role = step.get("key") or step.get("role", "executor")
        provider, api_base, api_key, model = resolve_model(role, config)
        # 执行引擎：固定 Claude Code CLI（agent 自主读写/跑码/编译）。
        # 找不到 CLI 直接失败并提示安装，绝不降级为 API 直连。
        # 记录步骤状态
        step_start = time.time()
        steps[step["key"]] = {"status": "running", "label": step["label"],
                              "skill": step["skill"], "checkpoint": step.get("checkpoint", False),
                              "model": model, "executor": "cli",
                              "msg": "执行中"}
        db.update_workflow(wid, steps=steps, step=step["key"],
                           progress=int(idx / total * 100))
        _push(wid, {"type": "step", "step": step["key"], "status": "running",
                    "label": step["label"], "progress": int(idx / total * 100), "msg": "执行中"})
        try:
            system = compose_skill_prompt(step["skill"], template, step["key"])
            user = build_user_message(step, config, file_index, template)
            # claude CLI agent 会话（cwd=工作区，CLAUDE.md 承载指令）
            copied = prepare_cli_workspace(ws, config, file_index,
                                           step_list=step_list,
                                           current=step, template=template)
            if copied:
                _push(wid, {"type": "log", "step": step["key"],
                            "msg": f"模板注入 ws/_templates/: {'，'.join(copied)}"})
            out_text, cli_meta = run_step_via_cli(
                ws, user, system_text=system or "", provider=provider,
                api_base=api_base, api_key=api_key, model=model,
                wid=wid, step_key=step["key"])
            used_rounds = int(cli_meta.get("num_turns") or 1)
            cost = cli_meta.get("cost")
            extra = f" · {cli_meta.get('tool_calls', 0)} 次工具调用"
            if cost is not None:
                extra += f" · ${cost:.3f}"
            _push(wid, {"type": "log", "step": step["key"],
                        "msg": f"CLI 会话完成：{used_rounds} 轮{extra}"})
            _push(wid, {"type": "log", "step": step["key"],
                        "msg": f"步骤完成：{step['label']}（{(out_text or '')[:80]}...）"})
            # 落盘产出文件
            ws = ws_path(wid)
            out_file = ws / step["out"]
            if step["out"].endswith((".tex", ".md", ".txt")):
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(out_text or "", encoding="utf-8")
            # 自检
            ok, detail = run_check(ws, wid, step["key"], step)
            # 复核语义（COMP_REVIEW_VERDICT 披露式 vs 阻断式）：
            #   disclose（默认）：comp-review 产出 VERDICT 后仅播报分级，不阻断；
            #   block：rc=1 保持原有 warn/failed 阻断语义。
            if step["key"] == "review":
                policy = ((config.get("review_policy") or "").strip().lower()
                          or (db.get_setting("review_policy", "") or "").strip().lower()
                          or "disclose")
                if policy not in ("disclose", "block"):
                    policy = "disclose"
                if ok and policy == "disclose":
                    verd = ws / "COMP_REVIEW_VERDICT.json"
                    fatal = major = minor = -1
                    if verd.is_file():
                        try:
                            vd = json.loads(verd.read_text(encoding="utf-8"))
                            fatal = int(vd.get("fatal", vd.get("fatal_count", -1)))
                            major = int(vd.get("major", vd.get("major_count", -1)))
                            minor = int(vd.get("minor", vd.get("minor_count", -1)))
                        except Exception:
                            pass
                    if fatal == 0 and major >= 0:
                        _push(wid, {"type": "log", "step": "review",
                                    "msg": f"复核披露：fatal={fatal} major={major} minor={minor} → 按披露模式放行，后续步骤须在论文中如实降级披露这些问题"})
                        detail = (detail or "") + f" | 复核披露: fatal={fatal} major={major} minor={minor}（disclose 放行）"
                    else:
                        _push(wid, {"type": "log", "step": "review",
                                    "msg": "复核披露模式：未解析到 COMP_REVIEW_VERDICT.json 或含 fatal，按普通完成继续（详见 COMP_REVIEW.md）"})
            # PDF 编译：CLI 会话记忆里 skill 已自行编译，此处仅做兜底补一次
            if step["key"] in ("compile", "improve"):
                tex_cand = ws / "paper" / "main.tex"
                if not tex_cand.is_file():
                    tex_cand = ws / "main.tex"
                pdf_cand = tex_cand.parent / "main.pdf"
                if tex_cand.is_file() and (not pdf_cand.exists()
                                           or pdf_cand.stat().st_size == 0):
                    # 兜底：skill 会话没编出 PDF（可能卡在权限/环境），本地补一次
                    ok_c, detail_c = compile_pdf(ws)
                    _push(wid, {"type": "log", "step": step["key"],
                                "msg": f"本地兜底编译：{'成功' if ok_c else '失败'} —— {detail_c[:160]}"})
                    if not ok_c:
                        ok = False
                    if detail in ("", "无自检脚本"):
                        detail = detail_c
                    else:
                        detail = f"{detail_c} | 自检: {detail}"
                else:
                    ok_cli = pdf_cand.is_file() and pdf_cand.stat().st_size > 1000
                    if not ok_cli and not tex_cand.is_file():
                        ok_cli = True       # 非论文类流水线无 tex，不算失败
                    if not ok_cli:
                        ok = False
                    detail = detail or ("PDF 编译由 CLI 会话完成" if ok_cli else "CLI 未产出 main.pdf")
                # compile 步骤的 LLM 说明文本（原 out=main.pdf 无处落盘）落盘为 compile_note.md
                if step["key"] == "compile" and out_text:
                    try:
                        (ws / "compile_note.md").write_text(out_text, encoding="utf-8")
                    except OSError:
                        pass
            dur = int(time.time() - step_start)
            steps[step["key"]] = {"status": "done" if ok else "warn",
                                  "label": step["label"], "skill": step["skill"],
                                  "checkpoint": step.get("checkpoint", False),
                                  "model": model, "executor": "cli",
                                  "duration": dur,
                                  "msg": (detail or "")[:200], "out": step["out"]}
            db.update_workflow(wid, steps=steps,
                               progress=int((idx + 1) / total * 100))
            _push(wid, {"type": "step", "step": step["key"],
                        "status": "done" if ok else "warn",
                        "label": step["label"], "duration": dur,
                        "progress": int((idx + 1) / total * 100)})
            # 人工检查点（P2 接线）：开启 manual_checkpoint 且本步为 checkpoint 步时，
            # 步骤完成后自动暂停，等待用户在运行页查看产物后点 resume 继续。
            if (config.get("manual_checkpoint") and step.get("checkpoint")
                    and idx + 1 < total):
                _pause_event(wid).clear()
                steps[step["key"]]["msg"] = ((steps[step["key"]].get("msg") or "") + "｜人工检查点：已暂停，预览产物后点继续")[:200]
                db.update_workflow(wid, steps=steps, status="paused")
                _push(wid, {"type": "step", "step": step["key"], "status": "paused",
                            "label": step["label"],
                            "msg": "人工检查点：预览产出后在运行页点「继续」恢复流水线"})
                _push(wid, {"type": "status", "status": "paused",
                            "msg": f"人工检查点（{step['label']}）：预览产物后点继续"})
                _pause_event(wid).wait()   # 阻塞直到用户 resume
                db.update_workflow(wid, status="running")
                _push(wid, {"type": "status", "status": "running", "msg": "已过检查点，继续流水线"})
        except Exception as e:
            dur = int(time.time() - step_start)
            steps[step["key"]] = {"status": "failed", "label": step["label"],
                                  "skill": step["skill"], "model": model,
                                  "duration": dur, "msg": str(e)[:200]}
            db.update_workflow(wid, steps=steps, status="failed")
            _push(wid, {"type": "step", "step": step["key"], "status": "failed",
                        "label": step["label"], "msg": str(e)[:120]})
            _push(wid, {"type": "status", "status": "failed"})
            _clear_pause(wid)
            return
    db.update_workflow(wid, steps=steps, status="completed", progress=100)
    _push(wid, {"type": "step", "status": "completed", "progress": 100})
    _push(wid, {"type": "status", "status": "completed"})
    _clear_pause(wid)

def start_job(wid):
    """在后台线程启动作业。

    防重复启动（P2-10）：同一工作流已处于 running/paused 时拒绝再次起线程，
    防止用户双击「启动」或误点产生两个 execute_job 并发写库；加锁消除检查与
    启动之间的竞态窗口。
    """
    with _JOB_START_LOCK:
        w = db.get_workflow(wid)
        if w and w.get("status") in ("running", "paused"):
            return None
        t = threading.Thread(target=execute_job, args=(wid,), daemon=True)
        t.start()
        db.update_workflow(wid, status="running")
        return t
# -*- coding: utf-8 -*-
"""配置驱动流水线模板：内置模板 seed + 模板 CRUD / 校验 / 快照。"""

from . import db

# 内置模板识别：随包分发内置，不可删除（可作为副本编辑）。用于种子数据。
BUILTIN_MARK = "builtin"


def _now():
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ==================== 内置模板（seed 数据 = 原 ModelFlow 三套国赛流） ====================
def builtin_pipelines():
    """返回内置流水线模板定义（含有序步骤）。作为种子数据写入 pipeline_definitions。
    每步: key,label,skill,out,checkpoint,role,check。model 可空=用默认预设。
    """
    return [
        {
            "name": "competition",
            "label": "国赛 · 极速全自动流",
            "desc": "极速全自动：赛题分析→建模求解→编程实现→图表生成→架构图→逻辑对抗复核→论文撰写→编译合规→改进循环。一键全自动，开冲最快。",
            "emoji": "⚡",
            "g": "comp",
            "builtin": 1,
            "steps": [
                {"key": "analysis", "label": "赛题分析", "skill": "comp-prob-analysis",
                 "out": "PROBLEM_ANALYSIS.md", "checkpoint": True, "role": "executor",
                 "check": "step_audit.py prob"},
                {"key": "modeling", "label": "建模求解", "skill": "comp-modeling",
                 "out": "MODELING_REPORT.md", "checkpoint": True, "role": "executor",
                 "check": "step_audit.py modeling"},
                {"key": "code", "label": "编程实现", "skill": "comp-code",
                 "out": "RESULTS.md", "checkpoint": True, "role": "executor",
                 "check": "step_audit.py code"},
                {"key": "figure", "label": "图表生成", "skill": "paper-figure",
                 "out": "FIGURES.md", "checkpoint": False, "role": "executor",
                 "check": "step_audit.py figure"},
                {"key": "arch", "label": "流程与架构图绘制", "skill": "paper-figure-html diagram-design",
                 "out": "ARCHITECTURE.md", "checkpoint": False, "role": "executor",
                 "check": "step_audit.py arch"},
                {"key": "review", "label": "逻辑对抗复核", "skill": "comp-review",
                 "out": "LOGIC_REVIEW.md", "checkpoint": False, "role": "reviewer",
                 "check": "step_audit.py review"},
                {"key": "paper", "label": "竞赛论文撰写", "skill": "comp-paper-zh",
                 "out": "main.tex", "checkpoint": True, "role": "editor",
                 "check": "step_audit.py paper"},
                {"key": "compile", "label": "编译与合规检查", "skill": "comp-compile-zh",
                 "out": "main.pdf", "checkpoint": False, "role": "executor",
                 "check": "step_audit.py compile"},
                {"key": "improve", "label": "论文改进循环", "skill": "auto-paper-improvement-loop",
                 "out": "IMPROVED_PAPER.md", "checkpoint": False, "role": "executor",
                 "check": "step_audit.py improve"},
            ],
        },
        {
            "name": "competition_bzd",
            "label": "国赛 · BZD 双审精制流",
            "desc": "BZD 2026 双审精制：题面解析→策略→执行→稳健→写作→摘要→两轮独立审查（章节自查+综合评审）→合规出库，含 26 项 AI 合规清单。正式比赛冲奖推荐（约 2-3 天）。",
            "emoji": "🏅",
            "g": "comp",
            "builtin": 1,
            "steps": [
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
            ],
        },
        {
            "name": "competition_mathmodel",
            "label": "国赛 · 个人自制流",
            "desc": "mathmodel-skill 适配：选题→解析→选型→基础→子问题循环→稳健→评价→写作→合规终审 9 步。问答式决策自动采用推荐项、决策日志落盘、断点可恢复，五维 rubric 自评。个人独立作战推荐。",
            "emoji": "🧭",
            "g": "comp",
            "builtin": 1,
            "steps": [
                {"key": "mms01_topic", "label": "选题决策", "skill": "mathmodel-skill",
                 "out": "TOPIC_DECISION.md", "checkpoint": False, "role": "executor", "check": ""},
                {"key": "mms02_analysis", "label": "问题深度解析与分解", "skill": "mathmodel-skill",
                 "out": "PROBLEM_DECOMPOSITION.md", "checkpoint": False, "role": "executor", "check": ""},
                {"key": "mms03_model", "label": "模型选型（候选对比）", "skill": "mathmodel-skill",
                 "out": "MODEL_SELECTION.md", "checkpoint": False, "role": "executor", "check": ""},
                {"key": "mms04_foundation", "label": "基础框架（假设·符号·术语）", "skill": "mathmodel-skill",
                 "out": "FOUNDATION.md", "checkpoint": False, "role": "executor", "check": ""},
                {"key": "mms05_solving", "label": "递归子问题求解循环", "skill": "mathmodel-skill paper-figure",
                 "out": "SOLVING_SUMMARY.md", "checkpoint": True, "role": "executor", "check": ""},
                {"key": "mms06_robust", "label": "全局灵敏度与稳健性", "skill": "mathmodel-skill paper-figure",
                 "out": "ROBUSTNESS_REPORT.md", "checkpoint": False, "role": "executor", "check": ""},
                {"key": "mms07_eval", "label": "模型评价与推广", "skill": "mathmodel-skill",
                 "out": "MODEL_EVALUATION.md", "checkpoint": False, "role": "executor", "check": ""},
                {"key": "mms08_writing", "label": "论文写作与合规装配", "skill": "mathmodel-skill diagram-design",
                 "out": "paper_workspace/main.tex", "checkpoint": True, "role": "editor", "check": ""},
                {"key": "mms09_review", "label": "提交合规与多视角终审", "skill": "mathmodel-skill",
                 "out": "SUBMISSION_REVIEW.md", "checkpoint": False, "role": "reviewer", "check": ""},
            ],
        },
    ]


# ==================== 模板 CRUD ====================
def seed_builtin():
    """启动时把内置模板写入数据库（若已存在同名校跳过）。"""
    for p in builtin_pipelines():
        if not db.get_pipeline(p["name"]):
            db.create_pipeline(p["name"], p["label"], p["desc"], p["emoji"],
                               p["g"], steps=p["steps"], builtin=1)


def validate_steps(steps):
    """校验步骤清单合法性。返回 (ok, error)。必须为正则字符键、非空 label、非空 skill。"""
    if not isinstance(steps, list):
        return False, "steps 必须是数组"
    if not steps:
        return False, "至少需要 1 个步骤"
    import re
    keys = set()
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            return False, f"第 {i+1} 步必须是对象"
        key = str(s.get("key") or "").strip()
        if not key:
            return False, f"第 {i+1} 步缺少 key"
        if not re.match(r"^[a-zA-Z0-9_-]+$", key):
            return False, f"第 {i+1} 步 key「{key}」只能含字母数字下划线连字符"
        if key in keys:
            return False, f"步骤 key「{key}」重复"
        keys.add(key)
        if not str(s.get("label") or "").strip():
            return False, f"第 {i+1} 步「{key}」缺少名称(label)"
        if not str(s.get("skill") or "").strip():
            return False, f"第 {i+1} 步「{key}」缺少 skill"
    return True, ""


def normalize_name(raw):
    """模板名规范化：小写 + 短横线。返回 (name, ok)"""
    import re
    s = (raw or "").strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9_-]", "", s)
    if not s:
        return "", False
    return s, True


def list_catalog():
    """返回全部模板 + metadata（创建时可选择）。"""
    return db.list_pipelines()


def _snapshot_config_defaults(config):
    """当步骤未配 model 时，回退到 config.model / 默认预设；供快照时把解析结果固定。"""
    out = {}
    cfg = config or {}
    step_models = cfg.get("step_models") or {}
    default_model = cfg.get("model") or ""
    for sk, sv in step_models.items():
        out[sk] = sv
    if default_model:
        # 兜底：所有未单步指定的步骤用全局 model
        pass
    return out
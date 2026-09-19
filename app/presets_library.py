# -*- coding: utf-8 -*-
"""出厂内置库：通用全自动工作流 + 配套技能。

设计：仓库里的 skills/ 是**只读出厂版**（升级时随包更新），
首次启动按版本号同步一份到可写的 modex-data/skills/ 供用户编辑；
内置流程模板写进数据库并打 builtin 标记，用户可自由改，
改完还能通过「恢复出厂」用出厂版重置回来。
"""
import shutil
from pathlib import Path

from . import db, paths

LIBRARY_VERSION = "1.0.0"

# 出厂技能清单（名字与 skills/<name>/SKILL.md 一一对应）
BUNDLED_SKILLS = [
    "ff-requirement-analysis",
    "ff-planning",
    "ff-research",
    "ff-execution",
    "ff-review",
    "ff-refine",
    "ff-delivery",
]


def _step(key, label, skill, out, *, role="executor", checkpoint=False, engine="",
          extra_prompt=""):
    return {"key": key, "label": label, "skill": skill, "out": out, "role": role,
            "checkpoint": checkpoint, "engine": engine, "model": "",
            "extra_prompt": extra_prompt}


AUTO_WORKFLOW_STEPS = [
    _step("clarify", "需求解析", "ff-requirement-analysis", "REQUIREMENTS.md",
          checkpoint=True),
    _step("plan", "方案拆解", "ff-planning", "PLAN.md", checkpoint=True),
    _step("research", "信息收集", "ff-research", "FINDINGS.md"),
    _step("execute", "逐项执行", "ff-execution", "EXECUTION.md", checkpoint=True),
    _step("review", "自检复核", "ff-review", "REVIEW.md", role="reviewer"),
    _step("refine", "修订打磨", "ff-refine", "FINAL.md", role="editor"),
    _step("deliver", "交付整合", "ff-delivery", "DELIVERABLE.md"),
]

QUICK_FLOW_STEPS = [
    _step("clarify", "需求确认", "ff-requirement-analysis", "REQUIREMENTS.md",
          extra_prompt="本流程是轻量三步流：只做必要的需求界定，验收标准精简为 3 条以内，"
                       "不要展开长篇范围分析。"),
    _step("execute", "直接执行", "ff-execution", "EXECUTION.md",
          extra_prompt="本流程无 PLAN.md：请把需求直接拆成 1–3 个任务就地完成，"
                       "并在 EXECUTION.md 里按这个粒度记台账。"),
    _step("check", "结果复核", "ff-review", "REVIEW.md", role="reviewer",
          extra_prompt="本流程无 PLAN.md，复核基准改为 REQUIREMENTS.md 的验收标准 + "
                       "EXECUTION.md 台账抽验。"),
]

BUILTIN_PIPELINES = [
    {
        "name": "auto-workflow",
        "label": "通用全自动工作流",
        "desc": "任何任务都能套的一条主线：先把需求钉死，再拆方案、备料、逐项执行、"
                "独立复核、修订、最后整合成交付说明。前两步和执行步设了人工检查点。",
        "g": "built-in",
        "steps": AUTO_WORKFLOW_STEPS,
    },
    {
        "name": "quick-flow",
        "label": "轻量三步流",
        "desc": "小任务快速通道：需求确认 → 直接执行 → 结果复核。全程不停检查点，"
                "适合十分钟能出活的事。",
        "g": "built-in",
        "steps": QUICK_FLOW_STEPS,
    },
]


def _sync_skills(force: bool) -> dict:
    """把出厂技能拷进可写技能目录。force=True 时覆盖同名文件。"""
    src_root = paths.BASE / "skills"
    if not src_root.is_dir():
        return {"copied": 0, "skipped": len(BUNDLED_SKILLS)}
    copied = skipped = 0
    for name in BUNDLED_SKILLS:
        src = src_root / name
        if not (src / "SKILL.md").is_file():
            continue
        dst = paths.USER_SKILLS_DIR / name
        if dst.exists() and not force:
            skipped += 1
            continue
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
        copied += 1
    return {"copied": copied, "skipped": skipped}


def seed(force: bool = False) -> dict:
    """幂等同步：技能落可写目录 + 内置模板入库。

    force=False 时只在版本号变化（或从未播种）时同步技能，
    已存在的模板一律不覆盖（保留用户编辑）。
    force=True 时技能覆盖回出厂版，内置模板的步骤一并重置。
    """
    ver = db.get_setting("library_version")
    result = {"skills_copied": 0, "skills_skipped": 0, "pipelines_created": [],
              "pipelines_reset": []}
    if force or ver != LIBRARY_VERSION:
        s = _sync_skills(force)
        result["skills_copied"] = s["copied"]
        result["skills_skipped"] = s["skipped"]
        db.set_setting("library_version", LIBRARY_VERSION)
    for p in BUILTIN_PIPELINES:
        if db.get_pipeline(p["name"]):
            if force:
                db.update_pipeline(p["name"], label=p["label"], desc=p["desc"],
                                   g=p["g"], steps=p["steps"], builtin=1)
                result["pipelines_reset"].append(p["name"])
            continue
        db.create_pipeline(p["name"], p["label"], p["desc"], "", p["g"],
                           steps=p["steps"], builtin=1)
        result["pipelines_created"].append(p["name"])
    return result


def factory_steps(name: str):
    """取某内置流程的出厂步骤清单（恢复单个流程时用）。"""
    for p in BUILTIN_PIPELINES:
        if p["name"] == name:
            return [dict(s) for s in p["steps"]]
    return None

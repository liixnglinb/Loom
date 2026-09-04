#!/usr/bin/env python3
"""CUMCM 9 阶段工作流 —— 环境与结构预检。

用法:
    python doctor.py                                  # 检查工作流包 + 工具链
    python doctor.py --skip-tools                     # 只做静态检查
    python doctor.py --workspace <cwd>                # 附加检查用户工作区
    python doctor.py --workspace <cwd> --check-paper  # 附加检查论文产物
    python doctor.py --json                           # 机器可读输出
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

WF_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "config/dim_weights.json",
    "templates/shared/decision_log.json",
    "references/rules_baseline.md",
    "references/ai_usage_governance.md",
    "references/model_fit_rubric.md",
    "references/writing_spec.md",
    "references/anti_patterns.md",
    "references/prompt_library.md",
    "references/rubrics.md",
    "references/feedback_l1_critic.md",
    "scripts/doctor.py",
    "scripts/score_artifact.py",
    "scripts/query_model_dict.py",
]

STAGE_FILES = [f"references/stage_0{i}_{n}.md" for i, n in enumerate([
    "kickoff_selection", "problem_decomposition", "model_selection",
    "foundation", "solving_loop", "robustness",
    "evaluation", "writing", "final_review",
], start=1)]

# SKILL.md 与 references/ 中引用的仓库相对路径的搜索基准
PATH_BASES = [
    "", "references", "config", "scripts",
    "templates/shared", "templates/latex", "templates",
]

PAPER_SECTIONS = ["01_abstract", "02_problem_restate", "03_analysis"]
PLACEHOLDER_RE = re.compile(r"XXXX|keyword1|关键词1|TITLE OF YOUR PAPER|待填|待补充|示例值")
ANONYMITY_RE = re.compile(r"(学校|学院|大学|University|指导教师|队员姓名|参赛队号[：:]\s*\S)")


class Report:
    def __init__(self):
        self.items = []

    def add(self, ok, category, message, level="required"):
        self.items.append({
            "ok": bool(ok), "category": category,
            "message": message, "level": level,
        })

    @property
    def failures(self):
        return [i for i in self.items if not i["ok"] and i["level"] == "required"]

    @property
    def warnings(self):
        return [i for i in self.items if not i["ok"] and i["level"] == "optional"]


def check_structure(rep):
    missing = [f for f in REQUIRED_FILES if not (WF_ROOT / f).exists()]
    if missing:
        rep.add(False, "package-structure", "缺少核心文件: " + ", ".join(missing))
    else:
        rep.add(True, "package-structure", "全部核心入口存在")

    missing_stage = [f for f in STAGE_FILES if not (WF_ROOT / f).exists()]
    if missing_stage:
        rep.add(False, "stage-files", f"缺少阶段文件: {len(missing_stage)} 个 -> " + ", ".join(missing_stage))
    else:
        rep.add(True, "stage-files", f"9 个阶段文件齐全 (1-9)")


def check_json(rep):
    json_files = list((WF_ROOT / "config").rglob("*.json")) + \
                 list((WF_ROOT / "templates").rglob("*.json"))
    bad = []
    for jf in json_files:
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except Exception as exc:
            bad.append(f"{jf.relative_to(WF_ROOT)}: {exc}")
    if bad:
        rep.add(False, "json-config", "JSON 解析失败 -> " + "; ".join(bad))
    else:
        rep.add(True, "json-config", f"{len(json_files)} 个 JSON 文件解析通过")


def check_schema(rep):
    p = WF_ROOT / "templates/shared/decision_log.json"
    if not p.exists():
        rep.add(False, "decision-log-schema", "模板不存在")
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        rep.add(False, "decision-log-schema", f"解析失败: {exc}")
        return
    ver = data.get("_schema_version")
    stages = [k for k in data.get("stages", {}) if not k.startswith("_")]
    scores = [k for k in data.get("scores", {}) if not k.startswith("_")]
    if ver != "4.0":
        rep.add(False, "decision-log-schema", f"schema 版本应为 4.0，实际 {ver}")
    elif sorted(stages) != [str(i) for i in range(1, 10)]:
        rep.add(False, "decision-log-schema", f"stages 应为 1-9，实际 {sorted(stages)}")
    else:
        rep.add(True, "decision-log-schema", f"schema {ver}，stages {len(stages)} 个，scores {len(scores)} 项")


def check_internal_references(rep):
    """检查 SKILL.md 与 references/ 中引用的仓库文件是否真实存在。

    这一项防止工作流自身出现失效引用 —— 文档与实现不一致的主要来源。
    """
    pattern = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_./\-]*\.(?:md|py|json|tex))`")
    scanned = [WF_ROOT / "SKILL.md"] + sorted((WF_ROOT / "references").glob("*.md"))
    refs = {}
    for f in scanned:
        if not f.exists():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in pattern.findall(text):
            refs.setdefault(m, set()).add(f.relative_to(WF_ROOT).as_posix())

    # 用户工作区路径与占位符写法不算失效
    ignore_prefix = ("state/", "<cwd>/", "<wf>/")
    ignore_exact = {"stage_NN.md", "stage_0N_*.md"}

    dead = []
    for ref, srcs in sorted(refs.items()):
        if ref.startswith(ignore_prefix) or ref in ignore_exact:
            continue
        cands = [WF_ROOT / b / ref for b in PATH_BASES]
        cands.append(WF_ROOT / Path(sorted(srcs)[0]).parent / ref)
        if not any(c.exists() for c in cands):
            dead.append(f"{ref} (引用自 {', '.join(sorted(srcs))})")

    if dead:
        rep.add(False, "internal-references",
                f"{len(refs)} 个引用中 {len(dead)} 个失效 -> " + "; ".join(dead))
    else:
        rep.add(True, "internal-references", f"{len(refs)} 个内部引用全部有效")


def check_tools(rep):
    py_ok = sys.version_info >= (3, 8)
    rep.add(py_ok, "python", f"Python {sys.version.split()[0]}")

    for tool in ("pandoc", "xelatex", "pdflatex"):
        found = shutil.which(tool) is not None
        rep.add(found, f"tool:{tool}",
                "已安装" if found else "未安装（正式渲染需要）",
                level="optional")


def check_workspace(rep, ws):
    ws = Path(ws)
    if not ws.exists():
        rep.add(False, "workspace", f"工作区不存在: {ws}")
        return
    rep.add(True, "workspace", f"工作区存在: {ws}")

    state = ws / "state" / "decision_log.json"
    if state.exists():
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
            stage = data.get("current_stage")
            if stage not in range(1, 10):
                rep.add(False, "workspace-state", f"current_stage 应为 1-9，实际 {stage}")
            else:
                rep.add(True, "workspace-state",
                        f"current_stage={stage}, task_type={data.get('task_type')}")
        except Exception as exc:
            rep.add(False, "workspace-state", f"解析失败: {exc}")
    else:
        rep.add(True, "workspace-state", "尚未初始化（首次运行时自动创建）", level="optional")

    for d in ("results", "figures", "paper_workspace"):
        exists = (ws / d).exists()
        rep.add(exists, f"workspace:{d}", "存在" if exists else "尚未创建",
                level="optional")


def check_paper(rep, ws):
    ws = Path(ws)
    pp = ws / "paper_workspace"
    if not pp.exists():
        rep.add(False, "paper", f"论文工作区不存在: {pp}")
        return

    files = sorted(pp.glob("*.md"))
    if not files:
        rep.add(False, "paper", "未找到任何章节文件")
        return
    rep.add(True, "paper", f"{len(files)} 个章节文件")

    hits = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in PLACEHOLDER_RE.finditer(text):
            line = text[:m.start()].count("\n") + 1
            hits.append(f"{f.name}:{line} [{m.group()}]")
    if hits:
        rep.add(False, "paper:placeholders",
                f"发现 {len(hits)} 处占位符 -> " + "; ".join(hits[:5]))
    else:
        rep.add(True, "paper:placeholders", "无占位符残留")

    anon = []
    for f in files:
        if f.name.startswith("01"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in ANONYMITY_RE.finditer(text):
            line = text[:m.start()].count("\n") + 1
            anon.append(f"{f.name}:{line} [{m.group()[:12]}]")
    if anon:
        rep.add(False, "paper:anonymity",
                f"疑似身份信息 {len(anon)} 处 -> " + "; ".join(anon[:5]),
                level="optional")
    else:
        rep.add(True, "paper:anonymity", "未发现明显身份信息", level="optional")


def main():
    ap = argparse.ArgumentParser(description="CUMCM 9 阶段工作流预检")
    ap.add_argument("--workspace", help="用户工作区路径")
    ap.add_argument("--check-paper", action="store_true", help="检查论文产物")
    ap.add_argument("--skip-tools", action="store_true", help="跳过工具链检查")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args()

    rep = Report()
    check_structure(rep)
    check_json(rep)
    check_schema(rep)
    check_internal_references(rep)
    if not args.skip_tools:
        check_tools(rep)
    if args.workspace:
        check_workspace(rep, args.workspace)
        if args.check_paper:
            check_paper(rep, args.workspace)

    if args.json:
        print(json.dumps({
            "items": rep.items,
            "passed": len(rep.items) - len(rep.failures) - len(rep.warnings),
            "failed": len(rep.failures),
            "warnings": len(rep.warnings),
        }, ensure_ascii=False, indent=2))
        return 1 if rep.failures else 0

    for it in rep.items:
        mark = "✓" if it["ok"] else ("!" if it["level"] == "optional" else "✗")
        print(f"{mark} {it['category']}: {it['message']}")

    print()
    print(f"Summary: {len(rep.items) - len(rep.failures) - len(rep.warnings)} passed, "
          f"{len(rep.warnings)} optional warnings, {len(rep.failures)} failed")
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""step_audit.py — 国赛 9 步确定性审计聚合器(引擎无关,经 run_check 调度)。

用法:
    python step_audit.py <step>
    step ∈ prob|modeling|code|figure|arch|review|paper|compile|improve

被 run_check 以 cwd=作业工作区 调用;对每个子审计运行 _utils_py 下的脚本,
聚合退出码: 任一 rc=1 → 1(步骤自检失败,阻断);全跳过(无适用输入)→ 2(不阻断);
否则 0(通过)。与 run_check 约定 {0,2}=通过一致。

本轮 gating 的确定性审计对齐 SKILL 的真实调用签名。
"""
import glob
import os
import subprocess
import sys
from pathlib import Path

# 编码自愈：Windows 默认 GBK 控制台遇到 ⚠/∈ 等字符会 UnicodeEncodeError 直接崩。
# 不依赖外部 PYTHONIOENCODING，脚本内部强制 UTF-8 输出，保证 AI 在 CLI 里怎么调都不跑偏。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent

# 每步: (脚本名, 参数, 超时秒)。参数含 '*' 时按 glob 展开,无匹配→该子审计跳过。
SUITES = {
    "prob": [
        ("facts_audit.py", ["--stage", "prob"], 150),
        ("capability_check.py", ["--checklist", "CAPABILITY_CHECKLIST.json", "--analysis", "PROBLEM_ANALYSIS.md"], 120),
    ],
    "modeling": [
        ("modeling_coverage_check.py", ["--modeling", "MODELING_REPORT.md"], 150),
        ("count_subproblems.py", ["MODELING_REPORT.md"], 60),
        ("cross_problem_check.py", [], 120),
        ("facts_audit.py", ["--stage", "modeling"], 150),
    ],
    "code": [
        ("count_subproblems.py", ["MODELING_REPORT.md"], 60),
        ("capability_audit.py", ["--checklist", "CAPABILITY_CHECKLIST.json", "--verdict", "CAPABILITY_VERDICT.json", "--fast", "1"], 180),
        ("claim_code_check.py", ["--modeling", "MODELING_REPORT.md", "--codedir", "code"], 180),
        ("data_ingest_check.py", ["--codedir", "code"], 120),
        ("delivery_audit.py", ["--codedir", "code", "--deliverables", "DELIVERABLES.json", "--results", "RESULTS.md"], 120),
        ("leakage_audit.py", ["--codedir", "code", "--results", "RESULTS.md"], 120),
        ("facts_audit.py", ["--stage", "code"], 150),
    ],
    "figure": [
        ("figure_check.py", ["--analysis", "PROBLEM_ANALYSIS.md", "--figdir", "figures"], 60),
        ("fig_include_size.py", ["--figdir", "figures", "--latex", "figures/latex_includes.tex"], 60),
        ("facts_audit.py", ["--stage", "figure"], 150),
    ],
    "arch": [
        ("tikz_check.py", ["figures/tikz_architecture_examples.tex"], 90),
        ("fig_include_size.py", ["--figdir", "figures", "--latex", "figures/latex_includes.tex"], 60),
    ],
    "review": [
        ("recipe_audit.py", ["--plan", "PROBLEM_ANALYSIS.md", "--figdir", "figures"], 120),
    ],
    "paper": [
        ("paper_claim_check.py", ["--fast", "1"], 120),
        ("writing_check.py", ["paper"], 180),
        ("fig_size_consistency_check.py", ["--latex", "figures/latex_includes.tex", "--paperdir", "paper"], 120),
        ("facts_audit.py", ["--stage", "paper"], 150),
    ],
    "compile": [
        ("compile_check.py", ["paper"], 180),
        ("writing_check.py", ["paper"], 180),
        ("html_pdf_check.py", ["figures/*.pdf"], 180),
        ("claim_code_check.py", ["--modeling", "MODELING_REPORT.md", "--codedir", "code"], 180),
    ],
    "improve": [
        ("html_pdf_check.py", ["figures/*.pdf"], 180),
        ("facts_audit.py", ["--stage", "full"], 150),
    ],
}


def expand_args(args):
    """展开含 glob 的参数;返回 (final_args, matched)。"""
    out = []
    matched = True
    for a in args:
        if "*" in a or "?" in a:
            hits = sorted(glob.glob(a))
            if not hits:
                matched = False
            out.extend(hits)
        else:
            out.append(a)
    return out, matched


def run_item(script, args, timeout):
    sp = HERE / script
    if not sp.is_file():
        return None, f"脚本 {script} 不存在"
    args2, matched = expand_args(args)
    if not matched:
        return None, None  # 无适用输入 → 跳过
    try:
        # 子进程也强制 UTF-8 输出，与父进程 encoding='utf-8' 解码一致，防 GBK 子脚本乱码
        _env = dict(os.environ)
        _env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, str(sp), *args2],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=_env)
        out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
        return r.returncode, out[-1500:]
    except subprocess.TimeoutExpired:
        return -1, f"超时(>{timeout}s)"
    except Exception as e:
        return -1, str(e)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in SUITES:
        print("用法: python step_audit.py <step>; step = " + "|".join(SUITES))
        return 2
    step = sys.argv[1]
    items = SUITES[step]
    failed = False
    ran_any = False
    print(f"=== step_audit[{step}] — {len(items)} 项确定性审计 ===")
    for script, args, timeout in items:
        label = f"{script} {' '.join(args)}".strip()
        rc, out = run_item(script, args, timeout)
        if rc is None:
            if out is None:
                print(f"  [SKIP] {label} — 无适用输入(未配套产物)")
            else:
                print(f"  [SKIP] {label} — {out}")
            continue
        ran_any = True
        if rc in (0, 2):
            print(f"  [PASS] {label} (rc={rc})")
        else:
            failed = True
            print(f"  [FAIL] {label} (rc={rc})")
        if out:
            # 节选尾部证据,回喂给 LLM/用户
            for line in out.splitlines()[-8:]:
                print(f"        | {line}")
    if failed:
        print(f"=== step_audit[{step}]: 存在 FAIL,步骤自检未通过 (exit 1) ===")
        return 1
    if not ran_any:
        print(f"=== step_audit[{step}]: 全部跳过(无适用产物) (exit 2) ===")
        return 2
    print(f"=== step_audit[{step}]: 全部通过 (exit 0) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
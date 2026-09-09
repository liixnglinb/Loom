# -*- coding: utf-8 -*-
"""
code_starter 自动调用入口
用法:
  python run_starter.py <family> [--out <prefix>]
  family: optimization | prediction | evaluation | classification | simulation
          | graph | stats | dynamical | signal | decision
          | matlab_ode | matlab_optimization
自动把脚本复制到工作区运行 (对应 CODE_STYLE §3 调用协议), 返回状态与产物路径。
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PY = r"C:\Users\李星历\AppData\Local\Programs\Python\Python312\python.exe"
MATLAB = r"D:\Matlab\bin\matlab.exe"

HERE = Path(__file__).resolve().parent.parent  # skill 根目录
STARTER = HERE / "templates" / "shared" / "code_starter"

FAMILY_PY = {
    "optimization": "optimization.py",
    "prediction": "prediction.py",
    "evaluation": "evaluation.py",
    "classification": "classification.py",
    "simulation": "simulation.py",
    "graph": "graph.py",
    "stats": "stats_analysis.py",
    "dynamical": "dynamical.py",
    "signal": "signal_analysis.py",
    "decision": "decision.py",
}
FAMILY_MAT = {
    "matlab_ode": "matlab_ode.m",
    "matlab_optimization": "matlab_optimization.m",
    "matlab_prediction": "matlab_prediction.m",
    "matlab_evaluation": "matlab_evaluation.m",
    "matlab_classification": "matlab_classification.m",
    "matlab_simulation": "matlab_simulation.m",
    "matlab_graph": "matlab_graph.m",
    "matlab_stats": "matlab_stats.m",
    "matlab_signal": "matlab_signal.m",
    "matlab_decision": "matlab_decision.m",
}


def run_python(script, cwd, out_prefix=None):
    cmd = [PY, str(script)]
    env = dict(os.environ)
    if out_prefix:
        env["OUT_PREFIX"] = out_prefix
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def run_matlab(script, cwd):
    cmd = [MATLAB, "-batch", f"run('{script.name}')"]
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    if len(sys.argv) < 2:
        print("用法: python run_starter.py <family>")
        print("可用: " + ", ".join(list(FAMILY_PY) + list(FAMILY_MAT)))
        return 1
    family = sys.argv[1]
    out_prefix = sys.argv[2] if len(sys.argv) > 2 else None

    cwd = Path.cwd()
    os.makedirs(cwd / "results", exist_ok=True)
    os.makedirs(cwd / "figures", exist_ok=True)

    if family in FAMILY_PY:
        src = STARTER / FAMILY_PY[family]
        dst = cwd / FAMILY_PY[family]
        shutil.copy(src, dst)
        code, out, err = run_python(dst, cwd, out_prefix)
        print(f"[{family}] exit={code}")
        print(out[-1500:] if out else err[-1500:])
        # 运行后清理临时副本
        try:
            dst.unlink()
        except OSError:
            pass
        return code
    if family in FAMILY_MAT:
        src = STARTER / FAMILY_MAT[family]
        dst = cwd / FAMILY_MAT[family]
        shutil.copy(src, dst)
        code, out, err = run_matlab(dst, cwd)
        print(f"[{family}] exit={code}")
        print(out[-1500:] if out else err[-1500:])
        try:
            dst.unlink()
        except OSError:
            pass
        return code

    print(f"未知 family: {family}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

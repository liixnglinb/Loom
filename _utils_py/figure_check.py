#!/usr/bin/env python
"""图表清单对账 — math-modeling skill Step3 闸门。
作用: 校验 FIGURE_MANIFEST(在 PROBLEM_ANALYSIS.md 的 <!-- BEGIN/END FIGURE_MANIFEST --> 区块)
      中规划的全部图都在 figures/ 有对应产物。少一张即报错。
用法:
    python _utils/figure_check.py --analysis PROBLEM_ANALYSIS.md --figdir figures
退出码: 0=全部产出  1=有缺失
"""
import argparse
import os
import re
import sys

BEGIN = "<!-- BEGIN FIGURE_MANIFEST -->"
END = "<!-- END FIGURE_MANIFEST -->"
# 统一匹配 'fig_xxx' 与 'tikz_xxx' 名称(不含扩展名)
NAME = re.compile(r"\b(fig_\w+|tikz_\w+)")


def extract_names(text):
    if BEGIN not in text or END not in text:
        return None
    seg = text.split(BEGIN, 1)[1].split(END, 1)[0]
    return set(NAME.findall(seg))


def main():
    ap = argparse.ArgumentParser(description="FIGURE_MANIFEST 对账")
    ap.add_argument("--analysis", required=True, help="PROBLEM_ANALYSIS.md 路径")
    ap.add_argument("--figdir", required=True, help="figures 目录")
    args = ap.parse_args()

    if not os.path.isfile(args.analysis):
        print("SKIP: 无 PROBLEM_ANALYSIS.md（分析步未产出，无法对账）(exit 2)")
        return 2
    text = open(args.analysis, encoding="utf-8").read()
    names = extract_names(text)
    if names is None:
        print("SKIP: 未找到 FIGURE_MANIFEST 区块 (exit 2)")
        return 2

    existing = {os.path.splitext(p)[0] for p in os.listdir(args.figdir)} if os.path.isdir(args.figdir) else set()
    missing = [n for n in names if n not in existing]
    for n in names:
        print(f"  {'✓' if n in existing else '✗'} {n}")

    if missing:
        print(f"FAIL: 缺 {len(missing)} 张: {missing}", file=sys.stderr)
        return 1
    print("PASS: 规划图全部产出")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
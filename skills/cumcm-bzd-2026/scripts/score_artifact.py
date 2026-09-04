#!/usr/bin/env python3
"""CUMCM 9 阶段工作流 —— 评分校验与 verdict 重算。

设计原则：verdict 由脚本重算，不采信模型自报。

用法:
    # 单阶段评分
    python score_artifact.py --stage 5 \
        --critique <cwd>/state/critique_v0.json \
        --decision-log <cwd>/state/decision_log.json

    # per-Qi 聚合
    python score_artifact.py --mode aggregate_qi \
        --qi-results <cwd>/state/qi_results.json \
        --decision-log <cwd>/state/decision_log.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

WF_ROOT = Path(__file__).resolve().parent.parent
WEIGHTS_PATH = WF_ROOT / "config" / "dim_weights.json"

CLAMP_MIN, CLAMP_MAX = 0.7, 1.5
MAX_ITER = 3

# verdict 判定阈值（与 references/feedback_l1_critic.md 严格一致）
PASS_EARLY_MIN, PASS_EARLY_MEAN = 9, 9
PASS_MIN, PASS_MEAN = 7, 8


class ScoreError(Exception):
    pass


def load_weights():
    if not WEIGHTS_PATH.exists():
        return {}
    return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))


def resolve_decision_log(cli_value):
    if cli_value:
        return Path(cli_value)
    for var in ("CUMCM9_STATE_DIR", "MATHMODEL_STATE_DIR"):
        if os.environ.get(var):
            return Path(os.environ[var]) / "decision_log.json"
    return Path.cwd() / "state" / "decision_log.json"


def load_json(path, what):
    p = Path(path)
    if not p.exists():
        raise ScoreError(f"{what} 不存在: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ScoreError(f"{what} 解析失败: {exc}")


def validate_critique(critique):
    """校验 critique JSON 结构。返回 (errors, warnings)。"""
    errors, warnings = [], []

    if "stage" not in critique:
        errors.append("缺少 stage 字段")
    stage = critique.get("stage")
    if stage is not None and stage not in range(1, 10):
        errors.append(f"stage 应为 1-9，实际 {stage}")

    scores = critique.get("scores")
    if not isinstance(scores, dict) or not scores:
        errors.append("scores 必须非空对象")
        return errors, warnings

    for dim, val in scores.items():
        if not isinstance(val, (int, float)):
            errors.append(f"维度 {dim} 的分数必须是数字，实际 {type(val).__name__}")
        elif not (1 <= val <= 10):
            errors.append(f"维度 {dim} 的分数 {val} 超出 [1, 10]")

    for issue in critique.get("issues", []):
        if issue.get("severity") not in ("high", "medium", "low"):
            warnings.append(f"issue 的 severity 取值异常: {issue.get('severity')}")

    return errors, warnings


def weighted_mean(scores, weights):
    """加权均分。权重缺失默认 1.0，并 clamp 到 [0.7, 1.5]。"""
    num = den = 0.0
    for dim, val in scores.items():
        w = weights.get(dim, 1.0)
        w = max(CLAMP_MIN, min(CLAMP_MAX, float(w)))
        num += float(val) * w
        den += w
    return num / den if den else 0.0


def compute_verdict(scores, issues, task_type, stage, iteration, weights_all):
    """按 references/feedback_l1_critic.md 的规则重算 verdict。"""
    raw_min = min(scores.values())
    stage_weights = weights_all.get(task_type or "default", {}).get(str(stage), {})
    if not isinstance(stage_weights, dict):
        stage_weights = {}
    wmean = weighted_mean(scores, stage_weights)

    has_high = any(i.get("severity") == "high" for i in issues or [])

    if has_high:
        verdict = "block"
    elif raw_min >= PASS_EARLY_MIN and wmean >= PASS_EARLY_MEAN:
        verdict = "pass_early"
    elif raw_min >= PASS_MIN and wmean >= PASS_MEAN:
        verdict = "pass"
    elif iteration >= MAX_ITER:
        verdict = "carryover"
    else:
        verdict = "refine"

    return {
        "min": round(raw_min, 2),
        "mean": round(sum(scores.values()) / len(scores), 2),
        "weighted_mean": round(wmean, 2),
        "verdict": verdict,
        "iteration": iteration,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }


def persist(decision_log_path, stage, entry, qi_id=None):
    p = Path(decision_log_path)
    if p.exists():
        log = load_json(p, "decision_log")
    else:
        log = {}
        p.parent.mkdir(parents=True, exist_ok=True)

    key = f"{stage}_per_qi" if qi_id else str(stage)
    log.setdefault("scores", {})
    log["scores"].setdefault(key, [])
    log["scores"][key].append(entry)

    log.setdefault("iterations", {})
    log["iterations"][key] = entry["iteration"]

    # 原子写入
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return log


def handle_stage(args):
    weights_all = load_weights()
    critique = load_json(args.critique, "critique")

    errors, warnings = validate_critique(critique)
    for w in warnings:
        print(f"[WARN] {w}")
    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        return 1

    stage = critique["stage"]
    iteration = int(critique.get("iteration", 0))
    issues = critique.get("issues", [])

    log_path = resolve_decision_log(args.decision_log)
    task_type = "default"
    if log_path.exists():
        try:
            task_type = load_json(log_path, "decision_log").get("task_type") or "default"
        except Exception:
            pass

    result = compute_verdict(critique["scores"], issues, task_type, stage,
                             iteration, weights_all)

    print(f"[OK] stage={stage} iter={iteration} task_type={task_type}")
    print(f"     min={result['min']} mean={result['mean']} "
          f"weighted_mean={result['weighted_mean']}")
    print(f"     verdict = {result['verdict']}")

    suggested = critique.get("verdict_suggestion")
    if suggested and suggested != result["verdict"]:
        print(f"[WARN] 模型自报 verdict '{suggested}' 与重算结果 "
              f"'{result['verdict']}' 不一致，以重算结果为准")

    if args.dry_run:
        print("[DRY-RUN] 未写入 decision_log")
        return 0

    entry = dict(result)
    entry["scores"] = critique["scores"]
    entry["issues"] = issues
    if critique.get("qi_id"):
        entry["qi_id"] = critique["qi_id"]

    persist(log_path, stage, entry, qi_id=critique.get("qi_id"))
    print(f"[OK] 已写入 {log_path}")
    return 0


def handle_aggregate(args):
    """per-Qi 聚合：重算 qi_status / review_qis / refine_qis 与 stage-level verdict。"""
    weights_all = load_weights()
    qi_results = load_json(args.qi_results, "qi-results")

    if not isinstance(qi_results, list) or not qi_results:
        raise ScoreError("qi-results 必须是非空数组，每项含 qi_id / scores / issues")

    log_path = resolve_decision_log(args.decision_log)
    task_type = "default"
    if log_path.exists():
        try:
            task_type = load_json(log_path, "decision_log").get("task_type") or "default"
        except Exception:
            pass

    qi_status, review_qis, refine_qis, block_qis = {}, [], [], []
    all_scores, all_issues, per_qi_entries = {}, [], []

    for item in qi_results:
        qi = item.get("qi_id")
        if not qi:
            raise ScoreError("qi-results 中每项都必须含 qi_id")
        scores = item.get("scores", {})
        if not scores:
            raise ScoreError(f"{qi} 缺少 scores")

        for dim, val in scores.items():
            if not isinstance(val, (int, float)) or not (1 <= val <= 10):
                raise ScoreError(f"{qi} 的维度 {dim} 分数非法: {val}")

        issues = item.get("issues", [])
        r = compute_verdict(scores, issues, task_type, 5,
                            int(item.get("iteration", 0)), weights_all)
        r["qi_id"] = qi
        r["scores"] = scores
        per_qi_entries.append(r)

        qi_status[qi] = r["verdict"]
        all_scores[qi] = r["weighted_mean"]
        all_issues.extend(issues)

        if r["verdict"] == "block":
            block_qis.append(qi)
        elif r["verdict"] in ("refine", "refine_partial"):
            refine_qis.append(qi)
        elif r["min"] < PASS_MIN:
            review_qis.append(qi)

    # stage-level：按各 Qi 加权均分作为整体表现
    log = load_json(log_path, "decision_log") if log_path.exists() else {}
    qi_weights = (log.get("stages", {}).get("5", {}) or {}).get("qi_weights") or \
                 [1.0] * len(qi_results)
    if len(qi_weights) != len(qi_results):
        print(f"[WARN] qi_weights 长度 {len(qi_weights)} 与子问数 "
              f"{len(qi_results)} 不符，改用均匀权重")
        qi_weights = [1.0] * len(qi_results)

    num = sum(all_scores[q] * qi_weights[i] for i, q in enumerate(all_scores))
    den = sum(qi_weights)
    stage_wmean = num / den if den else 0.0
    stage_min = min(min(r["scores"].values()) for r in per_qi_entries)

    has_high = any(i.get("severity") == "high" for i in all_issues)

    if block_qis or has_high:
        stage_verdict = "block"
    elif stage_min >= PASS_EARLY_MIN and stage_wmean >= PASS_EARLY_MEAN:
        stage_verdict = "pass_early"
    elif stage_min >= PASS_MIN and stage_wmean >= PASS_MEAN:
        stage_verdict = "pass_with_review" if review_qis else "pass"
    elif len(refine_qis) < len(qi_results):
        stage_verdict = "refine_partial"
    else:
        stage_verdict = "refine"

    print(f"[OK] 聚合 {len(qi_results)} 个子问 (task_type={task_type})")
    for r in per_qi_entries:
        print(f"     {r['qi_id']}: min={r['min']:>4} wmean={r['weighted_mean']:>5} "
              f"-> {r['verdict']}")
    print(f"     stage: min={stage_min} wmean={round(stage_wmean, 2)} "
          f"-> {stage_verdict}")
    if refine_qis:
        print(f"     refine_qis: {', '.join(refine_qis)}")
    if review_qis:
        print(f"     review_qis: {', '.join(review_qis)}")
    if block_qis:
        print(f"     block_qis: {', '.join(block_qis)}")

    if args.dry_run:
        print("[DRY-RUN] 未写入 decision_log")
        return 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = load_json(log_path, "decision_log") if log_path.exists() else {}
    log.setdefault("stages", {})
    log["stages"].setdefault("5", {})
    log["stages"]["5"]["qi_count"] = len(qi_results)
    log["stages"]["5"]["qi_weights"] = qi_weights
    log["stages"]["5"]["qi_status"] = qi_status
    log["stages"]["5"]["review_qis"] = review_qis
    log["stages"]["5"]["refine_qis"] = refine_qis
    log["stages"]["5"]["block_qis"] = block_qis
    log["stages"]["5"]["aggregate"] = {
        "min": round(stage_min, 2),
        "weighted_mean": round(stage_wmean, 2),
        "verdict": stage_verdict,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }

    log.setdefault("scores", {})
    log["scores"]["5_per_qi"] = per_qi_entries
    log["scores"].setdefault("5", []).append(log["stages"]["5"]["aggregate"])

    tmp = log_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(log_path)
    print(f"[OK] 已原子写入 {log_path}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="CUMCM 9 阶段评分与 verdict 重算")
    ap.add_argument("--mode", choices=["stage", "aggregate_qi"], default="stage")
    ap.add_argument("--stage", type=int, help="阶段号 1-9")
    ap.add_argument("--critique", help="critic 输出的 JSON 路径")
    ap.add_argument("--qi-results", help="per-Qi 结果 JSON 路径（aggregate_qi 模式）")
    ap.add_argument("--decision-log", help="decision_log.json 路径")
    ap.add_argument("--dry-run", action="store_true", help="只计算结果不写入")
    args = ap.parse_args()

    try:
        if args.mode == "aggregate_qi":
            if not args.qi_results:
                raise ScoreError("aggregate_qi 模式需要 --qi-results")
            return handle_aggregate(args)
        else:
            if not args.critique:
                raise ScoreError("stage 模式需要 --critique")
            return handle_stage(args)
    except ScoreError as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

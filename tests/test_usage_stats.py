# -*- coding: utf-8 -*-
"""Token 用量：两家 CLI 的字段归一、解析落库、以及统计页的聚合口径。

正文只能由 CLI 产出，token 数也只能来自它们自报的事件 —— 解析错了统计页
就在报假数，所以这里把事件形状钉死。
"""
from datetime import date, timedelta

import pytest

from app import agents, db, runner


def _state():
    return {"texts": [], "final": "", "tools": 0, "turns": 0, "is_error": False,
            "duration_ms": None, "cost_usd": None, "error": "", "errors": 0,
            "abort": False, "tok": {}, "tok_total": None}


def test_tok_add_maps_both_vendors_onto_one_key_set():
    """字段名对齐本机装好的 CLI：Claude 用 cache_read/cache_creation，
    Codex 用 cached_input/cache_write_input + reasoning_output。
    任一家改名都会在这里暴露，而不是让统计页静默少一项。"""
    claude = agents._tok_add({}, {"input_tokens": 1200, "output_tokens": 800,
                                  "cache_read_input_tokens": 9000,
                                  "cache_creation_input_tokens": 100})
    assert claude == {"in": 1200, "out": 800, "cache_read": 9000,
                      "cache_write": 100, "total": 11100}
    codex = agents._tok_add({}, {"input_tokens": 5000, "cached_input_tokens": 4000,
                                 "cache_write_input_tokens": 50,
                                 "output_tokens": 900,
                                 "reasoning_output_tokens": 300,
                                 "total_tokens": 5900})
    # 5000 输入里含着 4000 读缓存和 50 写缓存，两头都要减出来才不重叠
    assert codex == {"in": 950, "out": 900, "cache_read": 4000,
                     "cache_write": 50, "reason": 300, "total": 5900}


def test_codex_total_matches_its_own_reported_total():
    """codex 自己会算 total_tokens。归一后的四项相加必须等于它，
    这条不是装饰：包含关系理解错一次（比如漏减写缓存），两边就会差出那一截。
    缓存值故意给非零 —— 全给 0 的话这条永远查不出问题。"""
    raw = {"input_tokens": 48000, "cached_input_tokens": 45000,
           "cache_write_input_tokens": 700, "output_tokens": 1200,
           "reasoning_output_tokens": 700}
    got = agents._tok_add({}, raw)
    assert got["total"] == raw["input_tokens"] + raw["output_tokens"]
    assert got["in"] == 48000 - 45000 - 700


def test_tok_add_never_double_counts_reason():
    """reasoning 是 output 的一段，进 total 就会重复。"""
    got = agents._tok_add({}, {"input_tokens": 10, "output_tokens": 40,
                               "reasoning_output_tokens": 30})
    assert got["reason"] == 30 and got["total"] == 50


def test_tok_add_ignores_missing_and_non_numeric():
    got = agents._tok_add({}, {"input_tokens": 7, "output_tokens": None, "bogus": "9"})
    assert got == {"in": 7, "total": 7}


def test_tok_add_clamps_negative_input():
    """缓存不可能比输入还大；真出现了也不把 in 算成负的（缓存那一段照原样保留）。"""
    got = agents._tok_add({}, {"input_tokens": 100, "cached_input_tokens": 260,
                               "output_tokens": 5})
    assert got.get("in", 0) == 0 and got["cache_read"] == 260 and got["total"] == 265


def test_claude_result_event_captures_tokens():
    st = _state()
    agents._claude_events({"type": "result", "is_error": False, "num_turns": 3,
                           "duration_ms": 9000, "total_cost_usd": 0.05,
                           "usage": {"input_tokens": 1200, "output_tokens": 800,
                                     "cache_read_input_tokens": 9000,
                                     "cache_creation_input_tokens": 100},
                           "result": "ok"}, lambda e: None, st)
    assert st["cost_usd"] == 0.05
    assert st["tok_total"] == {"in": 1200, "out": 800, "cache_read": 9000,
                               "cache_write": 100, "total": 11100}


def test_codex_prefers_its_own_cumulative_total():
    """token_count 带的是累计总量。逐回合相加只是没有该事件时的兜底，
    两者都在时必须是累计值赢，否则同一份用量会被数两遍。"""
    st = _state()
    agents._codex_events({"type": "turn.completed",
                          "usage": {"input_tokens": 10, "output_tokens": 5}},
                         lambda e: None, st)
    assert st["tok"] == {"in": 10, "out": 5, "total": 15}
    agents._codex_events({"type": "token_count", "info": {"total_token_usage": {
        "input_tokens": 900, "cached_input_tokens": 800, "output_tokens": 200,
        "reasoning_output_tokens": 60}}}, lambda e: None, st)
    # 900 的输入里含着 800 缓存，所以 total 仍是 900+200，不是 900+800+200
    assert st["tok_total"] == {"in": 100, "out": 200, "cache_read": 800,
                               "reason": 60, "total": 1100}
    assert (st["tok_total"] or st["tok"])["in"] == 100


@pytest.mark.parametrize("offsets,expect", [
    ([], (0, 0)),
    ([0, 1, 2], (3, 3)),
    ([0, 1, 3], (2, 2)),          # 中间断一天，当前连续只数到断点
    ([0, 2, 3, 4], (1, 3)),       # 昨天没动 → 当前连续归 1，最长仍是 3
    ([5, 6, 7], (0, 3)),          # 最近一次是 5 天前 → 当前连续清零
])
def test_streaks(offsets, expect):
    today = date.today()
    daily = {(today - timedelta(days=o)).isoformat(): {"tokens": 10, "steps": 1}
             for o in offsets}
    assert runner._streaks(daily) == expect


def test_usage_stats_totals_tokens_and_buckets_by_day():
    today = date.today().isoformat()
    yest = (date.today() - timedelta(days=1)).isoformat()
    steps = [
        {"key": "a", "label": "A", "status": "done",
         "meta": {"tokens": {"in": 100, "out": 40}, "duration_ms": 5000,
                  "cost_usd": 0.01, "tools": 2, "turns": 1, "day": today}},
        {"key": "b", "label": "B", "status": "done",
         "meta": {"tokens": {"in": 30, "out": 10}, "duration_ms": 9000,
                  "cost_usd": 0.02, "tools": 1, "turns": 1, "day": yest}},
    ]
    db.create_run("run-tok-stat", "auto-workflow", "t", steps)
    db.update_run("run-tok-stat", status="done", steps=steps)
    st = runner.usage_stats()
    # 别的用例可能也往这张临时库里写过，所以只断言下界和这一天的归属
    assert st["tokens"]["in"] >= 130 and st["tokens"]["out"] >= 50
    assert st["tokens_total"] >= 180
    assert st["daily"][today]["tokens"] >= 140
    assert st["peak_day"] == today or st["peak_day_tokens"] >= 140
    assert st["streak_now"] >= 2
    assert st["peak_step_ms"] >= 9000


def test_usage_stats_survives_steps_without_tokens():
    """老 run 的 meta 里根本没有 tokens 字段，缺了要按 0 计而不是抛。"""
    steps = [{"key": "a", "label": "A", "status": "done",
              "meta": {"duration_ms": 1200, "cost_usd": 0.001}}]
    db.create_run("run-tok-legacy", "quick-flow", "t", steps)
    db.update_run("run-tok-legacy", status="done", steps=steps)
    st = runner.usage_stats()
    assert isinstance(st["tokens_total"], int)
    assert st["streak_best"] >= 0


def test_run_totals_are_not_limited_by_the_scan_window(dbsession, fresh_runs, monkeypatch):
    """逐条累计只扫最近 500 条是性能决定，但"总共跑过几次"和状态分布不是：
    它们走 COUNT(*)。这里把窗口压成 1 条，总次数仍要是全表的 3。"""
    real = db.list_runs
    for i, st in enumerate(("done", "failed", "done")):
        dbsession.create_run(f"run-window{i:03d}", "p", steps=[])
        dbsession.update_run(f"run-window{i:03d}", status=st)
    monkeypatch.setattr(db, "list_runs", lambda pipeline=None, limit=50: real(pipeline, 1))
    d = runner.usage_stats()
    assert d["runs"] == 3, "总次数跟着扫描窗口走了，跑到 500 就会永远卡在 500"
    assert d["by_status"] == {"done": 2, "failed": 1}


def test_orphan_scan_covers_every_run_not_just_the_window(dbsession, fresh_runs,
                                                          workspaces, monkeypatch):
    """孤儿工作区=有目录没记录。以前拿 list_runs 的前 500 条当"全部记录"，
    第 501 条的现场就被当成孤儿报出来 —— 那一栏旁边可是"清理"的语义。
    这里把窗口打成空，判定必须仍然认得这些 id。"""
    dbsession.create_run("run-keepme001", "p", steps=[])
    (workspaces / "run-keepme001").mkdir(parents=True, exist_ok=True)
    dbsession.create_run("run-keepme002", "p", steps=[])
    (workspaces / "run-keepme002").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(db, "list_runs", lambda *a, **k: [])
    names = {o["name"] for o in runner.orphan_workspaces()}
    assert "run-keepme001" not in names and "run-keepme002" not in names
    (workspaces / "run-keepme001").rmdir()
    (workspaces / "run-keepme002").rmdir()


def test_daily_buckets_carry_turns_and_tools(dbsession, fresh_runs):
    """悬停卡片要写"多少轮消息"，那个数只能从每步 meta.turns 归到当天。
    以前 daily 只有 tokens/steps，卡片就只能报一半。"""
    today = date.today().isoformat()
    steps = [{"key": "a", "status": "done", "model_used": "claude-sonnet-4-5",
              "meta": {"tokens": {"in": 10, "out": 5, "total": 15}, "turns": 3,
                       "tools": 7, "day": today, "engine": "claude"}}]
    db.create_run("run-daily-turns", "p", "t", steps)
    db.update_run("run-daily-turns", status="done", steps=steps)
    d = runner.usage_stats()["daily"][today]
    assert d["turns"] == 3 and d["tools"] == 7
    assert d["tokens"] == 15 and d["steps"] == 1


def test_by_model_buckets_engine_and_model_apart(dbsession, fresh_runs):
    """模型用量那张卡按 引擎 + 模型 分桶。没注入端点的步骤 model 是空串 ——
    "沿用 CLI 自身配置"是给人看的标签，不该进接口。"""
    today = date.today().isoformat()
    steps = [
        {"key": "a", "status": "done", "meta": {"tokens": {"total": 100}, "turns": 2,
                                                "day": today, "engine": "claude",
                                                "model": "claude-sonnet-4-5"}},
        {"key": "b", "status": "done", "meta": {"tokens": {"total": 40}, "turns": 1,
                                                "day": today, "engine": "codex"},
         "model_used": "（沿用 CLI 自身配置）"},
        {"key": "c", "status": "done", "meta": {"tokens": {"total": 7}, "turns": 1,
                                                "day": today, "engine": "codex",
                                                "model": "gpt-5-codex"}},
    ]
    db.create_run("run-by-model", "p", "t", steps)
    db.update_run("run-by-model", status="done", steps=steps)
    bm = runner.usage_stats()["by_model"]
    by = {(b["engine"], b["model"]): b for b in bm}
    assert by[("claude", "claude-sonnet-4-5")]["tokens"] == 100
    assert by[("codex", "")]["steps"] == 1 and by[("codex", "")]["turns"] == 1
    assert by[("codex", "gpt-5-codex")]["tokens"] == 7
    assert sum(b["tokens"] for b in bm) == 147


def test_step_meta_records_the_model(dbsession):
    """新跑的步骤必须把模型名留在 meta 里，否则模型用量只能靠那句人读的标签倒推。"""
    import inspect
    src = inspect.getsource(runner)
    assert '"model": conf["model"]' in src, "step.meta 里没有 model 这个键"

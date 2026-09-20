# -*- coding: utf-8 -*-
"""跑一次真实子进程的完整生命周期：用假 CLI 顶替 claude / codex。

刻意走 subprocess 而不是打桩 Popen —— 要验的就是「行协议 → 状态机 →
落盘 → 事件总线 → 转录日志」这一整条链路，包括 Windows 下 .cmd 垫片。
"""
import json
import os
import stat
import sys
import time
from pathlib import Path

import pytest

from app import agents, db, runner

STUB = r'''
import json, sys
if "--version" in sys.argv:
    print("loom-stub 0.0.1"); sys.exit(0)
sys.stdin.read()                      # 提示词从 stdin 进来，读掉别堵管道
mode = "ok"
for a in sys.argv:
    if a.startswith("--stub-mode="):
        mode = a.split("=", 1)[1]
w = sys.stdout.write
w(json.dumps({"type": "system", "subtype": "init", "model": "stub-1",
              "tools": ["Read", "Write"]}) + "\n")
w(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "Write", "input": {"file_path": "draft.md"}}]}}) + "\n")
w(json.dumps({"type": "user", "message": {"content": [
    {"type": "tool_result", "content": "written"}]}}) + "\n")
if mode == "fail":
    w(json.dumps({"type": "system", "subtype": "api_retry", "attempt": 1,
                  "max_retries": 3, "error": "ConnectionRefused",
                  "retry_delay_ms": 1000}) + "\n")
    w(json.dumps({"type": "result", "is_error": True, "num_turns": 1,
                  "duration_ms": 420, "result": "连不上端点"}) + "\n")
else:
    w(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "# 草稿\n桩产出的正文"}]}}) + "\n")
    w(json.dumps({"type": "result", "is_error": False, "num_turns": 2,
                  "duration_ms": 1400, "total_cost_usd": 0.0123,
                  "result": "# 草稿\n桩产出的正文"}) + "\n")
sys.stdout.flush()
'''


@pytest.fixture
def stub_cli(tmp_path):
    """生成一个假 CLI 并把 claude_cli 指过去；返回可注入的额外参数。"""
    script = tmp_path / "stub_agent.py"
    script.write_text(STUB, encoding="utf-8")
    if os.name == "nt":
        shim = tmp_path / "stub-claude.cmd"
        # 批处理按本机 ANSI 码页读，用 utf-8 写会把中文用户名路径解成乱码
        shim.write_bytes(
            ("@echo off\r\nset PYTHONIOENCODING=utf-8\r\n"
             f'"{sys.executable}" "{script}" %*\r\n').encode("mbcs"))
    else:
        shim = tmp_path / "stub-claude"
        shim.write_text(
            f'#!/bin/sh\nPYTHONIOENCODING=utf-8 exec "{sys.executable}" '
            f'"{script}" "$@"\n', encoding="utf-8")
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP)
    db.set_setting("claude_cli", str(shim))
    db.set_setting("default_engine", "claude")
    agents.clear_bin_cache()
    yield str(shim)
    db.set_setting("claude_cli", "")
    agents.clear_bin_cache()


@pytest.fixture
def flow(dbsession):
    dbsession.create_pipeline("lifecycle-flow", label="生命周期",
                              steps=[{"key": "draft", "label": "起草", "out": "draft.md",
                                      "engine": "claude", "skill": ""}])
    yield "lifecycle-flow"
    dbsession.delete_pipeline("lifecycle-flow")


def _wait(run_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = db.get_run(run_id)
        if r and r["status"] not in ("running", "revising", "pending"):
            return r
        time.sleep(0.15)
    raise AssertionError(f"运行 {run_id} {timeout}s 还没收敛：{db.get_run(run_id)}")


def test_stub_binary_resolves(stub_cli):
    assert agents.resolve_binary("claude") == stub_cli


def test_happy_path_end_to_end(client, stub_cli, flow, workspaces):
    run = runner.start_run(flow, label="一次跑", brief="写点什么")
    done = _wait(run["id"])
    assert done["status"] == "done", done["error"]
    step = done["steps"][0]
    assert step["status"] == "done"
    assert step["meta"]["tools"] == 1 and step["meta"]["turns"] == 2
    assert step["meta"]["duration_ms"] == 1400
    assert step["meta"]["log"].endswith(".jsonl")
    assert step["engine_used"] == "claude"

    # 智能体只把正文打在回答里、没真落盘 —— runner 兜底代写，下游才有输入
    f = runner.workspace_dir(run['id']) / "draft.md"
    assert f.is_file() and "桩产出的正文" in f.read_text(encoding="utf-8")

    body = client.get(f"/api/runs/{run['id']}").json()
    assert "draft.md" in body["artifacts"]
    names = [x["name"] for x in body["logs"]]
    assert names == [step["meta"]["log"]]

    d = client.get(f"/api/runs/{run['id']}/logs/{names[0]}").json()
    parsed = [json.loads(x) for x in d["lines"]]
    assert parsed[0]["subtype"] == "init"
    assert parsed[-1]["type"] == "result"
    assert not d["truncated"]


def test_failed_step_keeps_log(client, stub_cli, flow, monkeypatch, workspaces):
    monkeypatch.setattr(agents, "_claude_args",
                        lambda *a, **k: ["--stub-mode=fail"])
    run = runner.start_run(flow, label="会失败")
    done = _wait(run["id"])
    assert done["status"] == "failed"
    step = done["steps"][0]
    assert step["status"] == "failed"
    assert "连不上端点" in step["msg"]
    assert step["meta"]["log"], "失败步骤必须留下可诊断的转录"
    log = runner.workspace_dir(run['id']) / "_turn_logs" / step["meta"]["log"]
    assert "api_retry" in log.read_text(encoding="utf-8")
    # 失败时引擎的 final 是报错文本，不能当产物落盘给下一步
    assert not (runner.workspace_dir(run['id']) / "draft.md").exists()


def test_transcript_log_is_per_step_not_shared(stub_cli, dbsession, workspaces):
    dbsession.create_pipeline("two-step", label="两步", steps=[
        {"key": "a", "label": "A", "out": "a.md", "engine": "claude", "skill": ""},
        {"key": "b", "label": "B", "out": "b.md", "engine": "claude", "skill": ""}])
    run = runner.start_run("two-step", label="两步")
    done = _wait(run["id"])
    logs = [s["meta"]["log"] for s in done["steps"]]
    assert len(set(logs)) == 2, f"两步共用了同一份转录：{logs}"
    assert logs[0].startswith("01_a_") and logs[1].startswith("02_b_")
    dbsession.delete_pipeline("two-step")


def test_checkpoint_waits_then_resumes(stub_cli, dbsession, workspaces):
    dbsession.create_pipeline("gated", label="有闸", steps=[
        {"key": "a", "label": "A", "out": "a.md", "engine": "claude", "skill": "",
         "checkpoint": True},
        {"key": "b", "label": "B", "out": "b.md", "engine": "claude", "skill": ""}])
    run = runner.start_run("gated", label="带检查点")
    paused = _wait(run["id"])
    assert paused["status"] == "waiting", paused["status"]
    assert paused["steps"][0]["status"] == "done"
    assert paused["steps"][1]["status"] == "pending"
    runner.resume_run(run["id"])
    done = _wait(run["id"])
    assert done["status"] == "done"
    assert [s["status"] for s in done["steps"]] == ["done", "done"]
    dbsession.delete_pipeline("gated")


def test_auto_continue_skips_checkpoint(stub_cli, dbsession, workspaces):
    db.set_setting("auto_continue", "1")
    dbsession.create_pipeline("auto", label="全自动", steps=[
        {"key": "a", "label": "A", "out": "a.md", "engine": "claude", "skill": "",
         "checkpoint": True},
        {"key": "b", "label": "B", "out": "b.md", "engine": "claude", "skill": ""}])
    run = runner.start_run("auto", label="一次推到底")
    done = _wait(run["id"])
    assert done["status"] == "done", done["status"]
    assert done["steps"][1]["status"] == "done"
    db.set_setting("auto_continue", "0")
    dbsession.delete_pipeline("auto")


def test_retry_loop_gives_up_after_configured_attempts(stub_cli, dbsession, monkeypatch):
    db.set_setting("step_retry", "2")
    calls = {"n": 0}
    real = agents.run_agent

    def flaky(*a, **k):
        calls["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(agents, "run_agent", flaky)
    monkeypatch.setattr(agents, "_claude_args",
                        lambda *a, **k: ["--stub-mode=fail"])
    dbsession.create_pipeline("flaky", label="老失败", steps=[
        {"key": "a", "label": "A", "out": "a.md", "engine": "claude", "skill": ""}])
    run = runner.start_run("flaky", label="重试")
    done = _wait(run["id"])
    assert done["status"] == "failed"
    assert calls["n"] == 3, f"step_retry=2 应该一共 3 次，实际 {calls['n']}"
    db.set_setting("step_retry", "0")
    dbsession.delete_pipeline("flaky")


# ==================== 局部修订的并发守卫 ====================
# 这三条都必须在真的起线程之前就 raise，所以用例故意让它们在守卫处返回。

def _run_with(dbsession, run_id, steps, status="done"):
    dbsession.create_run(run_id, "auto-workflow", "t", steps)
    dbsession.update_run(run_id, status=status, steps=steps)


def test_revise_refuses_while_the_pipeline_is_running(dbsession):
    """修订线程和流水线线程各持一份 steps 整体回写同一行 JSON，
    同跑一步就是后写覆盖前写；codex 那路还要抢工作区的 AGENTS.md。"""
    _run_with(dbsession, "run-rev-run", [{"key": "a", "label": "A", "status": "pending", "out": "a.md"}], status="running")
    with pytest.raises(ValueError):
        runner.revise_step("run-rev-run", 0, "改一下")


def test_revise_refuses_a_second_concurrent_revision(dbsession):
    _run_with(dbsession, "run-rev-two", [
        {"key": "a", "label": "A", "status": "revising", "out": "a.md"},
        {"key": "b", "label": "B", "status": "done", "out": "b.md"}])
    with pytest.raises(ValueError):
        runner.revise_step("run-rev-two", 1, "改一下")


def test_revise_clears_a_stale_cancel_flag(dbsession):
    """cancel_run 只往 _CANCEL 里加，清它的活儿原先只在 _run_thread 的 finally。
    取消过一次再从那条 run 上发起修订，agents 一进来就当被取消，之后每次都秒失败。"""
    _run_with(dbsession, "run-rev-cancel", [{"key": "a", "label": "A", "status": "done", "out": ""}])
    runner._CANCEL.add("run-rev-cancel")
    with pytest.raises(ValueError):
        runner.revise_step("run-rev-cancel", 0, "改一下")
    assert "run-rev-cancel" not in runner._CANCEL

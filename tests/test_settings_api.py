# -*- coding: utf-8 -*-
"""设置类接口的往返与边界：这些值是直接喂给 CLI 命令行参数的，不能靠前端兜。"""
import pytest


def _get(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    return r.json()


def test_agents_payload_shape(client):
    d = _get(client)
    for key in ("agents", "default_engine", "sandbox_options", "effort_options",
                "step_retry", "reasoning_effort", "auto_continue", "bundled_skills", "paths"):
        assert key in d, f"/api/agents 少了 {key}"
    assert {a["engine"] for a in d["agents"]} == {"claude", "codex"}
    assert d["effort_options"][0] == "auto"


def test_agents_roundtrip(client):
    body = {"codex_sandbox": "read-only", "reasoning_effort": "high",
            "step_retry": "2", "auto_continue": "1", "agent_timeout": "900"}
    assert client.post("/api/agents", json=body).status_code == 200
    d = _get(client)
    assert d["codex_sandbox"] == "read-only"
    assert d["reasoning_effort"] == "high"
    assert d["step_retry"] == "2"
    assert d["auto_continue"] == "1"
    assert d["agent_timeout"] == "900"


@pytest.mark.parametrize("body,field", [
    ({"codex_sandbox": "no-pe"}, "沙箱"),
    ({"reasoning_effort": "ultra"}, "推理"),
    ({"step_retry": "9"}, "重试"),
    ({"step_retry": "-1"}, "重试"),
    ({"step_retry": "abc"}, "重试"),
    ({"agent_timeout": "5"}, "超时"),
    ({"agent_timeout": "99999"}, "超时"),
    ({"agent_timeout": "soon"}, "超时"),
    ({"default_engine": "gpt"}, "引擎"),
])
def test_agents_rejects_bad_values(client, body, field):
    assert client.post("/api/agents", json=body).status_code == 400


def test_bad_request_leaves_setting_untouched(client):
    client.post("/api/agents", json={"step_retry": "1"})
    before = _get(client)["step_retry"]
    assert client.post("/api/agents", json={"step_retry": "77"}).status_code == 400
    assert _get(client)["step_retry"] == before


def test_partial_post_keeps_other_fields(client):
    client.post("/api/agents", json={"reasoning_effort": "low", "step_retry": "3",
                                     "codex_sandbox": "danger-full-access"})
    assert client.post("/api/agents", json={"step_retry": "0"}).status_code == 200
    d = _get(client)
    assert d["step_retry"] == "0"
    assert d["reasoning_effort"] == "low"
    assert d["codex_sandbox"] == "danger-full-access"


def test_empty_string_clears(client):
    client.post("/api/agents", json={"claude_cli": "C:/nowhere/claude.exe"})
    assert _get(client)["claude_cli"] == "C:/nowhere/claude.exe"
    client.post("/api/agents", json={"claude_cli": ""})
    assert _get(client)["claude_cli"] in ("", None)


def test_appearance_bulk_roundtrip(client):
    body = {"ui_lang": "en", "ui_theme": "light", "ui_accent": "gold", "ui_font": "mono"}
    assert client.post("/api/settings/bulk", json=body).status_code == 200
    d = client.get("/api/settings").json()
    assert d["ui_accent"] == "gold" and d["ui_theme"] == "light"


def test_appearance_bulk_cannot_touch_engine_keys(client):
    """外观面板只能写 ui_*，别想从这儿把 default_engine / claude_cli 改掉。"""
    client.post("/api/agents", json={"step_retry": "1"})
    before = _get(client)["step_retry"]
    client.post("/api/settings/bulk",
                json={"ui_theme": "dark", "step_retry": "3", "default_engine": "codex",
                      "claude_cli": "C:/evil.exe"})
    d = _get(client)
    assert d["step_retry"] == before
    assert d["default_engine"] != "codex"
    assert d["claude_cli"] == ""


def test_pipelines_expose_run_count(client, dbsession, fresh_runs):
    """侧栏「项目」= 真跑过的流程，靠 /api/pipelines 里的 runs 字段筛。"""
    dbsession.create_pipeline("proj-a", label="A", steps=[{"key": "a"}])
    dbsession.create_pipeline("proj-b", label="B", steps=[{"key": "b"}])
    for i in range(2):
        dbsession.create_run(f"run-projcount{i}", "proj-a", steps=[])
    dbsession.create_run("run-projcount-x", "proj-b", steps=[])
    try:
        d = client.get("/api/pipelines").json()
        by = {p["name"]: p["runs"] for p in d["pipelines"]}
        assert by["proj-a"] == 2 and by["proj-b"] == 1
        assert all(isinstance(p["runs"], int) for p in d["pipelines"])
        # 从没跑过的内置模板必须是 0，而不是缺字段
        assert by.get("auto-workflow", 0) == 0
    finally:
        conn = dbsession.get_conn()
        conn.execute("DELETE FROM runs WHERE pipeline IN ('proj-a','proj-b')")
        conn.execute("DELETE FROM pipeline_definitions WHERE name IN ('proj-a','proj-b')")
        conn.commit(); conn.close()


def test_run_counts_zero_when_nothing_ran(client, dbsession, fresh_runs):
    assert dbsession.run_counts() == {}
    d = client.get("/api/pipelines").json()
    assert d["pipelines"], "内置模板应当已播种"
    assert all(p["runs"] == 0 for p in d["pipelines"])


def test_reveal_rejects_arbitrary_path(client, monkeypatch):
    """只认白名单键；命中后真去开资源管理器的动作要打桩，测试不能弹窗口。"""
    import subprocess
    opened = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: opened.append(a))
    assert client.post("/api/reveal", params={"which": "../../windows"}).status_code == 400
    assert client.post("/api/reveal", params={"which": "data"}).status_code == 200
    assert len(opened) == 1

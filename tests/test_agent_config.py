# -*- coding: utf-8 -*-
"""引擎与端点解析阶梯：决定「这一步到底拿什么配置去喂 CLI」。

这条阶梯是软件的核心约定（正文只能由智能体产出，API 预设只是注入给 CLI），
所以每一级的优先级都要钉住。
"""
import pytest

from app import agents, db, runner


@pytest.fixture(autouse=True)
def _clean_presets():
    conn = db.get_conn()
    conn.execute("DELETE FROM api_presets")
    conn.commit()
    conn.close()
    yield


@pytest.fixture
def both_clis(monkeypatch):
    """假装两个 CLI 都在，别依赖测试机的 PATH。"""
    monkeypatch.setattr(agents, "resolve_binary",
                        lambda e: f"C:/fake/{e}.cmd" if e in agents.ENGINES else "")


def test_engine_ladder(both_clis):
    assert runner.resolve_agent_config({})["engine"] == "claude"      # ENGINES 里第一个
    db.set_setting("default_engine", "codex")
    assert runner.resolve_agent_config({})["engine"] == "codex"
    assert runner.resolve_agent_config({"engine": "claude"})["engine"] == "claude"
    assert runner.resolve_agent_config({"engine": "gpt"})["engine"] == "codex"


def test_no_cli_anywhere_raises(monkeypatch):
    monkeypatch.setattr(agents, "resolve_binary", lambda e: "")
    with pytest.raises(RuntimeError, match="未检测到任何智能体 CLI"):
        runner.resolve_agent_config({})


def test_no_preset_injects_nothing(both_clis):
    c = runner.resolve_agent_config({"engine": "claude"})
    assert c["api_base"] == "" and c["api_key"] == "" and c["model"] == ""
    assert c["warn"] == ""


def test_step_model_matching_a_preset_name_wins(both_clis):
    db.add_preset("deepseek", provider="openai", api_base="https://x/v1",
                  api_key="k-1", model="deepseek-chat")
    db.add_preset("kimi", provider="openai", api_base="https://k/v1",
                  api_key="k-2", model="kimi-k2")
    db.set_default_preset(db.get_preset_by_name("deepseek")["id"])
    c = runner.resolve_agent_config({"engine": "codex", "model": "kimi"})
    assert c["api_base"] == "https://k/v1" and c["api_key"] == "k-2"
    assert c["preset"] == "kimi"


def test_bare_model_id_rides_on_default_preset(both_clis):
    db.add_preset("kimi", provider="openai", api_base="https://k/v1",
                  api_key="k-2", model="kimi-k2")
    c = runner.resolve_agent_config({"engine": "codex", "model": "glm-4.6"})
    assert c["api_base"] == "https://k/v1"
    assert c["model"] == "glm-4.6"


def test_model_map_then_fallback_then_preset_model(both_clis):
    db.add_preset("route", provider="openai", api_base="https://r/v1", api_key="k",
                  model="base-model",
                  extra={"fallback_model": "fb-model",
                         "model_map": {"draft": "mapped-model"}})
    step = {"engine": "codex", "key": "draft"}
    assert runner.resolve_agent_config(step)["model"] == "mapped-model"
    step["key"] = "review"
    assert runner.resolve_agent_config(step)["model"] == "fb-model"
    db.update_preset(db.get_preset_by_name("route")["id"], extra={})
    assert runner.resolve_agent_config(step)["model"] == "base-model"


def test_wire_api_forwarded(both_clis):
    db.add_preset("kimi", provider="openai", api_base="https://k/v1", api_key="k",
                  model="m", extra={"wire_api": "responses"})
    assert runner.resolve_agent_config({"engine": "codex"})["wire_api"] == "responses"


def test_protocol_mismatch_drops_injection(both_clis):
    """anthropic 端点喂给 codex：不注入，改走 CLI 自身登录，并留下原因。"""
    db.add_preset("claude-ep", provider="anthropic", api_base="https://a/api",
                  api_key="k", model="claude-x")
    c = runner.resolve_agent_config({"engine": "codex", "key": "draft"})
    assert c["api_base"] == "" and c["api_key"] == ""
    assert "不兼容" in c["warn"]


def test_anthropic_hint_counts_as_compatible(both_clis):
    db.add_preset("relay", provider="", api_base="https://gate/apps/anthropic",
                  api_key="k", model="claude-x")
    c = runner.resolve_agent_config({"engine": "claude", "key": "draft"})
    assert c["api_base"] == "https://gate/apps/anthropic"
    assert c["warn"] == ""


# ---------------- 协议门本身 ----------------

@pytest.mark.parametrize("engine,provider,base,ok", [
    ("claude", "", "", True),
    ("claude", "anthropic", "https://x/api", True),
    ("claude", "openai", "https://x/v1", False),
    ("claude", "openai", "https://x/claudecode", True),
    ("claude", "", "https://x/tokenplan/personal", True),
    ("codex", "openai", "https://x/v1", True),
    ("codex", "anthropic", "https://x/api", False),
    ("codex", "", "", True),
])
def test_protocol_ok(engine, provider, base, ok):
    assert agents.protocol_ok(engine, provider, base) is ok


def test_codex_args_carry_reasoning_effort(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "get_setting", lambda k, d="": {
        "reasoning_effort": "high", "codex_sandbox": "workspace-write"}.get(k, d))
    args = agents._codex_args(tmp_path, None, "gpt-5", "", "", "chat")
    joined = " ".join(args)
    assert 'model_reasoning_effort="high"' in joined
    assert "network_access=true" in joined
    assert "--skip-git-repo-check" in joined


def test_codex_args_omit_effort_when_auto(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "get_setting", lambda k, d="": "")
    args = " ".join(agents._codex_args(tmp_path, None, "", "", "", ""))
    assert "model_reasoning_effort" not in args
    assert 'model="' not in args             # 没填模型就别越权指定


def test_provider_display_name_is_loom_not_flowforge(monkeypatch, tmp_path):
    args = " ".join(agents._codex_args(tmp_path, None, "", "https://k/v1", "k", "chat"))
    assert 'name="Loom"' in args
    assert "FLOWFORGE_API_KEY" in args       # 环境变量名是内部契约，改名要同步

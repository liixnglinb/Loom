# -*- coding: utf-8 -*-
"""两家 CLI 的能力盘点：只读，而且绝不把"值"带出接口。

这些目录与文件是 claude / codex 自己的配置面，里面就是真密钥 —— 本机
~/.claude/settings.json 的 env 里有 ANTHROPIC_AUTH_TOKEN，~/.claude.json 里有
oauthAccount，~/.codex/config.toml 里有 experimental_bearer_token。
盘点只准报名字、条数和路径，值一个字节都不许进接口。
"""
import json

import pytest

from app import cli_inventory as ci

SECRETS = ("sk-CLAUDE-SECRET", "sk-OAUTH-SECRET", "sk-MCP-SECRET",
           "sk-HOOK-SECRET", "tok-CODEX-SECRET")


@pytest.fixture
def home(tmp_path, monkeypatch):
    c = tmp_path / ".claude"
    c.mkdir()
    (c / "settings.json").write_text(json.dumps({
        "env": {"ANTHROPIC_AUTH_TOKEN": "sk-CLAUDE-SECRET",
                "ANTHROPIC_BASE_URL": "https://gate.example"}}), encoding="utf-8")
    (c / "settings.local.json").write_text(json.dumps({
        "hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "node s.js --token=sk-HOOK-SECRET"}]}]},
        "permissions": {"allow": ["Bash"]}}), encoding="utf-8")
    (tmp_path / ".claude.json").write_text(json.dumps({
        "oauthAccount": {"token": "sk-OAUTH-SECRET"},
        "officialMarketplaceAutoInstallAttempted": True,
        "officialMarketplaceAutoInstalled": False,
        "enabledPlugins": {"superpowers@qoder": True},
        "mcpServers": {"windows-mcp": {"command": "npx", "env": {"KEY": "sk-MCP-SECRET"}}},
        "projects": {"C:/p": {"mcpServers": {"proj-mcp": {}}}}}), encoding="utf-8")
    sk = c / "skills" / "brandkit"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text("# 品牌规范\n", encoding="utf-8")
    x = tmp_path / ".codex"
    x.mkdir()
    (x / "AGENTS.md").write_text("# 全局记忆\n", encoding="utf-8")
    (x / "config.toml").write_text(
        'model = "gpt-5"\nnotify = "/bin/x --tok tok-CODEX-SECRET"\n'
        '[model_providers.custom]\nexperimental_bearer_token = "tok-CODEX-SECRET"\n'
        '[mcp_servers.node_repl]\ncommand = "node"\n[mcp_servers.node_repl.env]\nA = "1"\n'
        '[mcp_servers.cua_repl]\ncommand = "node"\n'
        '[plugins."chatcut@chatcut-inc"]\nenabled = true\n'
        '[marketplaces.openai-curated]\nsource = "git"\n', encoding="utf-8")
    fg = x / "skills" / "figma"
    fg.mkdir(parents=True)
    (fg / "SKILL.md").write_text("# Figma\n", encoding="utf-8")
    monkeypatch.setattr(ci, "HOME", tmp_path)
    return tmp_path


def _scan():
    return ci.scan()


def _item(d, engine, key):
    return {i["key"]: i for i in d[engine]["items"]}[key]


def test_both_engines_report_the_same_categories(home):
    d = _scan()
    assert set(d) == {"claude", "codex"}
    ck = [i["key"] for i in d["claude"]["items"]]
    xk = [i["key"] for i in d["codex"]["items"]]
    assert ck == xk, "两个引擎的类目必须逐一对齐，切引擎时才不会少行或多行"
    assert len(ck) >= 7 and len(set(ck)) == len(ck)


def test_skills_are_listed_by_name(home):
    it = _item(_scan(), "claude", "skills")
    assert it["found"] is True and it["count"] == 1
    assert [n["name"] for n in it["entries"]] == ["brandkit"]


def test_missing_category_keeps_its_row_and_its_expected_path(home):
    """没找到不能把整行藏掉：那看着像功能坏了。给期望路径，用户才知道去哪儿建。"""
    it = _item(_scan(), "claude", "commands")
    assert it["found"] is False and it["count"] == 0
    assert it["path"].replace("\\", "/").endswith(".claude/commands")


def test_mcp_names_come_from_every_scope(home):
    d = _scan()
    assert "windows-mcp" in [n["name"] for n in _item(d, "claude", "mcp")["entries"]]
    assert "proj-mcp" in [n["name"] for n in _item(d, "claude", "mcp")["entries"]]
    cx = _item(d, "codex", "mcp")
    assert sorted(n["name"] for n in cx["entries"]) == ["cua_repl", "node_repl"]


def test_hooks_report_event_names_only(home):
    it = _item(_scan(), "claude", "hooks")
    assert it["found"] is True and [n["name"] for n in it["entries"]] == ["PostToolUse"]


def test_plugins_and_marketplaces_are_named(home):
    it = _item(_scan(), "codex", "plugins")
    names = [n["name"] for n in it["entries"]]
    assert "plugins.chatcut@chatcut-inc" in names
    assert "marketplaces.openai-curated" in names


def test_no_value_from_those_files_ever_reaches_the_payload(home):
    blob = json.dumps(_scan(), ensure_ascii=False)
    for s in SECRETS:
        assert s not in blob, f"{s} 被带进接口了"
    assert "ANTHROPIC_BASE_URL" not in blob or "gate.example" not in blob


def test_scan_creates_nothing(tmp_path, monkeypatch):
    """只读盘点不能顺手把两家 CLI 的目录建出来 —— 那是用户机器的真目录。"""
    fresh = tmp_path / "fresh-home"
    monkeypatch.setattr(ci, "HOME", fresh)
    d = ci.scan_for("claude")
    assert d["items"]
    assert not fresh.exists()


def test_reveal_resolves_only_known_keys(home):
    assert ci.reveal_path("claude", "skills") == (home / ".claude" / "skills")
    assert ci.reveal_path("codex", "memory") == (home / ".codex" / "AGENTS.md")
    assert ci.reveal_path("claude", "no-such-key") is None
    assert ci.reveal_path("vscode", "skills") is None
    assert ci.reveal_path("claude", "commands") is None   # 这台机器上没有的，不给跳


def test_the_route_reports_names_only(client, home, monkeypatch):
    """接口那一层再验一次：路由不能顺手把值补回去。"""
    monkeypatch.setattr(ci, "HOME", home)
    d = client.get("/api/agents/capabilities").json()
    assert {e["key"] for e in d["claude"]["items"]} == set(ci.CATS)
    body = client.get("/api/agents/capabilities").text
    for s in SECRETS:
        assert s not in body, f"{s} 从 /api/agents/capabilities 漏出去了"


def test_reveal_refuses_unknown_keys_and_absent_dirs(client, home, monkeypatch):
    import subprocess
    opened = []
    monkeypatch.setattr(ci, "HOME", home)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: opened.append(a))
    assert client.post("/api/reveal", params={"which": "agent", "engine": "claude",
                                              "key": "skills"}).status_code == 200
    assert client.post("/api/reveal", params={"which": "agent", "engine": "claude",
                                              "key": "commands"}).status_code == 404
    assert client.post("/api/reveal", params={"which": "agent", "engine": "claude",
                                              "key": "../../windows"}).status_code == 404
    assert client.post("/api/reveal", params={"which": "agent", "engine": "notes",
                                              "key": "skills"}).status_code == 404
    assert len(opened) == 1, "只该为真存在的那一项开一次资源管理器"
    assert not (home / ".claude" / "commands").exists(), "reveal 不能顺手把目录建出来"


def test_preview_resolves_only_through_the_inventory(home):
    """预览的入参只有 引擎 + 类目 + 条目名，路径全部由清单自己算。"""
    p = ci.preview_path("claude", "skills", "brandkit")
    assert p and p.name == "SKILL.md"
    assert ci.preview_path("claude", "memory", "") == (home / ".claude" / "CLAUDE.md") or \
        ci.preview_path("claude", "memory", "") is None      # 这台机器上没建 CLAUDE.md
    assert ci.preview_path("codex", "memory", "") == home / ".codex" / "AGENTS.md"


def test_preview_refuses_traversal_and_non_markdown(home):
    for bad in ("../../settings.json", "..", ".claude.json", "a/b", "x.toml"):
        assert ci.preview_path("claude", "skills", bad) is None, bad
    assert ci.preview_path("claude", "mcp", "windows-mcp") is None, "MCP 的值不外泄"
    assert ci.preview_path("claude", "hooks", "PostToolUse") is None
    assert ci.preview_path("nope", "skills", "brandkit") is None


def test_preview_route_returns_text_for_a_real_entry(client, home, monkeypatch):
    monkeypatch.setattr(ci, "HOME", home)
    r = client.get("/api/agents/capabilities/claude/skills/brandkit")
    assert r.status_code == 200, r.text
    assert "品牌规范" in r.json()["text"]
    assert client.get("/api/agents/capabilities/claude/skills/nope").status_code == 404
    assert client.get("/api/agents/capabilities/claude/mcp/x").status_code == 404
    assert client.get("/api/agents/capabilities/vscode/skills/brandkit").status_code == 404


def test_bookkeeping_flags_are_not_plugins(home):
    """真机上踩到的：officialMarketplaceAutoInstalled 这类记账布尔不是插件。"""
    it = _item(_scan(), "claude", "plugins")
    names = [n["name"] for n in it["entries"]]
    assert "superpowers@qoder" in names
    assert not [n for n in names if "Marketplace" in n or "Attempted" in n]


def test_mcp_subsection_is_not_a_second_server(home):
    """[mcp_servers.node_repl.env] 是那一台的子段，不是第二台服务器。"""
    names = [n["name"] for n in _item(_scan(), "codex", "mcp")["entries"]]
    assert sorted(names) == ["cua_repl", "node_repl"]

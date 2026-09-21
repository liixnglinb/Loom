# -*- coding: utf-8 -*-
"""技能从哪儿来：Loom 自己那份，还是两家 CLI 各自的 skills 目录。

选外部技能时 Loom 一律不拷正文、不改写 —— 那些 SKILL.md 是别人家的东西，
复制进工作区就等于把一份会随 CLI 升级而变的文件冻在我们这儿的快照上。
提示词里只按名字引用，让 CLI 用自己的发现机制加载。
"""
from pathlib import Path

import pytest

from app import cli_inventory, db, paths, runner  # noqa: E402


@pytest.fixture
def ext(tmp_path, monkeypatch):
    """假 HOME：~/.claude/skills/brandkit 与 ~/.codex/skills/figma 存在。"""
    for eng, name in (("claude", "brandkit"), ("codex", "figma")):
        d = tmp_path / (".claude" if eng == "claude" else ".codex") / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"# {name} 正文标记 EXTERNAL-BODY\n", encoding="utf-8")
    monkeypatch.setattr(cli_inventory, "HOME", tmp_path)
    monkeypatch.setattr(runner, "EXTERNAL_SKILL_ROOTS",
                        {"claude": tmp_path / ".claude" / "skills",
                         "codex": tmp_path / ".codex" / "skills"})
    return tmp_path


def test_normalize_keeps_the_source_field():
    from app import pipelines
    st = pipelines.normalize_steps([{"key": "a", "skill": "brandkit", "skill_src": "claude"},
                                    {"key": "b", "skill": "x", "skill_src": "vscode"},
                                    {"key": "c", "skill": "y"}])[0]
    assert "skill_src" in st and st["skill_src"] == "claude"


def test_normalize_drops_an_unknown_source():
    from app import pipelines
    s = pipelines.normalize_steps([{"key": "a", "skill": "x", "skill_src": "../etc"}])[0]
    assert s["skill_src"] == ""


def test_external_skill_is_referenced_not_inlined(ext):
    text, loaded, missing = runner.compose_skill_prompt("brandkit", "claude")
    assert loaded == ["brandkit"] and missing == []
    assert "EXTERNAL-BODY" not in text, "外部技能的正文不该被 Loom 抄进提示词"
    assert "brandkit" in text and "claude" in text


def test_a_loom_skill_is_still_inlined(ext):
    d = paths.USER_SKILLS_DIR / "mine"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("自己的技能全文 LOOM-BODY", encoding="utf-8")
    text, loaded, missing = runner.compose_skill_prompt("mine", "")
    assert loaded == ["mine"] and "LOOM-BODY" in text
    (d / "SKILL.md").unlink(); d.rmdir()


def test_missing_external_skill_is_reported_not_silently_dropped(ext):
    text, loaded, missing = runner.compose_skill_prompt("nope", "codex")
    assert missing == ["nope"] and loaded == [] and text == ""


def test_wrong_engine_warns_but_does_not_block(ext, dbsession, monkeypatch):
    """格式三家相同，抄错引擎顶多加载不到 —— 给个原因进运行台，别替用户拍板。"""
    monkeypatch.setattr(db, "get_setting", lambda k, d="": "codex" if k == "default_engine" else d)
    conf = runner.resolve_agent_config({"key": "a", "engine": "", "skill_src": "claude"})
    assert conf["engine"] == "codex"
    assert "claude" in conf["warn"] and "不匹配" in conf["warn"]


def test_matching_engine_adds_no_warning(ext, dbsession, monkeypatch):
    monkeypatch.setattr(db, "get_setting", lambda k, d="": "claude" if k == "default_engine" else d)
    conf = runner.resolve_agent_config({"key": "a", "engine": "", "skill_src": "claude"})
    # 别的测试可能在这张共享库里留了预设，所以只断言"没多出来源不匹配这条"
    assert "不匹配" not in conf["warn"]

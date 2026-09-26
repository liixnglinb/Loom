# -*- coding: utf-8 -*-
"""「检测连通」这条直连路：它曾经整条是死的。

chat() 里两个分支各引用了一个不存在的名字（一个错字参数、一个已删函数），
而 test_connection 把异常吞成 (False, msg) —— 于是按钮永远红，161 条测试全绿，
因为路由侧的测试直接把 test_connection 打了桩。这几条只桩到 HTTP 那一层，
让 chat / _chat_openai / _chat_anthropic 真的跑一遍。
"""
from types import SimpleNamespace

from app import llm


class _Resp:
    status_code = 200
    text = ""

    def json(self):
        return {"content": [{"type": "text", "text": "ok"}]}


def test_anthropic_probe_actually_reaches_the_wire(monkeypatch):
    sent = {}

    def _post(url, json=None, headers=None, timeout=None):
        sent.update(url=url, body=json, headers=headers)
        return _Resp()

    monkeypatch.setattr(llm.requests, "post", _post)
    ok, msg = llm.test_connection("anthropic", "https://gw.example/v1", "sk-x",
                                  "claude-sonnet-4-5")
    assert ok, msg
    assert msg == "ok", "应答没从 content[] 里取出来"
    assert sent["url"] == "https://gw.example/v1/messages"
    assert sent["headers"]["x-api-key"] == "sk-x"


def test_openai_probe_actually_reaches_the_wire(monkeypatch):
    import openai
    seen = {}

    class _FakeClient:
        def __init__(self, **kw):
            seen["base_url"] = kw["base_url"]

        chat = SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kw: seen.update(kw) or SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])))

    monkeypatch.setattr(openai, "OpenAI", _FakeClient)
    ok, msg = llm.test_connection("openai", "https://gw.example", "sk-x", "gpt-4o-mini")
    assert ok, msg
    assert msg == "ok"
    assert seen["base_url"] == "https://gw.example/v1"


def test_direct_exit_is_capped_at_a_probe_size(monkeypatch):
    """硬顶：直连出口一次最多 64 token。想拿它生成正文必须先拆掉这行，
    拆掉就一定在这个断言上露出来 —— 正文只能由本机 CLI 智能体产出。"""
    import openai
    seen = {}
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kw: seen.update(kw) or SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])))))
    llm.chat("openai", "https://gw.example", "sk-x", "m", [{"role": "user", "content": "x"}],
             max_tokens=200000)
    assert 0 < seen["max_tokens"] <= 64


def test_llm_module_offers_no_streaming_exit():
    """流式出口已随执行链一起删掉，别再留着名字让人以为能生成正文。"""
    for name in ("chat_stream", "_stream_openai", "_stream_anthropic"):
        assert not hasattr(llm, name), f"llm.{name} 又长回来了"


class _ThinkOnlyResp:
    """思考型模型预算不够时的真实形状（百炼 qwen3.8-flash，max_tokens=16 实测）：
    只有 thinking 块，stop_reason 是 max_tokens。"""
    status_code = 200
    text = ""

    def json(self):
        return {"stop_reason": "max_tokens", "content": [
            {"type": "thinking", "thinking": "用户要我回 ok，那我就只回 ok。",
             "signature": ""}]}


def test_anthropic_probe_falls_back_to_thinking_when_there_is_no_text(monkeypatch):
    """连接是通的、回文却是空的，界面上就是"点了没反应"。
    没有 text 块时把 thinking 的开头回显出来，至少看得出对面真回了话。"""
    monkeypatch.setattr(llm.requests, "post",
                        lambda *a, **k: _ThinkOnlyResp())
    ok, msg = llm.test_connection("anthropic", "https://gw.example/apps/anthropic",
                                  "sk-x", "qwen3.8-flash")
    assert ok
    assert msg, "只回 thinking 的模型不该把回文清空"
    assert "ok" in msg and msg.startswith("（思考）"), msg


def test_probe_budget_clears_the_thinking_stage(monkeypatch):
    """探测预算必须给到 64：16 token 连思考都出不来，
    于是每次测一个推理模型都是绿灯空白（上面那条就是那个形状）。"""
    sent = {}

    def _post(url, json=None, headers=None, timeout=None):
        sent["body"] = json
        return _Resp()

    monkeypatch.setattr(llm.requests, "post", _post)
    llm.test_connection("anthropic", "https://gw.example/v1", "sk-x", "m")
    assert sent["body"]["max_tokens"] == 64, sent["body"]
    # 但绝不允许越过 chat() 那道硬顶
    assert sent["body"]["max_tokens"] <= 64

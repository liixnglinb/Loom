# -*- coding: utf-8 -*-
"""LLM 客户端：支持 OpenAI 兼容 + Anthropic 双协议。

极简版用途：设置页「检测连通」。执行链已移除，LLM 调用由外部 CLI 完成。
"""
import requests

class LLMError(Exception):
    pass


def anthropic_url(base):
    """拼接 Anthropic Messages 端点（与 Claude CLI 的 ANTHROPIC_BASE_URL 语义一致）：
    已带 /messages 用原样；以 /v1 结尾（如 Kimi/硅基流动的 base）补 /messages；
    否则补 /v1/messages。"""
    b = (base or "").rstrip("/")
    if not b:
        return b
    if b.endswith("/messages"):
        return b
    if b.endswith("/v1"):
        return b + "/messages"
    return b + "/v1/messages"


def _openai_base(api_base):
    """OpenAI base：已经带 /v1 就不用重复补；否则补齐 /v1。"""
    b = (api_base or "").rstrip("/")
    if not b:
        return b
    return b if (b.endswith("/v1") or b.endswith("/v1/")) else b + "/v1"


def _chat_openai(api_base, api_key, model, messages, temperature, max_tokens):
    from openai import OpenAI
    client = OpenAI(base_url=_openai_base(api_base), api_key=api_key, timeout=60)
    try:
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        raise LLMError(f"LLM 调用失败: {e}")
    return resp.choices[0].message.content or ""


def _chat_anthropic(api_base, api_key, model, messages, temperature, max_tokens):
    if not api_key:
        raise LLMError("未配置 API Key")
    url = anthropic_url(api_base)
    if not url:
        raise LLMError("未配置 API Base 地址")
    system = "\n".join((m.get("content") or "") for m in messages if m.get("role") == "system")
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in messages if m.get("role") in ("user", "assistant")]
    if not msgs:
        msgs = [{"role": "user", "content": "请开始"}]
    headers = {
        "x-api-key": api_key,
        "Authorization": f"Bearer {api_key}",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model or "claude-sonnet-4-5",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": msgs,
    }
    if system:
        body["system"] = system
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=60)
    except Exception as e:
        raise LLMError(f"LLM 调用失败: {e}")
    if resp.status_code != 200:
        raise LLMError(f"LLM 调用失败 HTTP {resp.status_code}: {resp.text[:300]}")
    try:
        data = resp.json()
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if not text.strip():
            # 思考型模型先出 thinking 再出 text（百炼 qwen3.8-flash 实测：16 token 的
            # 预算全花在 thinking 上，stop_reason=max_tokens，一个 text 块都没有）。
            # 连接明明是通的、回文却是空的，界面上就成了"点了没反应"。
            # 退一步把 thinking 的开头回显出来，至少看得出对面真回了话。
            think = "".join(b.get("thinking", "") for b in blocks
                            if b.get("type") == "thinking").strip()
            if think:
                text = "（思考）" + think
        return text
    except Exception:
        raise LLMError(f"LLM 返回异常: {resp.text[:300]}")


def chat(provider, api_base, api_key, model, messages, temperature=0.7, max_tokens=64):
    """唯一的直连出口，只给 test_connection 做连通性探测用。
    流水线正文一律走 agents.run_agent 交给本机 CLI —— 想拿这里生成内容，
    先要绕过下面这个硬顶，也就一定会在 diff 里露出来。"""
    max_tokens = min(int(max_tokens or 0), 64)
    provider = (provider or "openai").lower().strip()
    if provider == "anthropic":
        return _chat_anthropic(api_base, api_key, model, messages, temperature, max_tokens)
    return _chat_openai(api_base, api_key, model, messages, temperature, max_tokens)


def test_connection(provider="openai", api_base="", api_key="", model=""):
    """一次连通性探测。预算给到 64（= chat() 那个硬顶）而不是 16：
    思考型模型 16 token 只够它想，正文一个字都出不来，看着就像没通。
    再往上给就要先动 chat() 里那行硬顶，而那行是产品红线的守门人。"""
    try:
        text = chat(provider, api_base, api_key, model,
                    [{"role": "user", "content": "连接测试：回复ok两个字"}], max_tokens=64)
        return True, (text or "").strip()[:50]
    except Exception as e:
        return False, str(e)

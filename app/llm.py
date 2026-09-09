# -*- coding: utf-8 -*-
"""LLM 客户端：支持 OpenAI 兼容 + Anthropic 双协议。"""
import requests

class LLMError(Exception):
    pass

_PROVIDERS = ("openai", "anthropic")

def anthropic_url(base):
    """拼接 Anthropic Messages 端点（与 Claude CLI 的 ANTHROPIC_BASE_URL 语义一致）：
    已带 /messages 用原样；以 /v1 结尾（如 Kimi/硅基流动的 base）补 /messages；
    否则补 /v1/messages。修复：此前统一补 /v1/messages，会把
    https://api.moonshot.cn/v1 拼成 …/v1/v1/messages 导致 404。"""
    b = (base or "").rstrip("/")
    if not b:
        return b
    if b.endswith("/messages"):
        return b
    if b.endswith("/v1"):
        return b + "/messages"
    return b + "/v1/messages"

def _chat_openai(api_base, api_key, model, messages, temperature, max_tokens, stream):
    from openai import OpenAI
    client = OpenAI(base_url=_openai_base(api_base), api_key=api_key, timeout=300)
    try:
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )
    except Exception as e:
        raise LLMError(f"LLM 调用失败: {e}")
    if stream:
        buf = []
        for chunk in resp:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                buf.append(chunk.choices[0].delta.content)
        return "".join(buf)
    return resp.choices[0].message.content or ""

def _openai_base(api_base):
    """OpenAI base：已经带 /v1 就不用重复补；否则补齐 /v1。"""
    b = (api_base or "").rstrip("/")
    if not b:
        return b
    return b if (b.endswith("/v1") or b.endswith("/v1/")) else b + "/v1"

def _chat_anthropic(api_base, api_key, model, messages, temperature, max_tokens):
    if not api_key:
        raise LLMError("未配置 API Key，请在「设置」页填写")
    url = anthropic_url(api_base)
    if not url:
        raise LLMError("未配置 API Base 地址，请在「设置」页填写")
    # system 拆出，messages 只保留 user/assistant
    system = "\n".join((m.get("content") or "") for m in messages if m.get("role") == "system")
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in messages if m.get("role") in ("user", "assistant")]
    if not msgs:
        msgs = [{"role": "user", "content": "请开始"}]
    # 同时带 x-api-key（Anthropic 官方）与 Bearer（多数三方网关）
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
        resp = requests.post(url, json=body, headers=headers, timeout=300)
    except Exception as e:
        raise LLMError(f"LLM 调用失败: {e}")
    if resp.status_code != 200:
        raise LLMError(f"LLM 调用失败 HTTP {resp.status_code}: {resp.text[:300]}")
    try:
        data = resp.json()
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    except Exception:
        raise LLMError(f"LLM 返回异常: {resp.text[:300]}")

def chat(provider, api_base, api_key, model, messages, temperature=0.7, max_tokens=8192, stream=False):
    """按 provider 路由到 OpenAI 兼容或 Anthropic。provider 缺省视为 openai（向后兼容）。"""
    provider = (provider or "openai").lower().strip()
    if provider == "anthropic":
        return _chat_anthropic(api_base, api_key, model, messages, temperature, max_tokens)
    return _chat_openai(api_base, api_key, model, messages, temperature, max_tokens, stream)

def test_connection(provider="openai", api_base="", api_key="", model=""):
    try:
        text = chat(provider, api_base, api_key, model,
                    [{"role": "user", "content": "连接测试：回复ok两个字"}], max_tokens=16)
        return True, (text or "").strip()[:50]
    except Exception as e:
        return False, str(e)
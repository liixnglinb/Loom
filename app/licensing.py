# -*- coding: utf-8 -*-
"""客户端授权：机器指纹 + HMAC 令牌本地预检 + 服务器在线校验。

一码一机：激活时服务器把码绑定到机器指纹（管理员码除外，不限机不绑定）。
激活后每次启动尝试在线校验（权威判断）；本地 HMAC 只是快速预检。
在线校验失败（码不存在/已吊销/设备不匹配）立即视为未激活并清除本地授权。
网络不可用时允许 7 天离线宽限（基于上次成功在线校验时间）。
令牌 = HMAC-SHA256(secret, code|mid) 前 32 位（仅用于本地预检，权威判断在服务端）。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import time
import uuid
from pathlib import Path

_CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

import requests

from . import paths

SERVER = "https://lxlrwxs.top/modelflow"
# 注意：此密钥仅用于本地快速预检。权威授权判断由服务端 /api/check 完成，
# 即使此密钥被反编译泄露，伪造的令牌也无法通过在线校验（码不存在/已吊销会被拒绝）。
SECRET = "1adee14c497b3b976a3beb1aa602744a8a54b04782e2b2526ccb0800924b9af3"

OFFLINE_GRACE_SECONDS = 7 * 24 * 3600  # 离线宽限 7 天
ONLINE_CHECK_INTERVAL = 3600             # 在线校验最短间隔 1 小时（避免频繁请求）

_cache: dict | None = None


def machine_id() -> str:
    """稳定机器指纹：Windows MachineGuid 优先，回退主板 UUID / MAC。"""
    raw = ""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"SOFTWARE\Microsoft\Cryptography")
        raw, _ = winreg.QueryValueEx(k, "MachineGuid")
    except Exception:
        raw = ""
    if not raw:
        try:
            out = subprocess.run(["wmic", "csproduct", "get", "UUID"],
                                 capture_output=True, text=True, timeout=15, creationflags=_CNW)
            lines = [l.strip() for l in (out.stdout or "").splitlines() if l.strip()]
            raw = lines[-1] if len(lines) > 1 else ""
        except Exception:
            raw = ""
    if not raw:
        raw = str(uuid.getnode())
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _license_file() -> Path:
    return paths.DB_DIR / "license.json"


def load() -> dict | None:
    global _cache
    if _cache is not None:
        return _cache
    p = _license_file()
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    _cache = d
    return d


def _save(d: dict) -> None:
    """保存授权文件并更新缓存。"""
    global _cache
    _license_file().write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    _cache = d


def _clear() -> None:
    """清除本地授权（在线校验判定无效时调用）。"""
    global _cache
    p = _license_file()
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass
    _cache = None


def _verify_local(code: str, mid: str, token: str) -> bool:
    """本地快速预检（HMAC）。仅用于快速筛选，权威判断在 _check_online。"""
    expect = hmac.new(SECRET.encode(), f"{code}|{mid}".encode(),
                      hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(expect, token or "")


def _check_online(code: str, mid: str, token: str) -> dict:
    """调用服务端 /api/check 做权威在线校验。
    返回 {ok, admin, reason, network_error}。
    """
    try:
        r = requests.post(f"{SERVER}/api/check",
                          json={"code": code, "mid": mid, "token": token},
                          timeout=10)
        data = r.json()
        if r.status_code == 200 and data.get("ok"):
            return {"ok": True, "admin": bool(data.get("admin")), "reason": "", "network_error": False}
        return {"ok": False, "admin": False,
                "reason": data.get("reason") or data.get("msg") or "online_rejected",
                "network_error": False}
    except Exception:
        return {"ok": False, "admin": False, "reason": "network_error", "network_error": True}


def status() -> dict:
    """{activated, admin, code, mid, offline}。
    流程：本地预检 → 在线权威校验（1小时间隔）→ 离线宽限（7天）。
    在线校验判定无效（吊销/不匹配/码不存在）立即清除本地授权。
    """
    d = load()
    mid = machine_id()
    if not d:
        return {"activated": False, "admin": False, "code": "", "mid": mid, "offline": False}

    # 1. 本地快速预检（HMAC + 设备匹配）
    ok_local = _verify_local(d.get("code", ""), d.get("mid", ""), d.get("token", "")) \
        and d.get("mid") == mid
    if not ok_local:
        return {"activated": False, "admin": False, "code": "", "mid": mid, "offline": False}

    code = d.get("code", "")
    token = d.get("token", "")
    last_check = d.get("last_online_check", 0) or 0
    now = int(time.time())

    # 2. 1 小时内已成功在线校验过 → 跳过，直接返回已激活
    if now - last_check < ONLINE_CHECK_INTERVAL:
        return {"activated": True, "admin": bool(d.get("admin")),
                "code": code, "mid": mid, "offline": False}

    # 3. 尝试在线权威校验
    result = _check_online(code, mid, token)

    if result["ok"]:
        # 在线校验通过 → 更新最后校验时间，返回已激活
        d["last_online_check"] = now
        d["admin"] = result["admin"]
        _save(d)
        return {"activated": True, "admin": result["admin"],
                "code": code, "mid": mid, "offline": False}

    if result["network_error"]:
        # 网络不可用 → 检查离线宽限（7天内有过成功在线校验则允许离线）
        if last_check > 0 and (now - last_check) < OFFLINE_GRACE_SECONDS:
            return {"activated": True, "admin": bool(d.get("admin")),
                    "code": code, "mid": mid, "offline": True}
        # 超过离线宽限 → 未激活（提示联网验证）
        return {"activated": False, "admin": False, "code": "", "mid": mid,
                "offline": False, "need_online": True}

    # 在线校验明确拒绝（码不存在/已吊销/设备不匹配/token无效）→ 清除本地授权
    _clear()
    return {"activated": False, "admin": False, "code": "", "mid": mid, "offline": False}


def is_activated() -> bool:
    return status()["activated"]


def activate(code: str) -> dict:
    """向服务器激活并落盘。返回 {ok, msg, admin}。"""
    global _cache
    code = (code or "").strip().upper()
    mid = machine_id()
    if not code:
        return {"ok": False, "msg": "请输入授权码"}
    try:
        r = requests.post(f"{SERVER}/api/activate",
                          json={"code": code, "mid": mid}, timeout=20)
        data = r.json()
    except Exception as e:
        return {"ok": False, "msg": f"无法连接授权服务器: {str(e)[:120]}"}
    if r.status_code != 200 or not data.get("ok"):
        return {"ok": False, "msg": data.get("msg") or f"激活失败 (HTTP {r.status_code})"}
    lic = {"code": code, "mid": mid, "token": data["token"],
           "admin": bool(data.get("admin")),
           "activated_at": data.get("activated_at", ""),
           "last_online_check": int(time.time())}
    _save(lic)
    return {"ok": True, "admin": lic["admin"], "msg": "激活成功"}

# -*- coding: utf-8 -*-
"""自动更新：查 GitHub Releases 最新版，流式下载并回报进度。

仓库写在 settings 的 update_repo（形如 owner/name）。没配置时一切接口都
明确回 "not-configured"，不去猜地址、也不静默失败。

只做到「下载完成 + 字节数核对」。替换自身真正装上去要等打包形态定了再做，
这里不留半成品安装逻辑。
"""
import re
import threading
import time
from pathlib import Path

import requests

from . import db, paths
from .version import APP_VERSION

_LOCK = threading.Lock()
_DL = {}          # 下载线程句柄，防重入
STATE = {
    "phase": "idle",        # idle|checking|available|current|error|downloading|ready
    "local": APP_VERSION,
    "latest": "",
    "notes": "",
    "url": "",
    "asset": "",
    "size": 0,
    "got": 0,
    "path": "",
    "error": "",
    "checked_at": "",
}


def repo() -> str:
    return (db.get_setting("update_repo") or "").strip()


def updates_dir() -> Path:
    d = paths.DATA_DIR / "updates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ver(s: str):
    """把 v1.2.3 / 1.2.3-rc1 拆成可比较的整数元组；非数字段丢掉。"""
    nums = re.findall(r"\d+", (s or "").split("+")[0])
    return tuple(int(n) for n in nums[:4]) or (0,)


def is_newer(latest: str, local: str = APP_VERSION) -> bool:
    return _ver(latest) > _ver(local)


def snapshot() -> dict:
    with _LOCK:
        out = dict(STATE)
    out["repo"] = repo()
    out["configured"] = bool(out["repo"])
    return out


def _set(**kw):
    with _LOCK:
        STATE.update(kw)


def norm_tag(s: str) -> str:
    """去掉版本号前的 v。只认 v+数字（v1.2.3），否则 vault-client 会被削成 ault-client。"""
    return re.sub(r"^[vV](?=\d)", "", (s or "").strip())


def check(force: bool = False) -> dict:
    """问一次 GitHub。已经拿到结果且不是 force 就直接回缓存，避免每次轮询打网络。"""
    r = repo()
    if not r:
        _set(phase="idle", error="", latest="", url="", size=0, got=0)
        return snapshot()
    with _LOCK:
        cached = STATE["phase"] in ("available", "current") and STATE["url"] and not force
    if cached:
        return snapshot()
    _set(phase="checking", error="")
    try:
        resp = requests.get(f"https://api.github.com/repos/{r}/releases/latest",
                            headers={"User-Agent": "loom-updater", "Accept": "application/vnd.github+json"},
                            timeout=(8, 15))
        if resp.status_code != 200:
            raise RuntimeError(f"GitHub 返回 {resp.status_code}")
        rel = resp.json()
        latest = norm_tag(rel.get("tag_name") or rel.get("name") or "")
        if not latest:
            raise RuntimeError("最新发布没有版本号")
        assets = [a for a in (rel.get("assets") or []) if a.get("browser_download_url")]
        want = (db.get_setting("update_asset") or "").strip()
        hit = next((a for a in assets if want and want in a.get("name", "")), assets[0] if assets else None)
        if not hit:
            raise RuntimeError("这个 release 里没有可下载的文件")
        _set(phase="available" if is_newer(latest) else "current",
             latest=latest, notes=(rel.get("body") or "")[:2000],
             url=hit["browser_download_url"] if is_newer(latest) else "",
             asset=hit.get("name") or "",
             size=int(hit.get("size") or 0), got=0, path="",
             checked_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        _set(phase="error", error=str(e)[:300])
    return snapshot()


def _download(url: str, dest: Path, expect: int):
    got = 0
    try:
        with requests.get(url, stream=True, timeout=(15, 120),
                          headers={"User-Agent": "loom-updater"}) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    got += len(chunk)
                    _set(got=got)
        if expect and got != expect:
            raise RuntimeError(f"字节数对不上：收到 {got}，应为 {expect}")
        _set(phase="ready", got=got, path=str(dest))
    except Exception as e:
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        _set(phase="error", error=str(e)[:300], got=0)


def start_download() -> dict:
    s = snapshot()
    if s["phase"] == "ready":
        return s
    if not s["url"]:
        _set(phase="error", error="没有可下载的更新，先检查版本")
        return snapshot()
    with _LOCK:
        alive = _DL.get("t")
        if alive and alive.is_alive():
            return dict(STATE)
    dest = updates_dir() / (s["asset"] or "update.bin")
    _set(phase="downloading", got=0, error="", path=str(dest))
    t = threading.Thread(target=_download, args=(s["url"], dest, s["size"]),
                         daemon=True, name="loom-update")
    _DL["t"] = t
    t.start()
    return snapshot()

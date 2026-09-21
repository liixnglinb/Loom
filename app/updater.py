# -*- coding: utf-8 -*-
"""自动更新：读 COS 上的 latest.json 清单，流式下载安装包、核对 sha256，再静默装上。

清单地址写在 settings 的 update_url，留空走 DEFAULT_UPDATE_URL。
下载页和软件内更新器读的是同一份 latest.json —— 页面下到的版本
和软件里报的版本必须永远一致，所以只留这一个源。

装自身的做法：把 setup.exe 交给一个脱离本进程的批处理去跑，
安装器会自己关掉正在运行的 Loom，装完再由用户重启。源码运行时
没有"自身"可换，这条路直接明确报错，不假装成功。
"""
import hashlib
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests

from . import db, paths
from .version import APP_VERSION

DEFAULT_UPDATE_URL = "https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/latest.json"

_LOCK = threading.Lock()
_DL = {}          # 下载线程句柄，防重入
STATE = {
    "phase": "idle",        # idle|checking|available|current|error|downloading|ready
    "local": APP_VERSION,
    "latest": "",
    "notes": "",
    "url": "",
    "asset": "",
    "sha256": "",
    "size": 0,
    "got": 0,
    "path": "",
    "error": "",
    "checked_at": "",
    "frozen": bool(getattr(sys, "frozen", False)),
}


def update_url() -> str:
    return (db.get_setting("update_url") or "").strip() or DEFAULT_UPDATE_URL


def manifest_url() -> str:
    """清单地址。STATE["url"] 存的是安装包地址，两个别混。"""
    return update_url()


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
    out["update_url"] = update_url()
    out["configured"] = True
    out["default_url"] = DEFAULT_UPDATE_URL
    return out


def _set(**kw):
    with _LOCK:
        STATE.update(kw)


def norm_tag(s: str) -> str:
    """去掉版本号前的 v。只认 v+数字（v1.2.3），否则 vault-client 会被削成 ault-client。"""
    return re.sub(r"^[vV](?=\d)", "", (s or "").strip())


def check(force: bool = False) -> dict:
    """问一次清单。已经拿到结果且不是 force 就直接回缓存，避免每次轮询打网络。

    下载正在飞的时候连 force 也不问：一次检查会把 phase 改成 checking、
    再把进度 got 清成 0、把正在写的包路径 path 抹掉，进度条当场跳回原点，
    而后台那个线程还在往原路径里写 —— 看着像卡住，其实是状态被踩了。"""
    with _LOCK:
        # _LOCK 不是可重入的：绝不能在 with 里 return snapshot()，那自己等自己。
        downloading = STATE["phase"] == "downloading"
        cached = (not downloading and STATE["phase"] in ("available", "current")
                  and STATE["url"] and not force)
    if downloading or cached:
        return snapshot()
    _set(phase="checking", error="")
    try:
        resp = requests.get(update_url(), timeout=(8, 15),
                            headers={"User-Agent": "loom-updater"})
        if resp.status_code != 200:
            raise RuntimeError(f"更新清单返回 {resp.status_code}")
        m = resp.json()
        latest = norm_tag(str(m.get("version") or ""))
        if not latest:
            raise RuntimeError("清单里没有 version 字段")
        url = str(m.get("url") or "")
        if not url.startswith("https://"):
            raise RuntimeError("清单里的下载地址不是 https")
        newer = is_newer(latest)
        _set(phase="available" if newer else "current",
             latest=latest, notes=str(m.get("notes") or "")[:2000],
             url=url if newer else "",
             asset=str(m.get("file") or Path(url).name),
             sha256=str(m.get("sha256") or ""),
             size=int(m.get("size") or 0), got=0, path="",
             checked_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        _set(phase="error", error=str(e)[:300])
    return snapshot()


def _download(url: str, dest: Path, expect: int, want_sha: str):
    got = 0
    h = hashlib.sha256()
    try:
        with requests.get(url, stream=True, timeout=(15, 120),
                          headers={"User-Agent": "loom-updater"}) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    h.update(chunk)
                    got += len(chunk)
                    _set(got=got)
        if expect and got != expect:
            raise RuntimeError(f"字节数对不上：收到 {got}，应为 {expect}")
        if want_sha and h.hexdigest().lower() != want_sha.lower():
            raise RuntimeError("sha256 校验不通过，安装包可能不完整")
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
    dest = updates_dir() / (s["asset"] or "update.exe")
    _set(phase="downloading", got=0, error="", path=str(dest))
    t = threading.Thread(target=_download,
                         args=(s["url"], dest, s["size"], s["sha256"]),
                         daemon=True, name="loom-update")
    _DL["t"] = t
    t.start()
    return snapshot()


BAT_TMPL = """@echo off
rem Loom 更新脚本：等主进程退出 -> 静默安装 -> 装完自删
timeout /t 3 /nobreak >nul
start "" /wait "{setup}" /SILENT /NORESTART /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS
if %errorlevel% equ 0 del "%~f0"
"""


def apply_update() -> dict:
    """交给一个脱离本进程的批处理去跑安装器，然后我们自己退出。

    只在打包态可用：源码运行没有"被替换的 exe"，这里返回错误而不是演一遍。
    """
    s = snapshot()
    if not s["frozen"]:
        return {"ok": False, "detail": "源码运行没有可替换的程序，请用安装包装新版本"}
    if s["phase"] != "ready" or not s["path"] or not Path(s["path"]).is_file():
        return {"ok": False, "detail": "还没有下载完成的安装包"}
    exe = Path(sys.executable)
    bat = updates_dir() / "update.bat"
    bat.write_text(BAT_TMPL.format(setup=str(s["path"]).replace('"', "")), encoding="mbcs")
    flags = 0
    if os.name == "nt":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        flags = 0x00000008 | 0x00000200 | 0x08000000
    try:
        subprocess.Popen(["cmd", "/C", str(bat)], creationflags=flags,
                         close_fds=True, cwd=str(paths.DATA_DIR))
    except Exception as e:
        return {"ok": False, "detail": f"启动安装程序失败：{e}"}
    threading.Timer(0.8, lambda: os._exit(0)).start()
    return {"ok": True, "detail": f"正在安装并退出，稍后从 {exe.name} 重新启动即可"}

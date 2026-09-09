# -*- coding: utf-8 -*-
r"""在线更新器：清单检查 → 流式下载（SHA-256 校验）→ 分形态替换重启。

两种运行形态（2026-08-28 起支持装机版）：
  便携版：exe 直接放任意目录，data/ 在 exe 同级。更新 = 原地替换 exe（二段式 bat）。
  装机版：Inno Setup 装到 %LOCALAPPDATA%\Programs\FlowForge，Uninstall.exe 同目录。
          更新 = 下载新 setup.exe → 校验 → 静默安装（/VERYSILENT /SUPPRESSMSGBOXES /
          /MERGETASKS=keepsl 保住快捷方式勾选 /restart 跳过运行中检测）
          → Inno 升级语义覆盖程序文件、data/ 原样保留 → 前台实例自动重启。

更新源协议不变：{update_url}/latest.json + sha256 校验 + 授权码门禁下载。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests

from . import paths
from .version import APP_VERSION

STATUS = {                      # 进程内共享的更新状态（/api/update/status 读取）
    "phase": "idle",            # idle/checking/available/downloading/ready/error/applying
    "message": "",
    "current": APP_VERSION,
    "latest": "",
    "notes": "",
    "progress": 0.0,            # 下载 0~100
    "downloaded": 0,
    "total": 0,
}
_LOCK = threading.Lock()
_DL_THREAD: threading.Thread | None = None

# 默认更新源：COS 私有桶的公有读清单（用户未在设置页自填时兜底使用）。
# 软件内自动下载走 /api/update-download 换预签名 URL；latest.json 本身公有读。
DEFAULT_UPDATE_URL = "https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com"


def effective_update_url() -> str:
    """设置页填了更新源就用用户的，否则回退默认 COS 更新源。"""
    try:
        from . import db
        v = (db.get_setting("update_url", "") or "").strip()
        return v or DEFAULT_UPDATE_URL
    except Exception:
        return DEFAULT_UPDATE_URL


def update_dir() -> Path:
    # DB_DIR 两种运行模式都指向可写数据根（frozen=exe同级data/，源码=modex-data/）
    d = paths.DB_DIR / "update"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_exe_path() -> Path:
    return update_dir() / "FlowForge-new.exe"


def _set(**kw):
    with _LOCK:
        STATUS.update(kw)


def get_status() -> dict:
    with _LOCK:
        return dict(STATUS)


def sha256_of(p: Path, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _semver_tuple(v: str):
    parts = []
    for x in (v or "").strip().lstrip("v").split("."):
        try:
            parts.append(int(x))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _setup_install_cmd(setup_path: Path) -> list:
    """装机版静默升级命令。/MERGETASKS=keepsl：沿用上次安装时勾选的快捷方式任务。
    /FORCECLOSEAPPLICATIONS：浏览器等占用待更新文件时静默强制关闭（否则静默模式下
    RestartManager 弹窗被抑制 → 默认中止回滚，升级失败）。"""
    return [str(setup_path), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
            "/MERGETASKS=keepsl", "/FORCECLOSEAPPLICATIONS"]


def check(base_url: str, timeout: int = 15) -> dict:
    """拉取 latest.json 并对比版本。返回状态字典（phase=available/none/error）。"""
    base = (base_url or "").strip().rstrip("/")
    if not base:
        _set(phase="error", message="未配置更新源地址（设置页可填）")
        return get_status()
    _set(phase="checking", message="正在检查更新…", latest="", notes="")
    try:
        r = requests.get(base + "/latest.json", timeout=timeout)
        r.raise_for_status()
        mf = r.json()
    except Exception as e:
        _set(phase="error", message=f"检查失败: {str(e)[:180]}")
        return get_status()
    latest = str(mf.get("version") or "").strip()
    url = str(mf.get("url") or "").strip()
    sha = str(mf.get("sha256") or "").strip().lower()
    notes = str(mf.get("notes") or "")
    if not latest or not url:
        _set(phase="error", message="清单格式错误：缺 version/url")
        return get_status()
    update_dir().joinpath("latest.json").write_text(
        json.dumps(mf, ensure_ascii=False), encoding="utf-8")
    has_new = _semver_tuple(latest) > _semver_tuple(APP_VERSION)
    _set(latest=latest, notes=notes,
         phase="available" if has_new else "none",
         message=f"已是最新版本 {APP_VERSION}" if not has_new
                 else f"发现新版本 {latest}")
    if has_new:
        # 记住清单里的下载信息，供 download() 使用
        update_dir().joinpath("pending.json").write_text(
            json.dumps({"url": url, "sha256": sha, "version": latest},
                       ensure_ascii=False), encoding="utf-8")
    return get_status()


def _download_worker(url: str, sha: str, version: str):
    dest = new_exe_path()
    tmp = dest.with_suffix(".part")
    try:
        # COS 桶已设为私有，直链 403。先调用授权服务获取限时预签名下载 URL。
        # 已激活用户的 license.json 里有 code+token，后端校验后返回 10 分钟有效的签名 URL。
        dl_url = url
        try:
            from . import licensing
            lic = licensing.load()
            if lic and lic.get("code") and lic.get("token"):
                api = licensing.SERVER.rstrip("/") + "/api/update-download"
                resp = requests.post(api, json={
                    "code": lic["code"],
                    "token": lic["token"],
                    "version": version,
                }, timeout=20)
                if resp.ok:
                    data = resp.json()
                    if data.get("ok") and data.get("download_url"):
                        dl_url = data["download_url"]
        except Exception:
            pass  # 获取预签名 URL 失败时回退到原 URL（兼容过渡期）
        _set(phase="downloading", message=f"正在下载 {version}…", progress=0.0,
             downloaded=0, total=0)
        with requests.get(dl_url, stream=True, timeout=(10, 120)) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or 0)
            _set(total=total)
            done = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 19):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        _set(downloaded=done, total=total,
                             progress=round(done * 100.0 / total, 1))
        if sha and sha256_of(tmp) != sha:
            tmp.unlink(missing_ok=True)
            _set(phase="error", message="SHA-256 校验失败，已丢弃下载文件")
            return
        tmp.replace(dest)
        _set(phase="ready", progress=100.0,
             message=f"{version} 已就绪，点击「安装并重启」完成更新")
    except Exception as e:
        _set(phase="error", message=f"下载失败: {str(e)[:180]}")


def download() -> dict:
    """后台线程开始下载清单中记录的新版本。"""
    global _DL_THREAD
    pend = update_dir() / "pending.json"
    if not pend.exists():
        _set(phase="error", message="请先检查更新")
        return get_status()
    info = json.loads(pend.read_text(encoding="utf-8"))
    if _DL_THREAD and _DL_THREAD.is_alive():
        return get_status()
    _DL_THREAD = threading.Thread(
        target=_download_worker,
        args=(info["url"], info.get("sha256", ""), info.get("version", "")),
        daemon=True)
    _DL_THREAD.start()
    return get_status()


# ---------------- 启动自动检查 + 自动下载 ----------------
def _auto_check_worker(fallback_url: str):
    """启动后台自动检查：默认源 = 设置页填写的 update_url，否则 COS 公有读清单。

    检查到新版本（phase=available）后直接复用 download() 后台下载；
    下载就绪（phase=ready）只提示，安装仍需用户在设置页确认（不静默重启）。
    """
    try:
        from . import db
        configured = (db.get_setting("update_url", "") or "").strip()
    except Exception:
        configured = ""
    base = configured or fallback_url or DEFAULT_UPDATE_URL
    try:
        st = check(base, timeout=12)
        if st.get("phase") == "available":
            download()
    except Exception as e:
        _set(phase="idle", message="")


def start_auto_check(background_delay: float = 6.0):
    """应用启动后延迟触发一次「检查 + 自动下载」。绝不阻塞启动、失败静默。"""
    def _run():
        time.sleep(max(0.0, background_delay))
        _auto_check_worker("")
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def _write_update_bat(old_pid: int) -> Path:
    """便携版二段式替换脚本（等旧进程退出 → 替换 → 重启 → 自删）。"""
    exe = Path(sys.executable).resolve() if paths.FROZEN else \
        (paths.BASE / "dist" / "FlowForge.exe").resolve()
    new = new_exe_path().resolve()
    bat = update_dir() / "update.bat"
    bat.write_text(f"""@echo off
chcp 65001 >nul
set OLD_PID={old_pid}
set TARGET={exe}
set SOURCE={new}

:waitloop
tasklist /FI "PID eq %OLD_PID%" 2>nul | find /I "FlowForge" >nul
if not errorlevel 1 (
  timeout /t 1 /nobreak >nul
  goto waitloop
)
:copyloop
move /Y "%SOURCE%" "%TARGET%" >nul 2>&1
if exist "%SOURCE%" (
  timeout /t 2 /nobreak >nul
  goto copyloop
)
start "" "%TARGET%"
del "%~f0"
""", encoding="utf-8")
    return bat


def apply() -> dict:
    """校验就绪文件 → 分形态替换 → 本进程退出。

    装机版（paths.INSTALLED）：下载物重命名为 FlowForge-{ver}-setup.exe 后
    静默升级安装（Inno 覆盖程序文件、保留 data/ 与快捷方式），
    /restart 跳过运行中检测；本进程 1.2s 后退出为文件覆盖让路，
    Inno [Run] 段的 {app}\\FlowForge.exe --relaunch 会自动把新版拉起来。
    便携版：沿用二段式 bat 原地替换。
    """
    if paths.FROZEN:
        new = new_exe_path()
        if not new.exists():
            _set(phase="error", message="未找到已下载的更新包，请先下载")
            return get_status()
        pend = update_dir() / "pending.json"
        if pend.exists():
            info = json.loads(pend.read_text(encoding="utf-8"))
            want = (info.get("sha256") or "").lower()
            if want and sha256_of(new) != want:
                _set(phase="error", message="安装前校验失败，请重新下载")
                new.unlink(missing_ok=True)
                return get_status()
        if paths.INSTALLED:
            ver = info.get("version", "new") if pend.exists() else "new"
            setup = update_dir() / f"FlowForge-{ver}-setup.exe"
            new.replace(setup)
            cmd = _setup_install_cmd(setup)
            _set(phase="applying", message=f"正在静默升级到 {ver}…")
            DETACHED = 0x00000008 | 0x00000200   # DETACHED_PROCESS | NEW_PROCESS_GROUP
            subprocess.Popen(cmd, creationflags=DETACHED, close_fds=True)
            threading.Timer(1.2, lambda: os._exit(0)).start()
            return get_status()
        bat = _write_update_bat(os.getpid())
        _set(phase="applying", message="正在重启安装…")
        DETACHED = 0x00000008 | 0x00000200       # DETACHED_PROCESS | NEW_PROCESS_GROUP
        subprocess.Popen(["cmd", "/c", str(bat)],
                         creationflags=DETACHED, close_fds=True)
        threading.Timer(1.2, lambda: os._exit(0)).start()
        return get_status()
    _set(phase="error", message="源码运行模式不支持自更新（仅打包 exe 生效）")
    return get_status()

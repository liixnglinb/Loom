# -*- coding: utf-8 -*-
"""集中管理路径：区分「只读打包资源」与「可写数据目录」。

PyInstaller 冻结（frozen）时，只读资源在 sys._MEIPASS 临时解压目录，可写数据
（workspaces / modex.db / uploads / export）放到 exe 同级 data/ 目录，
确保工作流进度与产物在 exe 更新后不丢失。

源码运行（非 frozen）时保持与之前完全一致的目录布局，避免既有数据错位：
  modex-data/       数据库 + 上传 + 导出
  workspaces/       各工作流产物
"""
import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))

# 装机版识别：Inno Setup 的卸载器是 unins000.exe（不是 Uninstall.exe！曾因此
# 导致装机版自升级误走便携分支，把安装包二进制 bat 覆盖到主程序上）。
# 兼容三种证据：unins000.exe / Uninstall.exe / 注册表卸载项含本 exe 路径。
# 便携版 / 源码运行均为 False。用于更新器分形态替换。
def _detect_installed() -> bool:
    if not FROZEN:
        return False
    exe_dir = Path(sys.executable).parent
    if (exe_dir / "unins000.exe").exists() or (exe_dir / "Uninstall.exe").exists():
        return True
    try:
        import winreg
        for hive, path in ((winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                           (winreg.HKEY_LOCAL_MACHINE,
                            r"Software\Microsoft\Windows\CurrentVersion\Uninstall")):
            try:
                k = winreg.OpenKey(hive, path)
            except OSError:
                continue
            with k:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, i); i += 1
                    except OSError:
                        break
                    try:
                        with winreg.OpenKey(k, sub) as sk:
                            v, _t = winreg.QueryValueEx(sk, "InstallLocation")
                            if v and Path(v).resolve() == exe_dir.resolve():
                                return True
                    except OSError:
                        continue
    except Exception:
        pass
    return False

INSTALLED = _detect_installed()

if FROZEN:
    if INSTALLED:
        # 装机版：安装根目录可由安装器写入的环境变量覆盖（双开/自定义安装路径场景）
        _app = os.environ.get("MODELFLOW_APP_DIR") or Path(sys.executable).parent
        INSTALL_ROOT = Path(_app).resolve()
    else:
        INSTALL_ROOT = Path(sys.executable).parent
    _MEI = Path(getattr(sys, "_MEIPASS", INSTALL_ROOT))
    BASE = _MEI                                  # 打包的只读资源
    DATA_DIR = INSTALL_ROOT / "data"             # 安装根同级可写目录（升级自动保留）
    STATIC_DIR = BASE / "static"
    DB_DIR = DATA_DIR
    WS_ROOT = DATA_DIR / "workspaces"
    UPLOAD_DIR = DATA_DIR / "uploads"
    EXPORT_DIR = DATA_DIR / "export"
else:
    BASE = Path(__file__).resolve().parent.parent  # 源码根目录
    STATIC_DIR = BASE / "static"
    DB_DIR = BASE / "modex-data"                   # 数据库/上传/导出
    WS_ROOT = BASE / "workspaces"                  # 工作流产物
    UPLOAD_DIR = DB_DIR / "uploads"
    EXPORT_DIR = DB_DIR / "export"

for _p in (WS_ROOT, UPLOAD_DIR, EXPORT_DIR):
    _p.mkdir(parents=True, exist_ok=True)
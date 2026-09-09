# -*- coding: utf-8 -*-
"""集中管理路径：区分「只读打包资源」与「可写数据目录」。

配置驱动流水线：工作流实例与模板定义都落在可写数据目录，保证升级不丢。
源码运行（非 frozen）时数据落在项目根 modex-data/，与旧版一致。
"""
import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))


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
        _app = os.environ.get("MODELFLOW_APP_DIR") or Path(sys.executable).parent
        INSTALL_ROOT = Path(_app).resolve()
    else:
        INSTALL_ROOT = Path(sys.executable).parent
    _MEI = Path(getattr(sys, "_MEIPASS", INSTALL_ROOT))
    BASE = _MEI                                  # 打包只读资源（static/skills/templates/utils）
    DATA_DIR = INSTALL_ROOT / "data"             # 安装根同级可写目录
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

# 可配置的外部资源目录（SKILL 库 / 模板库 / 工具链），默认随包内置
SKILLS_DIR = Path(os.environ.get("MODELFLOW_SKILLS_DIR") or (BASE / "skills"))
TEMPLATES_DIR = Path(os.environ.get("MODELFLOW_TEMPLATES_DIR") or (BASE / "_templates"))
UTILS_DIR = Path(BASE / "_utils_py")
# 用户自建 skill 目录（可写数据目录下）：软件内新建的 skill 落在这里，
# 打包安装版同样可写；读取时优先级最高（见 jobs.load_skill_prompt）。
USER_SKILLS_DIR = DB_DIR / "skills"

for _p in (WS_ROOT, UPLOAD_DIR, EXPORT_DIR, USER_SKILLS_DIR):
    _p.mkdir(parents=True, exist_ok=True)
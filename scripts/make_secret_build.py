# -*- coding: utf-8 -*-
"""打包前生成 app/_secret_build.py（已 gitignore，PyInstaller 会一并带入 exe）。

用法（PowerShell，每次打包前执行一次；app/_secret_build.py 已存在则可跳过）：
    $env:MODELFLOW_LICENSE_SECRET = "<当前授权密钥>"
    python scripts/make_secret_build.py

密钥来源见「个人开发信息/个人网站信息/Voyra个人网站说明.md」第 3.2 节。
"""
import os
import sys
from pathlib import Path

secret = os.environ.get("MODELFLOW_LICENSE_SECRET", "")
if not secret:
    sys.exit("错误：请先设置环境变量 MODELFLOW_LICENSE_SECRET")

out = Path(__file__).resolve().parent.parent / "app" / "_secret_build.py"
out.write_text("SECRET = " + repr(secret) + "\n", encoding="utf-8")
print("已生成:", out)

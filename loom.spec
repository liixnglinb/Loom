# -*- mode: python ; coding: utf-8 -*-
# Loom 织流 onedir 打包配置（产物 dist_app/Loom/ 目录树，交给 installer.iss 打成 setup.exe）
#
# 打包要点：
#   - static/ 与 skills/ 是只读资源，走 datas 进 _MEIPASS；用户数据在 app/paths.py
#     里另算（冻结态 = exe 同级 data/），所以**绝不能把 modex-data 打进来**。
#   - fastapi / uvicorn / webview 都有动态导入，collect_all 比手写 hiddenimports 可靠。
#   - uvicorn 的 loop/protocol 实现是运行时按字符串选的，不显式声明就打包后 500。
#   - 排除掉的是开发期依赖（pytest）和这台机器上装了但 Loom 零引用的重库。
from PyInstaller.utils.hooks import collect_all

datas = [("static", "static"), ("skills", "skills")]
binaries = []
hiddenimports = [
    "anyio._backends._asyncio",
    "uvicorn.logging",
    "uvicorn.loops.asyncio",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.auto",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
]

for _pkg in ("fastapi", "uvicorn", "starlette", "pydantic",
             "requests", "multipart", "webview", "h11"):
    try:
        d, b, h = collect_all(_pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# 本机 Python 装了整套科学计算栈（开发机跑数模用的），而 collect_all 会去
# 摸这些包的可选子模块 —— 一摸就把 numpy → pandas → scipy → torch → PySide6
# 整条链拖进分析图，光 hook 处理就要几分钟，产物还会涨到几个 G。
# Loom 的运行时导入清单里一个都没有它们，这里显式断掉。
HEAVY_LOCALS = ["torch", "tensorflow", "jax", "pandas", "numpy", "scipy", "sklearn",
                "scikit-learn", "matplotlib", "PySide6", "PyQt5", "PyQt6", "shiboken6",
                "cv2", "numba", "llvmlite", "sympy", "statsmodels", "seaborn", "tensorboard"]

a = Analysis(
    ["loom_launch.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tkinter", "PIL", "IPython", "jedi",
              "setuptools", "pip", "test", "pydoc_data"] + HEAVY_LOCALS,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # onedir：二进制交给 COLLECT
    name="Loom",
    icon="assets/loom.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                  # 无黑窗；loom_launch 已处理流重定向与错误框
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Loom")

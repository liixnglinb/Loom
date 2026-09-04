# -*- mode: python ; coding: utf-8 -*-
# ModelFlow onedir spec（装机版专用，产物 dist_app/ModelFlow/ 目录树给 Inno Setup 打包）
# 与 ModelFlow.spec（onefile 便携版）共用 Analysis 配置；改动两处需同步。
from PyInstaller.utils.hooks import collect_all

datas = [('static', 'static'), ('skills', 'skills'),
         ('_utils_py', '_utils_py'),      # 自检/工具脚本（app/tools.py 与 jobs.run_check 使用）
         ('_templates', '_templates')]    # 竞赛 LaTeX 模板骨架（jobs.ensure_template_assets 使用）
binaries = []
hiddenimports = []
tmp_ret = collect_all('fastapi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('uvicorn')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openai')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# 数据图/建模/文档解析核心库：AI 写的 gen_fig_*.py / 数据读取 / PDF/docx/xlsx 抽取
# 重度依赖这些库，必须随包分发（否则打包后 AI 画不了图、读不了上传文件）。
for _pkg in ('matplotlib', 'pandas', 'scipy', 'pdfplumber', 'docx', 'pypdf', 'openpyxl', 'PIL', 'pymupdf', 'pptx'):
    try:
        tmp_ret = collect_all(_pkg)
        datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
    except Exception:
        pass


a = Analysis(
    ['app_launch.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow',
              # 打包减重：以下库 app/_utils_py 均零引用，属 matplotlib/pandas 钩子
              # 误拖入的纯冗余（Qt 绑定/LLVM 后端/IPython 补全/测试框架/机器学习）。
              'numba', 'llvmlite', 'PySide6', 'shiboken6', 'jedi', 'IPython', 'pytest',
              'sklearn', 'scikit-learn',
              # 强制 matplotlib 无头 Agg/SVG/PDF 后端，断掉 Qt 绑定钩子
              'matplotlib.backends.backend_qt', 'matplotlib.backends.backend_qtagg',
              'matplotlib.backends.backend_qt5', 'matplotlib.backends.backend_qt5agg',
              'matplotlib.backends.backend_qtcairo', 'matplotlib.backends.backend_qt5cairo'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # onedir：二进制交给 COLLECT 收集
    name='ModelFlow',
    icon='modelflow.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,             # GUI 子系统：无黑窗（app_launch 已适配流重定向+错误框）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='ModelFlow',
)

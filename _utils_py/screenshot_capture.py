#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ModelFlow 轻量出图内核 — 用系统 Edge/Chrome 无头 printToPDF / screenshot 替代 Electron。

国赛核心链路：HTML 流程图 → 矢量 PDF（单页、真矢量文字、\\includegraphics 直接引用）。
无需打包 Electron，本机已装 Edge/Chrome 即可离线出图。

契约（对齐 paper-figure-html SKILL.md 对 screenshot_capture.py 的调用口径）：
  --check                             探测出图内核是否可用。0=可用 2=不可用（调用方降级为占位符）
  --file fig.html --out fig.pdf --format pdf  单张矢量 PDF
  --file fig.html --out fig.png               单张 PNG（viewport 截图）
  --config shots.json                         批量（viewport/targets 结构同 Electron 版）
  --geom-check fig.html                       几何自检（轻量内核不支持→退 2，调用方跳过，不阻塞）

退出码：0=全部成功  1=部分/全部失败  2=内核不可用/无法检查（应降级）  3=参数/致命错误

shots.json 结构（同 Electron 版）:
  {"viewport": {"width":1280,"height":800},
   "targets": [{"file":"fig.html","out":"fig.pdf","format":"pdf"},
               {"url":"http://127.0.0.1:19001/","out":"shot.png","waitMs":1200}]}

renderMath:true → 尽力注入 KaTeX CDN 渲染 \\(...\\)/$$ 公式；离线时自动降级（图仍出、公式不渲染）。
⛔ 全标准库实现，不引第三方。
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TOTAL_TIMEOUT = 180

_BROWSER_CANDIDATES = [
    # 显式覆盖优先（AI 好调用：可注入确定性入口）
    lambda: os.environ.get("MH_BROWSER_EXE") or os.environ.get("MODELFLOW_BROWSER_EXE"),
    lambda: shutil.which("msedge"),
    lambda: shutil.which("chrome"),
    lambda: shutil.which("chromium"),
    lambda: r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    lambda: r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    lambda: r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    lambda: r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _resolve_browser():
    """返回 (exe, kind)。kind∈{'edge','chrome'}。找不到返回 (None, None)。"""
    for fn in _BROWSER_CANDIDATES:
        try:
            p = fn()
        except Exception:
            p = None
        if p and Path(p).exists():
            kind = "edge" if "edge" in Path(p).name.lower() else "chrome"
            return (str(Path(p)), kind)
    return (None, None)


def _as_url(file_or_url: str) -> str:
    if file_or_url.startswith(("http://", "https://", "file://")):
        return file_or_url
    return Path(file_or_url).resolve().as_uri()


def _inject_katex(html_path: Path) -> Path:
    """尽力注入 KaTeX（CDN）到 HTML，离线/失败时回退原文件。"""
    try:
        text = html_path.read_text(encoding="utf-8")
        if "katex" in text.lower() and "renderMathInElement" in text:
            return html_path
        snippet = (
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">\n'
            '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>\n'
            '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>\n'
            '<script>\n'
            'document.addEventListener("DOMContentLoaded",function(){'
            'if(window.renderMathInElement){renderMathInElement(document.body,{delimiters:['
            '{left:"\\\\(",right:"\\\\)",display:false},'
            '{left:"\\\\[",right:"\\\\]",display:true},'
            '{left:"$$",right:"$$",display:true}]});}});\n'
            '</script>\n'
        )
        if "</head>" in text:
            text = text.replace("</head>", snippet + "</head>", 1)
        else:
            text = snippet + text
        tmp = html_path.with_name(html_path.stem + "_katex.html")
        tmp.write_text(text, encoding="utf-8")
        return tmp
    except Exception:
        return html_path


def _run_one(target: dict, viewport: dict) -> dict:
    """执行单个目标，返回 {ok, out, ...}。"""
    exe, kind = _resolve_browser()
    if not exe:
        return {"ok": False, "out": target.get("out"), "reason": "browser_unavailable"}

    out = target.get("out")
    if not out:
        return {"ok": False, "reason": "no_out"}
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    src = target.get("file") or target.get("url")
    if not src:
        return {"ok": False, "out": out, "reason": "no_source"}

    fmt = (target.get("format") or "").lower()
    if not fmt:
        fmt = "pdf" if out_path.suffix.lower() == ".pdf" else "png"
    wait_ms = int(target.get("waitMs") or target.get("wait_ms") or 1000)
    w = int((viewport or {}).get("width", 1280))
    h = int((viewport or {}).get("height", 800))

    is_file = "file" in target and not (src or "").startswith(("http://", "https://"))
    target_ref = _as_url(src)

    if fmt == "pdf" and is_file and target.get("renderMath"):
        target_ref = _as_url(str(_inject_katex(Path(src))))

    args = [
        exe,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        # 每次调用独立 user-data-dir：否则 Edge 单实例复用导致 printToPDF 不落盘
        "--user-data-dir=%s" % tempfile.mkdtemp(prefix="mf_edge_"),
    ]
    if fmt == "pdf":
        args += ["--print-to-pdf=%s" % str(out_path.resolve()),
                 "--no-pdf-header-footer"]
    else:
        args += ["--screenshot=%s" % str(out_path.resolve()),
                 "--window-size=%d,%d" % (w, h)]
    args += [target_ref]

    env = dict(os.environ)
    env.setdefault("ELECTRON_DISABLE_SECURITY_WARNINGS", "1")
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=_TOTAL_TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return {"ok": False, "out": out, "reason": "timeout"}
    except Exception as e:
        return {"ok": False, "out": out, "reason": "spawn_failed: %s" % e}

    ok = out_path.exists() and out_path.stat().st_size > 1000
    return {"ok": ok, "out": out, "reason": "" if ok else "empty_or_missing",
            "stderr_tail": (proc.stderr or "")[-300:]}


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="ModelFlow 轻量出图内核(Edge/Chrome 无头)")
    ap.add_argument("--check", action="store_true", help="探测出图内核是否可用")
    ap.add_argument("--config", help="批量截图配置 JSON 路径")
    ap.add_argument("--url", help="单张：页面 URL")
    ap.add_argument("--file", help="单张：本地 HTML 文件路径")
    ap.add_argument("--out", help="单张：输出路径(.png 截图 / .pdf 矢量)")
    ap.add_argument("--format", choices=["png", "pdf"], help="单张：输出格式(缺省按 out 后缀推断)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--wait-ms", type=int, default=1000)
    ap.add_argument("--full-page", action="store_true")
    ap.add_argument("--render-math", action="store_true", help="尽力注入 KaTeX 渲染公式")
    ap.add_argument("--geom-check", metavar="HTML",
                    help="元素级几何自检（轻量内核不支持→退 2，调用方跳过）")
    args = ap.parse_args()

    if args.check:
        exe, kind = _resolve_browser()
        if exe:
            print(f"OK browser available: {exe} ({kind})")
            sys.exit(0)
        print("browser unavailable — 出图能力不可用，调用方应降级为占位符")
        sys.exit(2)

    if args.geom_check:
        # 轻量内核无 Electron capture.js 探针，无法做元素级几何自检 → 优雅降级
        print("geom-check unavailable — 轻量出图内核不支持几何自检，跳过（不阻塞）")
        sys.exit(2)

    if args.config:
        try:
            cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        except Exception as e:
            print("配置读取失败: %s" % e)
            sys.exit(3)
        targets = cfg.get("targets") or []
        viewport = cfg.get("viewport")
    else:
        if (args.url or args.file) and args.out:
            one = {"out": args.out, "waitMs": args.wait_ms}
            if args.url:
                one["url"] = args.url
            else:
                one["file"] = args.file
            if args.format:
                one["format"] = args.format
            if args.render_math:
                one["renderMath"] = True
            targets = [one]
            viewport = {"width": args.width, "height": args.height}
        else:
            print("需要 --config，或 (--url|--file) + --out")
            sys.exit(3)

    if not targets:
        print("没有截图目标")
        sys.exit(3)

    exe, kind = _resolve_browser()
    if not exe:
        print(json.dumps({"ok": False, "results": [], "reason": "browser_unavailable"},
                         ensure_ascii=False, indent=2))
        sys.exit(2)

    results = [_run_one(t, viewport or {}) for t in targets]
    ok_all = bool(results) and all(r.get("ok") for r in results)
    print(json.dumps({"ok": ok_all, "results": results,
                      "reason": "" if ok_all else "some_or_all_failed"},
                     ensure_ascii=False, indent=2))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""ModelFlow 科研工具集。

提供 REST API 封装 _utils_py/ 下 7 个工具：
  - scholar_fetch          学术文献搜索 + BibTeX（AMiner/S2/CrossRef/DBLP/OpenAlex 四级 fallback）
  - gpt_image              AI 图片生成（OpenAI 兼容 GPT-Image，PNG→PDF）
  - reviewer_client        外部 LLM 论文评审（OpenAI 兼容，多轮 thread）
  - paper_data_check       论文数据真实性检查（docx/pdf/table 三模式）
  - tikz_vision_check      TikZ 图视觉自检（vision LLM + 防震荡刹车）
  - derive_reference_from_docx  从 docx 派生通用排版参考
  - watchdog               任务监控（training/download）
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

_CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

from . import db, paths
from . import jobs as _jobs_mod   # 复用 resolve_python（frozen 模式下 sys.executable 是 exe 非 Python）

UTILS_DIR = paths.BASE / "_utils_py"


def _tool_python() -> str:
    """工具脚本的解释器：源码模式用 sys.executable；打包(frozen)后必须用独立 Python。"""
    if paths.FROZEN:
        p = _jobs_mod.resolve_python()
        if p:
            return p
    return sys.executable


def _run_tool(name: str, args: list[str], cwd: str | None = None,
              timeout: int = 180, env_extra: dict | None = None) -> dict:
    """在 _utils_py 目录运行工具脚本，统一 stdout 文本 + 退出码语义分层。

    退出码语义：
      0 = 成功（ok=True, degraded=False）
      2 = 已降级/跳过（ok=True, degraded=True —— 工具没干满活，如无 key/无依赖降级）
      其它 = 失败（ok=False）
    返回体恒含 ok / degraded / code，供前端与上层按语义区分，不再把 exit 2 当纯成功。
    """
    script = UTILS_DIR / (name + ".py")
    if not script.exists():
        return {"ok": False, "degraded": False,
                "error": f"工具 {name}.py 不存在", "code": 1}
    import os
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")   # 子进程 stdout 走 UTF-8，防 GBK 控制台打印 ⚠/中文 报错
    if env_extra:
        env.update({k: v for k, v in env_extra.items() if v})
    # 打包(frozen)后 sys.executable 是 exe，必须用独立 Python；并让它能 import 随包库
    if paths.FROZEN:
        _mei = os.environ.get("_MEIPASS") or getattr(sys, "_MEIPASS", None)
        if _mei:
            pp = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = _mei + (";" + pp if pp else "")
    try:
        r = subprocess.run(
            [_tool_python(), str(script), *args],
            cwd=cwd or str(paths.BASE),
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", creationflags=_CNW,
        )
        code = r.returncode
        if code == 0:
            ok, degraded = True, False
        elif code == 2:
            ok, degraded = True, True
        else:
            ok, degraded = False, False
        return {
            "ok": ok,
            "degraded": degraded,
            "code": code,
            "stdout": (r.stdout or "")[-12000:],
            "stderr": (r.stderr or "")[-3000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "degraded": False,
                "error": f"工具执行超时（>{timeout}s）", "code": -1}
    except Exception as e:
        return {"ok": False, "degraded": False, "error": str(e), "code": -1}


# ---------- 学术文献搜索 ----------

def tool_scholar_search(query: str, max_results: int = 5) -> dict:
    """搜索论文（元数据，不含 BibTeX）：search 子命令。"""
    r = _run_tool("scholar_fetch", ["search", query, "--max", str(int(max_results))], timeout=90)
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"] or "[]")
        return {"ok": True, "results": data if isinstance(data, list) else []}
    except json.JSONDecodeError:
        return {"ok": False, "error": "scholar_fetch 输出无法解析", "stdout": r["stdout"][:2000]}


def tool_scholar_bibtex(query: str, max_results: int = 5) -> dict:
    """搜索并获取 BibTeX（三级 fallback）：bibtex 子命令。"""
    r = _run_tool("scholar_fetch", ["bibtex", query, "--max", str(int(max_results))], timeout=150)
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"] or "[]")
        return {"ok": True, "results": data if isinstance(data, list) else []}
    except json.JSONDecodeError:
        return {"ok": False, "error": "scholar_fetch 输出无法解析", "stdout": r["stdout"][:2000]}


def tool_scholar_bibtex_doi(doi: str) -> dict:
    """通过 DOI 获取单篇 BibTeX。"""
    r = _run_tool("scholar_fetch", ["bibtex-doi", doi], timeout=60)
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"] or "{}")
        return {"ok": True, "result": data}
    except json.JSONDecodeError:
        return {"ok": False, "error": "scholar_fetch 输出无法解析"}


# ---------- AI 图片生成 ----------

def _tmp_png_path() -> Path:
    """生成临时输出文件路径（gpt_image 用）。"""
    fd = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    p = Path(fd.name)
    fd.close()
    return p


def tool_gpt_image(prompt: str, output: str = "", lang: str = "zh",
                   aspect_ratio: str = "16:9", preset_id: int = 0) -> dict:
    """调用 gpt_image 生成图片。

    配置解析优先级：
      1. preset_id 指定某图像预设 → 用该预设的 base/key/model
      2. 否则用「默认图像预设」（image_presets 表）
      3. 都没有 → 回退旧的 settings 表 gpt_image_* 字段（向后兼容）
    """
    api_base = api_key = model = ""
    if preset_id:
        p = db.get_image_preset(int(preset_id))
        if p:
            api_base, api_key, model = p["api_base"], p["api_key"], p["model"]
    if not api_key:
        d = db.get_default_image_preset()
        if d:
            api_base, api_key, model = d["api_base"], d["api_key"], d["model"]
    # 旧 settings 字段兜底（历史版本用户）
    if not api_key:
        api_key = db.get_setting("gpt_image_key", "")
        api_base = db.get_setting("gpt_image_base", "").strip() or api_base
        model = db.get_setting("gpt_image_model", "").strip() or model
    if not api_key:
        return {"ok": False, "error": "未配置图像生成预设，请在「设置 → 图片生成」新增一个预设并设为默认"}
    out_path = Path(output).resolve() if output else _tmp_png_path()
    args = ["--prompt", prompt, "--output", str(out_path),
            "--lang", lang, "--aspect-ratio", aspect_ratio]
    env = {"GPT_IMAGE_API_KEY": api_key}
    if api_base:
        env["GPT_IMAGE_BASE_URL"] = api_base
    if model:
        env["GPT_IMAGE_MODEL"] = model
    r = _run_tool("gpt_image", args, timeout=300, env_extra=env)
    r["output"] = str(out_path)
    r["output_exists"] = out_path.exists()
    return r


# ---------- 论文评审 ----------

def tool_review(prompt: str, system: str = "",
                provider: str = "openai", api_base: str = "", api_key: str = "",
                model: str = "") -> dict:
    """调用 OpenAI 兼容 LLM 评审论文。默认从设置库回退取 gpt_image_key/base/model。
    返回评审全文（含思考文本拼接 stderr 提示）。"""
    # 参数回退：未传 key/base 时，尝试从默认预设取
    if not api_key or not api_base:
        preset = db.get_default_preset()
        if preset:
            api_key = api_key or preset.get("api_key", "")
            api_base = api_base or preset.get("api_base", "")
            model = model or preset.get("model", "")
            provider = preset.get("provider", provider)
    if not api_key or not api_base:
        return {"ok": False, "error": "未配置评审 API（请在设置页新增默认预设，或在此传入 key/base/model）"}
    args = ["--prompt", prompt]
    if system:
        args += ["--system", system]
    r = _run_tool("reviewer_client", args, timeout=600,
                  env_extra={"OPENAI_API_KEY": api_key,
                             "OPENAI_BASE_URL": api_base,
                             "REVIEWER_MODEL_ID": model or "gpt-4o"})
    if r["ok"]:
        r["review"] = r["stdout"]
    return r


# ---------- 论文数据真实性检查 ----------

def tool_paper_data_check(workspace: str, mode: str = "docx") -> dict:
    """对工作区运行数据真实性硬规则检查 + 生成清单。"""
    ws = Path(workspace)
    if not ws.exists():
        return {"ok": False, "error": f"工作区不存在: {workspace}"}
    r = _run_tool("paper_data_check",
                  ["--mode", mode, "--workspace", str(ws), "--quiet"], timeout=120)
    r["need_self_check"] = (ws / "PAPER_DATA_CHECKLIST.md").exists()
    r["report"] = (ws / "PAPER_DATA_CHECK_REPORT.md").read_text(
        encoding="utf-8", errors="replace")[:6000] if (ws / "PAPER_DATA_CHECK_REPORT.md").exists() else ""
    return r


def tool_table_check(workspace: str) -> dict:
    """TABLE 文件 vs JSON 真实性核对（paper-figure 后）。"""
    ws = Path(workspace)
    if not ws.exists():
        return {"ok": False, "error": f"工作区不存在: {workspace}"}
    r = _run_tool("paper_data_check", ["--mode", "table", "--workspace", str(ws), "--quiet"], timeout=120)
    r["need_self_check"] = (ws / "TABLE_DATA_CHECKLIST.md").exists()
    return r


# ---------- TikZ 视觉检查 ----------

def tool_tikz_vision_check(image_path: str) -> dict:
    """TikZ 图视觉自检（vision LLM）。

    修复：此前取旧 gpt_image_key（图片生成 key），不是 vision model key，导致视觉
    质检大概率静默降级。现统一走 _resolve_vision_cred()（图片预设→默认 API 预设→
    旧字段兜底），与 CLI 侧 run_step_via_cli 注入的 EDITOR_AI_*/OPENAI_* 同源。
    """
    p = Path(image_path)
    if not p.exists():
        return {"ok": False, "error": f"图片不存在: {image_path}"}
    _prov, _base, _key, _model = _jobs_mod._resolve_vision_cred()
    if not _key:
        return {"ok": False, "degraded": True,
                "error": "未配置视觉模型（请在设置页添加多模态图片预设并设为默认）"}
    env_extra = {"EDITOR_AI_API_KEY": _key, "EDITOR_AI_MODEL_ID": _model or "gpt-4o"}
    if _base:
        env_extra["EDITOR_AI_BASE_URL"] = _base
    r = _run_tool("tikz_vision_check", [str(p)], timeout=120, env_extra=env_extra)
    return r


# ---------- DOCX 样式派生 ----------

def tool_derive_docx(docx_path: str, out_dir: str = "") -> dict:
    """从参考 docx 派生通用排版规范（reference_paper_general.json + .md）。"""
    p = Path(docx_path)
    if not p.exists() or p.suffix.lower() != ".docx":
        return {"ok": False, "error": f"请提供有效 .docx 文件: {docx_path}"}
    out = Path(out_dir) if out_dir else paths.BASE / "docx_style_profiles"
    out.mkdir(parents=True, exist_ok=True)
    r = _run_tool("derive_reference_from_docx", [str(p), "--out-dir", str(out)], timeout=180)
    r["out_dir"] = str(out)
    return r


# ---------- 监控 ----------

def tool_watchdog(action: str = "status", base_dir: str = "") -> dict:
    """任务监控（training/download）。base_dir 默认 /tmp/MH Agent-watchdog。"""
    bd = base_dir or "/tmp/MH Agent-watchdog"
    r = _run_tool("watchdog", [f"--{action}"], timeout=30,
                  cwd=str(Path("/") if sys.platform != "win32" else paths.BASE))
    return r


# ---------- DOCX 导出（md → Word 中文论文） ----------

def tool_docx_export(source: str, title: str = "", out_dir: str = "") -> dict:
    """把 Markdown 论文/报告转成规范 Word 文档（三线表/上标引用/中文排版）。"""
    src = Path(source)
    if not src.exists() or src.suffix.lower() not in (".md", ".txt"):
        return {"ok": False, "error": f"源文件不存在或非 md/txt: {source}"}
    out = (Path(out_dir) if out_dir else src.parent) / (src.stem + ".docx")
    r = _run_tool("md_to_docx",
                  ["--source", str(src), "--output", str(out), "--title", title or ""],
                  timeout=120)
    r["output"] = str(out)
    r["output_exists"] = out.exists()
    return r


# 镜像导出给 main.py 使用
TOOLS = {
    "scholar_search": tool_scholar_search,
    "scholar_bibtex": tool_scholar_bibtex,
    "scholar_bibtex_doi": tool_scholar_bibtex_doi,
    "gpt_image": tool_gpt_image,
    "review": tool_review,
    "paper_data_check": tool_paper_data_check,
    "table_check": tool_table_check,
    "tikz_vision_check": tool_tikz_vision_check,
    "derive_docx": tool_derive_docx,
    "docx_export": tool_docx_export,
    "watchdog": tool_watchdog,
}
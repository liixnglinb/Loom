# -*- coding: utf-8 -*-
"""配置驱动流水线 主入口：模板可编排的数模工作流引擎。"""
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from . import db, jobs, llm, paths, pipelines
from .ws import router as ws_router
import time, threading, json

app = FastAPI(title="配置驱动数模流水线")
db.init_db()

# 启动时 seed 内置模板（competition / competition_bzd / competition_mathmodel）
try:
    pipelines.seed_builtin()
except Exception:
    pass

# 启动时自动探测本机 Claude Code CLI 并写入配置（固定 CLI 执行，无则执行时报错提示安装）
try:
    jobs.auto_configure_cli()
except Exception:
    pass

# 启动后台自动检查更新（延迟 6s，发现新版自动下载；安装仍需用户在设置页确认）
try:
    from . import updater as _updater_boot
    _updater_boot.start_auto_check(background_delay=6.0)
except Exception:
    pass

# ---------- 授权锁（仅打包 exe 强制；源码开发模式不锁） ----------
from . import licensing

@app.middleware("http")
async def license_gate(request, call_next):
    if paths.FROZEN:
        p = request.url.path
        allowed = (p.startswith("/static") or p.startswith("/api/license")
                   or p in ("/", "/favicon.ico") or p.endswith(".svg"))
        if not allowed and not licensing.is_activated():
            return JSONResponse({"detail": "unlicensed", "msg": "请先激活授权码"},
                                status_code=403)
    return await call_next(request)

@app.get("/api/license/status")
def license_status():
    return licensing.status()

class ActivateIn(BaseModel):
    code: str

@app.post("/api/license/activate")
def license_activate(a: ActivateIn):
    return licensing.activate(a.code)

STATIC = paths.STATIC_DIR
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

# 静态资源缓存策略：
#   - /static/img/（图表 PNG，文件名已含主题，内容永不变）→ 长缓存 immutable：
#     切换主题时浏览器直接命中本地缓存，图表墙"瞬时"出图，无重载等待。
#   - 其余 /static（JS/CSS/HTML）→ no-cache（每次重新校验，ETag 命中则 304）：
#     保证版本升级后 WebView 拿到最新代码，304 不重传 body，性能不受影响。
@app.middleware("http")
async def _static_cache_policy(request, call_next):
    resp = await call_next(request)
    try:
        path = request.url.path
        if path.startswith("/static/img/"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith("/static/"):
            resp.headers["Cache-Control"] = "no-cache"
    except Exception:
        pass
    return resp

app.include_router(ws_router)

_job_threads = {}

# ---------- 页面（单页 SPA：所有路由返回同一入口，前端 hash 路由切换视图） ----------
_SPA = str(STATIC / "index.html")
@app.get("/")
def index(): return FileResponse(_SPA)
@app.get("/new")
def new(): return FileResponse(_SPA)
@app.get("/run/{wid}")
def run_page(wid: int): return FileResponse(_SPA)
@app.get("/settings")
def settings(): return FileResponse(_SPA)
@app.get("/tools")
def tools_page(): return FileResponse(_SPA)
@app.get("/pipelines")
def pipelines_page(): return FileResponse(_SPA)
@app.get("/pipeline-edit")
def pipeline_edit_page(): return FileResponse(_SPA)
@app.get("/pipeline-edit/{name}")
def pipeline_edit_name(name: str): return FileResponse(_SPA)

# ---------- 工作流 API ----------
class WorkflowIn(BaseModel):
    title: str
    template: str = "competition"
    step: str = ""
    config: dict = {}

@app.post("/api/workflows")
def create_wf(w: WorkflowIn):
    # 配置驱动：创建实例时快照所选模板的有序步骤清单（编辑模板不再影响已建实例）
    p = db.get_pipeline(w.template)
    if not p:
        return JSONResponse({"detail": f"未知流水线模板：{w.template}"}, 400)
    ok, err = pipelines.validate_steps(p.get("steps") or [])
    if not ok:
        return JSONResponse({"detail": f"模板「{w.template}」步骤配置非法：{err}"}, 400)
    # 每步模型解析快照：config.step_models / 每步自带 model 优先
    snapshot = []
    step_models = (w.config or {}).get("step_models") or {}
    for s in (p.get("steps") or []):
        sd = dict(s)
        if not sd.get("model"):
            chosen = (step_models.get(sd["key"]) or step_models.get(sd.get("role") or "")
                      or (w.config or {}).get("model") or "").strip()
            if chosen:
                sd["model"] = chosen
        snapshot.append(sd)
    wid = db.create_workflow(w.title, w.template, snapshot[0]["key"], w.config,
                             steps_snapshot=snapshot)
    return {"id": wid}

@app.get("/api/workflows")
def list_wf():
    return db.list_workflows()

@app.get("/api/workflows/{wid}")
def get_wf(wid: int):
    w = db.get_workflow(wid)
    if not w: return JSONResponse({"detail": "not found"}, 404)
    return w

@app.delete("/api/workflows/{wid}")
def del_wf(wid: int):
    db.delete_workflow(wid)
    return {"ok": True}

def _file_category(name: str):
    lower = Path(name).suffix.lower()
    if lower in (".py", ".sh", ".r", ".m"):
        return "code"
    if lower in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
        return "figures"
    if lower in (".json",):
        return "results"
    if lower in (".csv", ".xlsx", ".xls"):
        return "results"
    if lower == ".pdf":
        return "paper"
    if lower in (".tex", ".cls", ".sty"):
        return "paper"
    return "report"

def _step_key_from_name(name: str):
    """按文件名关键词把产物文件归属到某步骤。"""
    n = name.lower()
    rules = [
        ("analysis", ["problem", "analysis", "capability", "data_profile", "数据画像", "原始参数", "事实提取"]),
        ("modeling", ["modeling", "建模"]),
        ("code", ["results", "audit", "审计", "solution_"]),
        ("figure", ["figure", "fig", "plot", "chart", "图"]),
        ("arch", ["architecture", "arch", "tikz", ".html", "flowchart"]),
        ("review", ["logic_review", "review", "复核"]),
        ("paper", ["main.tex", "section", "sections", "main_paper", "body", "thesis.cls", ".cls"]),
        ("compile", ["main.pdf", "compile", "compile_", "合规", "compliance"]),
        ("improve", ["improved", "improvement", "loop", "轮", "workflow_report", "阻断"]),
    ]
    for key, kws in rules:
        if any(k in n for k in kws):
            return key
    return "analysis"

@app.get("/api/workflows/{wid}/files")
def wf_files(wid: int):
    """扫描工作流产物目录，按步骤分组返回真实文件（含大小/分类）。"""
    ws = jobs.ws_path(wid)
    if not ws.exists():
        return {"groups": {}}
    out = {}
    for f in ws.rglob("*"):
        if not f.is_file():
            continue
        rel = str(f.relative_to(ws)).replace("\\", "/")
        # 去掉首层路径前缀，聚焦文件名归属
        key = _step_key_from_name(f.name)
        out.setdefault(key, []).append({
            "name": f.name,
            "path": rel,
            "size": f.stat().st_size,
            "cat": _file_category(f.name),
        })
    for k in out:
        out[k].sort(key=lambda x: x["name"])
    return {"groups": out}

@app.get("/api/workflows/{wid}/file")
def wf_file(wid: int, path: str = "", dl: int = 0):
    """预览/下载工作流产物目录下的单个文件。path 为相对 workspace 的路径。"""
    if not path:
        return JSONResponse({"detail": "path 为空"}, 404)
    ws = jobs.ws_path(wid)
    fp = (ws / path).resolve()
    # 防穿越：必须在 workspace 目录内（is_relative_to 语义正确，startswith 前缀会被 ../job_12 绕过）
    if not fp.is_relative_to(ws.resolve()):
        return JSONResponse({"detail": "非法路径"}, 400)
    if not fp.exists() or not fp.is_file():
        return JSONResponse({"detail": "文件不存在"}, 404)
    if dl:
        from fastapi.responses import FileResponse
        return FileResponse(str(fp), filename=fp.name)
    from fastapi.responses import Response
    data = fp.read_bytes()
    ctype = "image/png"
    ext = fp.suffix.lower()
    if ext in (".pdf",): ctype = "application/pdf"
    elif ext in (".txt", ".md"): ctype = "text/plain; charset=utf-8"
    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".svg"): ctype = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/svg+xml" if ext == ".svg" else "image/gif"
    elif ext in (".json",): ctype = "application/json; charset=utf-8"
    elif ext in (".tex", ".cls", ".sty"): ctype = "text/plain; charset=utf-8"
    elif ext in (".csv",): ctype = "text/csv; charset=utf-8"
    elif ext in (".py",): ctype = "text/plain; charset=utf-8"
    return Response(content=data, media_type=ctype)

@app.get("/api/workflows/{wid}/export")
def export_wf(wid: int):
    """把工作流产物目录打包成 zip 下载；目录不存在则返回 404。"""
    from fastapi.responses import FileResponse
    import zipfile, io
    ws = jobs.ws_path(wid)
    if not ws.exists():
        return JSONResponse({"detail": "产物目录不存在，请先启动作业"}, 404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in ws.rglob("*"):
            if f.is_file():
                try:
                    z.write(f, f.relative_to(ws).as_posix())
                except Exception:
                    pass
    import shutil
    tmp = paths.EXPORT_DIR
    tmp.mkdir(parents=True, exist_ok=True)
    dest = tmp / f"job_{wid}.zip"
    dest.write_bytes(buf.getvalue())
    return FileResponse(str(dest), media_type="application/zip",
                        filename=f"job_{wid}.zip")

# 参赛版导出白名单：只打包"提交参赛"所需文件（论文/报告/图表/代码/数据/模板骨架），
# 排除 _bzd 环境模板、_utils_py、日志、临时等内部目录，避免 zip 塞满无关文件。
_EXPORT_COMP_DIRS = ("_bzd", "_utils_py", "_templates", "_checkpoints", "_proof",
                     "__pycache__", ".git", ".mimosa", "node_modules", "logs")


@app.get("/api/workflows/{wid}/export-comp")
def export_wf_comp(wid: int):
    """参赛版导出：只打包论文、报告、图表、代码、数据与模板（exclude 内部环境目录）。"""
    from fastapi.responses import FileResponse
    import zipfile, io
    ws = jobs.ws_path(wid)
    if not ws.exists():
        return JSONResponse({"detail": "产物目录不存在，请先启动作业"}, 404)

    def _keep(rel: str, name: str, p: Path) -> bool:
        parts = rel.split("/")
        if any(part in _EXPORT_COMP_DIRS for part in parts):
            return False
        if name.startswith("_") or name.startswith("."):
            return False
        if name.endswith((".log", ".lock")):
            return False
        return True

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in ws.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(ws).as_posix()
            if _keep(rel, f.name, f):
                try:
                    z.write(f, rel)
                except Exception:
                    pass
    tmp = paths.EXPORT_DIR
    tmp.mkdir(parents=True, exist_ok=True)
    dest = tmp / f"job_{wid}_comp.zip"
    dest.write_bytes(buf.getvalue())
    return FileResponse(str(dest), media_type="application/zip",
                        filename=f"job_{wid}-参赛版.zip")

@app.get("/api/workflows/{wid}/export-docx")
def export_wf_docx(wid: int):
    """把工作区内主 Markdown 论文转成 Word 下载；无 .md 则 404。
    优先 paper/main.md，其次工作区根任意 *.md（取最大者，通常是论文主体）。"""
    from fastapi.responses import FileResponse
    from .tools import tool_docx_export
    ws = jobs.ws_path(wid)
    if not ws.exists():
        return JSONResponse({"detail": "产物目录不存在"}, 404)
    candidates = [ws / "paper" / "main.md"]
    candidates += sorted(ws.rglob("*.md"), key=lambda p: p.stat().st_size, reverse=True)
    src = next((p for p in candidates if p.exists() and p.stat().st_size > 100), None)
    if not src:
        return JSONResponse({"detail": "工作区内没有可导出的 Markdown 论文"}, 404)
    r = tool_docx_export(str(src), title="", out_dir=str(paths.EXPORT_DIR))
    if not r.get("ok") or not r.get("output_exists"):
        return JSONResponse({"detail": r.get("error") or "DOCX 导出失败"}, 500)
    return FileResponse(r["output"], media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        filename=f"job_{wid}.docx")

@app.post("/api/workflows/{wid}/start")
def start_wf(wid: int):
    w = db.get_workflow(wid)
    if not w: return JSONResponse({"detail": "not found"}, 404)
    jobs.start_job(wid)
    return {"ok": True, "id": wid}

class StepStatusIn(BaseModel):
    key: str
    status: str
    msg: str = ""

@app.post("/api/workflows/{wid}/pause")
def pause_wf(wid: int):
    jobs.pause_job(wid)          # 修复4：真暂停（线程事件，execute_job 在步骤边界阻塞）
    db.update_workflow(wid, status="paused")
    return {"ok": True}
@app.post("/api/workflows/{wid}/resume")
def resume_wf(wid: int):
    w = db.get_workflow(wid)
    if not w:
        return JSONResponse({"detail": "not found"}, 404)
    st = w.get("status")
    if st in ("pending", "failed", "completed"):
        jobs.start_job(wid)      # 从未启动/已结束：起线程（自动跳过已完成步骤续跑）
    else:
        jobs.resume_job(wid)     # paused/running：置位事件，被阻塞线程继续
    db.update_workflow(wid, status="running")
    return {"ok": True}

class RerunStepIn(BaseModel):
    step: str

@app.post("/api/workflows/{wid}/rerun")
def rerun_step(wid: int, q: RerunStepIn):
    """把指定步骤及其后的所有步骤重置为待重跑，并从该步骤重新生成。

    仅允许工作流处于 pending/failed/completed（运行中或已暂停时拒接，
    先等结束/点继续，避免与现有执行线程并发写库）。被重置步骤的旧状态
    （msg/duration/out）会被清掉，execute_job 启动后会跳过仍是 done 的更早步骤。
    """
    w = db.get_workflow(wid)
    if not w:
        return JSONResponse({"detail": "not found"}, 404)
    if w.get("status") in ("running", "paused"):
        return JSONResponse({"detail": "工作流正在运行/已暂停，请先等待完成或点「继续」后再重跑单步"}, 400)
    steps = dict(w.get("steps") or {})
    # 配置驱动：从实例快照读步骤顺序
    step_list = jobs.resolve_steps(w)
    keys = [s["key"] for s in step_list]
    if q.step not in keys:
        return JSONResponse({"detail": f"未知步骤：{q.step}"}, 400)
    reset_keys = keys[keys.index(q.step):]
    changed = False
    for k in reset_keys:
        st = steps.get(k)
        # 重置任意「已执行过」的状态：done/warn/failed 之外，也覆盖中断/暂停残留的
        # running/paused（接口已拒绝整体 running/paused，此时残留线程必然已不存在，可安全重置）
        if not isinstance(st, dict) or st.get("status") in ("pending", "wait"):
            continue
        st = dict(st)
        st["status"] = "pending"
        for _f in ("msg", "duration", "out", "model", "executor"):
            st.pop(_f, None)
        steps[k] = st
        changed = True
    if not changed:
        return {"ok": True, "msg": "该环节尚未执行过，无需重跑"}
    # 重跑语义是连续生成：临时关掉人工检查点，避免重跑过程卡在检查点
    config = dict(w.get("config") or {})
    if config.get("manual_checkpoint"):
        config["manual_checkpoint"] = False
    db.update_workflow(wid, steps=steps, config=config, status="pending", progress=0)
    jobs.start_job(wid)
    return {"ok": True, "from": q.step, "reset": reset_keys}

# ---------- 文件上传 ----------
# 允许上传的扩展名白名单（赛题/数据/模板/图片/视频等）；防止任意文件落盘。
_UPLOAD_ALLOWED = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".pptx", ".ppt",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".svg",
    ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".ts", ".mts", ".mpg", ".mpeg",
    ".tex", ".cls", ".sty", ".bib", ".md", ".txt", ".json", ".ipynb", ".py", ".zip",
}
_UPLOAD_MAX_BYTES = 500 * 1024 * 1024  # 500MB 上限，防超大文件打满磁盘


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    name = file.filename or ""
    ext = Path(name).suffix.lower()
    if ext not in _UPLOAD_ALLOWED:
        return JSONResponse({"detail": f"不支持的文件类型：{ext or '(无扩展名)'}"}, status_code=400)
    up = paths.UPLOAD_DIR
    up.mkdir(parents=True, exist_ok=True)
    dest = up / Path(name).name
    content = await file.read()
    if len(content) > _UPLOAD_MAX_BYTES:
        return JSONResponse({"detail": "文件超过 500MB 上限"}, status_code=413)
    dest.write_bytes(content)
    return {"name": name, "size": len(content), "path": str(dest)}

# ---------- 健康检查 ----------
import shutil as _shutil
@app.get("/api/health")
def health():
    from .version import APP_VERSION
    return {"ok": True, "latex": _shutil.which("xelatex") is not None,
            "version": APP_VERSION}

@app.get("/api/runtimes")
def runtimes():
    """本地运行时自检清单（启动遮罩逐项显示 + 缺项安装引导）。"""
    try:
        return {"ok": True, "runtimes": jobs.detect_runtimes()}
    except Exception:
        return {"ok": True, "runtimes": {}}

class InstallRuntimeIn(BaseModel):
    name: str

@app.post("/api/runtimes/install")
def install_runtime(a: InstallRuntimeIn):
    """按需安装缺失的本地运行时（winget 静默安装，国内镜像优先）。

    仅对已明确约定为「缺哪个装哪个」的组件生效；敏感/大体积组件只返回指引，不静默执行。
    """
    return jobs.install_runtime(a.name)

# ---------- 在线更新 ----------
from . import updater
from .version import APP_VERSION as _APP_VERSION

class UpdateUrlIn(BaseModel):
    url: str

@app.get("/api/update/info")
def update_info():
    return {"version": _APP_VERSION,
            "update_url": db.get_setting("update_url", ""),
            "effective_url": updater.effective_update_url(),
            "auto_check": True,
            "status": updater.get_status()}

@app.post("/api/update/url")
def set_update_url(u: UpdateUrlIn):
    db.set_setting("update_url", u.url.strip())
    return {"ok": True}

@app.post("/api/update/check")
def update_check():
    return updater.check(db.get_setting("update_url", ""))

@app.post("/api/update/download")
def update_download():
    return updater.download()

@app.get("/api/update/status")
def update_status():
    return updater.get_status()

@app.post("/api/update/apply")
def update_apply():
    return updater.apply()

# ---------- 流水线模板（配置驱动：模板存数据库，可自建/编辑/另存副本） ----------
class PipelineIn(BaseModel):
    name: str
    label: str = ""
    desc: str = ""
    emoji: str = ""
    g: str = "custom"
    steps: list = []

class PipelineUpdate(BaseModel):
    label: str = ""
    desc: str = ""
    emoji: str = ""
    g: str = ""
    steps: list = None

@app.get("/api/pipelines")
def list_pipelines():
    """返回全部流水线模板（含内置三套 + 用户自建），步骤清单完整返回。"""
    out = []
    for p in db.list_pipelines():
        out.append({"template": p["name"], "name": p["name"], "label": p["label"],
                    "desc": p["desc"], "emoji": p["emoji"], "g": p["g"],
                    "builtin": bool(p.get("builtin")),
                    "steps": p.get("steps") or []})
    comp = next((p for p in out if p["name"] == "competition"), None)
    return {"pipelines": out, "competition": comp}

@app.post("/api/pipelines")
def create_pipeline(p: PipelineIn):
    name, ok = pipelines.normalize_name(p.name)
    if not ok:
        return JSONResponse({"detail": "模板名只能含小写字母/数字/连字符/下划线"}, 400)
    if db.get_pipeline(name):
        return JSONResponse({"detail": f"模板名「{name}」已存在"}, 400)
    okv, err = pipelines.validate_steps(p.steps)
    if not okv:
        return JSONResponse({"detail": err}, 400)
    db.create_pipeline(name, p.label or name, p.desc, p.emoji, p.g or "custom",
                       steps=p.steps, builtin=0)
    return {"ok": True, "name": name}

@app.put("/api/pipelines/{name}")
def update_pipeline(name: str, u: PipelineUpdate):
    p = db.get_pipeline(name)
    if not p:
        return JSONResponse({"detail": "not found"}, 404)
    if u.steps is not None:
        okv, err = pipelines.validate_steps(u.steps)
        if not okv:
            return JSONResponse({"detail": err}, 400)
    db.update_pipeline(name, label=u.label or None, desc=u.desc or None,
                       emoji=u.emoji or None, g=u.g or None, steps=u.steps)
    return {"ok": True}

@app.delete("/api/pipelines/{name}")
def delete_pipeline(name: str):
    p = db.get_pipeline(name)
    if not p:
        return JSONResponse({"detail": "not found"}, 404)
    if p.get("builtin"):
        return JSONResponse({"detail": "内置模板不可删除，可另存为副本后编辑"}, 400)
    db.delete_pipeline(name)
    return {"ok": True}

@app.post("/api/pipelines/{name}/duplicate")
def duplicate_pipeline(name: str, p: PipelineIn):
    """把内置/现有模板另存为用户副本（用于编辑内置模板的步骤）。"""
    src = db.get_pipeline(name)
    if not src:
        return JSONResponse({"detail": "not found"}, 404)
    newname, ok = pipelines.normalize_name(p.name)
    if not ok:
        return JSONResponse({"detail": "模板名只能含小写字母/数字/连字符/下划线"}, 400)
    if db.get_pipeline(newname):
        return JSONResponse({"detail": f"模板名「{newname}」已存在"}, 400)
    steps = p.steps if p.steps else (src.get("steps") or [])
    okv, err = pipelines.validate_steps(steps)
    if not okv:
        return JSONResponse({"detail": err}, 400)
    db.create_pipeline(newname, p.label or (src["label"] + " 副本"), p.desc or src["desc"],
                       p.emoji or src["emoji"], p.g or src["g"], steps=steps, builtin=0)
    return {"ok": True, "name": newname}

@app.get("/api/skills")
def list_skills():
    """枚举可绑定的 skill 目录（skills/ 下含 SKILL.md 的子目录名）。"""
    out = []
    for base in (paths.SKILLS_DIR, paths.BASE / "skills"):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists() and d.name not in [x["name"] for x in out]:
                out.append({"name": d.name})
    return {"skills": out}

# ---------- 提示词定制（查看原版 / 追加 / 替换 / 恢复） ----------
class OverrideIn(BaseModel):
    template: str
    step_key: str
    skill: str = ""
    extra_prompt: str = ""
    replace_prompt: str = ""

@app.get("/api/skill-prompt")
def get_skill_prompt_api(template: str, step_key: str, skill: str):
    """返回某步骤的提示词三件套：原版 SKILL、当前覆盖（若有）、合成预览。"""
    base = jobs.load_skill_prompt(skill)
    ov = db.get_skill_override(template, step_key)
    return {"base": base, "override": ov,
            "composed": jobs.compose_skill_prompt(skill, template, step_key),
            "customized": bool(ov and ((ov.get("extra_prompt") or "").strip()
                                       or (ov.get("replace_prompt") or "").strip()))}

@app.post("/api/skill-override")
def set_skill_override_api(o: OverrideIn):
    db.set_skill_override(o.template, o.step_key, o.skill, o.extra_prompt, o.replace_prompt)
    return {"ok": True}

@app.delete("/api/skill-override")
def clear_skill_override_api(template: str, step_key: str):
    db.clear_skill_override(template, step_key)
    return {"ok": True}

# ---------- 设置 ----------
class SettingIn(BaseModel):
    key: str
    value: str

@app.post("/api/settings")
def save_setting(s: SettingIn):
    db.set_setting(s.key, s.value)
    return {"ok": True}

@app.get("/api/settings")
def get_settings():
    return db.get_all_settings()

class TestConnIn(BaseModel):
    provider: str = "openai"
    api_base: str = ""
    api_key: str = ""
    model: str = ""

class ModelsListIn(BaseModel):
    api_base: str = ""
    api_key: str = ""
    provider: str = "openai"
    models_url: str = ""
    is_full_url: bool = False
    user_agent: str = ""

_MODEL_COMPAT_SUFFIXES = (
    "/api/claudecode", "/api/anthropic", "/apps/anthropic", "/api/coding",
    "/claudecode", "/anthropic", "/step_plan", "/coding", "/claude",
)


def _model_url_candidates(base: str, override: str = "", is_full_url: bool = False):
    """构造 /models 候选，兼容 Anthropic 子路径。"""
    if override.strip():
        return [override.strip()]
    b = (base or "").strip().rstrip("/")
    if not b:
        return []
    if is_full_url:
        if "/v1/" in b:
            return [b.split("/v1/", 1)[0] + "/v1/models"]
        root = b.rsplit("/", 1)[0]
        return [root + "/v1/models"] if "://" in root else []
    out = []
    last = b.rsplit("/", 1)[-1]
    versioned = len(last) > 1 and last[0] == "v" and last[1:].isdigit()
    if versioned:
        out.append(b + "/models")
        if last != "v1":
            out.append(b + "/v1/models")
    else:
        out.append(b + "/v1/models")
    for suffix in _MODEL_COMPAT_SUFFIXES:
        if b.endswith(suffix):
            root = b[:-len(suffix)].rstrip("/")
            out += [root + "/v1/models", root + "/models"]
            break
    return list(dict.fromkeys(out))


@app.post("/api/models/list")
def models_list(b: ModelsListIn):
    """按候选策略拉取模型列表，支持 OpenAI/Anthropic/Gemini 认证头。"""
    import requests as _requests
    urls = _model_url_candidates(b.api_base, b.models_url, b.is_full_url)
    if not urls:
        return {"ok": False, "models": [], "error": "缺少或无法解析模型端点", "tried": []}
    proto = (b.provider or "openai").lower()
    headers = {"Accept": "application/json"}
    if b.user_agent.strip():
        headers["User-Agent"] = b.user_agent.strip()
    if b.api_key:
        if proto in ("anthropic", "anthropic-messages"):
            headers["x-api-key"] = b.api_key
            headers["anthropic-version"] = "2023-06-01"
        elif proto in ("gemini", "google-generative-ai"):
            headers["x-goog-api-key"] = b.api_key
        else:
            headers["Authorization"] = "Bearer " + b.api_key
    errors = []
    for url in urls:
        try:
            resp = _requests.get(url, headers=headers, timeout=15)
            if resp.status_code in (404, 405):
                errors.append(f"{url}: HTTP {resp.status_code}")
                continue
            if resp.status_code in (401, 403) and proto in ("anthropic", "anthropic-messages"):
                # 部分 Anthropic 兼容服务的 /models 仍只接受 Bearer，安全地重试同一候选。
                retry_headers = dict(headers)
                retry_headers.pop("x-api-key", None)
                retry_headers["Authorization"] = "Bearer " + b.api_key
                resp = _requests.get(url, headers=retry_headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("data") or data.get("models") or data.get("items") or []
            if isinstance(raw, dict):
                raw = raw.get("data") or raw.get("items") or []
            models = []
            for item in raw if isinstance(raw, list) else []:
                if isinstance(item, str):
                    models.append({"id": item})
                elif isinstance(item, dict):
                    mid = item.get("id") or item.get("model") or item.get("name")
                    if mid:
                        models.append({**item, "id": mid})
            models.sort(key=lambda x: str(x.get("id", "")))
            return {"ok": True, "models": models, "endpoint": url, "tried": urls}
        except Exception as e:
            msg = str(e).replace(b.api_key, "[REDACTED]") if b.api_key else str(e)
            errors.append(f"{url}: {msg[:180]}")
    # 部分 Coding / Agent Plan（如火山方舟 /api/plan）不开放 /models，但固定
    # ark-code-latest 别名可正常推理。不能把「不可枚举」误判为连接失败：返回该预设
    # 已填写的模型作为可选项，并明确标记 degraded，让前端仍可保存/选用。
    known_model = ""
    if b.api_base.rstrip("/").endswith(("/api/plan", "/api/plan/v3")):
        known_model = "ark-code-latest"
    if known_model:
        return {"ok": True, "degraded": True,
                "models": [{"id": known_model, "owned_by": "volcengine-agent-plan"}],
                "warning": "该 Agent Plan 不开放模型枚举接口，已使用固定 Auto 模型别名",
                "detail": errors[-3:], "tried": urls}
    return {"ok": False, "models": [], "error": "所有候选模型端点均失败", "detail": errors[-3:], "tried": urls}

@app.post("/api/settings/test")
def test_conn(t: TestConnIn):
    ok, msg = llm.test_connection(t.provider, t.api_base, t.api_key, t.model)
    return {"ok": ok, "msg": msg}

# ---------- 编辑器（需求2：文件保存 + AI 改稿） ----------
class EditorSaveIn(BaseModel):
    wid: int
    path: str
    content: str

class EditorAiIn(BaseModel):
    wid: int
    path: str
    instruction: str = "润色优化本文件内容"

@app.post("/api/editor/save")
def editor_save(b: EditorSaveIn):
    """保存编辑器中的工作区文件（防穿越：必须落在该工作流工作区内）。"""
    ws = jobs.ws_path(b.wid)
    fp = (ws / b.path).resolve()
    if not fp.is_relative_to(ws.resolve()):
        return {"ok": False, "error": "非法路径"}
    if not fp.is_file():
        return {"ok": False, "error": "文件不存在"}
    try:
        fp.write_text(b.content, encoding="utf-8")
        return {"ok": True}
    except OSError as e:
        return {"ok": False, "error": str(e)[:150]}

@app.post("/api/editor/ai")
def editor_ai(b: EditorAiIn):
    """AI 编辑：读文件 → 默认预设调 LLM 按指令改写 → 返回新内容（不自动落盘，前端确认后保存）。"""
    ws = jobs.ws_path(b.wid)
    fp = (ws / b.path).resolve()
    if not fp.is_relative_to(ws.resolve()) or not fp.is_file():
        return {"ok": False, "error": "非法路径或文件不存在"}
    if fp.stat().st_size > 512 * 1024:
        return {"ok": False, "error": "文件过大（>512KB），请手动编辑"}
    try:
        content = fp.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"ok": False, "error": str(e)[:150]}
    preset = db.get_default_preset()
    if not preset:
        return {"ok": False, "error": "未配置 API 预设，请先在设置页新增并设为默认"}
    msgs = [
        {"role": "system", "content":
         "你是学术写作与代码编辑助手。按用户指令修改给定文件内容；"
         "保持原有结构与格式约定，只做指令要求的改动；直接返回修改后的完整文件内容，不要解释。"},
        {"role": "user", "content":
         f"【编辑指令】\n{b.instruction}\n\n【文件：{b.path}】\n{content}"},
    ]
    try:
        new_content = llm.chat(preset.get("provider", "openai"), preset.get("api_base", ""),
                               preset.get("api_key", ""), preset.get("model", ""),
                               msgs, temperature=0.3, max_tokens=8192)
    except Exception as e:
        return {"ok": False, "error": str(e)[:180]}
    if not (new_content or "").strip():
        return {"ok": False, "error": "LLM 返回空内容"}
    return {"ok": True, "content": new_content}

# ---------- API 预设库（仿 cc-switch：Provider / Config） ----------
class PresetIn(BaseModel):
    name: str
    provider: str = "openai"   # openai | anthropic
    api_base: str = ""
    api_key: str = ""
    model: str = ""
    extra: dict = {}           # 高级选项：upstream/authfield/model_map/fallback_model/user_agent

class PresetUpdate(BaseModel):
    name: str = ""
    provider: str = ""
    api_base: str = ""
    api_key: str = ""          # 空 = 保留原密钥
    model: str = ""
    clear_key: bool = False    # 显式清除密钥
    extra: dict = {}           # 高级选项（空 dict = 不修改）

class PresetTestIn(BaseModel):
    provider: str = "openai"
    api_base: str = ""
    api_key: str = ""
    model: str = ""

@app.get("/api/providers")
def list_providers():
    return {"presets": db.list_presets(), "default": db.get_default_preset()}

# ---------- 图片生成预设库（image_presets：自定义配置，无供应商目录） ----------
class ImagePresetIn(BaseModel):
    name: str
    api_base: str = ""
    api_key: str = ""
    model: str = ""
    extra: dict = {}

class ImagePresetUpdate(BaseModel):
    name: str = ""
    api_base: str = ""
    api_key: str = ""   # 空 = 保留原密钥
    model: str = ""
    extra: dict = None
    clear_key: bool = False

@app.get("/api/image-presets")
def list_image_presets():
    return {"presets": db.list_image_presets(), "default": db.get_default_image_preset()}

@app.post("/api/image-presets")
def add_image_preset(p: ImagePresetIn):
    name = p.name.strip()
    if not name:
        return JSONResponse({"detail": "预设名不能为空"}, 400)
    if db.get_image_preset_by_name(name):
        return JSONResponse({"detail": f"预设名「{name}」已存在"}, 400)
    pid = db.add_image_preset(name, p.api_base, p.api_key, p.model, p.extra)
    return {"ok": True, "id": pid, "presets": db.list_image_presets(),
            "default": db.get_default_image_preset()}

@app.put("/api/image-presets/{pid}")
def update_image_preset(pid: int, u: ImagePresetUpdate):
    p = db.get_image_preset(pid)
    if not p:
        return JSONResponse({"detail": "not found"}, 404)
    new_name = (u.name or "").strip() or p["name"]
    dup = db.get_image_preset_by_name(new_name)
    if dup and dup["id"] != pid:
        return JSONResponse({"detail": f"预设名「{new_name}」已存在"}, 400)
    api_key = p["api_key"]
    if u.clear_key:
        api_key = ""
    elif u.api_key.strip():
        api_key = u.api_key.strip()
    db.update_image_preset(pid, name=new_name,
                           api_base=u.api_base or p["api_base"],
                           api_key=api_key,
                           model=u.model or p["model"],
                           extra=u.extra if u.extra is not None else None)
    return {"ok": True, "presets": db.list_image_presets(),
            "default": db.get_default_image_preset()}

@app.delete("/api/image-presets/{pid}")
def del_image_preset(pid: int):
    if not db.get_image_preset(pid):
        return JSONResponse({"detail": "not found"}, 404)
    db.delete_image_preset(pid)
    return {"ok": True, "presets": db.list_image_presets(),
            "default": db.get_default_image_preset()}

@app.post("/api/image-presets/{pid}/default")
def set_default_image_preset(pid: int):
    if not db.get_image_preset(pid):
        return JSONResponse({"detail": "not found"}, 404)
    db.set_default_image_preset(pid)
    return {"ok": True, "presets": db.list_image_presets(),
            "default": db.get_default_image_preset()}

@app.post("/api/providers")
def add_provider(p: PresetIn):
    name = p.name.strip()
    if not name:
        return JSONResponse({"detail": "预设名不能为空"}, 400)
    if db.get_preset_by_name(name):
        return JSONResponse({"detail": f"预设名「{name}」已存在"}, 400)
    pid = db.add_preset(name, (p.provider or "openai"), p.api_base, p.api_key, p.model,
                        extra=p.extra or {})
    return {"ok": True, "id": pid, "presets": db.list_presets(),
            "default": db.get_default_preset()}

@app.put("/api/providers/{pid}")
def update_provider(pid: int, u: PresetUpdate):
    p = db.get_preset(pid)
    if not p:
        return JSONResponse({"detail": "not found"}, 404)
    new_name = u.name.strip() or p["name"]
    dup = db.get_preset_by_name(new_name)
    if dup and dup["id"] != pid:
        return JSONResponse({"detail": f"预设名「{new_name}」已存在"}, 400)
    api_key = p["api_key"]
    if u.clear_key:
        api_key = ""
    elif u.api_key.strip():
        api_key = u.api_key.strip()
    db.update_preset(pid, name=new_name, provider=u.provider or p["provider"],
                     api_base=u.api_base or p["api_base"], api_key=api_key,
                     model=u.model or p["model"], extra=(u.extra or None))
    return {"ok": True, "presets": db.list_presets(),
            "default": db.get_default_preset()}

@app.delete("/api/providers/{pid}")
def del_provider(pid: int):
    if not db.get_preset(pid):
        return JSONResponse({"detail": "not found"}, 404)
    db.delete_preset(pid)
    return {"ok": True, "presets": db.list_presets(),
            "default": db.get_default_preset()}

@app.post("/api/providers/{pid}/default")
def set_default(pid: int):
    if not db.get_preset(pid):
        return JSONResponse({"detail": "not found"}, 404)
    db.set_default_preset(pid)
    return {"ok": True, "presets": db.list_presets(),
            "default": db.get_default_preset()}

@app.post("/api/providers/test")
def test_provider(t: PresetTestIn):
    ok, msg = llm.test_connection(t.provider, t.api_base, t.api_key, t.model)
    return {"ok": ok, "msg": msg}

# ---------- 预设使用量查询（服务端代理：绕 CORS + SSRF 防护） ----------
class UsageQueryIn(BaseModel):
    url: str
    api_key: str = ""

@app.post("/api/usage/query")
def usage_query(q: UsageQueryIn):
    import socket, ipaddress, requests
    from urllib.parse import urlparse
    u = (q.url or "").strip()
    if not u:
        return {"ok": False, "error": "缺少查询地址"}
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        return {"ok": False, "error": "仅支持 http(s) 地址"}
    host = parsed.hostname or ""
    try:
        ips = {ai[4][0] for ai in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)}
    except Exception:
        return {"ok": False, "error": f"无法解析主机：{host}"}
    for ip in ips:
        ipo = ipaddress.ip_address(ip)
        if ipo.is_private or ipo.is_loopback or ipo.is_link_local or ipo.is_reserved:
            return {"ok": False, "error": "出于安全考虑禁止查询内网地址"}
    try:
        r = requests.get(u, headers={"Authorization": f"Bearer {q.api_key}",
                                     "Accept": "application/json"}, timeout=15)
        try:
            body = json.dumps(r.json(), ensure_ascii=False)
        except Exception:
            body = r.text[:2000]
        return {"ok": r.status_code == 200, "status": r.status_code, "body": body}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}

# ============================================================
# 科研工具集（见 app/tools.py）
# ============================================================
from . import tools as tools_mod

class ScholarIn(BaseModel):
    query: str
    max: int = 5

@app.post("/api/tools/scholar")
def tool_scholar(q: ScholarIn):
    """学术文献搜索（元数据）。"""
    from .tools import tool_scholar_search
    return tool_scholar_search(q.query, q.max)

class ScholarBibIn(BaseModel):
    query: str = ""
    max: int = 5
    doi: str = ""

@app.post("/api/tools/scholar/bibtex")
def tool_scholar_bib(q: ScholarBibIn):
    """搜索并获取 BibTeX，或按 DOI 获取。"""
    from .tools import tool_scholar_bibtex, tool_scholar_bibtex_doi
    if q.doi:
        return tool_scholar_bibtex_doi(q.doi)
    return tool_scholar_bibtex(q.query, q.max)

class GptImageIn(BaseModel):
    prompt: str
    lang: str = "zh"
    aspect_ratio: str = "16:9"
    preset_id: int = 0

@app.post("/api/tools/gpt-image")
def tool_gpt_image_api(q: GptImageIn):
    """AI 图片生成（PNG+PDF）。"""
    from .tools import tool_gpt_image
    return tool_gpt_image(q.prompt, lang=q.lang, aspect_ratio=q.aspect_ratio,
                          preset_id=q.preset_id)

class ReviewIn(BaseModel):
    prompt: str
    system: str = ""
    api_key: str = ""
    api_base: str = ""
    model: str = ""

@app.post("/api/tools/review")
def tool_review_api(q: ReviewIn):
    """论文评审（默认用默认预设，可覆盖 key/base/model）。"""
    from .tools import tool_review
    return tool_review(q.prompt, q.system, api_key=q.api_key,
                       api_base=q.api_base, model=q.model)

class DataCheckIn(BaseModel):
    workspace: str
    mode: str = "docx"

@app.post("/api/tools/data-check")
def tool_data_check_api(q: DataCheckIn):
    """论文数据真实性检查（docx/pdf/table）。"""
    from .tools import tool_paper_data_check, tool_table_check
    if q.mode == "table":
        return tool_table_check(q.workspace)
    return tool_paper_data_check(q.workspace, q.mode)

class TikuIn(BaseModel):
    image: str

@app.post("/api/tools/tikz-check")
def tool_tikz_api(q: TikuIn):
    """TikZ 图视觉自检。"""
    from .tools import tool_tikz_vision_check
    return tool_tikz_vision_check(q.image)

class DeriveIn(BaseModel):
    docx: str
    out_dir: str = ""

@app.post("/api/tools/derive-docx")
def tool_derive_api(q: DeriveIn):
    """从参考 docx 派生排版规范。"""
    from .tools import tool_derive_docx
    return tool_derive_docx(q.docx, q.out_dir)

class DocxExportIn(BaseModel):
    source: str
    title: str = ""
    out_dir: str = ""

@app.post("/api/tools/docx-export")
def tool_docx_export_api(q: DocxExportIn):
    """Markdown → Word 中文论文导出（三线表/上标引用/中文排版）。"""
    from .tools import tool_docx_export
    return tool_docx_export(q.source, q.title, q.out_dir)

@app.get("/api/tools")
def tool_index():
    """工具集能力清单。"""
    return {"tools": sorted(tools_mod.TOOLS.keys()),
            "desc": "科研工具集：scholar(文献)/gpt-image(生图)/review(评审)/data-check(数据检查)/tikz-check(TikZ视觉)/derive-docx(样式派生)"}

class WsPingIn(BaseModel):
    type: str = "ping"
    msg: str = ""

@app.post("/api/ws-ping/{wid}")
def ws_ping(wid: int, q: WsPingIn):
    """手动向某工作流的 WebSocket 订阅者推送一条消息（用于连通性测试/运营推送）。"""
    from .ws import push_sync
    push_sync(wid, {"type": q.type or "ping", "wid": wid, "msg": q.msg or "ping", "ts": int(time.time())})
    return {"ok": True, "wid": wid}

@app.get("/api/tools-file")
def tool_file(p: str = "", dl: int = 0):
    """预览/下载工具产生的外部文件（如图片生成结果）。p 为绝对路径。
    安全限制：仅允许访问系统临时目录 / uploads / workspaces 下的文件，
    避免被利用读取任意本机文件。"""
    if not p:
        return JSONResponse({"detail": "path 为空"}, 404)
    fp = Path(p).resolve()
    if not fp.exists() or not fp.is_file():
        return JSONResponse({"detail": "文件不存在"}, 404)
    import tempfile, os as _os
    allowed_roots = [
        Path(tempfile.gettempdir()).resolve(),
        Path(paths.UPLOAD_DIR).resolve(),
        Path(paths.WS_ROOT).resolve(),
    ]
    if not any(fp.is_relative_to(r) for r in allowed_roots):
        return JSONResponse({"detail": "路径不在允许范围内"}, 403)
    from fastapi.responses import FileResponse as _FR
    return _FR(str(fp), filename=fp.name,
               media_type="application/octet-stream" if dl else None)

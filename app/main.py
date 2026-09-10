# -*- coding: utf-8 -*-
"""FlowForge 智模流水线 —— 极简版主入口。

只保留两大能力：
  1. 创建流程：可视化编排流程模板（步骤清单，每步绑定 skill / 产物 / 检查点）
  2. 创建 skill：技能库管理（新建 / 编辑 / 另存副本 / 删除 / 导入标准 skill 包）

外加设置页（API 预设 / 连通检测）。无工作流执行、无内置模板、无授权墙、无更新器。
"""
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from . import db, llm, paths, pipelines

app = FastAPI(title="FlowForge 智模流水线")

STATIC = paths.STATIC_DIR
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.middleware("http")
async def _static_cache_policy(request, call_next):
    """静态资源 no-cache：版本升级后 WebView 拿最新代码，ETag 304 不重传。"""
    resp = await call_next(request)
    try:
        if request.url.path.startswith("/static/"):
            resp.headers["Cache-Control"] = "no-cache"
    except Exception:
        pass
    return resp


# ---------- 页面（单页 SPA：所有路由返回同一入口，前端 hash 路由切换视图） ----------
_SPA = str(STATIC / "index.html")

@app.get("/")
def index(): return FileResponse(_SPA)
@app.get("/pipelines")
def pipelines_page(): return FileResponse(_SPA)
@app.get("/pipeline-edit")
def pipeline_edit_page(): return FileResponse(_SPA)
@app.get("/pipeline-edit/{name}")
def pipeline_edit_name(name: str): return FileResponse(_SPA)
@app.get("/skills")
def skills_page(): return FileResponse(_SPA)
@app.get("/skill-edit")
def skill_edit_page(): return FileResponse(_SPA)
@app.get("/skill-edit/{name}")
def skill_edit_name(name: str): return FileResponse(_SPA)
@app.get("/settings")
def settings_page(): return FileResponse(_SPA)


# ---------- 健康检查 ----------
@app.get("/api/health")
def health():
    from .version import APP_VERSION
    return {"ok": True, "version": APP_VERSION}


# ---------- 流程模板（配置驱动：模板存数据库，全部用户自建） ----------
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
    """返回全部流程模板（步骤清单完整返回，供编排器/新建页展示）。"""
    out = []
    for p in db.list_pipelines():
        out.append({"template": p["name"], "name": p["name"], "label": p["label"],
                    "desc": p["desc"], "emoji": p["emoji"], "g": p["g"],
                    "steps": p.get("steps") or []})
    return {"pipelines": out}


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
                       steps=p.steps)
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
    if not db.get_pipeline(name):
        return JSONResponse({"detail": "not found"}, 404)
    db.delete_pipeline(name)
    return {"ok": True}


@app.post("/api/pipelines/{name}/duplicate")
def duplicate_pipeline(name: str, p: PipelineIn):
    """把现有模板另存为副本（用于复制一份改造）。"""
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
                       p.emoji or src["emoji"], p.g or src["g"], steps=steps)
    return {"ok": True, "name": newname}


@app.get("/api/pipelines/{name}/export")
def export_pipeline(name: str):
    """导出模板为 JSON 文件（备份 / 分享）。"""
    import json as _json
    p = db.get_pipeline(name)
    if not p:
        return JSONResponse({"detail": "not found"}, 404)
    p = dict(p)
    p.pop("id", None)
    p["steps"] = p.pop("steps", [])
    return JSONResponse(p, headers={
        "Content-Disposition": f'attachment; filename="flowforge-{name}.json"'})


# ---------- Skill 库（自建 + 随包内置只读） ----------
@app.get("/api/skills")
def list_skills():
    """枚举 skill（自建优先）。

    每个 skill 返回：name、desc（SKILL.md 首个非空标题/首段，截断 120 字）、
    source（user=自建可编辑 / bundled=随包内置只读）、chars（正文长度）。
    """
    seen = {}
    for base, source in ((paths.USER_SKILLS_DIR, "user"), (paths.BASE / "skills", "bundled")):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not (d.is_dir() and (d / "SKILL.md").exists()):
                continue
            if d.name in seen:
                continue
            try:
                text = (d / "SKILL.md").read_text(encoding="utf-8")
            except Exception:
                text = ""
            desc = ""
            for line in text.splitlines():
                t = line.strip().lstrip("#").strip()
                if t:
                    desc = t[:120]
                    break
            seen[d.name] = {"name": d.name, "desc": desc, "source": source,
                            "chars": len(text)}
    out = list(seen.values())
    out.sort(key=lambda x: (x["source"] != "user", x["name"]))
    return {"skills": out}


@app.get("/api/skills/{name}")
def get_skill(name: str):
    """读取单个 skill 的 SKILL.md 全文（用于技能管理页查看/编辑）。"""
    for base in (paths.USER_SKILLS_DIR, paths.BASE / "skills"):
        p = base / name / "SKILL.md"
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                return JSONResponse({"detail": "skill 文件读取失败"}, 500)
            return {"name": name, "content": text,
                    "editable": base == paths.USER_SKILLS_DIR}
    return JSONResponse({"detail": "skill 不存在"}, 404)


def _skill_dir_safe(name: str) -> Path | None:
    """校验 skill 名（防目录穿越），合法返回自建目录路径。"""
    import re as _re
    if not name or not _re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name):
        return None
    return paths.USER_SKILLS_DIR / name


class SkillIn(BaseModel):
    name: str
    content: str = ""
    desc: str = ""   # 仅用于新建时若无正文标题则补一行简介头


@app.post("/api/skills")
def create_skill(s: SkillIn):
    """新建自建 skill：写入 modex-data/skills/<name>/SKILL.md（可写目录）。"""
    d = _skill_dir_safe(s.name.strip())
    if not d:
        return JSONResponse({"detail": "skill 名只能含小写字母/数字/连字符/下划线"}, 400)
    if d.exists():
        return JSONResponse({"detail": f"skill「{s.name}」已存在"}, 400)
    content = (s.content or "").strip()
    if not content:
        content = (s.desc or "").strip() or (s.name + " 技能说明")
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(content + "\n", encoding="utf-8")
    return {"ok": True, "name": s.name}


@app.put("/api/skills/{name}")
def update_skill(name: str, s: SkillIn):
    """更新自建 skill 内容（内置 skill 不可改，需另存副本）。"""
    d = _skill_dir_safe(name)
    if not d or not (d / "SKILL.md").exists():
        return JSONResponse({"detail": "自建 skill 不存在（内置 skill 只读）"}, 404)
    (d / "SKILL.md").write_text((s.content or "").rstrip() + "\n", encoding="utf-8")
    return {"ok": True, "name": name}


@app.post("/api/skills/{name}/duplicate")
def duplicate_skill(name: str, s: SkillIn):
    """把内置/现有 skill 另存为自建副本（副本可编辑）。"""
    src_text = ""
    found = False
    for base in (paths.USER_SKILLS_DIR, paths.BASE / "skills"):
        p = base / name / "SKILL.md"
        if p.exists():
            src_text = p.read_text(encoding="utf-8")
            found = True
            break
    if not found:
        return JSONResponse({"detail": "skill 不存在"}, 404)
    newname = (s.name or "").strip()
    d = _skill_dir_safe(newname)
    if not d:
        return JSONResponse({"detail": "skill 名只能含小写字母/数字/连字符/下划线"}, 400)
    if d.exists():
        return JSONResponse({"detail": f"skill「{newname}」已存在"}, 400)
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(src_text, encoding="utf-8")
    return {"ok": True, "name": newname}


@app.delete("/api/skills/{name}")
def delete_skill(name: str):
    """删除自建 skill（内置 skill 只读不可删）。"""
    d = _skill_dir_safe(name)
    if not d or not (d / "SKILL.md").exists():
        return JSONResponse({"detail": "自建 skill 不存在"}, 404)
    import shutil
    shutil.rmtree(d, ignore_errors=True)
    return {"ok": True}


# ---------- 导入标准 skill 包（zip / 单个 SKILL.md / SKILL.md+附属文件） ----------
_SKILL_BANNED_PARTS = ("__pycache__", ".git", "node_modules", ".venv", "venv")
_SKILL_MAX_FILES = 500          # 单包文件数上限（防 zip 炸弹）
_SKILL_MAX_BYTES = 200 * 1024 * 1024  # 解压总量上限 200MB


def _skill_name_from_md(md_text: str, fallback: str) -> tuple[str, str]:
    """从 SKILL.md 的 YAML frontmatter 提取 name（有则用），返回 (name, meta_note)。"""
    import re as _re
    m = _re.match(r"^---\s*\n(.*?)\n---\s*\n", md_text, _re.S)
    if not m:
        return fallback, ""
    name = ""
    for line in m.group(1).splitlines():
        lm = _re.match(r"^name\s*:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line.strip())
        if lm:
            name = lm.group(1).strip()
            break
    return name, ("frontmatter.name" if name else "")


def _norm_skill_name(raw: str) -> str:
    """技能名规范化：小写、空格→短横线、剥非法字符、去首尾连字符。"""
    import re as _re
    s = (raw or "").strip().lower().replace(" ", "-").replace("_", "-")
    s = _re.sub(r"[^a-z0-9-]", "", s).strip("-")
    return s[:64]


def _extract_zip_safe(zf, dest: Path) -> int:
    """安全解 zip 到 dest（防穿越/防炸弹）。返回解出的文件数。"""
    import zipfile
    total = 0
    names = zf.namelist()
    if len(names) > _SKILL_MAX_FILES:
        raise ValueError(f"包内文件过多（{len(names)} > {_SKILL_MAX_FILES}）")
    for info in names:
        if info.endswith("/"):
            continue
        p = (dest / info).resolve()
        if not p.is_relative_to(dest.resolve()):
            raise ValueError(f"zip 内含非法路径：{info}")
        total += 1
    if total == 0:
        raise ValueError("压缩包为空")
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for info in names:
        if info.endswith("/"):
            continue
        p = (dest / info).resolve()
        if not p.is_relative_to(dest.resolve()):
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(p, "wb") as out:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                total += len(chunk)
                if total > _SKILL_MAX_BYTES:
                    raise ValueError("解压总量超过 200MB 上限")
        count += 1
    return count


def _find_skill_md(root: Path) -> Path | None:
    """在目录里定位 SKILL.md：根目录优先，其次唯一一层子目录（标准 skill 包结构）。"""
    direct = root / "SKILL.md"
    if direct.is_file():
        return direct
    subs = [d for d in root.iterdir() if d.is_dir()] if root.is_dir() else []
    hits = [d / "SKILL.md" for d in subs if (d / "SKILL.md").is_file()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        # 多个同名结构：取与包名一致的子目录
        for h in hits:
            if h.parent.name.lower() == root.name.lower():
                return h
        return hits[0]
    return None


def _install_skill_dir(src: Path, name: str) -> dict:
    """把含 SKILL.md 的目录装进技能库（移动整个目录，保留 references/scripts 等附属文件）。"""
    import shutil
    name = _norm_skill_name(name)
    if not name:
        raise ValueError("无法确定技能名（SKILL.md 缺少 frontmatter.name，且目录名不含合法字符）")
    dest = paths.USER_SKILLS_DIR / name
    if dest.exists():
        raise ValueError(f"技能「{name}」已存在，请先删除或改名")
    paths.USER_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    n_files = sum(1 for f in dest.rglob("*") if f.is_file())
    chars = len((dest / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
    return {"name": name, "files": n_files, "chars": chars}


@app.post("/api/skills/import")
async def import_skill(file: UploadFile = File(...)):
    """导入标准 skill 模式的技能包。

    接受三种形态：
      1. zip 压缩包：内含 SKILL.md（根目录或唯一子目录），附属文件随包进入
      2. 单个 SKILL.md 文件（按 frontmatter.name 或文件所在名入库）
    技能名优先取 SKILL.md frontmatter 的 name 字段，否则用 zip 内层目录名 / 文件名。
    """
    import zipfile, tempfile, shutil, io
    raw = await file.read()
    if len(raw) > _SKILL_MAX_BYTES:
        return JSONResponse({"detail": "文件超过 200MB 上限"}, 413)
    fname = (file.filename or "").strip()
    lower = fname.lower()

    tmp_root = Path(tempfile.mkdtemp(prefix="ff_import_"))
    try:
        if lower.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    _extract_zip_safe(zf, tmp_root)
            except zipfile.BadZipFile:
                return JSONResponse({"detail": "不是有效的 zip 压缩包"}, 400)
            except ValueError as e:
                return JSONResponse({"detail": str(e)}, 400)
            md = _find_skill_md(tmp_root)
            if not md:
                return JSONResponse({"detail": "压缩包内未找到 SKILL.md（标准 skill 包需含 SKILL.md）"}, 400)
            pkg_name = md.parent.name if md.parent != tmp_root else (Path(fname).stem or "skill")
            text = md.read_text(encoding="utf-8", errors="replace")
            fm_name, _note = _skill_name_from_md(text, pkg_name)
            try:
                result = _install_skill_dir(md.parent, fm_name or pkg_name)
            except ValueError as e:
                return JSONResponse({"detail": str(e)}, 400)
            return {"ok": True, **result}

        if lower.endswith(".md") or fname == "SKILL.md":
            text = raw.decode("utf-8", errors="replace")
            stem = Path(fname).stem
            fm_name, _note = _skill_name_from_md(text, stem)
            name = _norm_skill_name(fm_name or stem)
            if not name:
                return JSONResponse({"detail": "无法确定技能名（文件名与 frontmatter.name 均无效）"}, 400)
            dest = paths.USER_SKILLS_DIR / name
            if dest.exists():
                return JSONResponse({"detail": f"技能「{name}」已存在，请先删除或改名"}, 400)
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text(text, encoding="utf-8")
            return {"ok": True, "name": name, "files": 1, "chars": len(text)}

        return JSONResponse(
            {"detail": "仅支持 .zip（标准 skill 包）或 .md（SKILL.md）文件"}, 400)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


# ---------- 设置（API 预设 / 连通检测） ----------
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


class PresetIn(BaseModel):
    name: str
    provider: str = "openai"
    api_base: str = ""
    api_key: str = ""
    model: str = ""
    extra: dict = {}

class PresetUpdate(BaseModel):
    name: str = ""
    provider: str = ""
    api_base: str = ""
    api_key: str = ""   # 空 = 保留原密钥
    model: str = ""
    extra: dict = None
    clear_key: bool = False

class PresetTestIn(BaseModel):
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


@app.get("/api/providers")
def list_providers():
    return {"presets": db.list_presets(), "default": db.get_default_preset()}


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


_MODEL_COMPAT_SUFFIXES = (
    "/api/claudecode", "/api/anthropic", "/apps/anthropic", "/api/coding",
    "/claudecode", "/anthropic", "/coding", "/claude",
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
    return {"ok": False, "models": [], "error": "；".join(errors) or "无法获取模型列表",
            "tried": urls}

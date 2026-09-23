# -*- coding: utf-8 -*-
"""流程执行引擎：把每个步骤交给本机智能体 CLI（claude / codex）执行。

设计要点（沿用旧版的工程纪律，去掉与单一学科绑定的部分）：
- 一次运行 = 一个后台线程 + 一个事件总线（SSE 消费）
- 步骤之间**用工作区文件对话**：上一步落盘的文件就是下一步的输入，
  不在提示词里内联长文（智能体有文件工具，让它自己读）
- 检查点：步骤完成后 run 转 waiting，等用户 continue
- 局部修订 / 从此步重跑：都走同一个智能体引擎
- 取消：置 cancel_flag，步骤间隙退出
"""
import json
import re
import threading
import time
import uuid
from datetime import date
from pathlib import Path

from . import agents, db, paths

# run_id -> 事件总线；进程重启后 runs 表仍在，事件流按当前状态重建
_BUSES: dict = {}
_BUS_LOCK = threading.Lock()
_CANCEL: set = set()

# 工作区里不属于「产物」的文件（引擎自己的落盘）
_INTERNAL = {"AGENTS.md", "_step_system.txt"}
_ROLE_HINT = {
    "executor": "你是本步的执行者：按技能规范把任务真做完，产出真实文件。",
    "reviewer": "你是本步的独立评审：默认前序产出有问题，用证据逐条判定，不动手修。",
    "editor": "你是本步的修订者：按评审意见逐条修复，改文件本体并复验。",
}
_RUN_STATUS = ("pending", "running", "done", "failed", "cancelled", "revising")
# 步骤没注入端点时给运行台看的那句话。它是标签，不是模型名 ——
# 统计按模型分桶时要把它还原成空串，否则接口里会混进一句中文当键。
_NO_MODEL_HINT = "（沿用 CLI 自身配置）"


def _norm_run_id(rid: str) -> str | None:
    return rid if (rid and re.fullmatch(r"run-[a-z0-9]{6,40}", rid)) else None


def new_run_id() -> str:
    return "run-" + uuid.uuid4().hex[:12]


class RunBus:
    """一个运行的事件总线：runner 线程 publish，SSE 订阅者 consume。"""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.lock = threading.Lock()
        self.subs: list[list[dict]] = []
        self.history: list[dict] = []
        self.closed = False

    def publish(self, ev: dict):
        ev = dict(ev)
        ev.setdefault("ts", time.time())
        with self.lock:
            self.history.append(ev)
            if len(self.history) > 4000:
                self.history = self.history[-3000:]
            for q in self.subs:
                q.append(ev)

    def subscribe(self) -> list[dict]:
        q: list[dict] = []
        with self.lock:
            self.subs.append(q)
        return q

    def unsubscribe(self, q: list[dict]):
        with self.lock:
            if q in self.subs:
                self.subs.remove(q)

    def snapshot_events(self) -> list[dict]:
        run = db.get_run(self.run_id)
        if not run:
            return [{"type": "state", "run": None}]
        return [{"type": "state", "run": run, "artifacts": read_artifacts(run)}]


def bus_for(run_id: str) -> RunBus:
    with _BUS_LOCK:
        b = _BUSES.get(run_id)
        if not b:
            b = RunBus(run_id)
            _BUSES[run_id] = b
        return b


def drop_bus(run_id: str):
    with _BUS_LOCK:
        b = _BUSES.get(run_id)
        if b:
            b.closed = True


def is_cancelled(run_id: str) -> bool:
    return run_id in _CANCEL


# ==================== 工作区与产物 ====================
def _ws_path(run_id: str) -> Path:
    name = run_id if str(run_id).startswith("run-") else f"run-{run_id}"
    return paths.WORKSPACES_DIR / name


def workspace_dir(run_id: str) -> Path:
    d = _ws_path(run_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_out_name(out: str) -> str | None:
    out = (out or "").strip()
    if not out or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", out):
        return None
    return out


_ARTIFACT_SUFFIX = (".md", ".txt", ".json", ".csv", ".tex", ".py", ".html", ".yaml",
                    ".yml", ".log")


def _is_internal(rel: str) -> bool:
    """整条相对路径任一段以下划线开头就算内部文件 —— 只看文件名会让
    _turn_logs/xxx.jsonl 这种漏进清单，下一步的提示词里就多了引擎原始转录。"""
    parts = [p for p in rel.split("/") if p]
    return any(p in _INTERNAL or p.startswith("_") or p.startswith("AGENTS") for p in parts)


def list_workspace(run_id: str) -> list:
    """工作区文件清单（相对路径 + 字节数 + 改动时间），供提示词与产物面板共用。"""
    ws = _ws_path(run_id)          # 不建目录：提示词预览也会走这里
    out = []
    if not ws.is_dir():
        return out
    for f in sorted(ws.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(ws).as_posix()
        if _is_internal(rel):
            continue
        try:
            st = f.stat()
            out.append({"path": rel, "bytes": st.st_size, "mtime": int(st.st_mtime),
                        "kind": file_kind(rel)})
        except Exception:
            continue
    out.sort(key=lambda x: -x["mtime"])
    return out


_TEXT_EXT = {".md", ".markdown", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".py", ".js", ".ts",
             ".html", ".css", ".tex", ".bib", ".yaml", ".yml", ".toml", ".ini", ".log", ".r", ".m"}
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
_PREVIEW_MAX_BYTES = 400_000


def ws_file(run_id: str, rel: str) -> Path:
    """工作区内的一个真实文件。校验只写这一处 —— 预览和下载共用，
    才不会一个入口严、一个入口松。

    内部文件必须在这里一起挡掉：清单早就过滤了 _is_internal，但路径是拼出来的，
    直接输 /api/runs/<id>/artifacts/_step_system.txt 就能把引擎原始转录和
    本次注入的系统提示词整份下下来 —— 那里面带着用户的项目内容与密钥路径。"""
    ws = _ws_path(run_id).resolve()
    rel = str(rel or "").replace("\\", "/")
    f = (ws / rel).resolve()
    if f == ws or not f.is_relative_to(ws) or not f.is_file() or _is_internal(rel):
        raise FileNotFoundError(str(rel))
    return f


def file_kind(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in _IMAGE_EXT:
        return "image"
    if ext == ".pdf":
        return "pdf"
    if ext in _TEXT_EXT:
        return "text"
    return "binary"


def read_workspace_file(run_id: str, rel: str, max_bytes: int = _PREVIEW_MAX_BYTES) -> dict:
    """预览一个工作区文件。二进制（pptx / docx / xlsx / 压缩包）只报类型，
    正文一律不给 —— 前端拿到 kind 自己决定是渲染还是给下载。
    内部文件由 ws_file 统一挡，预览和下载两条口不会一个严一个松。"""
    f = ws_file(run_id, rel)
    size = f.stat().st_size
    kind = file_kind(f.name)
    out = {"path": str(rel), "kind": kind, "bytes": size, "truncated": False, "text": ""}
    if kind != "text":
        return out
    with f.open("rb") as fh:
        raw = fh.read(max_bytes + 1)
    out["truncated"] = len(raw) > max_bytes
    # ignore 而不是 replace：切在多字节中间时 replace 会补出一个 3 字节的 U+FFFD，
    # 结果"截断后的正文"反而比上限还长。
    out["text"] = raw[:max_bytes].decode("utf-8", errors="ignore")
    return out


_LOG_DIR = "_turn_logs"
_LOG_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\.jsonl$")
_LOG_TAIL_BYTES = 400_000


def workspace_bytes() -> tuple:
    """(全部工作区占用字节, 工作区目录数)。设置页「使用统计」用。"""
    root = paths.WORKSPACES_DIR
    if not root.is_dir():
        return 0, 0
    total, dirs = 0, 0
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        dirs += 1
        for f in d.rglob("*"):
            try:
                if f.is_file():
                    total += f.stat().st_size
            except Exception:
                pass
    return total, dirs


def orphan_workspaces() -> list:
    """有目录但没有对应运行记录的残留工作区 —— 只报，不自动删。

    目录名就是 run id（_ws_path 对已带 run- 前缀的 id 不再加前缀），
    所以这里绝不能剥前缀再比，否则每条正常的工作区都会被误判成孤儿。
    """
    root = paths.WORKSPACES_DIR
    if not root.is_dir():
        return []
    known = db.all_run_ids()
    out = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        if d.name in known or ("run-" + d.name) in known:
            continue
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        out.append({"name": d.name, "bytes": size})
    return out


def _streaks(daily: dict) -> tuple:
    """连续天数只数有活动的日子。当前连续以「今天或昨天」为锚 —— 隔了两天没开就归零，
    否则几天不用也会一直显示一个大数，那是自欺。"""
    days = sorted(d for d, v in daily.items() if v.get("tokens") or v.get("steps"))
    if not days:
        return 0, 0
    ds = [date.fromisoformat(x) for x in days]
    best = cur = 1
    for a, b in zip(ds, ds[1:]):
        cur = cur + 1 if (b - a).days == 1 else 1
        best = max(best, cur)
    if (date.today() - ds[-1]).days > 1:
        return 0, best
    now = 1
    for a, b in zip(reversed(ds[1:]), reversed(ds[:-1])):
        if (a - b).days != 1:
            break
        now += 1
    return now, best


def usage_stats() -> dict:
    """把 runs 表里的 step.meta 汇总成看得懂的用量。没有的字段一律按 0 计。

    逐条累计的那几项（token / 时长 / 步骤 / 成本）只扫最近 500 条 —— 一次
    list_runs 要把每行的 steps JSON 全解出来，跑几千条再点设置页会卡住。
    但"总共跑过几次"和状态分布不看窗口：那是 COUNT(*) 一下的事，
    跟着窗口走就会在 500 这条线上永远卡住。"""
    runs = db.list_runs(None, 500)
    by_status = db.run_status_counts()
    cost = dur = tools = turns = steps_done = steps_total = 0
    for r in runs:
        for s in (r.get("steps") or []):
            steps_total += 1
            if s.get("status") == "done":
                steps_done += 1
            m = s.get("meta") or {}
            cost += float(m.get("cost_usd") or 0)
            dur += int(m.get("duration_ms") or 0)
            tools += int(m.get("tools") or 0)
            turns += int(m.get("turns") or 0)
    tok = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0, "reason": 0, "total": 0}
    daily: dict = {}
    by_model: dict = {}
    peak_dur = 0
    for r in runs:
        for st in (r.get("steps") or []):
            m = st.get("meta") or {}
            t = m.get("tokens") or {}
            day = m.get("day") or (r.get("created_at") or "")[:10]
            for k in ("in", "out", "cache_read", "cache_write", "reason"):
                v = t.get(k)
                if isinstance(v, int):
                    tok[k] += v
            n = t.get("total")
            if not isinstance(n, int):
                # 老数据里没有 total，按四项不相交的明细补一份（reason 不在此列）
                n = sum(v for k in ("in", "out", "cache_read", "cache_write")
                        if isinstance((v := t.get(k)), int))
            tok["total"] += n
            s_turns = int(m.get("turns") or 0)
            s_tools = int(m.get("tools") or 0)
            if day:
                d = daily.setdefault(day, {"tokens": 0, "steps": 0, "turns": 0, "tools": 0})
                d["tokens"] += n
                d["steps"] += 1
                d["turns"] += s_turns
                d["tools"] += s_tools
            # 模型用量按「引擎 + 模型」分桶。老步骤的 meta 里没有 model，退回 step.model_used，
            # 但那句给人看的标签要还原成空串 —— 接口里不该出现中文标签当键。
            model = str(m.get("model") or "")
            if not model:
                used = str(st.get("model_used") or "")
                model = "" if used == _NO_MODEL_HINT else used
            eng = str(m.get("engine") or st.get("engine_used") or "")
            b = by_model.setdefault((eng, model), {"engine": eng, "model": model,
                                                   "tokens": 0, "turns": 0, "steps": 0,
                                                   "cost_usd": 0.0, "daily": {}})
            b["tokens"] += n
            b["turns"] += s_turns
            b["steps"] += 1
            b["cost_usd"] += float(m.get("cost_usd") or 0)
            if day:
                # 趋势图按模型画多条线，所以每个桶自带逐日序列
                b["daily"][day] = b["daily"].get(day, 0) + n
            peak_dur = max(peak_dur, int(m.get("duration_ms") or 0))
    streak_now, streak_best = _streaks(daily)
    ws_bytes, ws_dirs = workspace_bytes()
    return {
        "runs": sum(by_status.values()),
        "by_status": by_status,
        "steps_done": steps_done,
        "steps_total": steps_total,
        "tool_calls": tools,
        "agent_turns": turns,
        "duration_ms": dur,
        "cost_usd": round(cost, 4),
        "tokens": tok,
        "tokens_total": tok["total"],
        "peak_step_ms": peak_dur,
        "daily": dict(sorted(daily.items())),
        "by_model": sorted(by_model.values(), key=lambda x: (-x["tokens"], x["engine"])),
        "peak_day": max(daily.items(), key=lambda kv: kv[1]["tokens"])[0] if daily else "",
        "peak_day_tokens": max((d["tokens"] for d in daily.values()), default=0),
        "streak_now": streak_now,
        "streak_best": streak_best,
        "workspace_bytes": ws_bytes,
        "workspaces": ws_dirs,
        "workflows": len(db.list_pipelines()),
        "per_workflow": db.run_counts(),
        "orphans": orphan_workspaces(),
    }


def list_logs(run_id: str) -> list:
    """智能体原始转录日志（每步每次调用一份 jsonl），失败时唯一的现场证据。"""
    d = _ws_path(run_id) / _LOG_DIR
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.iterdir(), key=lambda p: p.name):
        if f.suffix != ".jsonl" or not f.is_file():
            continue
        try:
            st = f.stat()
        except Exception:
            continue
        out.append({"name": f.name, "bytes": st.st_size,
                    "modified": time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime(st.st_mtime))})
    return out


def read_log(run_id: str, name: str, max_lines: int = 500) -> dict:
    """读一份转录日志的尾部。只认纯文件名，且解析后必须仍在 _turn_logs 内。"""
    if not _LOG_NAME_RE.fullmatch(name or ""):
        raise ValueError("日志名无效")
    ws = _ws_path(run_id).resolve()
    f = (ws / _LOG_DIR / name).resolve()
    if not str(f).startswith(str(ws / _LOG_DIR)) or not f.is_file():
        raise FileNotFoundError("日志不存在")
    size = f.stat().st_size
    truncated = size > _LOG_TAIL_BYTES
    with open(f, "rb") as fh:
        if truncated:
            fh.seek(size - _LOG_TAIL_BYTES)
        raw = fh.read()
    lines = raw.decode("utf-8", "replace").splitlines()
    if truncated:                 # 截断处的第一行是半条，丢掉
        lines = lines[1:]
    total = len(lines)
    keep = max(1, min(max_lines, 2000))
    tail = lines[-keep:] if lines else []
    return {"name": name, "bytes": size, "truncated": truncated,
            "lines": tail, "dropped": total - len(tail)}


def read_artifacts(run: dict) -> dict:
    """读取工作区可预览产物，返回 {相对路径: 内容}。"""
    out = {}
    ws = workspace_dir(run["id"])
    names = set()
    for s in run.get("steps") or []:
        n = _safe_out_name(s.get("out") or "")
        if n:
            names.add(n)
    for item in list_workspace(run["id"]):
        p = item["path"]
        if Path(p).suffix.lower() in _ARTIFACT_SUFFIX and item["bytes"] <= 600_000:
            names.add(p)
    for n in names:
        f = ws / n
        if not f.is_file():
            continue
        try:
            out[n] = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return out


class _Cancelled(Exception):
    pass


# ==================== 技能加载 ====================
def _skill_dir(name: str) -> Path | None:
    """只认用户技能目录：软件不再随包带任何出厂技能，
    留着 BASE/skills 这一支，装过旧版本的目录里那份出厂技能就会悄悄复活。"""
    d = paths.USER_SKILLS_DIR / name
    return d if (d / "SKILL.md").is_file() else None


def _skill_body(name: str) -> str:
    d = _skill_dir(name)
    if not d:
        return ""
    try:
        return (d / "SKILL.md").read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""


def _refs_text(d: Path, limit=8000) -> str:
    """技能附属 references/*.md 拼成附录。"""
    ref = d / "references"
    if not ref.is_dir():
        return ""
    parts, total = [], 0
    for f in sorted(ref.rglob("*")):
        if not (f.is_file() and f.suffix.lower() in (".md", ".txt")):
            continue
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        seg = f"\n#### 附属文件 {f.name}\n\n{t}\n"
        if total >= limit:
            break
        parts.append(seg[:max(0, limit - total)])
        total += len(seg)
    return "".join(parts)


# 两家 CLI 各自的技能目录。和 Loom 那份同格式（<name>/SKILL.md），
# 所以能按名引用 —— 但引用不等于复制：那些文件会随 CLI 升级而变，
# 抄一份进工作区就是把它冻在我们的快照上。
EXTERNAL_SKILL_ROOTS = {
    "claude": Path.home() / ".claude" / "skills",
    "codex": Path.home() / ".codex" / "skills",
}


def _external_ref(name: str, src: str) -> str:
    return (f"### 技能「{name}」（{src} CLI 自带，按名加载）\n\n"
            f"本步要求使用 {src} 已安装的 skill「{name}」。请按你原生的 skill 发现机制加载并遵守；"
            f"Loom 不复制它的正文，也不代为改写到这份提示里。")


def compose_skill_prompt(skill_field: str, skill_src: str = "") -> tuple:
    """skill 字段可空格分隔叠多个技能（主技能 + 叠加规范），依次拼接。

    skill_src 非空时引用的是那家 CLI 自己的技能：只按名字挂进提示词，
    不读文件、不拷正文；Loom 自己的技能照旧内联全文。
    返回 (正文, [实际生效的技能名], [缺失的技能名])。
    """
    names = [n for n in re.split(r"\s+", (skill_field or "").strip()) if n]
    chunks, loaded, missing = [], [], []
    root = EXTERNAL_SKILL_ROOTS.get((skill_src or "").strip())
    if root is not None:
        for n in names:
            if (root / n / "SKILL.md").is_file():
                chunks.append(_external_ref(n, skill_src))
                loaded.append(n)
            else:
                missing.append(n)
        return ("\n\n---\n\n".join(chunks), loaded, missing)
    for n in names:
        body = _skill_body(n)
        if not body:
            missing.append(n)
            continue
        d = _skill_dir(n)
        refs = _refs_text(d) if d else ""
        chunks.append(f"### 技能「{n}」\n\n{body}" + (f"\n\n{refs}" if refs else ""))
        loaded.append(n)
    if not chunks:
        return "", loaded, missing
    return "\n\n---\n\n".join(chunks), loaded, missing


# ==================== 模型与引擎解析 ====================
def resolve_agent_config(step: dict) -> dict:
    """本步用哪个引擎、哪个端点与模型。

    引擎：步级 engine > 设置 default_engine > 本机第一个可用的 CLI。
    端点/模型阶梯：步级 model 是预设名 > 默认预设的 model_map[步骤key] >
    步级 model 当裸模型名挂在默认预设上 > 默认预设的 fallback_model > 默认预设。
    全部留空时不注入任何环境变量，沿用 CLI 自身的登录配置。
    """
    engine = (step.get("engine") or "").strip().lower()
    if engine not in agents.ENGINES:
        engine = (db.get_setting("default_engine") or "").strip().lower()
    if engine not in agents.ENGINES:
        engine = next((e for e in agents.ENGINES if agents.resolve_binary(e)), "")
    if not engine:
        raise RuntimeError(
            "本机未检测到任何智能体 CLI（claude / codex）。装好任意一个，"
            "或在设置页「智能体引擎」里填可执行文件路径。")

    conf = {"engine": engine, "provider": "", "api_base": "", "api_key": "",
            "model": "", "wire_api": "", "preset": "", "warn": ""}
    src = str(step.get("skill_src") or "").strip()
    if src and src != engine:
        # 三家技能是同一个格式，抄错引擎顶多加载不到那份规范 —— 给原因进运行台，
        # 但不替用户拍板禁用：他可能就是想把一份 claude 的写法喂给 codex。
        conf["warn"] = (f"本步技能来自 {src} 的技能目录，与本步引擎 {engine} 不匹配 —— "
                        f"{engine} 大概率加载不到「{step.get('skill') or ''}」。")
    want = (step.get("model") or "").strip()
    preset = db.get_preset_by_name(want) if want else None
    raw_model_id = ""
    if preset:
        conf["preset"] = preset.get("name") or ""
    else:
        preset = db.get_default_preset()
        if want:
            raw_model_id = want        # 步级填的是裸模型名，端点沿用默认预设
        if preset:
            conf["preset"] = preset.get("name") or ""
            extra = preset.get("extra") or {}
            mapped = ""
            if isinstance(extra.get("model_map"), dict):
                mapped = str(extra.get("model_map").get(step.get("key") or "") or "")
            conf["model"] = mapped or str(extra.get("fallback_model") or "")
    if not preset:
        return conf
    if raw_model_id:
        conf["model"] = raw_model_id
    if not agents.protocol_ok(engine, preset.get("provider") or "",
                              preset.get("api_base") or ""):
        # 协议对不上：不注入端点，改走该 CLI 自身的登录配置，并把原因留在轨迹里
        conf["model"] = ""
        conf["warn"] = (f"默认预设「{preset.get('name')}」协议为 "
                        f"{preset.get('provider') or 'openai'}，与 {engine} 引擎不兼容 —— "
                        "本步不注入该端点，改用 CLI 自身登录配置。")
        return conf
    conf["provider"] = preset.get("provider") or ""
    conf["api_base"] = preset.get("api_base") or ""
    conf["api_key"] = preset.get("api_key") or ""
    conf["wire_api"] = str((preset.get("extra") or {}).get("wire_api") or "")
    conf["model"] = conf["model"] or (preset.get("model") or "")
    return conf


# ==================== 提示词组装 ====================
def _flow_map(steps: list, idx: int) -> str:
    parts = []
    for i, s in enumerate(steps):
        tag = s.get("label") or s.get("key")
        parts.append(f"**{tag}**" if i == idx else tag)
    return " → ".join(parts)


def build_step_prompt(run: dict, idx: int) -> tuple:
    """返回 (system_text, user_text)。system 是技能规范全文，user 是任务与契约。"""
    steps = run.get("steps") or []
    step = steps[idx]
    ws = workspace_dir(run["id"])
    skill_text, loaded, missing = compose_skill_prompt(step.get("skill"),
                                                    step.get("skill_src") or "")

    role = step.get("role") or "executor"
    sys_parts = [
        "# 你在一条全自动工作流中执行单个步骤",
        "",
        f"- 流程：{run.get('label') or run.get('pipeline')}",
        f"- 当前步骤：第 {idx+1}/{len(steps)} 步 · {step.get('label')}",
        "",
        "## 本步角色",
        _ROLE_HINT.get(role, _ROLE_HINT["executor"]),
        "",
        "## 工作区约定",
        f"- 你的工作目录就是本工作区：`{ws}`",
        "- 步骤之间靠**工作区文件**传递信息：需要的前序产物请自己 Read，"
        "不要等别人把全文贴给你。",
        "- 产出必须**真实写入文件**，只在回答里贴正文不算完成。",
        "- 只做本步范围内的事，别顺手把后面的步骤也做了。",
    ]
    if missing:
        sys_parts += ["", f"⚠️ 下列技能在工作区里读不到，其规范缺失：{'、'.join(missing)}"]
    if skill_text:
        sys_parts += ["", "## 本步执行规范（技能全文，最高优先级）", "", skill_text]
    system_text = "\n".join(sys_parts)

    files = list_workspace(run["id"])
    upstream = []
    for s in steps[:idx]:
        n = _safe_out_name(s.get("out") or "")
        if n:
            upstream.append(n)
    user = [
        "# 任务说明（用户原始输入，一切判断的最终依据）",
        (run.get("brief") or "").strip() or "（用户未填写任务说明，仅给了流程名）",
        "",
        "# 本步指令",
        _ROLE_HINT.get(role, _ROLE_HINT["executor"]),
        "",
        "流程位置：" + _flow_map(steps, idx),
    ]
    if files:
        listing = "\n".join(f"- `{f['path']}`（{f['bytes']} 字节）" for f in files[:80])
        user += ["", "# 工作区现有文件", listing]
    if upstream:
        user += ["", "# 上游产物（动手前请先 Read 这些文件）",
                 "\n".join(f"- `{n}`" for n in upstream)]
    out = _safe_out_name(step.get("out") or "")
    if out:
        user += ["", f"# 输出契约", f"- 本步产出必须写入工作区文件 `{out}`，"
                                  f"文件结构按上方技能规范里的模板。"]
    if (step.get("extra_prompt") or "").strip():
        user += ["", "# 本步补充要求（优先级高于技能规范）", step["extra_prompt"].strip()]
    user += ["", "现在开始执行本步。"]
    return system_text, "\n".join(user)


# ==================== 执行 ====================
def _save_step_output(run_id: str, step: dict, text: str):
    n = _safe_out_name(step.get("out") or "")
    if n and text.strip():
        (workspace_dir(run_id) / n).write_text(text.rstrip() + "\n", encoding="utf-8")


def _run_step(run: dict, idx: int, bus: RunBus, extra_instruction: str = "") -> dict:
    """跑一个步骤，返回 {ok, text, error, meta}。"""
    run_id = run["id"]
    steps = run.get("steps") or []
    step = steps[idx]
    conf = resolve_agent_config(step)
    system_text, user_text = build_step_prompt(run, idx)
    if extra_instruction:
        user_text += f"\n\n# 追加指令（用户在本步现场提出）\n{extra_instruction}"
    ws = workspace_dir(run_id)
    if conf["engine"] == "codex":
        (ws / "AGENTS.md").write_text(system_text, encoding="utf-8")
        sys_arg = ""
    else:
        sys_arg = system_text

    step["engine_used"] = conf["engine"]
    step["model_used"] = conf["model"] or _NO_MODEL_HINT
    step["started_at"] = time.strftime("%H:%M:%S")
    step["trace"] = []
    if conf.get("warn"):
        step["trace"].append({"kind": "status", "text": conf["warn"]})
        bus.publish({"type": "status", "index": idx, "text": conf["warn"]})
    buf: list = []

    def _emit(ev: dict):
        kind = ev.get("type")
        if kind == "delta":
            text = ev.get("text") or ""
            buf.append(text)
            bus.publish({"type": "delta", "index": idx, "text": text})
            return
        if kind in ("tool", "status", "note"):
            line = {"kind": kind, "name": ev.get("name") or "",
                    "text": (ev.get("preview") or ev.get("text") or "")[:400]}
            step["trace"].append(line)
            if len(step["trace"]) > 120:
                del step["trace"][:60]
            bus.publish({"type": kind, "index": idx, "text": line["text"],
                         "name": line["name"]})

    try:
        res = agents.run_agent(
            conf["engine"], user_text, ws=ws, system_text=sys_arg,
            model=conf["model"], api_base=conf["api_base"], api_key=conf["api_key"],
            wire_api=conf["wire_api"], label=f"{idx+1:02d}_{step.get('key')}",
            emit=_emit, cancel_check=lambda: is_cancelled(run_id))
    except agents.AgentCancelled:
        raise _Cancelled()
    except agents.AgentError as e:
        log = Path(e.log).name if getattr(e, "log", "") else ""
        return {"ok": False, "error": str(e), "text": "".join(buf),
                "meta": {"log": log} if log else {}}

    out_name = _safe_out_name(step.get("out") or "")
    if (out_name and not (ws / out_name).is_file() and res["text"].strip()
            and not res["is_error"]):
        # 智能体只在回答里写了正文、没落盘 —— 兜底代写，保证下游有输入。
        # 出错时的 final 往往是 API 报错文本，绝不能当成产物写进去。
        (ws / out_name).write_text(res["text"].rstrip() + "\n", encoding="utf-8")
        bus.publish({"type": "note", "index": idx,
                     "text": f"智能体未落盘 {out_name}，已按最终回答代写"})
    meta = {"tools": res["tools"], "turns": res["turns"],
            "duration_ms": res["duration_ms"], "cost_usd": res["cost_usd"],
            "engine": res["engine"], "model": conf["model"],
            "tokens": res.get("tokens") or {},
            "day": time.strftime("%Y-%m-%d"),
            "log": Path(res["log"]).name if res.get("log") else ""}
    return {"ok": not res["is_error"], "error": res["error"],
            "text": res["text"] or "".join(buf), "meta": meta}


def _run_thread(run_id: str, start_step: int = 0):
    bus = bus_for(run_id)
    try:
        run = db.get_run(run_id)
        if not run:
            return
        # 从中间某步重跑也必须置 running。留在 pending 的代价不只是"没有停止按钮"：
        # 文件面板不轮询、count_active_runs 也数不到它，于是更新器可以在智能体
        # 正写盘的中途把程序换掉。顺带清掉上一轮的 error，重跑成功了别还挂着红条。
        db.update_run(run_id, status="running", waiting_reason="", error="",
                      cur_step=start_step)
        bus.publish({"type": "state", "run": db.get_run(run_id)})
        steps = run.get("steps") or []
        for idx in range(start_step, len(steps)):
            if is_cancelled(run_id):
                db.update_run(run_id, status="cancelled")
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
            step = steps[idx]
            step["status"] = "running"
            step["chars"] = 0
            db.update_run(run_id, cur_step=idx, steps=steps)
            bus.publish({"type": "step_start", "index": idx, "step": dict(step)})
            try:
                attempts = agents.step_retry() + 1
                r = None
                for attempt in range(attempts):
                    # 传同一个 steps 列表对象：_run_step 里写的 engine_used 等字段才会被持久化
                    try:
                        r = _run_step({**run, "steps": steps}, idx, bus)
                    except _Cancelled:
                        raise
                    except Exception as e:
                        r = {"ok": False, "error": f"第 {idx+1} 步异常：{e}",
                             "text": "", "meta": {}}
                    if r["ok"]:
                        break
                    if attempt + 1 < attempts:
                        bus.publish({"type": "status", "index": idx,
                                     "text": f"本步失败（{(r['error'] or '')[:80]}），"
                                             f"重试 {attempt+2}/{attempts}"})
            except _Cancelled:
                step["status"] = "cancelled"
                db.update_run(run_id, status="cancelled", steps=steps)
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
            except Exception as e:
                step["status"] = "failed"
                db.update_run(run_id, status="failed", error=f"第 {idx+1} 步异常：{e}",
                              steps=steps)
                bus.publish({"type": "error", "index": idx, "message": str(e)})
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
            step["meta"] = r["meta"]
            step["chars"] = len(r["text"] or "")
            if r["ok"]:
                step["status"] = "done"
                step["msg"] = ""
                db.update_run(run_id, steps=steps)
                bus.publish({"type": "step_done", "index": idx, "step": dict(step),
                             "chars": step["chars"]})
            else:
                step["status"] = "failed"
                step["msg"] = (r["error"] or "执行失败")[:400]
                db.update_run(run_id, status="failed", steps=steps,
                              error=f"第 {idx+1} 步：{step['msg']}")
                bus.publish({"type": "error", "index": idx, "message": step["msg"]})
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
            if step.get("checkpoint") and idx < len(steps) - 1:
                if agents.auto_continue():
                    bus.publish({"type": "note", "index": idx,
                                 "text": "全自动模式：已自动越过本步检查点"})
                    continue
                db.update_run(run_id, status="waiting", waiting_reason="checkpoint",
                              cur_step=idx + 1)
                bus.publish({"type": "checkpoint", "index": idx})
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
        db.update_run(run_id, status="done", cur_step=len(steps))
        bus.publish({"type": "state", "run": db.get_run(run_id)})
        bus.publish({"type": "done"})
    except Exception as e:
        try:
            db.update_run(run_id, status="failed", error=str(e)[:500])
            bus.publish({"type": "error", "message": str(e)[:500]})
            bus.publish({"type": "state", "run": db.get_run(run_id)})
        except Exception:
            pass
    finally:
        _CANCEL.discard(run_id)


def _snapshot_steps(pipeline: dict) -> list:
    steps = []
    for s in (pipeline.get("steps") or []):
        d = dict(s)
        d["status"] = "pending"
        d.pop("delta", None)
        steps.append(d)
    return steps


def start_run(pipeline_name: str, label: str = "", brief: str = "", engine: str = "",
              model: str = "") -> dict:
    p = db.get_pipeline(pipeline_name)
    if not p:
        raise ValueError(f"流程「{pipeline_name}」不存在")
    run_id = new_run_id()
    steps = _snapshot_steps(p)
    # 下任务时选的引擎覆盖每一步，留空则沿用步骤自身/全局默认
    if (engine or "").strip().lower() in agents.ENGINES:
        for s in steps:
            s["engine"] = engine.strip().lower()
    # 模型同理：盖的是步级那个值，所以「预设名 > 裸模型名 > 默认预设」那套阶梯照旧走，
    # 不在这里重复判断端点（协议对不上由 resolve_agent_config 报进运行台）。
    m = (model or "").strip()
    if m:
        for s in steps:
            s["model"] = m
    run = db.create_run(run_id, pipeline_name,
                        label or p.get("label") or pipeline_name,
                        steps, brief=brief)
    threading.Thread(target=_run_thread, args=(run_id, 0), daemon=True,
                     name=f"ff-run-{run_id}").start()
    return run


def resume_run(run_id: str) -> dict:
    run = db.get_run(run_id)
    if not run:
        raise ValueError("运行不存在")
    if run["status"] not in ("waiting",):
        raise ValueError(f"当前状态 {run['status']} 不可继续")
    _CANCEL.discard(run_id)
    db.update_run(run_id, status="running", waiting_reason="", error="")
    bus_for(run_id).publish({"type": "state", "run": db.get_run(run_id)})
    threading.Thread(target=_run_thread, args=(run_id, run["cur_step"]), daemon=True,
                     name=f"ff-run-{run_id}").start()
    return db.get_run(run_id)


def rerun_from(run_id: str, index: int) -> dict:
    """从第 index 步起重跑：该步及其后全部复位为 pending，产物文件保留（智能体自行覆盖）。"""
    run = db.get_run(run_id)
    if not run:
        raise ValueError("运行不存在")
    if run["status"] in ("running", "revising"):
        raise ValueError("运行中不能重跑，请先停止")
    steps = run.get("steps") or []
    if index < 0 or index >= len(steps):
        raise ValueError("步骤序号无效")
    for s in steps[index:]:
        s["status"] = "pending"
        s.pop("msg", None)
        s.pop("meta", None)
        s["chars"] = 0
    db.update_run(run_id, status="pending", error="", waiting_reason="",
                  cur_step=index, steps=steps)
    _CANCEL.discard(run_id)
    bus = bus_for(run_id)
    bus.publish({"type": "state", "run": db.get_run(run_id)})
    threading.Thread(target=_run_thread, args=(run_id, index), daemon=True,
                     name=f"ff-run-{run_id}").start()
    return db.get_run(run_id)


def cancel_run(run_id: str) -> dict:
    run = db.get_run(run_id)
    if not run:
        raise ValueError("运行不存在")
    _CANCEL.add(run_id)
    if run["status"] in ("waiting",):
        db.update_run(run_id, status="cancelled", waiting_reason="")
        b = _BUSES.get(run_id)
        if b:
            b.publish({"type": "state", "run": db.get_run(run_id)})
    return db.get_run(run_id)


# ==================== 局部修订（让智能体就地改产物文件） ====================
def revise_step(run_id: str, index: int, instruction: str) -> dict:
    """对第 index 步的产物发起对话式修改：仍走该步配置的引擎。"""
    run = db.get_run(run_id)
    if not run:
        raise ValueError("运行不存在")
    steps = run.get("steps") or []
    if index < 0 or index >= len(steps):
        raise ValueError("步骤序号无效")
    step = steps[index]
    # 修订线程和流水线线程各持一份 steps 整体回写同一行 JSON，同跑一步就是后写覆盖前写；
    # codex 那路还要覆写工作区的 AGENTS.md，两步同时在改会读到彼此的规范。
    if run.get("status") == "running":
        raise ValueError("这条流水线还在跑，先取消或等它停下再改这一步")
    if any((s.get("status") or "") == "revising" for s in steps):
        raise ValueError("已经有一步在修订了，一次只改一步")
    # cancel_run 只加标志、_run_thread 的 finally 才清；从取消过的那条 run 上发起修订
    # 时必须先清掉，否则 agents 那边一进来就当被取消，每次都秒失败。
    _CANCEL.discard(run_id)
    out_name = _safe_out_name(step.get("out") or "")
    if not out_name:
        raise ValueError("该步骤没有产物文件，无法修订（可改用「从此步重跑」）")
    bus = bus_for(run_id)
    step["status"] = "revising"
    db.update_run(run_id, steps=steps)
    bus.publish({"type": "state", "run": db.get_run(run_id)})

    def _thread():
        try:
            conf = resolve_agent_config(step)
            system_text = (
                "# 产物修订\n"
                f"你在修订工作区文件 `{out_name}`。只改用户要求的位置，其余保持原样；"
                "改完直接把同一文件写回，不要新建文件、不要输出解释。")
            ws = workspace_dir(run_id)
            if conf["engine"] == "codex":
                (ws / "AGENTS.md").write_text(system_text, encoding="utf-8")
                sys_arg = ""
            else:
                sys_arg = system_text
            prompt = (f"# 修订目标\n工作区文件 `{out_name}`\n\n"
                      f"# 修改要求\n{instruction}\n\n"
                      f"# 步骤上下文\n本步：{step.get('label')}（第 {index+1} 步）\n"
                      "请先读该文件，按要求修改后原地写回同一个文件。")

            def _emit(ev):
                kind = ev.get("type")
                if kind == "delta":
                    bus.publish({"type": "revise_delta", "index": index,
                                 "text": ev.get("text") or ""})
                elif kind in ("tool", "status", "note"):
                    bus.publish({**ev, "index": index})

            res = agents.run_agent(conf["engine"], prompt, ws=ws, system_text=sys_arg,
                                   model=conf["model"], api_base=conf["api_base"],
                                   api_key=conf["api_key"], wire_api=conf["wire_api"],
                                   label=f"rev{index+1:02d}_{step.get('key')}",
                                   emit=_emit,
                                   cancel_check=lambda: is_cancelled(run_id))
            try:
                new_text = (ws / out_name).read_text(encoding="utf-8", errors="replace")
            except Exception:
                new_text = res["text"] or ""
                if new_text.strip():
                    (ws / out_name).write_text(new_text, encoding="utf-8")
            step["status"] = "done" if new_text.strip() else "failed"
            step["chars"] = len(new_text)
            if res["is_error"] and not new_text.strip():
                step["status"] = "failed"
                step["msg"] = res["error"][:400]
            db.update_run(run_id, steps=steps)
            bus.publish({"type": "revise_done", "index": index, "chars": len(new_text),
                         "ok": step["status"] == "done"})
            bus.publish({"type": "state", "run": db.get_run(run_id)})
        except (_Cancelled, agents.AgentCancelled):
            # agents 那边中止抛的是它自己的 AgentCancelled，不接住就会掉进下面的
            # 通用分支：记成 failed、错误消息是空串，界面上只剩一个没有原因的的红点
            step["status"] = "cancelled"
            db.update_run(run_id, steps=steps)
            bus.publish({"type": "state", "run": db.get_run(run_id)})
        except Exception as e:
            step["status"] = "failed"
            step["msg"] = str(e)[:400]
            db.update_run(run_id, steps=steps)
            bus.publish({"type": "error", "index": index, "message": str(e)[:400]})
            bus.publish({"type": "state", "run": db.get_run(run_id)})

    threading.Thread(target=_thread, daemon=True, name=f"ff-rev-{run_id}").start()
    return {"ok": True}


# ==================== 提示词预览（编排页「看看这一步实际发什么」） ====================
def preview_step_prompt(pipeline_name: str, index: int, brief: str = "") -> dict:
    p = db.get_pipeline(pipeline_name)
    if not p:
        raise ValueError("流程不存在")
    run = {"id": "run-preview0000", "label": p.get("label") or pipeline_name,
           "pipeline": pipeline_name, "brief": brief,
           "steps": _snapshot_steps(p)}
    system_text, user_text = build_step_prompt(run, index)
    return {"system": system_text, "user": user_text,
            "engine": (p["steps"][index].get("engine")
                       or db.get_setting("default_engine") or "")}

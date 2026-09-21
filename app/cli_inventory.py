# -*- coding: utf-8 -*-
"""只读盘点两家 CLI（claude / codex）自己的配置面。

为什么只读：这些文件里就是真密钥 —— ~/.claude/settings.json 的 env、~/.claude.json
的 oauthAccount、~/.codex/config.toml 的 experimental_bearer_token。schema 也不归我们，
版本一升级字段就会变（codex 把 wire_api="chat" 直接判死就是眼前例子）。
所以这里只取"名字、条数、路径"三样，值一律不解析、不回传；
要改，请用户走各自的官方入口（claude mcp add / codex mcp add / /plugin）。
"""
import json
import re
import sys
from pathlib import Path

HOME = Path.home()

# 两个引擎都按这一份清单出行 —— 缺的类目也出行（found=False），
# 切换引擎时行集合不变，界面才不会一会儿多一会儿少。
CATS = ("memory", "skills", "commands", "agents", "mcp", "hooks", "plugins")


def _item(key, path, entries=(), note=""):
    """entries 只装 {name, bytes}。构造时就不给值留位置，比事后过滤可靠。"""
    entries = sorted([{"name": str(e["name"]), "bytes": int(e.get("bytes") or 0)}
                      for e in entries], key=lambda e: e["name"])
    return {"key": key, "path": str(path).replace("\\", "/"),
            "found": bool(Path(path).exists()), "count": len(entries),
            "entries": entries, "note": note}


def _dir_entries(root: Path, want_md=False):
    """列目录里的技能/命令。技能认 <name>/SKILL.md，命令认 <name>.md。"""
    out = []
    if not root.is_dir():
        return out
    for p in sorted(root.iterdir()):
        if p.is_dir() and (p / "SKILL.md").is_file():
            out.append({"name": p.name, "bytes": (p / "SKILL.md").stat().st_size})
        elif want_md and p.is_file() and p.suffix == ".md":
            out.append({"name": p.stem, "bytes": p.stat().st_size})
    return out


def _json_keys(path: Path, walk=None):
    """只回 JSON 里某几层的键名。值一律不碰：解析出来也不带进返回值。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    return walk(data) if walk else list(data)


def _claude_mcp(data: dict):
    names = list((data.get("mcpServers") or {}))
    for proj in (data.get("projects") or {}).values():
        if isinstance(proj, dict):
            names += list((proj.get("mcpServers") or {}))
    return [{"name": n, "bytes": 0} for n in set(names)]


def _claude_plugins(data: dict):
    """插件只认那几个容器键。按"名字里带 Plugin/Marketplace"筛会把
    officialMarketplaceAutoInstalled 这类记账布尔当成插件 —— 真机上就是这么误判的。"""
    out = []
    for k in ("enabledPlugins", "plugins", "installedPlugins"):
        v = data.get(k)
        if isinstance(v, dict):
            out += [str(x) for x in v]
        elif isinstance(v, list):
            out += [str(x) for x in v if isinstance(x, str)]
    return out


def _toml_sections(path: Path):
    """扫 config.toml 的段名。逐行只取 [..] 里那一串，等号后面的东西根本不进内存。"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    out = []
    for m in re.finditer(r"^\s*\[([^\]]+)\]", text, re.M):
        out.append(m.group(1).strip().strip('"'))
    return out


def _toml_top_keys(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    return [m.group(1) for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", text, re.M)]


def scan_for(engine: str) -> dict:
    engine = (engine or "").strip().lower()
    if engine == "claude":
        return _scan_claude()
    if engine == "codex":
        return _scan_codex()
    return {"engine": engine, "home": "", "items": []}


def _scan_claude() -> dict:
    root = HOME / ".claude"
    cfg = HOME / ".claude.json"
    items = [
        _item("memory", root / "CLAUDE.md",
              [{"name": "CLAUDE.md", "bytes": (root / "CLAUDE.md").stat().st_size}]
              if (root / "CLAUDE.md").is_file() else ()),
        _item("skills", root / "skills", _dir_entries(root / "skills")),
        _item("commands", root / "commands", _dir_entries(root / "commands", want_md=True)),
        _item("agents", root / "agents", _dir_entries(root / "agents", want_md=True)),
        _item("mcp", cfg, _json_keys(cfg, _claude_mcp) if cfg.is_file() else ()),
    ]
    hooks = []
    for f in ("settings.json", "settings.local.json"):
        names = _json_keys(root / f, lambda d: list((d.get("hooks") or {})))
        hooks += [{"name": n, "bytes": 0} for n in names]
    items.append(_item("hooks", root / "settings.json",
                       {h["name"]: h for h in hooks}.values(),
                       "settings.json 与 settings.local.json"))
    plugs = _dir_entries(root / "plugins", want_md=True)
    if cfg.is_file():
        plugs += [{"name": n, "bytes": 0} for n in _json_keys(cfg, _claude_plugins)]
    items.append(_item("plugins", root / "plugins", plugs))
    return {"engine": "claude", "home": str(root).replace("\\", "/"), "items": items}


def _scan_codex() -> dict:
    root = HOME / ".codex"
    cfg = root / "config.toml"
    secs = _toml_sections(cfg)
    # [mcp_servers.node_repl.env] 是那一台的子段，不是第二台服务器 —— 只收恰好一层的
    mcp = [{"name": s.split(".", 1)[1], "bytes": 0} for s in secs
           if s.startswith("mcp_servers.") and "." not in s.split(".", 1)[1]]
    # 段名原样留着（只去引号）：plugins.x@y 与 marketplaces.z 是两种东西，
    # 削掉前缀在界面上就分不出来了。
    plugs = [{"name": s.replace('"', ""), "bytes": 0} for s in secs
             if s.startswith("plugins.") or s.startswith("marketplaces.")]
    hooks = [{"name": k, "bytes": 0} for k in _toml_top_keys(cfg) if k == "notify"]
    items = [
        _item("memory", root / "AGENTS.md",
              [{"name": "AGENTS.md", "bytes": (root / "AGENTS.md").stat().st_size}]
              if (root / "AGENTS.md").is_file() else ()),
        _item("skills", root / "skills", _dir_entries(root / "skills")),
        _item("commands", root / "prompts", _dir_entries(root / "prompts", want_md=True)),
        _item("agents", root / "agents", _dir_entries(root / "agents", want_md=True)),
        _item("mcp", cfg, mcp),
        _item("hooks", cfg, hooks, "codex 的 notify 钩子（值不回传）"),
        _item("plugins", cfg, plugs),
    ]
    return {"engine": "codex", "home": str(root).replace("\\", "/"), "items": items}


def scan() -> dict:
    return {"claude": scan_for("claude"), "codex": scan_for("codex")}


def reveal_path(engine: str, key: str):
    """给 /api/reveal 用：路径由这份清单自己算，调用方只能挑引擎和类目键。"""
    if key not in CATS:
        return None
    for it in scan_for(engine)["items"]:
        if it["key"] == key and it["found"]:
            return Path(it["path"])
    return None


# 只有这四类是"用户写的 markdown"，可以预览正文；mcp / hooks / plugins 的值里
# 可能就是密钥（本机 ~/.claude/settings.json 的 env、config.toml 的 bearer token），
# 所以那三类连预览口都不开。
PREVIEWABLE = ("memory", "skills", "commands", "agents")
_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-.]{0,63}")


def preview_path(engine: str, key: str, name: str = ""):
    """路径只从这份清单里算：调用方给的是 引擎 + 类目 + 条目名，不是路径。"""
    if key not in PREVIEWABLE:
        return None
    item = next((i for i in scan_for(engine)["items"] if i["key"] == key), None)
    if not item or not item["found"]:
        return None
    base = Path(item["path"])
    if key == "memory":
        return base if base.is_file() and base.suffix == ".md" else None
    if not name or not _NAME_RE.fullmatch(name):
        return None
    p = (base / name / "SKILL.md") if key == "skills" else (base / (name + ".md"))
    return p if p.is_file() else None


def preview_text(engine: str, key: str, name: str = "", max_bytes: int = 200_000):
    p = preview_path(engine, key, name)
    if not p:
        return None
    raw = p.read_bytes()[:max_bytes + 1]
    cut = len(raw) > max_bytes
    return {"engine": engine, "key": key, "name": name,
            "path": str(p).replace("\\", "/"),
            "text": raw[:max_bytes].decode("utf-8", errors="ignore"),
            "truncated": cut}

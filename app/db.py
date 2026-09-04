# -*- coding: utf-8 -*-
"""SQLite 数据层：工作流 / 作业 / 设置。"""
import sqlite3, json, time
from pathlib import Path
from . import paths

DB_DIR = paths.DB_DIR
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "modex.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS workflows(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        template TEXT NOT NULL,          -- competition / research / academic / from_assets / one_shot / ipr
        step TEXT NOT NULL,              -- 当前自动流水线标识
        status TEXT NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed/paused
        progress INTEGER NOT NULL DEFAULT 0,
        config TEXT NOT NULL DEFAULT '{}',   -- 前端保存的表单配置 JSON
        steps TEXT NOT NULL DEFAULT '{}',    -- 各步骤状态 JSON
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""")
    # API 预设库（Provider / Config，仿 cc-switch）
    c.execute("""CREATE TABLE IF NOT EXISTS api_presets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,        -- 预设名（展示 / 运行时按名引用）
        provider TEXT NOT NULL DEFAULT 'openai',  -- openai | anthropic
        api_base TEXT NOT NULL DEFAULT '',
        api_key TEXT NOT NULL DEFAULT '',
        model TEXT NOT NULL DEFAULT '',
        is_default INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    # 提示词定制库：每个流水线步骤可追加/替换其 SKILL.md（空=跟随原版）
    c.execute("""CREATE TABLE IF NOT EXISTS skill_overrides(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template TEXT NOT NULL,             -- 流水线模板（competition / paper_writing…）
        step_key TEXT NOT NULL,             -- 步骤键（analysis / modeling…）
        skill TEXT NOT NULL DEFAULT '',     -- 冗余记录 skill 名便于展示
        extra_prompt TEXT NOT NULL DEFAULT '',  -- 追加提示词（拼在原版之后）
        replace_prompt TEXT NOT NULL DEFAULT '',-- 完全替换（优先于 extra；空=不替换）
        updated_at TEXT NOT NULL,
        UNIQUE(template, step_key)
    )""")
    # 0.5.3 迁移：api_presets 增加高级选项列（幂等：列已存在则忽略）
    cols = [r[1] for r in c.execute("PRAGMA table_info(api_presets)").fetchall()]
    if "extra" not in cols:
        c.execute("ALTER TABLE api_presets ADD COLUMN extra TEXT NOT NULL DEFAULT '{}'")
    # 图片生成预设库（独立于对话 api_presets；自定义配置，不做供应商目录）
    c.execute("""CREATE TABLE IF NOT EXISTS image_presets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        api_base TEXT NOT NULL DEFAULT '',
        api_key TEXT NOT NULL DEFAULT '',
        model TEXT NOT NULL DEFAULT '',
        extra TEXT NOT NULL DEFAULT '{}',
        is_default INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    _img_cols = [r[1] for r in c.execute("PRAGMA table_info(image_presets)").fetchall()]
    if "extra" not in _img_cols:
        c.execute("ALTER TABLE image_presets ADD COLUMN extra TEXT NOT NULL DEFAULT '{}'")
    # 默认设置（不再硬编码任何 API 地址，模型由 api_presets 决定）
    defaults = {
        "themes": "亮白",
        "gpt_image_key": "",
        "claude_cli": "",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", (k, v))
    conn.commit(); conn.close()

def _row(r):
    if r is None: return None
    d = dict(r)
    d["config"] = json.loads(d["config"])
    d["steps"] = json.loads(d["steps"])
    return d

def create_workflow(title, template, step, config):
    conn = get_conn(); c = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO workflows(title,template,step,status,config,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
              (title, template, step, "pending", json.dumps(config, ensure_ascii=False), now, now))
    wid = c.lastrowid; conn.commit(); conn.close()
    return wid

def list_workflows():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM workflows ORDER BY id DESC")]
    conn.close()
    for r in rows:
        r["config"] = json.loads(r["config"])
        r["steps"] = json.loads(r["steps"])
    return rows

def get_workflow(wid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM workflows WHERE id=?", (wid,)).fetchone()
    conn.close()
    return _row(r)

def update_workflow(wid, **fields):
    if not fields: return
    fields["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    # SQLite 不支持 dict/list 绑定：自动 JSON 序列化（steps 等字段）
    for k, v in list(fields.items()):
        if isinstance(v, (dict, list)):
            fields[k] = json.dumps(v, ensure_ascii=False)
    conn = get_conn(); c = conn.cursor()
    sets = ", ".join(f'"{k}"=?' for k in fields)
    c.execute(f"UPDATE workflows SET {sets} WHERE id=?", (*fields.values(), wid))
    conn.commit(); conn.close()

def delete_workflow(wid):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM workflows WHERE id=?", (wid,))
    conn.commit(); conn.close()

# settings 内存缓存：读多写少，避免高频路径（作业进度循环等）反复开库连接
_MISS = object()
_SETTING_CACHE: dict = {}


def set_setting(key, value):
    _SETTING_CACHE.pop(key, None)   # 失效缓存，下次读取重新落库为准
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.commit(); conn.close()

def get_setting(key, default=""):
    v = _SETTING_CACHE.get(key, _MISS)
    if v is not _MISS:
        return v
    conn = get_conn()
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    v = r["value"] if r else default
    _SETTING_CACHE[key] = v
    return v

def get_all_settings():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT key,value FROM settings")]
    conn.close()
    d = {r["key"]: r["value"] for r in rows}
    _SETTING_CACHE.update(d)        # 全量回填缓存
    return d

# ---------------- API 预设库 ----------------
def preset_to_dict(r):
    if r is None: return None
    d = dict(r)
    d["is_default"] = bool(d.get("is_default"))
    try:
        d["extra"] = json.loads(d.get("extra") or "{}")
    except Exception:
        d["extra"] = {}
    return d

def list_presets():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM api_presets ORDER BY is_default DESC, id ASC").fetchall()
    conn.close()
    return [preset_to_dict(r) for r in rows]

def get_preset(pid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM api_presets WHERE id=?", (pid,)).fetchone()
    conn.close()
    return preset_to_dict(r)

def get_preset_by_name(name):
    conn = get_conn()
    r = conn.execute("SELECT * FROM api_presets WHERE name=?", (name,)).fetchone()
    conn.close()
    return preset_to_dict(r)

def get_default_preset():
    conn = get_conn()
    r = conn.execute("SELECT * FROM api_presets WHERE is_default=1 ORDER BY id ASC LIMIT 1").fetchone()
    conn.close()
    return preset_to_dict(r)

def add_preset(name, provider="openai", api_base="", api_key="", model="", extra=None):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    extra_json = json.dumps(extra or {}, ensure_ascii=False)
    conn = get_conn(); c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(api_presets)").fetchall()]
    if "extra" in cols:
        c.execute("""INSERT INTO api_presets(name,provider,api_base,api_key,model,extra,is_default,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,0,?,?)""",
                  (name, provider, api_base, api_key, model, extra_json, now, now))
    else:
        c.execute("""INSERT INTO api_presets(name,provider,api_base,api_key,model,is_default,created_at,updated_at)
                     VALUES(?,?,?,?,?,0,?,?)""",
                  (name, provider, api_base, api_key, model, now, now))
    pid = c.lastrowid
    if len(c.execute("SELECT COUNT(*) c FROM api_presets WHERE is_default=1").fetchone()) == 0:
        c.execute("UPDATE api_presets SET is_default=1, updated_at=? WHERE id=?", (now, pid))
    conn.commit(); conn.close()
    return pid

def update_preset(pid, name=None, provider=None, api_base=None, api_key=None, model=None, extra=None):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    p = get_preset(pid)
    if not p: return False
    fields = {
        "name": name if name is not None else p["name"],
        "provider": provider if provider is not None else p["provider"],
        "api_base": api_base if api_base is not None else p["api_base"],
        "api_key": api_key if api_key is not None else p["api_key"],
        "model": model if model is not None else p["model"],
    }
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE api_presets SET name=?, provider=?, api_base=?, api_key=?, model=?, updated_at=? WHERE id=?",
              (fields["name"], fields["provider"], fields["api_base"], fields["api_key"],
               fields["model"], now, pid))
    if extra is not None:
        cols = [r[1] for r in c.execute("PRAGMA table_info(api_presets)").fetchall()]
        if "extra" in cols:
            c.execute("UPDATE api_presets SET extra=?, updated_at=? WHERE id=?",
                      (json.dumps(extra, ensure_ascii=False), now, pid))
    conn.commit(); conn.close()
    return True

def set_default_preset(pid):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE api_presets SET is_default=0")
    c.execute("UPDATE api_presets SET is_default=1, updated_at=? WHERE id=?", (now, pid))
    conn.commit(); conn.close()

def delete_preset(pid):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM api_presets WHERE id=?", (pid,))
    conn.commit(); conn.close()
# ---------------- 提示词定制（skill_overrides） ----------------
def get_skill_override(template, step_key):
    conn = get_conn()
    r = conn.execute("SELECT * FROM skill_overrides WHERE template=? AND step_key=?",
                     (template, step_key)).fetchone()
    conn.close()
    return dict(r) if r else None

def set_skill_override(template, step_key, skill, extra_prompt, replace_prompt=""):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn(); c = conn.cursor()
    c.execute("""INSERT INTO skill_overrides(template,step_key,skill,extra_prompt,replace_prompt,updated_at)
                 VALUES(?,?,?,?,?,?)
                 ON CONFLICT(template,step_key) DO UPDATE SET
                   skill=excluded.skill,
                   extra_prompt=excluded.extra_prompt,
                   replace_prompt=excluded.replace_prompt,
                   updated_at=excluded.updated_at""",
              (template, step_key, skill or "", extra_prompt or "", replace_prompt or "", now))
    conn.commit(); conn.close()
    return True


# 模块加载时即建表：保证任何模块在 import db 后立即可查询（jobs.py 模块级
# 会直接 db.get_setting，而 app.main 的 init_db() 在其 import jobs 之后才执行）
init_db()

def clear_skill_override(template, step_key):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM skill_overrides WHERE template=? AND step_key=?", (template, step_key))
    conn.commit(); conn.close()

def list_skill_overrides():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM skill_overrides ORDER BY id")]
    conn.close()
    return rows

# ---------------- 图片生成预设库（image_presets） ----------------
def _img_row(r):
    if r is None:
        return None
    d = dict(r)
    d["is_default"] = bool(d.get("is_default"))
    try:
        d["extra"] = json.loads(d.get("extra") or "{}")
    except Exception:
        d["extra"] = {}
    return d

def list_image_presets():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM image_presets ORDER BY is_default DESC, id ASC")]
    conn.close()
    return [_img_row(r) for r in rows]

def get_image_preset(pid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM image_presets WHERE id=?", (pid,)).fetchone()
    conn.close()
    return _img_row(r)

def get_default_image_preset():
    conn = get_conn()
    r = conn.execute("SELECT * FROM image_presets WHERE is_default=1 ORDER BY id ASC LIMIT 1").fetchone()
    conn.close()
    return _img_row(r)

def get_image_preset_by_name(name):
    conn = get_conn()
    r = conn.execute("SELECT * FROM image_presets WHERE name=?", (name,)).fetchone()
    conn.close()
    return _img_row(r)

def add_image_preset(name, api_base="", api_key="", model="", extra=None):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    extra_json = json.dumps(extra or {}, ensure_ascii=False)
    conn = get_conn(); c = conn.cursor()
    c.execute("""INSERT INTO image_presets(name,api_base,api_key,model,extra,is_default,created_at,updated_at)
                 VALUES(?,?,?,?,?,0,?,?)""",
              (name, api_base, api_key, model, extra_json, now, now))
    pid = c.lastrowid
    # 首个预设自动设为默认
    if c.execute("SELECT COUNT(*) c FROM image_presets WHERE is_default=1").fetchone()[0] == 0:
        c.execute("UPDATE image_presets SET is_default=1 WHERE id=?", (pid,))
    conn.commit(); conn.close()
    return pid

def update_image_preset(pid, name=None, api_base=None, api_key=None, model=None, extra=None):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    p = get_image_preset(pid)
    if not p:
        return False
    fields = {
        "name": name if name is not None else p["name"],
        "api_base": api_base if api_base is not None else p["api_base"],
        "api_key": api_key if api_key is not None else p["api_key"],
        "model": model if model is not None else p["model"],
        "extra": json.dumps(extra, ensure_ascii=False) if extra is not None else json.dumps(p.get("extra") or {}, ensure_ascii=False),
    }
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE image_presets SET name=?, api_base=?, api_key=?, model=?, extra=?, updated_at=? WHERE id=?",
              (fields["name"], fields["api_base"], fields["api_key"], fields["model"], fields["extra"], now, pid))
    conn.commit(); conn.close()
    return True

def set_default_image_preset(pid):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE image_presets SET is_default=0")
    c.execute("UPDATE image_presets SET is_default=1, updated_at=? WHERE id=?", (now, pid))
    conn.commit(); conn.close()

def delete_image_preset(pid):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM image_presets WHERE id=?", (pid,))
    conn.commit(); conn.close()

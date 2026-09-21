# -*- coding: utf-8 -*-
"""流程模板：校验 / 名称规范化（模板 CRUD 走 db.py，内置模板由 presets_library 播种）。"""
import re

from . import agents

STEP_FIELDS = ("key", "label", "skill", "out", "checkpoint", "role", "engine",
               "model", "extra_prompt")


def validate_steps(steps):
    """校验步骤清单合法性。返回 (ok, error)。"""
    if not isinstance(steps, list):
        return False, "steps 必须是数组"
    if not steps:
        return False, "至少需要 1 个步骤"
    keys = set()
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            return False, f"第 {i+1} 步必须是对象"
        key = str(s.get("key") or "").strip()
        if not key:
            return False, f"第 {i+1} 步缺少 key"
        if not re.match(r"^[a-zA-Z0-9_-]+$", key):
            return False, f"第 {i+1} 步 key「{key}」只能含字母数字下划线连字符"
        if key in keys:
            return False, f"步骤 key「{key}」重复"
        keys.add(key)
        if not str(s.get("label") or "").strip():
            return False, f"第 {i+1} 步「{key}」缺少名称(label)"
        if not str(s.get("skill") or "").strip():
            return False, f"第 {i+1} 步「{key}」缺少 skill"
        eng = str(s.get("engine") or "").strip()
        if eng and eng not in agents.ENGINES:
            return False, f"第 {i+1} 步「{key}」引擎「{eng}」无效（可选：{' / '.join(agents.ENGINES)}，留空=跟随全局默认）"
    return True, ""


def normalize_steps(steps):
    """把外部传入的步骤裁剪成固定字段并补齐默认值（避免脏字段进库）。"""
    out = []
    for i, s in enumerate(steps or []):
        if not isinstance(s, dict):
            continue
        role = str(s.get("role") or "executor").strip()
        out.append({
            "key": str(s.get("key") or f"step{i+1}").strip(),
            "label": str(s.get("label") or "").strip(),
            "skill": str(s.get("skill") or "").strip(),
            # 技能从哪个目录来："" = Loom 自己那份；claude / codex = CLI 自带的那一处。
            # 只认这三个值：别的写法（路径、引擎别名）一律清成空，别让它进提示词。
            "skill_src": str(s.get("skill_src") or "").strip()
                         if str(s.get("skill_src") or "").strip() in ("", "claude", "codex")
                         else "",
            "out": str(s.get("out") or "").strip(),
            "checkpoint": bool(s.get("checkpoint")),
            "role": role if role in ("executor", "reviewer", "editor") else "executor",
            "engine": str(s.get("engine") or "").strip(),
            "model": str(s.get("model") or "").strip(),
            "extra_prompt": str(s.get("extra_prompt") or "").strip(),
        })
    return out


def normalize_name(raw):
    """模板名规范化：小写 + 短横线，去掉首尾连字符/下划线。返回 (name, ok)"""
    s = (raw or "").strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9_-]", "", s).strip("-_")
    if not s:
        return "", False
    return s, True

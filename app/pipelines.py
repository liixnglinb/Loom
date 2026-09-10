# -*- coding: utf-8 -*-
"""流程模板：校验 / 名称规范化（模板 CRUD 走 db.py，无内置 seed —— 全部由用户创建）。"""
import re


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
    return True, ""


def normalize_name(raw):
    """模板名规范化：小写 + 短横线，去掉首尾连字符/下划线。返回 (name, ok)"""
    s = (raw or "").strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9_-]", "", s).strip("-_")
    if not s:
        return "", False
    return s, True

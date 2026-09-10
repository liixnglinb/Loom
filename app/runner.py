# -*- coding: utf-8 -*-
"""流程执行引擎：按步骤清单依次调用 LLM（流式），产物写入工作区。

设计：
- 一次运行 = 一个后台线程 + 一个事件队列（SSE 消费）
- 步骤输入 = 任务指令 + 上一步产物（可达产物摘要）+ 技能规范
- 检查点：步骤完成后 run 转 waiting，等用户 continue
- 局部修订：挂起/完成后对指定步骤产物发起对话式修改，改完写回工作区
- 取消：置 cancel_flag，步骤间隙退出
"""
import json
import threading
import time
import uuid
from pathlib import Path

from . import db, llm, paths

# run_id -> 队列管理器（内存态；进程重启后 runs 表仍在，但事件流从当前状态重建）
_BUSES: dict = {}
_BUS_LOCK = threading.Lock()
_CANCEL: set = set()


def _norm_run_id(rid: str) -> str | None:
    import re
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
            # 事件历史限长（流式 delta 很多），全量快照靠 state 事件兜底
            if len(self.history) > 4000:
                self.history = self.history[-3000:]
            for q in self.subs:
                q.append(ev)

    def subscribe(self) -> list[dict]:
        """新订阅者只收订阅之后的事件；此前的状态由 snapshot_events 的 state 打底。"""
        q: list[dict] = []
        with self.lock:
            self.subs.append(q)
        return q

    def unsubscribe(self, q: list[dict]):
        with self.lock:
            if q in self.subs:
                self.subs.remove(q)

    def snapshot_events(self) -> list[dict]:
        """把当前状态压成一条 state 事件（SSE 断线重连/晚订阅兜底）。"""
        run = db.get_run(self.run_id)
        if not run:
            return [{"type": "state", "run": None}]
        arts = read_artifacts(run)
        return [{"type": "state", "run": run, "artifacts": arts}]


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
def workspace_dir(run_id: str) -> Path:
    d = paths.WORKSPACES_DIR / f"run-{run_id}" if not str(run_id).startswith("run-") \
        else paths.WORKSPACES_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_out_name(out: str) -> str | None:
    import re
    out = (out or "").strip()
    if not out or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", out):
        return None
    return out


def read_artifacts(run: dict) -> dict:
    """读取工作区全部产物文件（步骤 out 与额外文件），返回 {文件名: 内容}。"""
    out = {}
    ws = workspace_dir(run["id"])
    names = set()
    for s in run.get("steps") or []:
        n = _safe_out_name(s.get("out") or "")
        if n:
            names.add(n)
    for f in sorted(ws.glob("*")):
        if f.is_file() and f.suffix.lower() in (".md", ".txt", ".json", ".csv", ".tex"):
            names.add(f.name)
    for n in names:
        try:
            out[n] = (ws / n).read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return out



class _Cancelled(Exception):
    pass


def _guard_stream(stream, run_id: str):
    """包一层流：取消时抛 _Cancelled，保证调用方能感知中断。"""
    for chunk in stream:
        if is_cancelled(run_id):
            raise _Cancelled()
        yield chunk


# ==================== 提示词组装 ====================
_ROLE_HINT = {
    "executor": "你是执行者：按技能规范高质量完成本步任务，直接产出结果正文。",
    "reviewer": "你是检查者：审阅上一步产物，指出问题并给出结构化的修改意见清单（不要重写全文）。",
    "editor": "你是润色者：在既有产物基础上做编辑改进，输出改进后的完整文稿。",
}


def _skill_text(skill_name: str) -> str:
    d = paths.USER_SKILLS_DIR / (skill_name or "")
    md = d / "SKILL.md"
    if md.is_file():
        try:
            return md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return ""


def _refs_text(skill_name: str, limit=6000) -> str:
    """技能附属文件（references/ scripts/）拼成附录，供模型参考。"""
    d = paths.USER_SKILLS_DIR / (skill_name or "") / "references"
    if not d.is_dir():
        return ""
    parts, total = [], 0
    for f in sorted(d.rglob("*")):
        if not (f.is_file() and f.suffix.lower() in (".md", ".txt")):
            continue
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        seg = f"\n#### 附属文件 {f.name}\n\n{t}\n"
        if total + len(seg) > limit:
            seg = seg[:limit - total] + "\n…(截断)"
        parts.append(seg)
        total += len(seg)
        if total >= limit:
            break
    return "".join(parts)


def build_step_messages(run: dict, step_idx: int, artifacts: dict, extra_instruction: str = "") -> list:
    """组装一步的对话消息。step_idx 为步骤下标，上游产物取它之前的步骤。"""
    steps = run.get("steps") or []
    step = steps[step_idx]
    prev_out = []
    for s in steps[:step_idx]:
        n = _safe_out_name(s.get("out") or "")
        if n and n in artifacts:
            body = artifacts[n]
            if len(body) > 9000:
                body = body[:9000] + "\n…(前序产物截断)"
            prev_out.append(f"### 前序产物「{s.get('label') or s.get('key')}」（文件 {n}）\n\n{body}")
    skill_body = _skill_text(step.get("skill"))
    refs = _refs_text(step.get("skill"))
    user_parts = []
    if run.get("label"):
        user_parts.append(f"## 任务背景\n本流程：{run['label']}")
    user_parts.append(f"## 当前步骤（{step.get('label') or step.get('key')}）\n"
                      f"角色：{_ROLE_HINT.get(step.get('role') or 'executor', _ROLE_HINT['executor'])}")
    if skill_body:
        user_parts.append(f"## 技能规范（{step.get('skill')}）\n\n{skill_body[:12000]}")
    if refs:
        user_parts.append(f"## 技能附属资料\n{refs}")
    if prev_out:
        user_parts.append("## 上游产物\n" + "\n\n".join(prev_out[-2:]))  # 最近两步足够
    if step.get("out"):
        user_parts.append(f"## 输出要求\n把最终结果直接写成完整正文，末尾不要附加说明。"
                          f"正文将保存为文件 {step['out']}。")
    if extra_instruction:
        user_parts.append(f"## 补充指令\n{extra_instruction}")
    return [{"role": "user", "content": "\n\n---\n\n".join(user_parts)}]


def _resolve_llm(step: dict):
    """本步模型：步级预设名 > 默认预设。返回 (provider, base, key, model) 或 None。"""
    preset = None
    pname = (step.get("model") or "").strip()
    if pname:
        preset = db.get_preset_by_name(pname)
    if not preset:
        preset = db.get_default_preset()
    if not preset:
        return None
    return (preset.get("provider") or "openai", preset.get("api_base") or "",
            preset.get("api_key") or "", preset.get("model") or "")


# ==================== 执行线程 ====================
def _save_step_output(run_id: str, step: dict, text: str):
    n = _safe_out_name(step.get("out") or "")
    if n:
        (workspace_dir(run_id) / n).write_text(text, encoding="utf-8")


def _run_thread(run_id: str, start_step: int = 0):
    bus = bus_for(run_id)
    try:
        run = db.get_run(run_id)
        if not run:
            return
        if start_step == 0:
            db.update_run(run_id, status="running", waiting_reason="", error="", cur_step=0)
            bus.publish({"type": "state", "run": db.get_run(run_id)})
        steps = run.get("steps") or []
        for idx in range(start_step, len(steps)):
            if is_cancelled(run_id):
                db.update_run(run_id, status="cancelled")
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
            step = steps[idx]
            step["status"] = "running"
            db.update_run(run_id, cur_step=idx, steps=steps)
            bus.publish({"type": "step_start", "index": idx, "step": step})
            conf = _resolve_llm(step)
            if not conf:
                step["status"] = "failed"
                db.update_run(run_id, status="failed",
                              error=f"第 {idx+1} 步无法解析模型预设（请到设置页添加 API 预设并设为默认）",
                              steps=steps)
                bus.publish({"type": "error", "message": "未找到可用的 API 预设"})
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
            provider, base, key, model = conf
            artifacts = read_artifacts(db.get_run(run_id))
            messages = build_step_messages(db.get_run(run_id), idx, artifacts)
            buf = []
            try:
                for delta in _guard_stream(llm.chat_stream(provider, base, key, model, messages,
                                                           temperature=0.6, max_tokens=8000), run_id):
                    buf.append(delta)
                    step["delta"] = (step.get("delta") or "") + delta
                    bus.publish({"type": "delta", "index": idx, "text": delta})
            except _Cancelled:
                step["status"] = "cancelled"
                partial = "".join(buf)
                if partial.strip():
                    _save_step_output(run_id, step, partial + "\n\n(用户中止)")
                db.update_run(run_id, status="cancelled", steps=steps)
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
            except llm.LLMError as e:
                step["status"] = "failed"
                db.update_run(run_id, status="failed", error=f"第 {idx+1} 步：{e}", steps=steps)
                bus.publish({"type": "error", "index": idx, "message": str(e)})
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
            text = "".join(buf)
            step["status"] = "done"
            step["delta"] = text
            step["chars"] = len(text)
            _save_step_output(run_id, step, text)
            db.update_run(run_id, steps=steps)
            bus.publish({"type": "step_done", "index": idx, "step": step, "chars": len(text)})
            # 检查点：挂起等确认
            if step.get("checkpoint") and idx < len(steps) - 1:
                db.update_run(run_id, status="waiting", waiting_reason="checkpoint", cur_step=idx + 1)
                bus.publish({"type": "checkpoint", "index": idx})
                bus.publish({"type": "state", "run": db.get_run(run_id)})
                return
        run = db.get_run(run_id)
        db.update_run(run_id, status="done", cur_step=len(steps))
        bus.publish({"type": "state", "run": db.get_run(run_id)})
        bus.publish({"type": "done"})
    except Exception as e:  # 兜底：不让线程静默死掉
        try:
            db.update_run(run_id, status="failed", error=str(e)[:500])
            bus.publish({"type": "error", "message": str(e)})
            bus.publish({"type": "state", "run": db.get_run(run_id)})
        except Exception:
            pass
    finally:
        _CANCEL.discard(run_id)


def start_run(pipeline_name: str, label: str = "") -> dict:
    """创建运行实例并启动线程。返回 run。"""
    p = db.get_pipeline(pipeline_name)
    if not p:
        raise ValueError(f"流程「{pipeline_name}」不存在")
    steps = []
    for s in (p.get("steps") or []):
        steps.append({**s, "status": "pending"})
        steps[-1].pop("delta", None)
    run_id = new_run_id()
    run = db.create_run(run_id, pipeline_name, label or p.get("label") or pipeline_name, steps)
    threading.Thread(target=_run_thread, args=(run_id, 0), daemon=True,
                     name=f"ff-run-{run_id}").start()
    return run


def resume_run(run_id: str) -> dict:
    """检查点后继续执行。"""
    run = db.get_run(run_id)
    if not run:
        raise ValueError("运行不存在")
    if run["status"] not in ("waiting",):
        raise ValueError(f"当前状态 {run['status']} 不可继续")
    _CANCEL.discard(run_id)
    threading.Thread(target=_run_thread, args=(run_id, run["cur_step"]), daemon=True,
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


# ==================== 局部修订（对话式改指定产物） ====================
def revise_step(run_id: str, index: int, instruction: str, sync: bool = False) -> dict:
    """对第 index 步产物发起对话式局部修改。

    sync=True 时同步执行（阻塞返回新全文）；False 时走事件流（revision_start/delta/done）。
    修改结果直接写回工作区产物文件。
    """
    run = db.get_run(run_id)
    if not run:
        raise ValueError("运行不存在")
    steps = run.get("steps") or []
    if index < 0 or index >= len(steps):
        raise ValueError("步骤序号无效")
    step = steps[index]
    out_name = _safe_out_name(step.get("out") or "")
    ws = workspace_dir(run_id)
    old_text = (ws / out_name).read_text(encoding="utf-8", errors="replace") if out_name and (ws / out_name).exists() else ""
    conf = _resolve_llm(step)
    if not conf:
        raise llm.LLMError("未找到可用的 API 预设")
    provider, base, key, model = conf
    messages = [
        {"role": "system", "content":
            "你是文档修改助手。用户会给出一篇文档全文和修改要求，"
            "你输出修改后的【完整文档全文】，不要输出解释、对比或代码块包裹。"
            "保持未提及部分原样，只改用户要求的位置。"},
        {"role": "user", "content":
            f"# 文档全文\n\n{old_text or '（该步骤暂无产物）'}\n\n---\n\n# 修改要求\n\n{instruction}"},
    ]
    bus = bus_for(run_id)

    def _emit_status():
        db.update_run(run_id, steps=steps)
        bus.publish({"type": "state", "run": db.get_run(run_id)})

    step["status"] = "revising"
    _emit_status()

    def _thread():
        try:
            buf = []
            for delta in _guard_stream(llm.chat_stream(provider, base, key, model, messages,
                                                       temperature=0.4, max_tokens=8000), run_id):
                buf.append(delta)
                bus.publish({"type": "revise_delta", "index": index, "text": delta})
            text = "".join(buf).strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("markdown"):
                    text = text[8:]
                text = text.lstrip("\n")
            if out_name:
                (ws / out_name).write_text(text, encoding="utf-8")
            step["status"] = "done"
            step["delta"] = text
            step["chars"] = len(text)
            step.pop("revising", None)
            db.update_run(run_id, steps=steps)
            bus.publish({"type": "revise_done", "index": index, "chars": len(text)})
            bus.publish({"type": "state", "run": db.get_run(run_id)})
        except _Cancelled:
            step["status"] = "cancelled"
            step.pop("revising", None)
            db.update_run(run_id, steps=steps)
            bus.publish({"type": "state", "run": db.get_run(run_id)})
        except Exception as e:
            step["status"] = "failed" if step.get("status") == "revising" else step.get("status")
            step.pop("revising", None)
            db.update_run(run_id, steps=steps)
            bus.publish({"type": "error", "index": index, "message": str(e)})
            bus.publish({"type": "state", "run": db.get_run(run_id)})

    if sync:
        buf = []
        for delta in llm.chat_stream(provider, base, key, model, messages,
                                     temperature=0.4, max_tokens=8000):
            buf.append(delta)
        text = "".join(buf).strip()
        if out_name:
            (ws / out_name).write_text(text, encoding="utf-8")
        step["status"] = "done"
        step["delta"] = text
        step["chars"] = len(text)
        db.update_run(run_id, steps=steps)
        bus.publish({"type": "revise_done", "index": index, "chars": len(text)})
        bus.publish({"type": "state", "run": db.get_run(run_id)})
        return {"ok": True, "chars": len(text)}

    threading.Thread(target=_thread, daemon=True, name=f"ff-rev-{run_id}").start()
    return {"ok": True}

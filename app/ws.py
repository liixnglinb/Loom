# -*- coding: utf-8 -*-
"""ModelFlow WebSocket 实时推送 — 按工作流隔离（/ws/{wid}）。

工作流执行时通过 ws_manager.broadcast(wid, payload) 推送状态更新，
前端收到后即时重绘，不再依赖轮询。
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class WSManager:
    def __init__(self):
        self._conns: dict[int, set] = defaultdict(set)   # wid -> set[WebSocket]
        self._lock = asyncio.Lock()

    async def connect(self, wid: int, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._conns[wid].add(ws)

    async def disconnect(self, wid: int, ws: WebSocket):
        async with self._lock:
            s = self._conns.get(wid)
            if s:
                s.discard(ws)
                if not s:
                    self._conns.pop(wid, None)

    async def broadcast(self, wid: int, payload: dict):
        """向某工作流的所有连接推送消息。无人订阅时静默跳过。"""
        async with self._lock:
            conns = list(self._conns.get(wid, ()))
        if not conns:
            return
        text = json.dumps(payload, ensure_ascii=False)
        dead = []
        for ws in conns:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                s = self._conns.get(wid)
                for ws in dead:
                    s and s.discard(ws)

    async def broadcast_legacy(self, sender):
        """兼容 worker 线程用法：真正的 async broadcast 见上。"""
        return await self.broadcast(sender[0], sender[1])


manager = WSManager()


@router.websocket("/ws/{wid}")
async def ws_endpoint(ws: WebSocket, wid: int):
    global _MAIN_LOOP
    try:
        _MAIN_LOOP = asyncio.get_running_loop()   # 握手在主 loop 内，趁机记录
    except RuntimeError:
        pass
    await manager.connect(wid, ws)
    try:
        # 首帧主动推送当前状态摘要（前端可据此对齐）
        await ws.send_text(json.dumps(
            {"type": "hello", "wid": wid, "ts": None}, ensure_ascii=False))
        # 仅接收心跳/忽略客户端消息；主要方向是服务端→客户端
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(wid, ws)


# 兼容：worker 线程/非 async 环境通过 loop 调度
# ⛔ 跨线程推送必须调度到「持有连接的那个事件循环」，否则不同 loop 无法互操作。
#    WS 握手时（必在 uvicorn 主 loop 内）记录主循环，之后 worker 线程用它投递。
_MAIN_LOOP = None


def _get_main_loop():
    return _MAIN_LOOP


def push_sync(wid: int, payload: dict):
    """线程安全的跨线程推送：投递到主事件循环执行 broadcast。"""
    global _MAIN_LOOP
    loop = _MAIN_LOOP
    if loop is None:
        # 尚未握手过：尝试取当前（若在 loop 线程内，则即主循环）
        try:
            loop = asyncio.get_running_loop()
            _MAIN_LOOP = loop
        except RuntimeError:
            loop = None
    if loop is not None and loop.is_running():
        try:
            loop.call_soon_threadsafe(lambda: asyncio.ensure_future(manager.broadcast(wid, payload)))
            return
        except Exception:
            pass
    # 无主循环可投递时：静默跳过（无人订阅也无害）
    try:
        asyncio.run(manager.broadcast(wid, payload))
    except Exception:
        pass
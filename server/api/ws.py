"""WebSocket：会话级事件流（与 LangGraph stream 对齐）；协议见 docs/SPEC.md §7.2。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from server.agent.graph import run_agent_streaming
from server.agent.run_context import build_initial_agent_state
from server.agent.state import AgentState
from server.api.event_hub import SessionEventHub, get_event_hub
from server.api.routes import _session_meta, persist_session_state
from server.core.config import get_settings
from server.core.session_store import get_session_store

logger = logging.getLogger(__name__)

router = APIRouter()

WS_EVENT_SCHEMA: dict[str, Any] = {
    "version": 1,
    "events": [
        {"name": "schema", "payload": {"version": "int", "events": "list"}},
        {"name": "ready", "payload": {}},
        {"name": "node_enter", "payload": {"node": "str"}},
        {"name": "node_exit", "payload": {"node": "str", "payload": "object"}},
        {"name": "tool_call", "payload": {"tool": "str", "arguments": "object"}},
        {"name": "tool_result", "payload": {"tool": "str", "ok": "bool", "summary": "object"}},
        {"name": "final", "payload": {"final_answer": "str", "stop_reason": "str"}},
        {"name": "error", "payload": {"message": "str"}},
        {"name": "done", "payload": {}},
    ],
}


def _ensure_run_lock(session_id: str) -> asyncio.Lock:
    meta = _session_meta.get(session_id)
    if not meta:
        raise KeyError(session_id)
    lk = meta.get("run_lock")
    if lk is None:
        lk = asyncio.Lock()
        meta["run_lock"] = lk
    return lk  # type: ignore[return-value]


async def _pump_queue_to_ws(websocket: WebSocket, q: asyncio.Queue[dict[str, Any]]) -> None:
    while True:
        item = await q.get()
        await websocket.send_json(item)


async def _run_streaming_task(
    session_id: str,
    goal: str,
    max_iterations: int,
    hub: SessionEventHub,
    loop: asyncio.AbstractEventLoop,
) -> None:
    lock = _ensure_run_lock(session_id)
    async with lock:
        last_state = _session_meta[session_id].get("last_state")
        initial: AgentState = build_initial_agent_state(
            session_id, goal, max_iterations, last_state
        )

        def emit(ev: dict[str, Any]) -> None:
            ev2 = {**ev, "ts": time.time()}
            fut = asyncio.run_coroutine_threadsafe(hub.publish(session_id, ev2), loop)
            fut.result(timeout=120)

        try:
            out = await asyncio.to_thread(run_agent_streaming, initial, None, emit)
        except Exception as e:  # noqa: BLE001
            logger.exception("run_agent_streaming failed")
            await hub.publish(
                session_id,
                {"event": "error", "session_id": session_id, "message": str(e), "ts": time.time()},
            )
            return
        persist_session_state(session_id, out)
        await hub.publish(
            session_id,
            {
                "event": "final",
                "session_id": session_id,
                "final_answer": out.get("final_answer") or "",
                "stop_reason": out.get("stop_reason") or "",
                "ts": time.time(),
            },
        )
        await hub.publish(session_id, {"event": "done", "session_id": session_id, "ts": time.time()})


@router.websocket("/sessions/{session_id}/ws")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    hub = get_event_hub()
    await websocket.send_json({"event": "schema", "session_id": session_id, **WS_EVENT_SCHEMA})
    await websocket.send_json({"event": "ready", "session_id": session_id})
    q = await hub.register(session_id)
    pump = asyncio.create_task(_pump_queue_to_ws(websocket, q))
    loop = asyncio.get_running_loop()
    active_run: asyncio.Task[None] | None = None
    try:
        while True:
            msg = await websocket.receive_json()
            if msg.get("cmd") != "run":
                await websocket.send_json(
                    {
                        "event": "error",
                        "session_id": session_id,
                        "message": f"未知命令: {msg.get('cmd')!r}",
                        "ts": time.time(),
                    }
                )
                continue
            if active_run and not active_run.done():
                await websocket.send_json(
                    {
                        "event": "error",
                        "session_id": session_id,
                        "message": "已有任务运行中，请等待 done 后再发起",
                        "ts": time.time(),
                    }
                )
                continue
            if session_id not in _session_meta:
                await websocket.send_json(
                    {
                        "event": "error",
                        "session_id": session_id,
                        "message": "会话不存在",
                        "ts": time.time(),
                    }
                )
                continue
            if get_session_store().get(session_id) is None:
                await websocket.send_json(
                    {
                        "event": "error",
                        "session_id": session_id,
                        "message": "请先上传 CSV",
                        "ts": time.time(),
                    }
                )
                continue
            goal = str(msg.get("goal") or "分析这个数据集")
            s = get_settings()
            max_iter = int(msg.get("max_iterations") or s.max_iterations)
            active_run = asyncio.create_task(_run_streaming_task(session_id, goal, max_iter, hub, loop))
    except WebSocketDisconnect:
        pass
    finally:
        pump.cancel()
        try:
            await pump
        except asyncio.CancelledError:
            pass
        await hub.unregister(session_id, q)

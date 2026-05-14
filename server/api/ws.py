"""WebSocket：推送事件 schema（MVP）；完整 tool_call 流待 run 流式化后接入（见 docs/SPEC.md §7.2）。"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# 与 SPEC §7.2 对齐的契约说明（客户端可据此解析未来增量事件）
WS_EVENT_SCHEMA: dict = {
    "version": 1,
    "events": [
        {"name": "schema", "payload": {"version": "int", "events": "list"}},
        {"name": "node_enter", "payload": {"node": "str"}},
        {"name": "node_exit", "payload": {"node": "str"}},
        {"name": "tool_call", "payload": {"tool": "str", "arguments": "object"}},
        {"name": "tool_result", "payload": {"tool": "str", "ok": "bool", "summary": "object"}},
        {"name": "final", "payload": {"final_answer": "str", "stop_reason": "str"}},
        {"name": "error", "payload": {"message": "str"}},
        {"name": "idle", "payload": {"session_id": "str", "hint": "str"}},
    ],
}


@router.websocket("/sessions/{session_id}/ws")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        await websocket.send_json({"event": "schema", "session_id": session_id, **WS_EVENT_SCHEMA})
        await websocket.send_json(
            {
                "event": "idle",
                "session_id": session_id,
                "hint": "当前分析请使用 POST /sessions/{id}/run；完成后 GET /sessions/{id}/state 获取 execution_history。流式 tool_call 将在后续版本接入。",
            }
        )
        await websocket.close(code=1000)
    except WebSocketDisconnect:
        return

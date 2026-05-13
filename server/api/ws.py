"""WebSocket 进度推送（MVP 占位，详见 docs/TASKS.md Task 6）。"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/sessions/{session_id}/ws")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        await websocket.send_json(
            {"event": "hello", "session_id": session_id, "message": "WebSocket MVP 占位，事件流待实现。"}
        )
        await websocket.close()
    except WebSocketDisconnect:
        return

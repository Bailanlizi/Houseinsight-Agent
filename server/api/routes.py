from __future__ import annotations

import io
import uuid
import asyncio

from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from server.agent.graph import run_agent
from server.agent.run_context import build_initial_agent_state
from server.core.config import get_settings
from server.core.session_store import get_session_store
from server.tools.explore_tools import get_data_profile

router = APIRouter()

# 内存会话元数据（与 SessionStore 中的 DataFrame 对应）
_session_meta: dict[str, dict] = {}


def _sanitize_state_for_api(state: dict) -> dict:
    """移除/转换不可 JSON 序列化的消息对象。"""
    out = dict(state)
    msgs = out.get("messages")
    if isinstance(msgs, list):
        serializable = []
        for m in msgs:
            if isinstance(m, BaseMessage):
                serializable.append({"type": m.__class__.__name__, "content": str(m.content)})
            else:
                serializable.append(m)
        out["messages"] = serializable
    return out


def persist_session_state(session_id: str, out: dict[str, Any]) -> None:
    """将一次 run 的终态写入内存元数据（REST run 与 WS run 共用）。"""
    if session_id not in _session_meta:
        return
    safe = _sanitize_state_for_api(out)
    _session_meta[session_id]["last_state"] = safe
    _session_meta[session_id]["final_answer"] = out.get("final_answer") or ""


class RunBody(BaseModel):
    goal: str = Field(default="分析这个数据集")
    options: dict = Field(default_factory=dict)


@router.post("/sessions")
async def create_session() -> dict:
    sid = str(uuid.uuid4())
    _session_meta[sid] = {
        "final_answer": None,
        "last_state": None,
        "run_lock": asyncio.Lock(),
    }
    return {"session_id": sid}


@router.post("/sessions/{session_id}/upload")
async def upload_csv(session_id: str, file: UploadFile = File(...)) -> dict:
    if session_id not in _session_meta:
        raise HTTPException(status_code=404, detail="session not found")
    s = get_settings()
    raw = await file.read()
    if len(raw) > s.max_upload_bytes:
        raise HTTPException(status_code=413, detail="file too large")
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"csv parse error: {e}") from e
    if len(df) > s.max_csv_rows:
        raise HTTPException(status_code=413, detail="too many rows")
    get_session_store().put(session_id, df)
    return {"session_id": session_id, "rows": int(len(df)), "columns": list(df.columns)}


@router.post("/sessions/{session_id}/run")
async def run_session(session_id: str, body: RunBody) -> dict:
    if session_id not in _session_meta:
        raise HTTPException(status_code=404, detail="session not found")
    store = get_session_store()
    if store.get(session_id) is None:
        raise HTTPException(status_code=400, detail="upload csv first")

    s = get_settings()
    max_iter = int(body.options.get("max_iterations", s.max_iterations))
    last_state = _session_meta[session_id].get("last_state")
    initial = build_initial_agent_state(session_id, body.goal, max_iter, last_state)
    out = run_agent(initial)
    fa = out.get("final_answer") or ""
    persist_session_state(session_id, out)
    return {"session_id": session_id, "final_answer": fa, "stop_reason": out.get("stop_reason", "")}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    """释放会话元数据与 SessionStore 中的 DataFrame（SPEC Task 2 可选能力）。"""
    if session_id not in _session_meta:
        raise HTTPException(status_code=404, detail="session not found")
    _session_meta.pop(session_id, None)
    get_session_store().delete(session_id)
    return {"session_id": session_id, "deleted": True}


@router.get("/sessions/{session_id}/state")
async def session_state(session_id: str) -> dict:
    if session_id not in _session_meta:
        raise HTTPException(status_code=404, detail="session not found")
    st = _session_meta[session_id].get("last_state") or {}
    store = get_session_store()
    df = store.get(session_id)
    profile = st.get("data_profile")
    if profile is None and df is not None:
        _, profile = get_data_profile(df, {"sample_rows": 5})
    return {
        "session_id": session_id,
        "data_profile": profile,
        "iteration": st.get("iteration"),
        "stop_reason": st.get("stop_reason"),
        "execution_history": st.get("execution_history"),
        "messages": st.get("messages"),
        "final_answer": st.get("final_answer") or _session_meta[session_id].get("final_answer"),
    }


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}

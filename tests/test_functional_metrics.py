"""FC-xx 功能指标：见 docs/METRICS.md。"""
from __future__ import annotations

import io
import uuid

import pandas as pd
from fastapi.testclient import TestClient

from server.agent.graph import run_agent
from server.core.session_store import get_session_store
from server.main import app

from tests.helpers.agent_fixtures import (
    assert_execution_history_shape,
    load_wenjiang_df,
    make_initial_state,
)


def _tool_multiset(hist: list) -> list[str]:
    return sorted(str(h.get("tool")) for h in hist if h.get("tool"))


def test_fc01_fc02_fc03_pipeline(mock_llm_env, mock_llm_nodes):
    """FC-01/02/03：完成态、历史形状、核心工具出现。"""
    df = load_wenjiang_df(60)
    sid = str(uuid.uuid4())
    get_session_store().put(sid, df)
    out = run_agent(make_initial_state(sid, "analyze dataset", max_iterations=12))
    assert out.get("final_answer")
    assert out.get("stop_reason") in ("completed", "max_iterations", "error")
    hist = out.get("execution_history") or []
    assert_execution_history_shape(hist)
    tools = {h.get("tool") for h in hist}
    assert "get_basic_stats" in tools
    assert "parse_numeric_column" in tools


def test_fc04_api_run_matches_direct_run_agent(mock_llm_env, mock_llm_nodes):
    """FC-04：REST /run 与直接 run_agent 的工具多重集一致（两次运行间重置 DataFrame）。"""
    from server.core.config import get_settings

    get_settings.cache_clear()
    goal = "analyze dataset"
    max_iter = 10
    df_src = load_wenjiang_df(50)

    c = TestClient(app)
    r = c.post("/sessions")
    assert r.status_code == 200
    sid = r.json()["session_id"]

    get_session_store().put(sid, df_src.copy())
    direct = run_agent(make_initial_state(sid, goal, max_iterations=max_iter))

    get_session_store().put(sid, df_src.copy())
    run = c.post(
        f"/sessions/{sid}/run",
        json={"goal": goal, "options": {"max_iterations": max_iter}},
    )
    assert run.status_code == 200
    st = c.get(f"/sessions/{sid}/state")
    assert st.status_code == 200
    api_hist = st.json().get("execution_history") or []

    assert _tool_multiset(direct.get("execution_history") or []) == _tool_multiset(api_hist)
    get_settings.cache_clear()


def test_fc05_ws_event_sequence(mock_llm_env, mock_llm_nodes):
    """FC-05：schema→ready；含 tool_result、final；以 done 结束。"""
    from server.core.config import get_settings

    get_settings.cache_clear()
    c = TestClient(app)
    r = c.post("/sessions")
    sid = r.json()["session_id"]
    buf = io.StringIO()
    pd.DataFrame({"price": [1, 2], "district": ["A", "B"]}).to_csv(buf, index=False)
    up = c.post(
        f"/sessions/{sid}/upload",
        files={"file": ("t.csv", buf.getvalue().encode("utf-8"), "text/csv")},
    )
    assert up.status_code == 200

    events: list[str] = []
    with c.websocket_connect(f"/sessions/{sid}/ws") as ws:
        events.append(ws.receive_json().get("event"))
        events.append(ws.receive_json().get("event"))
        assert events[0] == "schema"
        assert events[1] == "ready"
        ws.send_json({"cmd": "run", "goal": "analyze", "max_iterations": 8})
        while True:
            msg = ws.receive_json()
            ev = str(msg.get("event"))
            events.append(ev)
            if ev == "done":
                break

    assert "tool_result" in events
    assert "final" in events
    assert events[-1] == "done"
    idx_tr = events.index("tool_result")
    idx_fin = events.index("final")
    idx_done = events.index("done")
    assert idx_tr < idx_fin < idx_done
    get_settings.cache_clear()

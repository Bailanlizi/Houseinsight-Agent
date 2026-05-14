"""PF-01 / PF-02：mock 下墙钟时间基线（不设严格阈值，避免 flaky）。"""
from __future__ import annotations

import io
import statistics
import time
import uuid

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from server.agent.graph import run_agent
from server.core.session_store import get_session_store
from server.main import app

from tests.helpers.agent_fixtures import load_wenjiang_df, make_initial_state

# 宽松上界：CI 慢机也不应失败；仅防回归数量级
MAX_RUN_AGENT_SEC = 120.0
MAX_HTTP_RUN_SEC = 120.0


@pytest.mark.perf
def test_pf01_run_agent_wall_clock(mock_llm_env, mock_llm_nodes):
    df = load_wenjiang_df(40)
    sid = str(uuid.uuid4())
    get_session_store().put(sid, df)
    samples = []
    for _ in range(3):
        get_session_store().put(sid, load_wenjiang_df(40))
        state = make_initial_state(sid, "analyze dataset", max_iterations=10)
        t0 = time.perf_counter()
        run_agent(state)
        samples.append(time.perf_counter() - t0)
    med = statistics.median(samples)
    assert med < MAX_RUN_AGENT_SEC, f"PF-01 median too slow: {med:.3f}s"


@pytest.mark.perf
def test_pf02_http_run_wall_clock(mock_llm_env, mock_llm_nodes):
    from server.core.config import get_settings

    get_settings.cache_clear()
    c = TestClient(app)
    r = c.post("/sessions")
    sid = r.json()["session_id"]
    buf = io.StringIO()
    load_wenjiang_df(40).to_csv(buf, index=False)
    up = c.post(
        f"/sessions/{sid}/upload",
        files={"file": ("w.csv", buf.getvalue().encode("utf-8"), "text/csv")},
    )
    assert up.status_code == 200

    t0 = time.perf_counter()
    run = c.post(
        f"/sessions/{sid}/run",
        json={"goal": "analyze dataset", "options": {"max_iterations": 10}},
    )
    elapsed = time.perf_counter() - t0
    assert run.status_code == 200
    assert elapsed < MAX_HTTP_RUN_SEC, f"PF-02 too slow: {elapsed:.3f}s"
    get_settings.cache_clear()


@pytest.mark.perf
def test_pf03_ws_first_tool_result_latency(mock_llm_env, mock_llm_nodes):
    """WS 发起到首个 tool_result 的间隔（仅记录上界）。"""
    from server.core.config import get_settings

    get_settings.cache_clear()
    c = TestClient(app)
    r = c.post("/sessions")
    sid = r.json()["session_id"]
    buf = io.StringIO()
    pd.DataFrame({"x": [1, 2]}).to_csv(buf, index=False)
    c.post(
        f"/sessions/{sid}/upload",
        files={"file": ("t.csv", buf.getvalue().encode("utf-8"), "text/csv")},
    )
    with c.websocket_connect(f"/sessions/{sid}/ws") as ws:
        ws.receive_json()
        ws.receive_json()
        t0 = time.perf_counter()
        ws.send_json({"cmd": "run", "goal": "go", "max_iterations": 8})
        while True:
            msg = ws.receive_json()
            if msg.get("event") == "tool_result":
                dt = time.perf_counter() - t0
                assert dt < 120.0
                break
            if msg.get("event") == "done":
                pytest.fail("done before tool_result")
    get_settings.cache_clear()

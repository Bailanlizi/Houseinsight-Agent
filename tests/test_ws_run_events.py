"""WS cmd:run 在 mock LLM 下应推送 node_exit / tool_result / final / done。"""
from __future__ import annotations

import io

import pandas as pd
from fastapi.testclient import TestClient

from server.main import app


def test_ws_run_streams_tool_events(monkeypatch):
    monkeypatch.setenv("HI_MOCK_LLM", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
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

    types: list[str] = []
    with c.websocket_connect(f"/sessions/{sid}/ws") as ws:
        assert ws.receive_json().get("event") == "schema"
        assert ws.receive_json().get("event") == "ready"
        ws.send_json({"cmd": "run", "goal": "analyze", "max_iterations": 8})
        while True:
            msg = ws.receive_json()
            types.append(str(msg.get("event")))
            if msg.get("event") == "done":
                break

    assert "tool_result" in types
    assert "node_exit" in types
    assert "final" in types
    assert types[-1] == "done"

    get_settings.cache_clear()

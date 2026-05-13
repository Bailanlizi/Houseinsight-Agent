import io

import pandas as pd
from fastapi.testclient import TestClient

from server.main import app


def test_api_flow(monkeypatch):
    monkeypatch.setenv("HI_MOCK_LLM", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from server.core.config import get_settings

    get_settings.cache_clear()

    c = TestClient(app)
    r = c.post("/sessions")
    assert r.status_code == 200
    sid = r.json()["session_id"]

    buf = io.StringIO()
    pd.DataFrame({"x": [1, 2]}).to_csv(buf, index=False)
    up = c.post(
        f"/sessions/{sid}/upload",
        files={"file": ("t.csv", buf.getvalue().encode("utf-8"), "text/csv")},
    )
    assert up.status_code == 200

    run = c.post(
        f"/sessions/{sid}/run",
        json={"goal": "analyze dataset", "options": {"max_iterations": 5}},
    )
    assert run.status_code == 200
    assert run.json().get("final_answer")

    st = c.get(f"/sessions/{sid}/state")
    assert st.status_code == 200
    assert st.json().get("execution_history")

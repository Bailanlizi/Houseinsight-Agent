import uuid
from pathlib import Path

import pandas as pd
from langchain_core.messages import HumanMessage

from server.agent.graph import run_agent
from server.agent.state import AgentState
from server.core.session_store import get_session_store

DATA_DIR = Path(__file__).resolve().parent / "data"
WENJIANG_CSV = DATA_DIR / "温江.csv"


def test_graph_smoke_mock(monkeypatch):
    monkeypatch.setenv("HI_MOCK_LLM", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from server.core.config import get_settings

    get_settings.cache_clear()

    df = pd.DataFrame({"price": [1, 2, 3], "district": ["A", "B", "A"]})
    sid = str(uuid.uuid4())
    get_session_store().put(sid, df)

    initial: AgentState = {
        "messages": [HumanMessage(content="analyze dataset")],
        "session_id": sid,
        "goal": "analyze dataset",
        "max_iterations": 5,
        "data_profile": {},
        "plan": [],
        "execution_history": [],
        "iteration": 0,
        "stop_reason": "",
        "should_finish": False,
        "final_answer": "",
    }
    out = run_agent(initial)
    assert out.get("final_answer")
    assert out.get("execution_history")


def test_graph_mock_runs_search_text_when_goal_mentions_transit(monkeypatch):
    """mock 规划在「交通/地铁」类目标下应调用 search_text（多列多词）。"""
    monkeypatch.setenv("HI_MOCK_LLM", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from server.core.config import get_settings

    get_settings.cache_clear()

    assert WENJIANG_CSV.is_file()
    df = pd.read_csv(WENJIANG_CSV, nrows=30)
    sid = str(uuid.uuid4())
    get_session_store().put(sid, df)

    initial: AgentState = {
        "messages": [HumanMessage(content="想找离地铁近的房源")],
        "session_id": sid,
        "goal": "想找离地铁近的房源",
        "max_iterations": 20,
        "data_profile": {},
        "plan": [],
        "execution_history": [],
        "iteration": 0,
        "stop_reason": "",
        "should_finish": False,
        "final_answer": "",
    }
    out = run_agent(initial)
    tools = [h.get("tool") for h in (out.get("execution_history") or [])]
    assert "search_text" in tools
    st_rec = next(h for h in out["execution_history"] if h.get("tool") == "search_text")
    assert st_rec.get("ok")
    summ = st_rec.get("summary") or {}
    assert summ.get("matched_rows", 0) >= 1

    get_settings.cache_clear()

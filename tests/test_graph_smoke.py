import uuid

import pandas as pd

from server.agent.graph import run_agent
from server.agent.state import AgentState
from server.core.session_store import get_session_store
from langchain_core.messages import HumanMessage


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

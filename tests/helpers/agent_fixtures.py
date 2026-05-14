"""Reusable AgentState / CSV paths for integration and metrics tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from langchain_core.messages import HumanMessage

from server.agent.state import AgentState

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WENJIANG_CSV = DATA_DIR / "温江.csv"


def load_wenjiang_df(nrows: int = 80) -> pd.DataFrame:
    if not WENJIANG_CSV.is_file():
        raise FileNotFoundError(WENJIANG_CSV)
    return pd.read_csv(WENJIANG_CSV, nrows=nrows)


def make_initial_state(
    session_id: str,
    goal: str,
    *,
    max_iterations: int = 14,
    messages: list | None = None,
) -> AgentState:
    return {
        "messages": messages if messages is not None else [HumanMessage(content=goal)],
        "session_id": session_id,
        "goal": goal,
        "max_iterations": max_iterations,
        "data_profile": {},
        "plan": [],
        "execution_history": [],
        "iteration": 0,
        "stop_reason": "",
        "should_finish": False,
        "final_answer": "",
    }


def assert_execution_history_shape(hist: list[Any]) -> None:
    """FC-02: each record has tool / arguments / summary."""
    for rec in hist:
        assert isinstance(rec, dict)
        assert "tool" in rec
        assert "arguments" in rec
        assert "summary" in rec

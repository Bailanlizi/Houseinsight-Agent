"""多轮对话：run_context 反序列化、transcript 与 initial 构造。"""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from server.agent.graph import run_agent
from server.agent.run_context import (
    build_initial_agent_state,
    format_transcript_for_prompt,
    messages_from_serializable,
)
from server.api.routes import _sanitize_state_for_api
from server.core.session_store import get_session_store
from tests.helpers.agent_fixtures import load_wenjiang_df


def test_messages_from_serializable_roundtrip() -> None:
    msgs = [HumanMessage(content="你好"), AIMessage(content="收到")]
    raw = _sanitize_state_for_api({"messages": msgs})["messages"]
    assert isinstance(raw, list)
    out = messages_from_serializable(raw)
    assert len(out) == 2
    assert isinstance(out[0], HumanMessage) and out[0].content == "你好"
    assert isinstance(out[1], AIMessage) and out[1].content == "收到"


def test_format_transcript_tail_keeps_recent() -> None:
    long_a = "A" * 500
    long_b = "B" * 500
    msgs = [HumanMessage(content=long_a), AIMessage(content=long_b)]
    t = format_transcript_for_prompt(msgs, max_chars=200)
    assert "B" * 50 in t
    assert len(t) <= 200


def test_build_initial_second_run_includes_prior(mock_llm_env: None) -> None:
    sid = "test-multi-sid"
    get_session_store().put(sid, load_wenjiang_df(20))
    first = build_initial_agent_state(sid, "先看基础统计", 8, None)
    assert first.get("prior_transcript") == ""
    out1 = run_agent(first)
    last = _sanitize_state_for_api(dict(out1))
    assert last.get("messages")
    second = build_initial_agent_state(sid, "接着问：行数是多少？", 8, last)
    pt = second.get("prior_transcript") or ""
    assert "用户：" in pt
    assert "助手：" in pt
    assert "先看基础统计" in pt


def test_build_initial_clean_caps_iterations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_ITERATIONS", "10")
    monkeypatch.setenv("MAX_CLEANING_ITERATIONS", "4")
    from server.core.config import get_settings

    get_settings.cache_clear()
    st = build_initial_agent_state("s", "清洗", 99, None, run_phase="clean")
    assert st["max_iterations"] == 4
    assert st["run_phase"] == "clean"
    st2 = build_initial_agent_state("s", "清洗", 2, None, run_phase="clean")
    assert st2["max_iterations"] == 2
    st3 = build_initial_agent_state("s", "分析", 99, None, run_phase="analyze")
    assert st3["max_iterations"] == 99
    assert st3.get("run_phase") == "analyze"
    get_settings.cache_clear()

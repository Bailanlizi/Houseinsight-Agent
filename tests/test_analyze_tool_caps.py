"""分析阶段：同类工具重复上限与 search_text 成功后 observe 早停。"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from server.agent.nodes import (
    _analyze_should_finish_after_tool,
    _apply_analyze_observe_overrides,
    _filter_plan_steps_for_analyze_caps,
    _mock_observe,
    _rule_observe_analyze,
    plan_node,
)
from server.agent.state import AgentState


def test_filter_plan_drops_repeat_search_text(monkeypatch) -> None:
    monkeypatch.setenv("MAX_SEARCH_TEXT_PER_RUN", "1")
    from server.core.config import get_settings

    get_settings.cache_clear()
    state: AgentState = {
        "run_phase": "analyze",
        "execution_history": [
            {"tool": "search_text", "ok": True, "arguments": {}, "summary": {}},
        ],
    }
    steps = [{"tool": "search_text", "arguments": {"columns": ["描述"], "terms": ["采光"], "how": "any_term_any_column"}}]
    out = _filter_plan_steps_for_analyze_caps(state, steps)
    assert out == []
    get_settings.cache_clear()


def test_rule_observe_finishes_filter_only_without_search_text() -> None:
    state: AgentState = {
        "run_phase": "analyze",
        "goal": "锦江区有哪些房",
        "execution_history": [
            {
                "tool": "filter_rows",
                "ok": True,
                "arguments": {},
                "summary": {"matched_rows": 2, "rows_preview": [{}]},
            },
        ],
        "data_profile": {"columns": ["区域"], "dtypes": {}},
        "plan": [],
    }
    obs = _rule_observe_analyze(state)
    assert obs is not None and obs.get("should_finish") is True
    last = state["execution_history"][-1]
    assert _analyze_should_finish_after_tool(state, last) is True


def test_observe_finishes_after_search_text_in_analyze() -> None:
    state: AgentState = {
        "run_phase": "analyze",
        "goal": "找采光好的房",
        "execution_history": [
            {"tool": "search_text", "ok": True, "arguments": {}, "summary": {"matched_rows": 3}},
        ],
        "data_profile": {"columns": ["描述"], "dtypes": {}},
        "plan": [],
    }
    obs = _apply_analyze_observe_overrides(state, _mock_observe(state))
    assert obs.get("should_finish") is True


def test_plan_node_filters_repeat_get_basic_stats(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("HI_MOCK_LLM", "1")
    monkeypatch.setenv("MAX_GET_BASIC_STATS_PER_RUN", "1")
    from server.core.config import get_settings

    get_settings.cache_clear()
    state: AgentState = {
        "session_id": "s1",
        "run_phase": "analyze",
        "goal": "温江房价",
        "data_profile": {"columns": ["区域", "总价"], "dtypes": {}},
        "execution_history": [
            {"tool": "get_basic_stats", "ok": True, "arguments": {}, "summary": {}},
        ],
    }
    out = plan_node(state, RunnableConfig())
    plan = out.get("plan") or []
    assert not any(p.get("tool") == "get_basic_stats" for p in plan)
    get_settings.cache_clear()

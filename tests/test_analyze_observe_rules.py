"""分析阶段：规则 observe、plan 队列路由与早停。"""
from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableConfig

from server.agent.nodes import (
    _apply_analyze_observe_overrides,
    _resolve_observe,
    _rule_observe_analyze,
    plan_node,
    route_after_execute,
)
from server.agent.state import AgentState


def test_rule_observe_finishes_after_filter_only_goal() -> None:
    state: AgentState = {
        "run_phase": "analyze",
        "goal": "推荐武侯区的房源",
        "execution_history": [
            {
                "tool": "filter_rows",
                "ok": True,
                "arguments": {"filters": [{"column": "区域", "op": "contains", "value": "武侯"}]},
                "summary": {"matched_rows": 5, "rows_preview": [{"区域": "武侯"}]},
            },
        ],
        "data_profile": {"columns": ["区域", "描述"], "dtypes": {}},
        "plan": [],
    }
    obs = _rule_observe_analyze(state)
    assert obs is not None
    assert obs.get("should_finish") is True


def test_rule_observe_finishes_after_search_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "server.agent.nodes._llm_observe",
        lambda _s: (_ for _ in ()).throw(AssertionError("should not call LLM observe")),
    )
    state: AgentState = {
        "run_phase": "analyze",
        "goal": "找采光好的房",
        "execution_history": [
            {"tool": "search_text", "ok": True, "arguments": {}, "summary": {"matched_rows": 3}},
        ],
        "data_profile": {"columns": ["描述"], "dtypes": {}},
        "plan": [],
    }
    obs, source = _resolve_observe(state)
    assert source == "rule"
    assert obs.get("should_finish") is True


def test_rule_observe_must_continue_price_pipeline() -> None:
    state: AgentState = {
        "run_phase": "analyze",
        "goal": "预算不超过200万的房源",
        "execution_history": [],
        "data_profile": {"columns": ["总价"], "dtypes": {"总价": "object"}},
        "plan": [],
    }
    obs = _rule_observe_analyze(state)
    assert obs is not None
    assert obs.get("should_finish") is False


def test_route_after_execute_drains_plan() -> None:
    state: AgentState = {
        "plan": [{"tool": "filter_rows"}, {"tool": "search_text"}],
        "execution_history": [{"tool": "parse_house_info_column", "ok": True, "summary": {}}],
    }
    assert route_after_execute(state) == "execute"


def test_route_after_execute_goes_observe_on_failure() -> None:
    state: AgentState = {
        "plan": [{"tool": "search_text"}],
        "execution_history": [{"tool": "filter_rows", "ok": False, "error": "x"}],
    }
    assert route_after_execute(state) == "observe"


def test_route_after_execute_empty_plan_goes_observe() -> None:
    state: AgentState = {
        "plan": [],
        "execution_history": [{"tool": "filter_rows", "ok": True}],
    }
    assert route_after_execute(state) == "observe"


def test_plan_node_preserves_nonempty_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "server.agent.nodes._llm_plan",
        lambda _s: (_ for _ in ()).throw(AssertionError("should not re-plan")),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("HI_MOCK_LLM", "0")
    from server.core.config import get_settings

    get_settings.cache_clear()
    state: AgentState = {
        "session_id": "s1",
        "run_phase": "analyze",
        "goal": "温江房价",
        "data_profile": {"columns": ["区域"], "dtypes": {}},
        "plan": [
            {"tool": "filter_rows", "arguments": {}},
            {"tool": "group_by_summary", "arguments": {}},
        ],
        "execution_history": [],
    }
    out = plan_node(state, RunnableConfig())
    plan = out.get("plan") or []
    assert len(plan) == 2
    assert plan[0].get("tool") == "filter_rows"
    get_settings.cache_clear()


def test_apply_overrides_filter_only_after_filter_rows() -> None:
    state: AgentState = {
        "run_phase": "analyze",
        "goal": "武侯区三室",
        "execution_history": [
            {"tool": "filter_rows", "ok": True, "arguments": {}, "summary": {"matched_rows": 1}},
        ],
        "data_profile": {"columns": ["区域"], "dtypes": {}},
    }
    obs = _apply_analyze_observe_overrides(
        state, {"should_finish": False, "stop_reason": "completed", "notes": ""}
    )
    assert obs.get("should_finish") is True

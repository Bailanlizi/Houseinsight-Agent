"""answer_node 用户可见文案保险丝与降级文案。"""
from __future__ import annotations

from server.agent.nodes import (
    ANSWER_FALLBACK_ILLEGAL,
    ANSWER_FALLBACK_QUERY_ISSUE,
    _answer_looks_illegal,
    _sanitize_answer,
    answer_node,
)

from tests.helpers.agent_fixtures import make_initial_state


def test_answer_looks_illegal_detects_plan_json():
    assert _answer_looks_illegal('[{"tool": "search_text", "arguments": {}}]')
    assert _answer_looks_illegal('{"steps": []}')
    assert _answer_looks_illegal("请先调用 search_text 再筛选")


def test_sanitize_answer_replaces_illegal():
    bad = '[{"tool": "search_text", "arguments": {"query": "采光"}}]'
    assert _sanitize_answer(bad) == ANSWER_FALLBACK_ILLEGAL


def test_sanitize_answer_keeps_normal_text():
    ok = "在新都区可优先关注南向、中高楼层，描述里带「采光好」的房源。"
    assert _sanitize_answer(ok) == ok


def test_answer_node_friendly_on_tool_failure(mock_llm_env, mock_llm_nodes):
    state = make_initial_state("sid-err", "推荐采光好的房源", max_iterations=8)
    state["stop_reason"] = "completed"
    state["execution_history"] = [
        {
            "tool": "search_text",
            "arguments": {},
            "summary": None,
            "ok": False,
            "error": "column missing: 描述",
        }
    ]
    out = answer_node(state, {})
    assert out["final_answer"] == ANSWER_FALLBACK_QUERY_ISSUE
    assert "column missing" not in out["final_answer"]
    assert "search_text" not in out["final_answer"].lower()

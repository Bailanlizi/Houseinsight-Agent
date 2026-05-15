"""计划阶段：LLM 结构化失败时的重试、规则降级与错误暴露。"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from server.agent.nodes import plan_node
from server.agent.state import AgentState


def test_plan_node_degrades_to_mock_when_llm_structured_fails(monkeypatch):
    """连续两次结构化失败后降级为 _mock_plan，仍可执行下一步（如 get_basic_stats）。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("HI_MOCK_LLM", "0")
    from server.core.config import get_settings

    get_settings.cache_clear()

    class _FakeStructured:
        def invoke(self, _messages):
            raise ValueError("structured output failed")

    class _FakeModel:
        def with_structured_output(self, _schema):
            return _FakeStructured()

    monkeypatch.setattr("server.agent.nodes.get_chat_model", lambda: _FakeModel())
    monkeypatch.setattr("server.agent.nodes._use_mock_llm", lambda: False)

    state: AgentState = {
        "session_id": "s1",
        "goal": "分析",
        "data_profile": {"columns": ["总价", "区域"]},
        "execution_history": [],
    }
    cfg: RunnableConfig = {}
    out = plan_node(state, cfg)
    plan = out.get("plan") or []
    assert plan and plan[0].get("tool") == "get_basic_stats"
    assert out.get("plan_generation_error") is None

    get_settings.cache_clear()


def test_plan_node_surfaces_error_when_llm_and_mock_both_empty(monkeypatch):
    """无 LLM、且规则计划也无下一步时，仍须暴露 plan_generation_error。"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("HI_MOCK_LLM", "0")
    from server.core.config import get_settings

    get_settings.cache_clear()

    class _FakeStructured:
        def invoke(self, _messages):
            raise ValueError("structured output failed")

    class _FakeModel:
        def with_structured_output(self, _schema):
            return _FakeStructured()

    monkeypatch.setattr("server.agent.nodes.get_chat_model", lambda: _FakeModel())
    monkeypatch.setattr("server.agent.nodes._use_mock_llm", lambda: False)
    monkeypatch.setattr("server.agent.nodes._mock_plan", lambda _state: [])

    state: AgentState = {
        "session_id": "s1",
        "goal": "分析",
        "data_profile": {"columns": ["总价", "区域"]},
        "execution_history": [],
    }
    cfg: RunnableConfig = {}
    out = plan_node(state, cfg)
    assert out.get("plan") == []
    err = out.get("plan_generation_error") or ""
    assert err
    assert "structured output failed" in err or "计划生成失败" in err or "计划为空" in err

    get_settings.cache_clear()

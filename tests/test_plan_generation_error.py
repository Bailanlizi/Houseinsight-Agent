"""Task 7：计划阶段结构化输出失败时须暴露 plan_generation_error（由 execute 写入 error）。"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from server.agent.nodes import plan_node
from server.agent.state import AgentState


def test_plan_node_surfaces_error_when_llm_structured_fails(monkeypatch):
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
    assert out.get("plan") == []
    assert out.get("plan_generation_error")
    assert "计划生成失败" in out["plan_generation_error"]

    get_settings.cache_clear()

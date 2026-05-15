"""单次 run 的初始状态：多轮对话 prior_transcript 与消息反序列化。"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from server.agent.state import AgentState
from server.core.config import get_settings


def messages_from_serializable(raw: list[Any]) -> list[BaseMessage]:
    """将 persist_session_state 保存的 messages 列表还原为 LangChain 消息。"""
    out: list[BaseMessage] = []
    for item in raw:
        if isinstance(item, BaseMessage):
            out.append(item)
            continue
        if not isinstance(item, dict):
            continue
        t = str(item.get("type") or "")
        content = str(item.get("content") or "")
        if t == "HumanMessage":
            out.append(HumanMessage(content=content))
        elif t == "AIMessage":
            out.append(AIMessage(content=content))
    return out


def format_transcript_for_prompt(messages: list[BaseMessage], max_chars: int) -> str:
    """格式化为「用户：/助手：」文本；超长时保留尾部。"""
    lines: list[str] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            lines.append(f"用户：{m.content}")
        elif isinstance(m, AIMessage):
            lines.append(f"助手：{m.content}")
    text = "\n".join(lines).strip()
    if len(text) <= max_chars:
        return text
    sep = "…（更早对话已省略）\n"
    budget = max_chars - len(sep)
    if budget < 100:
        return text[-max_chars:]
    return sep + text[-budget:]


def build_initial_agent_state(
    session_id: str,
    goal: str,
    max_iterations: int,
    last_state: dict[str, Any] | None,
    *,
    run_phase: Literal["clean", "analyze"] = "analyze",
) -> AgentState:
    prior = ""
    if last_state:
        raw_msgs = last_state.get("messages")
        if isinstance(raw_msgs, list) and raw_msgs:
            prior = format_transcript_for_prompt(
                messages_from_serializable(raw_msgs),
                get_settings().max_prior_transcript_chars,
            )
    s = get_settings()
    max_it = max_iterations
    if run_phase == "clean":
        cap = min(s.max_cleaning_iterations, s.max_iterations)
        max_it = min(max_iterations, cap)
    return {
        "messages": [HumanMessage(content=goal)],
        "prior_transcript": prior,
        "session_id": session_id,
        "goal": goal,
        "run_phase": run_phase,
        "max_iterations": max_it,
        "data_profile": {},
        "plan": [],
        "execution_history": [],
        "iteration": 0,
        "stop_reason": "",
        "should_finish": False,
        "final_answer": "",
    }

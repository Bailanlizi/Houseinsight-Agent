from collections.abc import Callable
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from server.agent.nodes import (
    answer_node,
    execute_node,
    explore_node,
    observe_node,
    plan_node,
    route_after_explore,
    route_after_observe,
)
from server.agent.state import AgentState


def build_agent_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("explore", explore_node)
    g.add_node("plan", plan_node)
    g.add_node("execute", execute_node)
    g.add_node("observe", observe_node)
    g.add_node("answer", answer_node)

    g.add_edge(START, "explore")
    g.add_conditional_edges(
        "explore",
        route_after_explore,
        {"plan": "plan", "answer": "answer"},
    )
    g.add_edge("plan", "execute")
    g.add_edge("execute", "observe")
    g.add_conditional_edges(
        "observe",
        route_after_observe,
        {"plan": "plan", "answer": "answer"},
    )
    g.add_edge("answer", END)
    return g.compile()


def _shallow_payload(upd: dict[str, Any], max_len: int = 2000) -> dict[str, Any]:
    """控制 node_exit 载荷体积，避免把整个 profile 塞进 WS。"""
    out: dict[str, Any] = {}
    for k, v in upd.items():
        if k == "messages":
            out[k] = f"<{len(v) if hasattr(v, '__len__') else '?'} messages>"
            continue
        try:
            s = repr(v)
        except Exception:  # noqa: BLE001
            s = "<unrepr>"
        if len(s) > max_len:
            s = s[:max_len] + "…"
        out[k] = s
    return out


def _summarize_tool_summary(summary: Any, limit: int = 1500) -> Any:
    if summary is None:
        return None
    if isinstance(summary, dict):
        try:
            import json

            s = json.dumps(summary, ensure_ascii=False, default=str)
        except Exception:  # noqa: BLE001
            return str(summary)[:limit]
        return s[:limit] + ("…" if len(s) > limit else "")
    s = str(summary)
    return s[:limit] + ("…" if len(s) > limit else "")


def run_agent_streaming(
    initial: AgentState,
    config: RunnableConfig | None = None,
    emit: Callable[[dict[str, Any]], None] | None = None,
) -> AgentState:
    """与 run_agent 等价终态；若提供 emit，则在 stream 过程中推送 node / tool 事件。"""
    graph = build_agent_graph()
    session_id = str(initial.get("session_id", "") or "")
    last_values: AgentState | None = None
    stream_iter = (
        graph.stream(initial, config, stream_mode=["updates", "values"])
        if config is not None
        else graph.stream(initial, stream_mode=["updates", "values"])
    )
    for mode, payload in stream_iter:
        if mode == "values":
            last_values = cast(AgentState, payload)
            continue
        if mode != "updates" or not emit or not isinstance(payload, dict):
            continue
        for node_name, upd in payload.items():
            if not isinstance(upd, dict):
                continue
            emit(
                {
                    "event": "node_enter",
                    "session_id": session_id,
                    "node": node_name,
                }
            )
            emit(
                {
                    "event": "node_exit",
                    "session_id": session_id,
                    "node": node_name,
                    "payload": _shallow_payload(upd),
                }
            )
            if node_name == "execute":
                hist = upd.get("execution_history")
                if isinstance(hist, list) and hist:
                    rec = hist[-1]
                    if isinstance(rec, dict):
                        emit(
                            {
                                "event": "tool_call",
                                "session_id": session_id,
                                "tool": rec.get("tool", ""),
                                "arguments": rec.get("arguments") or {},
                            }
                        )
                        emit(
                            {
                                "event": "tool_result",
                                "session_id": session_id,
                                "tool": rec.get("tool", ""),
                                "ok": rec.get("ok"),
                                "summary": _summarize_tool_summary(rec.get("summary")),
                                "error": rec.get("error"),
                            }
                        )
    if last_values is None:
        raise RuntimeError("agent stream produced no terminal state")
    return last_values


def run_agent(initial: AgentState) -> AgentState:
    graph = build_agent_graph()
    return graph.invoke(initial)  # type: ignore[return-value]

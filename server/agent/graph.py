from __future__ import annotations

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


def run_agent(initial: AgentState) -> AgentState:
    graph = build_agent_graph()
    return graph.invoke(initial)  # type: ignore[return-value]

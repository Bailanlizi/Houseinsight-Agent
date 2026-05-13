from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class PlanStepDict(TypedDict, total=False):
    tool: str
    arguments: dict[str, Any]
    rationale: str | None


class ExecutionRecord(TypedDict, total=False):
    tool: str
    arguments: dict[str, Any]
    ok: bool
    summary: dict[str, Any]
    error: str | None
    duration_ms: float


class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    goal: str
    max_iterations: int
    data_profile: dict[str, Any]
    plan: list[PlanStepDict]
    execution_history: Annotated[list[ExecutionRecord], operator.add]
    iteration: int
    stop_reason: Literal["completed", "max_iterations", "error", "user_abort", ""]
    should_finish: bool
    final_answer: str
    before_profile: dict[str, Any] | None  # 供 compare_cleaning_results 使用

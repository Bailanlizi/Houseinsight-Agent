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
    prior_transcript: str  # 上一轮及更早对话的节选（仅 initial 写入，供 prompt）
    session_id: str
    goal: str
    max_iterations: int
    data_profile: dict[str, Any]
    plan: list[PlanStepDict]
    plan_generation_error: str | None  # 非 mock 下 LLM 计划结构化失败时写入，供 execute/observe 终止
    execution_history: Annotated[list[ExecutionRecord], operator.add]
    iteration: int
    stop_reason: Literal["completed", "max_iterations", "error", "user_abort", ""]
    should_finish: bool
    final_answer: str
    before_profile: dict[str, Any] | None  # 供 compare_cleaning_results 使用

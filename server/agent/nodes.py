from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from server.agent.prompts import ANSWER_PROMPT, OBSERVE_PROMPT, PLAN_PROMPT, SYSTEM_ZH
from server.agent.state import AgentState, ExecutionRecord, PlanStepDict
from server.core.config import get_settings
from server.core.llm import get_chat_model
from server.core.session_store import get_session_store
from server.tools._dataframe import ensure_row_fingerprint
from server.tools.explore_tools import get_data_profile
from server.tools.register import TOOL_REGISTRY, dispatch_tool

logger = logging.getLogger(__name__)


class PlanStepModel(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class PlanLLMOutput(BaseModel):
    steps: list[PlanStepModel]


class ObserveLLMOutput(BaseModel):
    should_finish: bool
    stop_reason: Literal["completed", "error", "max_iterations"] = "completed"
    notes: str = ""


def _profile_excerpt(profile: dict[str, Any], limit: int = 1200) -> str:
    try:
        s = json.dumps(profile, ensure_ascii=False, default=str)[:limit]
        return s + ("…" if len(s) == limit else "")
    except Exception:  # noqa: BLE001
        return str(profile)[:limit]


def _history_excerpt(history: list[ExecutionRecord], limit: int = 2000) -> str:
    try:
        s = json.dumps(history[-8:], ensure_ascii=False, default=str)[:limit]
        return s + ("…" if len(s) == limit else "")
    except Exception:  # noqa: BLE001
        return str(history[-8:])[:limit]


def _use_mock_llm() -> bool:
    s = get_settings()
    return s.hi_mock_llm or not s.llm_configured


def explore_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config  # LangGraph 注入，当前节点未使用
    sid = state["session_id"]
    store = get_session_store()
    df = store.get(sid)
    if df is None:
        return {
            "data_profile": {},
            "stop_reason": "error",
            "should_finish": True,
            "messages": [AIMessage(content="错误：会话中不存在数据表，请先上传 CSV。")],
        }
    df2 = ensure_row_fingerprint(df)
    store.put(sid, df2)
    _, prof = get_data_profile(df2, {"sample_rows": 5})
    return {
        "data_profile": prof,
        "before_profile": prof,
        "messages": [AIMessage(content="已完成数据探索与行指纹注入（如需要）。")],
    }


def _mock_plan(state: AgentState) -> list[PlanStepDict]:
    hist = state.get("execution_history", [])
    prof = state.get("data_profile", {}) or {}
    cols: list[str] = list(prof.get("columns", []) or [])

    if not any(h.get("tool") == "get_basic_stats" for h in hist):
        return [{"tool": "get_basic_stats", "arguments": {}, "rationale": "先了解数值列分布"}]

    price_like = next((c for c in cols if any(k in c.lower() for k in ("价", "price", "总价"))), None)
    if price_like and not any(
        h.get("tool") == "parse_numeric_column" and (h.get("arguments") or {}).get("column") == price_like
        for h in hist
    ):
        dtypes = prof.get("dtypes", {})
        if dtypes.get(price_like) not in ("float64", "int64", "Int64"):
            return [
                {
                    "tool": "parse_numeric_column",
                    "arguments": {"column": price_like},
                    "rationale": "将价格类文本转为数值",
                }
            ]

    group_like = next((c for c in cols if any(k in c for k in ("区", "区域", "地段", "location", "区县"))), None)
    val_col = next((c for c in cols if any(k in c.lower() for k in ("价", "price", "均价"))), None)
    if group_like and val_col and not any(h.get("tool") == "group_by_summary" for h in hist):
        return [
            {
                "tool": "group_by_summary",
                "arguments": {"group_by": group_like, "value": val_col, "stat": "mean"},
                "rationale": "按区域看均价",
            }
        ]

    if cols and not any(h.get("tool") == "top_k_values" for h in hist):
        return [{"tool": "top_k_values", "arguments": {"column": cols[0], "k": min(10, max(3, len(cols)))}}]

    return []


def _llm_plan(state: AgentState) -> list[PlanStepDict]:
    tool_names = "\n".join(f"- {k}" for k in sorted(TOOL_REGISTRY))
    prompt = PLAN_PROMPT.format(
        tool_names=tool_names,
        profile_excerpt=_profile_excerpt(state.get("data_profile", {})),
        goal=state.get("goal", ""),
        history_excerpt=_history_excerpt(state.get("execution_history", [])),
    )
    model = get_chat_model()
    structured = model.with_structured_output(PlanLLMOutput)
    try:
        out: PlanLLMOutput = structured.invoke(
            [
                SystemMessage(content=SYSTEM_ZH),
                HumanMessage(content=prompt),
            ]
        )
        return [s.model_dump(exclude_none=True) for s in out.steps][:3]
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM plan failed, fallback mock: %s", e)
        return _mock_plan(state)


def plan_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config
    if state.get("stop_reason") == "error" and not state.get("data_profile"):
        return {"plan": []}
    if _use_mock_llm():
        steps = _mock_plan(state)
    else:
        steps = _llm_plan(state)
    return {"plan": steps}


def execute_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config
    sid = state["session_id"]
    store = get_session_store()
    df = store.get(sid)
    if df is None:
        rec: ExecutionRecord = {
            "tool": "",
            "arguments": {},
            "ok": False,
            "summary": {},
            "error": "无数据",
            "duration_ms": 0.0,
        }
        return {"execution_history": [rec], "plan": []}

    plan = list(state.get("plan") or [])
    if not plan:
        rec = {
            "tool": "",
            "arguments": {},
            "ok": False,
            "summary": {},
            "error": "计划为空",
            "duration_ms": 0.0,
        }
        return {"execution_history": [rec], "plan": []}

    step: PlanStepDict = plan[0]
    remaining = plan[1:]
    tool = step.get("tool", "")
    arguments = dict(step.get("arguments") or {})
    t0 = time.perf_counter()
    new_df, payload, mutates = dispatch_tool(tool, df, arguments)
    dt = (time.perf_counter() - t0) * 1000
    if mutates and payload.get("ok"):
        store.put(sid, new_df)
        _, new_prof = get_data_profile(new_df, {"sample_rows": 5})
        return {
            "plan": remaining,
            "data_profile": new_prof,
            "execution_history": [
                {
                    "tool": tool,
                    "arguments": arguments,
                    "ok": True,
                    "summary": payload,
                    "error": None,
                    "duration_ms": dt,
                }
            ],
        }

    rec: ExecutionRecord = {
        "tool": tool,
        "arguments": arguments,
        "ok": bool(payload.get("ok")),
        "summary": payload,
        "error": None if payload.get("ok") else str(payload.get("error")),
        "duration_ms": dt,
    }
    return {"plan": remaining, "execution_history": [rec]}


def _mock_observe(state: AgentState) -> dict[str, Any]:
    hist = state.get("execution_history", [])
    last = hist[-1] if hist else None
    if last and last.get("ok") is False:
        return {"should_finish": True, "stop_reason": "error", "notes": "工具执行失败，结束循环。"}
    if last and last.get("tool") == "get_basic_stats" and last.get("ok"):
        return {"should_finish": True, "stop_reason": "completed", "notes": "已完成基础统计（mock）。"}
    if not state.get("plan"):
        return {"should_finish": True, "stop_reason": "completed", "notes": "计划已空（mock）。"}
    return {"should_finish": False, "stop_reason": "completed", "notes": "继续下一步。"}


def _llm_observe(state: AgentState) -> dict[str, Any]:
    hist = state.get("execution_history", [])
    last = hist[-1] if hist else {}
    prompt = OBSERVE_PROMPT.format(goal=state.get("goal", ""), last_result=json.dumps(last, ensure_ascii=False))
    model = get_chat_model()
    structured = model.with_structured_output(ObserveLLMOutput)
    try:
        out: ObserveLLMOutput = structured.invoke(
            [SystemMessage(content=SYSTEM_ZH), HumanMessage(content=prompt)]
        )
        return {
            "should_finish": out.should_finish,
            "stop_reason": out.stop_reason,
            "notes": out.notes,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM observe failed, fallback mock: %s", e)
        return _mock_observe(state)


def observe_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config
    max_iter = int(state.get("max_iterations") or get_settings().max_iterations)
    it = int(state.get("iteration", 0)) + 1
    updates: dict[str, Any] = {"iteration": it}
    if it >= max_iter:
        updates["should_finish"] = True
        updates["stop_reason"] = "max_iterations"
        updates["messages"] = [AIMessage(content=f"已达最大循环次数 {max_iter}（observe 计数）。")]
        return updates
    if _use_mock_llm():
        obs = _mock_observe(state)
    else:
        obs = _llm_observe(state)
    updates.update(obs)
    if obs.get("notes"):
        updates.setdefault("messages", [])
        if isinstance(updates["messages"], list):
            updates["messages"].append(AIMessage(content=f"观察：{obs['notes']}"))
    return updates


def answer_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config
    if _use_mock_llm():
        prof = state.get("data_profile", {})
        n = prof.get("n_rows", "未知")
        lines = [
            "## 分析结论（mock 模式）",
            f"- 数据行数：**{n}**",
            f"- 停止原因：**{state.get('stop_reason', '') or 'completed'}**",
            "- 已执行工具摘要见会话状态 `execution_history`。",
        ]
        return {"final_answer": "\n".join(lines)}

    prompt = ANSWER_PROMPT.format(
        goal=state.get("goal", ""),
        profile_excerpt=_profile_excerpt(state.get("data_profile", {})),
        history_excerpt=_history_excerpt(state.get("execution_history", [])),
    )
    model = get_chat_model()
    resp = model.invoke([SystemMessage(content=SYSTEM_ZH), HumanMessage(content=prompt)])
    text = getattr(resp, "content", str(resp))
    return {"final_answer": str(text)}


def route_after_explore(state: AgentState) -> Literal["plan", "answer"]:
    if state.get("stop_reason") == "error":
        return "answer"
    return "plan"


def route_after_observe(state: AgentState) -> Literal["plan", "answer"]:
    if state.get("should_finish"):
        return "answer"
    it = int(state.get("iteration", 0))
    max_iter = int(state.get("max_iterations") or get_settings().max_iterations)
    if it >= max_iter:
        return "answer"
    return "plan"

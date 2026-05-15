from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from server.agent.plan_schema import PlanStructuredOutput, plan_steps_to_plan_dicts
from server.agent.prompts import (
    ANSWER_PROMPT,
    CLEAN_PHASE_OBSERVE_APPEND,
    CLEAN_PHASE_PLAN_APPEND,
    INTENT_AND_FILTER_GUIDE,
    OBSERVE_PROMPT,
    PLAN_PROMPT,
    SYSTEM_ZH,
    format_plan_structure_retry_hint,
)
from server.agent.state import AgentState, ExecutionRecord, PlanStepDict
from server.core.config import get_settings
from server.core.llm import get_chat_model
from server.core.session_store import get_session_store
from server.tools._dataframe import ensure_row_fingerprint
from server.tools.explore_tools import get_data_profile
from server.tools.register import TOOL_REGISTRY, dispatch_tool

logger = logging.getLogger(__name__)


def _log_hi_timing(kind: str, **fields: Any) -> None:
    """终端可 grep：`[hi_timing]`；键值单行便于扫读。"""
    parts = [kind] + [f"{k}={v}" for k, v in fields.items()]
    logger.info("[hi_timing] %s", " ".join(parts))


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


def _prior_for_prompt(state: AgentState) -> str:
    t = state.get("prior_transcript")
    if isinstance(t, str) and t.strip():
        return t
    return "（无）"


def _use_mock_llm() -> bool:
    s = get_settings()
    return s.hi_mock_llm or not s.llm_configured


def explore_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config  # LangGraph 注入，当前节点未使用
    t0 = time.perf_counter()
    sid = state["session_id"]
    try:
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
    finally:
        _log_hi_timing("node=explore", session_id=sid, duration_ms=f"{(time.perf_counter() - t0) * 1000:.1f}")


def _house_info_column(cols: list[str]) -> str | None:
    if "房屋信息" in cols:
        return "房屋信息"
    for c in cols:
        if "房屋" in c and "信息" in c:
            return c
    return None


def _parse_house_done(hist: list[ExecutionRecord], col: str | None) -> bool:
    if not col:
        return True
    return any(
        h.get("tool") == "parse_house_info_column"
        and h.get("ok")
        and (h.get("arguments") or {}).get("column") == col
        for h in hist
    )


def _columns_and_profile(state: AgentState) -> tuple[list[str], dict[str, Any]]:
    prof = state.get("data_profile", {}) or {}
    return list(prof.get("columns", []) or []), prof


def _price_like_column(cols: list[str]) -> str | None:
    return next(
        (c for c in cols if any(k in c.lower() for k in ("价", "price", "总价"))),
        None,
    )


def _group_and_value_columns(cols: list[str]) -> tuple[str | None, str | None]:
    group_like = next(
        (c for c in cols if any(k in c for k in ("区", "区域", "地段", "location", "区县"))),
        None,
    )
    val_col = next((c for c in cols if any(k in c.lower() for k in ("价", "price", "均价"))), None)
    return group_like, val_col


def _parse_succeeded_for_column(hist: list[ExecutionRecord], col: str) -> bool:
    return any(
        h.get("tool") == "parse_numeric_column"
        and h.get("ok")
        and (h.get("arguments") or {}).get("column") == col
        for h in hist
    )


def _goal_implies_numeric_price_intent(goal: str) -> bool:
    """用户是否在问总价/预算/多少万等需数值比较的问题（轻量关键词）。"""
    g = (goal or "").strip()
    if not g:
        return False
    if any(
        k in g
        for k in ("总价", "预算", "万元", "不超过", "不低于", "万以下", "万以上", "万内", "多少万")
    ):
        return True
    return bool(re.search(r"\d+\s*万", g))


def _must_continue_for_price_pipeline(state: AgentState) -> bool:
    """总价列仍为文本且用户意图依赖数值比较时，observe 不应过早结束。"""
    if not _goal_implies_numeric_price_intent(str(state.get("goal", ""))):
        return False
    cols, prof = _columns_and_profile(state)
    price_like = _price_like_column(cols)
    if not price_like:
        return False
    dtypes = prof.get("dtypes", {}) or {}
    if dtypes.get(price_like) in ("float64", "int64", "Int64"):
        return False
    hist = state.get("execution_history") or []
    if _parse_succeeded_for_column(hist, price_like):
        return False
    return True


def _needs_price_parse(prof: dict[str, Any], hist: list[ExecutionRecord], cols: list[str]) -> bool:
    price_like = _price_like_column(cols)
    if not price_like:
        return False
    dtypes = prof.get("dtypes", {})
    if dtypes.get(price_like) in ("float64", "int64", "Int64"):
        return False
    return not _parse_succeeded_for_column(hist, price_like)


def _text_columns_for_search(cols: list[str]) -> list[str]:
    return [c for c in ("描述", "位置信息", "房屋信息") if c in cols]


def _terms_from_goal(goal: str) -> list[str]:
    """从用户目标抽取可能出现在房源文案中的短词（通用子串检索，非业务硬编码工具）。"""
    g = goal or ""
    bucket: list[str] = []
    if any(k in g for k in ("地铁", "近地铁", "轨道", "号线", "交通", "站点")):
        bucket.extend(["地铁", "轨道", "号线"])
    if any(k in g for k in ("阳台", "露台")):
        bucket.extend(["阳台", "露台"])
    if any(k in g for k in ("采光", "通透", "明厨", "明卫")):
        bucket.extend(["采光", "明厨", "明卫"])
    if any(k in g for k in ("学区", "学位", "学校", "名校")):
        bucket.extend(["学区", "学位", "学校"])
    if any(k in g for k in ("电梯", "梯户")):
        bucket.extend(["电梯", "梯户"])
    return list(dict.fromkeys(bucket))


def _mock_plan_soft_search(state: AgentState) -> PlanStepDict | None:
    cols, _ = _columns_and_profile(state)
    text_cols = _text_columns_for_search(cols)
    if not text_cols:
        return None
    hist = state.get("execution_history", [])
    if any(h.get("tool") == "search_text" for h in hist):
        return None
    terms = _terms_from_goal(str(state.get("goal", "") or ""))
    if not terms:
        return None
    return {
        "tool": "search_text",
        "arguments": {
            "columns": text_cols,
            "terms": terms,
            "how": "any_term_any_column",
            "case_insensitive": True,
        },
        "rationale": "用户目标含非结构化卖点，多列多词 OR 检索",
    }


def _mock_plan(state: AgentState) -> list[PlanStepDict]:
    hist = state.get("execution_history", [])
    cols, prof = _columns_and_profile(state)

    if not any(h.get("tool") == "get_basic_stats" for h in hist):
        return [{"tool": "get_basic_stats", "arguments": {}, "rationale": "先了解数值列分布"}]

    soft = _mock_plan_soft_search(state)
    if soft is not None:
        return [soft]

    hi = _house_info_column(cols)
    if hi and not _parse_house_done(hist, hi):
        return [
            {
                "tool": "parse_house_info_column",
                "arguments": {"column": hi},
                "rationale": "解析房屋信息中的户型/面积/装修等字段",
            }
        ]

    price_like = _price_like_column(cols)
    if price_like and not _parse_succeeded_for_column(hist, price_like):
        dtypes = prof.get("dtypes", {})
        if dtypes.get(price_like) not in ("float64", "int64", "Int64"):
            return [
                {
                    "tool": "parse_numeric_column",
                    "arguments": {"column": price_like},
                    "rationale": "将价格类文本转为数值",
                }
            ]

    group_like, val_col = _group_and_value_columns(cols)
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


def _llm_plan(state: AgentState) -> tuple[list[PlanStepDict], str | None]:
    tool_names = "\n".join(f"- {k}" for k in sorted(TOOL_REGISTRY))
    base_human = (
        PLAN_PROMPT.format(
            tool_names=tool_names,
            profile_excerpt=_profile_excerpt(state.get("data_profile", {})),
            prior_transcript=_prior_for_prompt(state),
            goal=state.get("goal", ""),
            history_excerpt=_history_excerpt(state.get("execution_history", [])),
        )
        + INTENT_AND_FILTER_GUIDE
    )
    if state.get("run_phase") == "clean":
        base_human += CLEAN_PHASE_PLAN_APPEND
    model = get_chat_model()
    structured = model.with_structured_output(PlanStructuredOutput)
    last_err = ""
    for attempt in (1, 2):
        human = base_human if attempt == 1 else base_human + format_plan_structure_retry_hint(last_err)
        try:
            out: PlanStructuredOutput = structured.invoke(
                [
                    SystemMessage(content=SYSTEM_ZH),
                    HumanMessage(content=human),
                ]
            )
            steps = plan_steps_to_plan_dicts(list(out.steps))[:3]
            if steps:
                return steps, None
            last_err = "模型返回了空的 steps（steps 数组长度为 0）"
            logger.warning("LLM plan empty steps (attempt %s)", attempt)
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            logger.warning("LLM plan failed (attempt %s): %s", attempt, e)
    return [], last_err or "计划生成失败"


def plan_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config
    t0 = time.perf_counter()
    sid = state.get("session_id", "")
    try:
        if state.get("stop_reason") == "error" and not state.get("data_profile"):
            return {"plan": [], "plan_generation_error": None}
        if _use_mock_llm():
            steps = _mock_plan(state)
            return {"plan": steps, "plan_generation_error": None}
        steps, err = _llm_plan(state)
        if err or not steps:
            fallback = _mock_plan(state)
            if fallback:
                _log_hi_timing(
                    "plan_degraded=mock",
                    session_id=sid,
                    reason=(err or "empty_steps")[:240],
                )
                return {"plan": fallback, "plan_generation_error": None}
            return {"plan": [], "plan_generation_error": err or "计划为空且规则降级无可用步骤"}
        return {"plan": steps, "plan_generation_error": None}
    finally:
        _log_hi_timing("node=plan", session_id=sid, duration_ms=f"{(time.perf_counter() - t0) * 1000:.1f}")


def execute_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config
    node_t0 = time.perf_counter()
    sid = state["session_id"]
    try:
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
            err = state.get("plan_generation_error") or "计划为空"
            rec = {
                "tool": "",
                "arguments": {},
                "ok": False,
                "summary": {},
                "error": err,
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
        ok = bool(payload.get("ok"))
        _log_hi_timing(
            "tool",
            session_id=sid,
            name=tool or "(empty)",
            ok=ok,
            duration_ms=f"{dt:.1f}",
        )
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
            "ok": ok,
            "summary": payload,
            "error": None if payload.get("ok") else str(payload.get("error")),
            "duration_ms": dt,
        }
        return {"plan": remaining, "execution_history": [rec]}
    finally:
        _log_hi_timing(
            "node=execute",
            session_id=sid,
            duration_ms=f"{(time.perf_counter() - node_t0) * 1000:.1f}",
        )


def _mock_observe(state: AgentState) -> dict[str, Any]:
    """与 _mock_plan 对齐的里程碑式结束条件（SPEC §13 自主性）。"""
    hist = state.get("execution_history", [])
    last = hist[-1] if hist else None
    cols, prof = _columns_and_profile(state)
    plan = state.get("plan") or []

    if last and last.get("ok") is False:
        return {"should_finish": True, "stop_reason": "error", "notes": "工具执行失败，结束循环。"}

    if state.get("run_phase") == "clean" and last and last.get("ok"):
        t = last.get("tool")
        if t == "parse_numeric_column":
            return {
                "should_finish": True,
                "stop_reason": "completed",
                "notes": "清洗阶段：价格列已解析，可进入对话分析。",
            }
        if t == "get_basic_stats":
            if _needs_price_parse(prof, hist, cols):
                return {
                    "should_finish": False,
                    "stop_reason": "completed",
                    "notes": "清洗阶段：基础统计完成，下一步解析价格列。",
                }
            return {
                "should_finish": True,
                "stop_reason": "completed",
                "notes": "清洗阶段：基础画像已具备，深入工具请留给后续用户提问。",
            }

    if any(h.get("tool") == "group_by_summary" and h.get("ok") for h in hist):
        if _must_continue_for_price_pipeline(state):
            return {
                "should_finish": False,
                "stop_reason": "completed",
                "notes": "用户含价格数值条件，须先解析总价列再继续。",
            }
        return {"should_finish": True, "stop_reason": "completed", "notes": "已完成分组聚合（mock）。"}

    if any(h.get("tool") == "top_k_values" and h.get("ok") for h in hist):
        if _must_continue_for_price_pipeline(state):
            return {
                "should_finish": False,
                "stop_reason": "completed",
                "notes": "用户含价格数值条件，须先解析总价列再继续。",
            }
        return {"should_finish": True, "stop_reason": "completed", "notes": "已完成高频值统计（mock）。"}

    # execute 每步会清空剩余 plan；空队列不代表任务结束，需看 _mock_plan 是否还有后续
    if not plan:
        if not hist:
            return {"should_finish": False, "stop_reason": "completed", "notes": "等待首轮计划。"}
        if last and last.get("ok") and not _mock_plan(state):
            if _must_continue_for_price_pipeline(state):
                return {
                    "should_finish": False,
                    "stop_reason": "completed",
                    "notes": "用户含价格数值条件，须先解析总价列再继续。",
                }
            return {"should_finish": True, "stop_reason": "completed", "notes": "无后续步骤（mock）。"}
        return {"should_finish": False, "stop_reason": "completed", "notes": "本轮计划已消费，继续规划。"}

    if state.get("run_phase") != "clean" and last and last.get("tool") == "get_basic_stats" and last.get("ok"):
        return {"should_finish": False, "stop_reason": "completed", "notes": "基础统计完成，继续清洗/分析。"}

    if last and last.get("tool") == "search_text" and last.get("ok"):
        return {"should_finish": False, "stop_reason": "completed", "notes": "文本检索完成，继续解析/聚合。"}

    if last and last.get("tool") == "parse_house_info_column" and last.get("ok"):
        return {"should_finish": False, "stop_reason": "completed", "notes": "房屋信息解析完成，继续价格/筛选。"}

    if state.get("run_phase") != "clean" and last and last.get("tool") == "parse_numeric_column" and last.get("ok"):
        return {"should_finish": False, "stop_reason": "completed", "notes": "价格列解析完成，继续聚合。"}

    if _needs_price_parse(prof, hist, cols):
        return {"should_finish": False, "stop_reason": "completed", "notes": "仍需解析价格列。"}

    group_like, val_col = _group_and_value_columns(cols)
    if group_like and val_col and not any(h.get("tool") == "group_by_summary" for h in hist):
        return {"should_finish": False, "stop_reason": "completed", "notes": "等待分组聚合。"}

    return {"should_finish": False, "stop_reason": "completed", "notes": "继续下一步。"}


def _llm_observe(state: AgentState) -> dict[str, Any]:
    hist = state.get("execution_history", [])
    last = hist[-1] if hist else {}
    if isinstance(last, dict) and last.get("ok") is False and last.get("error"):
        return {
            "should_finish": True,
            "stop_reason": "error",
            "notes": f"工具或计划失败：{last.get('error')}",
        }
    prompt = OBSERVE_PROMPT.format(
        prior_transcript=_prior_for_prompt(state),
        goal=state.get("goal", ""),
        last_result=json.dumps(last, ensure_ascii=False),
    )
    if state.get("run_phase") == "clean":
        prompt += CLEAN_PHASE_OBSERVE_APPEND
    model = get_chat_model()
    structured = model.with_structured_output(ObserveLLMOutput)
    try:
        out: ObserveLLMOutput = structured.invoke(
            [SystemMessage(content=SYSTEM_ZH), HumanMessage(content=prompt)]
        )
        if out.should_finish and _must_continue_for_price_pipeline(state):
            return {
                "should_finish": False,
                "stop_reason": "completed",
                "notes": "用户含价格数值条件，总价列尚未解析为数值，应继续 parse_numeric_column 再筛选。",
            }
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
    t0 = time.perf_counter()
    sid = state.get("session_id", "")
    max_iter = int(state.get("max_iterations") or get_settings().max_iterations)
    it = int(state.get("iteration", 0)) + 1
    updates: dict[str, Any] = {"iteration": it}
    try:
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
    finally:
        _log_hi_timing(
            "node=observe",
            session_id=sid,
            iteration=it,
            should_finish=updates.get("should_finish"),
            stop_reason=updates.get("stop_reason", ""),
            duration_ms=f"{(time.perf_counter() - t0) * 1000:.1f}",
        )


def answer_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    del config
    t0 = time.perf_counter()
    sid = state.get("session_id", "")
    try:
        if _use_mock_llm():
            prof = state.get("data_profile", {})
            n = prof.get("n_rows", "未知")
            sr = state.get("stop_reason", "") or "completed"
            lines = [
                "## 分析结论（mock 模式）",
                f"- 数据行数：**{n}**",
                f"- 停止原因：**{sr}**",
                "- 已执行工具摘要见会话状态 `execution_history`。",
            ]
            if sr == "error":
                err_hint = ""
                hist = state.get("execution_history") or []
                if hist and isinstance(hist[-1], dict) and hist[-1].get("error"):
                    err_hint = f"\n- 最近错误：**{hist[-1].get('error')}**"
                lines.append(err_hint or "\n- 最近一步执行失败，请查看 `execution_history` 中的 error。")
            text = "\n".join(lines)
            return {"final_answer": text, "messages": [AIMessage(content=text)]}

        prompt = ANSWER_PROMPT.format(
            prior_transcript=_prior_for_prompt(state),
            goal=state.get("goal", ""),
            profile_excerpt=_profile_excerpt(state.get("data_profile", {})),
            history_excerpt=_history_excerpt(state.get("execution_history", [])),
        )
        model = get_chat_model()
        try:
            resp = model.invoke([SystemMessage(content=SYSTEM_ZH), HumanMessage(content=prompt)])
            text = getattr(resp, "content", str(resp))
            fa = str(text)
            return {"final_answer": fa, "messages": [AIMessage(content=fa)]}
        except Exception as e:  # noqa: BLE001
            logger.warning("answer LLM failed, fallback to summary: %s", e)
            prof = state.get("data_profile", {}) or {}
            n = prof.get("n_rows", "未知")
            lines = [
                "## 分析结论（模型不可用时的摘要）",
                f"- 数据行数：**{n}**",
                f"- 停止原因：**{state.get('stop_reason', '') or 'completed'}**",
                "- 已执行工具见 `execution_history`；若需完整结论请检查 API Key 与网络后重试。",
            ]
            fa = "\n".join(lines)
            return {"final_answer": fa, "messages": [AIMessage(content=fa)]}
    finally:
        _log_hi_timing("node=answer", session_id=sid, duration_ms=f"{(time.perf_counter() - t0) * 1000:.1f}")


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

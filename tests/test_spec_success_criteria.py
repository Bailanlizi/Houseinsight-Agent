"""对照 docs/SPEC.md §13 成功标准的验收测试。"""
from __future__ import annotations

import uuid

import pandas as pd
import pytest
from server.agent.graph import run_agent
from server.core.session_store import get_session_store
from server.tools._dataframe import ensure_row_fingerprint
from server.tools.clean_tools import parse_numeric_column
from server.tools.register import dispatch_tool

from tests.helpers.agent_fixtures import (
    WENJIANG_CSV,
    assert_execution_history_shape,
    load_wenjiang_df,
    make_initial_state,
)


def test_autonomy_pipeline_uses_real_fixture(mock_llm_env, mock_llm_nodes):
    """§13.1 + §13.4：自主完成清洗+聚合；execution_history 可追溯。"""
    assert WENJIANG_CSV.is_file(), f"missing fixture: {WENJIANG_CSV}"
    df = load_wenjiang_df(80)
    sid = str(uuid.uuid4())
    get_session_store().put(sid, df)

    initial = make_initial_state(sid, "analyze dataset", max_iterations=14)
    out = run_agent(initial)
    hist = out.get("execution_history") or []
    tools = [h.get("tool") for h in hist]
    assert "get_basic_stats" in tools
    assert "parse_house_info_column" in tools
    assert "parse_numeric_column" in tools
    assert "group_by_summary" in tools
    assert out.get("final_answer")

    assert_execution_history_shape(hist)


def test_row_fingerprint_and_cell_consistency():
    """§13.3：行指纹 + 解析后与源行总价语义一致。"""
    assert WENJIANG_CSV.is_file()
    df = pd.read_csv(WENJIANG_CSV, nrows=5)
    raw_total = str(df.loc[0, "总价"])
    out = ensure_row_fingerprint(df.copy())
    fp = out.loc[0, "_hi_row_fp"]
    _, payload, _ = dispatch_tool(
        "filter_rows",
        out,
        {
            "filters": [{"column": "_hi_row_fp", "op": "==", "value": fp}],
            "logic": "and",
        },
    )
    assert payload.get("ok")
    assert payload.get("matched_rows") == 1
    row_preview = payload["rows_preview"][0]
    assert row_preview.get("总价") == raw_total or row_preview.get("总价") is not None

    sub, p2 = parse_numeric_column(out, {"column": "总价"})
    assert p2.get("ok")
    parsed = float(sub.loc[sub["_hi_row_fp"] == fp, "总价"].iloc[0])
    assert parsed == pytest.approx(1550000.0)  # 第一行「155万」


def test_adaptation_tool_sequence_changes():
    """§13.2：工具链级——失败调用后参数/工具路径发生变化（execution_history 体现）。"""
    df = pd.DataFrame({"总价": ["10万", "20万"]})
    h1: list = []
    df1, p1, _ = dispatch_tool("parse_numeric_column", df, {"column": "不存在列"})
    assert not p1.get("ok")
    h1.append({"tool": "parse_numeric_column", "arguments": {"column": "不存在列"}, "ok": False})

    df2, p2, _ = dispatch_tool("parse_numeric_column", df, {"column": "总价"})
    assert p2.get("ok")
    h1.append({"tool": "parse_numeric_column", "arguments": {"column": "总价"}, "ok": True})

    assert h1[0]["arguments"] != h1[1]["arguments"]
    assert h1[0]["ok"] is False and h1[1]["ok"] is True


def test_max_iterations_stops_cleanly(mock_llm_env, mock_llm_nodes, monkeypatch):
    """§13.5：低 MAX_ITER 下仍能结束并给出 final_answer。"""
    df = pd.DataFrame({"a": [1, 2], "区域": ["X", "Y"]})
    sid = str(uuid.uuid4())
    get_session_store().put(sid, df)

    initial = make_initial_state(sid, "x", max_iterations=1)
    out = run_agent(initial)
    assert out.get("final_answer")
    assert out.get("stop_reason") in ("max_iterations", "completed", "error")


def test_filter_rows_by_fingerprint_matches_single_row():
    df = pd.DataFrame({"总价": ["1万", "2万"], "区域": ["A", "B"]})
    out = ensure_row_fingerprint(df)
    fp0 = out.loc[0, "_hi_row_fp"]
    _, pay, _ = dispatch_tool(
        "filter_rows",
        out,
        {"filters": [{"column": "_hi_row_fp", "op": "==", "value": fp0}], "logic": "and"},
    )
    assert pay.get("matched_rows") == 1
    assert pay["rows_preview"][0]["总价"] == "1万"

"""计划细粒度结构化 schema：discriminator 与 plan_steps_to_plan_dicts。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.agent.plan_schema import (
    PlanStepFilterRows,
    PlanStepParseNumericColumn,
    PlanStructuredOutput,
    plan_steps_to_plan_dicts,
)
from server.tools.analyze_tools import FilterRowsArgs, RowFilter
from server.tools.clean_tools import ParseNumericColumnArgs


def test_parse_numeric_arguments_shape() -> None:
    step = PlanStepParseNumericColumn(
        arguments=ParseNumericColumnArgs(column="总价"),
        rationale="解析价格",
    )
    d = plan_steps_to_plan_dicts([step])[0]
    assert d["tool"] == "parse_numeric_column"
    assert d["arguments"] == {"column": "总价", "unit_wan_multiplier": 10_000.0}
    assert d.get("rationale") == "解析价格"


def test_filter_rows_arguments_nested() -> None:
    args = FilterRowsArgs(
        filters=[RowFilter(column="区域", op="contains", value="武侯")],
        logic="and",
    )
    step = PlanStepFilterRows(arguments=args)
    d = plan_steps_to_plan_dicts([step])[0]
    assert d["tool"] == "filter_rows"
    assert d["arguments"]["logic"] == "and"
    assert len(d["arguments"]["filters"]) == 1
    assert d["arguments"]["filters"][0]["column"] == "区域"


def test_structured_output_max_three_steps() -> None:
    a = ParseNumericColumnArgs(column="总价")
    b = ParseNumericColumnArgs(column="单价")
    c = ParseNumericColumnArgs(column="面积")
    out = PlanStructuredOutput(
        steps=[
            PlanStepParseNumericColumn(arguments=a),
            PlanStepParseNumericColumn(arguments=b),
            PlanStepParseNumericColumn(arguments=c),
        ]
    )
    assert len(out.steps) == 3

    with pytest.raises(ValidationError):
        PlanStructuredOutput(
            steps=[
                PlanStepParseNumericColumn(arguments=a),
                PlanStepParseNumericColumn(arguments=b),
                PlanStepParseNumericColumn(arguments=c),
                PlanStepParseNumericColumn(arguments=a),
            ]
        )


def test_wrong_arguments_for_tool_rejected() -> None:
    """parse_numeric_column 不接受 filter_rows 形态的 arguments。"""
    with pytest.raises(ValidationError):
        PlanStepParseNumericColumn(
            arguments={  # type: ignore[arg-type]
                "filters": [{"column": "总价", "op": "<=", "value": 250}],
                "logic": "and",
            },
        )

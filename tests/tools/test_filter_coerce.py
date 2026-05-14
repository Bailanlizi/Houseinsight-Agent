import pandas as pd

from server.tools.analyze_tools import coerce_filter_rows_arguments, filter_rows


def test_coerce_filter_conditions():
    raw = {"filter_conditions": {"描述": "地铁", "区域": "温江"}, "logic": "and"}
    coerced = coerce_filter_rows_arguments(raw)
    assert "filters" in coerced
    assert len(coerced["filters"]) == 2
    df = pd.DataFrame({"描述": ["近地铁", "远郊"], "区域": ["温江", "温江"]})
    _, out = filter_rows(df, raw)
    assert out["ok"]
    assert out["matched_rows"] == 1


def test_coerce_nested_structured_filter():
    raw = {"structured_filter": {"filter_conditions": {"总价": "100"}}}
    coerced = coerce_filter_rows_arguments(raw)
    assert coerced["filters"]

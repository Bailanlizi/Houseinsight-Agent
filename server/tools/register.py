from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from server.tools.analyze_tools import (
    CorrelationArgs,
    FilterRowsArgs,
    GroupBySummaryArgs,
    TopKValuesArgs,
    correlation_analysis,
    filter_rows,
    group_by_summary,
    top_k_values,
)
from server.tools.clean_tools import (
    FillMissingArgs,
    FilterOutliersArgs,
    ParseNumericColumnArgs,
    RemoveDuplicatesArgs,
    fill_missing,
    filter_outliers,
    parse_numeric_column,
    remove_duplicates,
)
from server.tools.explore_tools import GetBasicStatsArgs, GetDataProfileArgs, get_basic_stats, get_data_profile
from server.tools.search_tools import CompareCleaningResultsArgs, SearchListingsArgs, compare_cleaning_results, search_listings

ToolFn = Callable[[pd.DataFrame, dict[str, Any]], tuple[pd.DataFrame, dict[str, Any]]]


class ToolSpec:
    def __init__(self, fn: ToolFn, mutates: bool) -> None:
        self.fn = fn
        self.mutates = mutates


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "get_data_profile": ToolSpec(lambda df, a: get_data_profile(df, a), mutates=False),
    "get_basic_stats": ToolSpec(lambda df, a: get_basic_stats(df, a), mutates=False),
    "remove_duplicates": ToolSpec(lambda df, a: remove_duplicates(df, RemoveDuplicatesArgs.model_validate(a)), mutates=True),
    "filter_outliers": ToolSpec(lambda df, a: filter_outliers(df, FilterOutliersArgs.model_validate(a)), mutates=True),
    "fill_missing": ToolSpec(lambda df, a: fill_missing(df, FillMissingArgs.model_validate(a)), mutates=True),
    "parse_numeric_column": ToolSpec(
        lambda df, a: parse_numeric_column(df, ParseNumericColumnArgs.model_validate(a)),
        mutates=True,
    ),
    "group_by_summary": ToolSpec(lambda df, a: group_by_summary(df, GroupBySummaryArgs.model_validate(a)), mutates=False),
    "filter_rows": ToolSpec(lambda df, a: filter_rows(df, FilterRowsArgs.model_validate(a)), mutates=False),
    "correlation_analysis": ToolSpec(
        lambda df, a: correlation_analysis(df, CorrelationArgs.model_validate(a)),
        mutates=False,
    ),
    "top_k_values": ToolSpec(lambda df, a: top_k_values(df, TopKValuesArgs.model_validate(a)), mutates=False),
    "search_listings": ToolSpec(lambda df, a: search_listings(df, SearchListingsArgs.model_validate(a)), mutates=False),
    "compare_cleaning_results": ToolSpec(
        lambda df, a: compare_cleaning_results(df, CompareCleaningResultsArgs.model_validate(a)),
        mutates=False,
    ),
}


def dispatch_tool(name: str, df: pd.DataFrame, arguments: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], bool]:
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return df, {"ok": False, "error": f"未知工具: {name}"}, False
    new_df, payload = spec.fn(df, arguments)
    return new_df, payload, spec.mutates

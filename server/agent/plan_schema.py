"""计划阶段细粒度结构化输出：每步 tool 与 arguments 类型一一对应（Pydantic discriminated union）。"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

from server.agent.state import PlanStepDict
from server.tools.analyze_tools import (
    CorrelationArgs,
    FilterRowsArgs,
    GroupBySummaryArgs,
    SearchTextArgs,
    TopKValuesArgs,
)
from server.tools.clean_tools import (
    FillMissingArgs,
    FilterOutliersArgs,
    ParseNumericColumnArgs,
    RemoveDuplicatesArgs,
)
from server.tools.explore_tools import GetBasicStatsArgs, GetDataProfileArgs
from server.tools.house_tools import ParseHouseInfoColumnArgs
from server.tools.search_tools import CompareCleaningResultsArgs, SearchListingsArgs


class PlanStepGetDataProfile(BaseModel):
    tool: Literal["get_data_profile"] = "get_data_profile"
    arguments: GetDataProfileArgs = Field(default_factory=GetDataProfileArgs)
    rationale: str | None = None


class PlanStepGetBasicStats(BaseModel):
    tool: Literal["get_basic_stats"] = "get_basic_stats"
    arguments: GetBasicStatsArgs = Field(default_factory=GetBasicStatsArgs)
    rationale: str | None = None


class PlanStepRemoveDuplicates(BaseModel):
    tool: Literal["remove_duplicates"] = "remove_duplicates"
    arguments: RemoveDuplicatesArgs
    rationale: str | None = None


class PlanStepFilterOutliers(BaseModel):
    tool: Literal["filter_outliers"] = "filter_outliers"
    arguments: FilterOutliersArgs
    rationale: str | None = None


class PlanStepFillMissing(BaseModel):
    tool: Literal["fill_missing"] = "fill_missing"
    arguments: FillMissingArgs
    rationale: str | None = None


class PlanStepParseNumericColumn(BaseModel):
    tool: Literal["parse_numeric_column"] = "parse_numeric_column"
    arguments: ParseNumericColumnArgs
    rationale: str | None = None


class PlanStepParseHouseInfoColumn(BaseModel):
    tool: Literal["parse_house_info_column"] = "parse_house_info_column"
    arguments: ParseHouseInfoColumnArgs = Field(default_factory=ParseHouseInfoColumnArgs)
    rationale: str | None = None


class PlanStepGroupBySummary(BaseModel):
    tool: Literal["group_by_summary"] = "group_by_summary"
    arguments: GroupBySummaryArgs
    rationale: str | None = None


class PlanStepFilterRows(BaseModel):
    tool: Literal["filter_rows"] = "filter_rows"
    arguments: FilterRowsArgs
    rationale: str | None = None


class PlanStepSearchText(BaseModel):
    tool: Literal["search_text"] = "search_text"
    arguments: SearchTextArgs
    rationale: str | None = None


class PlanStepCorrelationAnalysis(BaseModel):
    tool: Literal["correlation_analysis"] = "correlation_analysis"
    arguments: CorrelationArgs
    rationale: str | None = None


class PlanStepTopKValues(BaseModel):
    tool: Literal["top_k_values"] = "top_k_values"
    arguments: TopKValuesArgs
    rationale: str | None = None


class PlanStepSearchListings(BaseModel):
    tool: Literal["search_listings"] = "search_listings"
    arguments: SearchListingsArgs
    rationale: str | None = None


class PlanStepCompareCleaningResults(BaseModel):
    tool: Literal["compare_cleaning_results"] = "compare_cleaning_results"
    arguments: CompareCleaningResultsArgs
    rationale: str | None = None


PlanStepUnion = Annotated[
    Union[
        PlanStepGetDataProfile,
        PlanStepGetBasicStats,
        PlanStepRemoveDuplicates,
        PlanStepFilterOutliers,
        PlanStepFillMissing,
        PlanStepParseNumericColumn,
        PlanStepParseHouseInfoColumn,
        PlanStepGroupBySummary,
        PlanStepFilterRows,
        PlanStepSearchText,
        PlanStepCorrelationAnalysis,
        PlanStepTopKValues,
        PlanStepSearchListings,
        PlanStepCompareCleaningResults,
    ],
    Field(discriminator="tool"),
]


class PlanStructuredOutput(BaseModel):
    """供 `with_structured_output` 使用；每步 arguments 与 tool 绑定，避免混用 filter_rows 形态。"""

    steps: list[PlanStepUnion] = Field(default_factory=list, max_length=3)


def plan_steps_to_plan_dicts(steps: list[Any]) -> list[PlanStepDict]:
    """转为图 execute 使用的 PlanStepDict（arguments 为 plain dict）。"""
    out: list[PlanStepDict] = []
    for step in steps:
        d = step.model_dump(mode="python", exclude_none=True)
        tool = str(d["tool"])
        arguments = d.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = dict(arguments) if hasattr(arguments, "__iter__") else {}
        item: PlanStepDict = {"tool": tool, "arguments": arguments}
        r = d.get("rationale")
        if r is not None:
            item["rationale"] = r
        out.append(item)
    return out

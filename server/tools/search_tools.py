from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from server.tools.analyze_tools import FilterRowsArgs, filter_rows


class SearchListingsArgs(BaseModel):
    """由 LLM 将自然语言解析后的结构化条件（SPEC）。"""

    structured_filter: dict[str, Any]
    limit: int = Field(default=50, ge=1, le=200)


def search_listings(df: pd.DataFrame, args: SearchListingsArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, SearchListingsArgs):
        args = SearchListingsArgs.model_validate(args)
    try:
        inner = FilterRowsArgs.model_validate(args.structured_filter)
    except Exception as e:  # noqa: BLE001
        return df, {
            "ok": False,
            "tool": "search_listings",
            "error": f"结构化条件无效: {e}",
            "clarify": "请提供更明确的筛选列名与比较关系。",
        }
    _df2, payload = filter_rows(df, inner)
    if not payload.get("ok"):
        return df, {"ok": False, "tool": "search_listings", "error": payload.get("error", "筛选失败")}
    preview = payload.get("rows_preview", [])
    if args.limit < len(preview):
        preview = preview[: args.limit]
    return df, {
        "ok": True,
        "tool": "search_listings",
        "matched_rows": payload.get("matched_rows"),
        "rows_preview": preview,
        "truncated": payload.get("truncated", False),
    }


class CompareCleaningResultsArgs(BaseModel):
    before_profile: dict[str, Any]
    after_profile: dict[str, Any]


def compare_cleaning_results(
    df: pd.DataFrame, args: CompareCleaningResultsArgs | dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, CompareCleaningResultsArgs):
        args = CompareCleaningResultsArgs.model_validate(args)
    b = args.before_profile
    a = args.after_profile
    out = {
        "ok": True,
        "tool": "compare_cleaning_results",
        "rows": {"before": b.get("n_rows"), "after": a.get("n_rows")},
        "columns": {"before": b.get("n_columns"), "after": a.get("n_columns")},
        "missing_rate_delta": _delta_missing(b.get("missing_rate", {}), a.get("missing_rate", {})),
    }
    return df, out


def _delta_missing(b: dict[str, float], a: dict[str, float]) -> dict[str, float]:
    keys = set(b) | set(a)
    return {k: float(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys}

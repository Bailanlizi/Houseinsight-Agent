from __future__ import annotations

from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field

from server.tools._dataframe import truncate_records

Op = Literal["==", "!=", "<", ">", "<=", ">=", "in", "contains"]


class RowFilter(BaseModel):
    column: str
    op: Op
    value: Any


class FilterRowsArgs(BaseModel):
    filters: list[RowFilter]
    logic: Literal["and", "or"] = "and"


def _apply_one(df: pd.DataFrame, f: RowFilter) -> pd.Series:
    if f.column not in df.columns:
        raise KeyError(f.column)
    col = df[f.column]
    if f.op == "contains":
        return col.astype(str).str.contains(str(f.value), na=False)
    if f.op == "in":
        if not isinstance(f.value, (list, tuple, set)):
            raise ValueError("in 操作需要 list/tuple/set 作为 value")
        return col.isin(list(f.value))
    left = col
    right = f.value
    if f.op in {"<", ">", "<=", ">="}:
        left = pd.to_numeric(col, errors="coerce")
        right = float(right) if right is not None else right
    ops = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "<": lambda a, b: a < b,
        ">": lambda a, b: a > b,
        "<=": lambda a, b: a <= b,
        ">=": lambda a, b: a >= b,
    }
    fn = ops.get(f.op)
    if fn is None:
        raise ValueError(f"不支持操作符: {f.op}")
    return fn(left, right)


def filter_rows(df: pd.DataFrame, args: FilterRowsArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, FilterRowsArgs):
        args = FilterRowsArgs.model_validate(args)
    try:
        masks = [_apply_one(df, f) for f in args.filters]
        if not masks:
            sub = df
        elif args.logic == "and":
            m = masks[0]
            for x in masks[1:]:
                m = m & x
            sub = df.loc[m]
        else:
            m = masks[0]
            for x in masks[1:]:
                m = m | x
            sub = df.loc[m]
        recs, trunc = truncate_records(sub.to_dict(orient="records"), limit=50)
        return df, {
            "ok": True,
            "tool": "filter_rows",
            "matched_rows": int(len(sub)),
            "rows_preview": recs,
            "truncated": trunc,
        }
    except Exception as e:  # noqa: BLE001
        return df, {"ok": False, "tool": "filter_rows", "error": str(e)}


class GroupBySummaryArgs(BaseModel):
    group_by: str
    value: str
    stat: Literal["mean", "median", "sum", "count", "min", "max"]


def group_by_summary(df: pd.DataFrame, args: GroupBySummaryArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, GroupBySummaryArgs):
        args = GroupBySummaryArgs.model_validate(args)
    for c in (args.group_by, args.value):
        if c not in df.columns:
            return df, {"ok": False, "tool": "group_by_summary", "error": f"列不存在: {c}"}
    num = pd.to_numeric(df[args.value], errors="coerce")
    df2 = df.assign(__v=num)
    g2 = df2.groupby(args.group_by, dropna=False)["__v"]
    stat_fn = {
        "mean": "mean",
        "median": "median",
        "sum": "sum",
        "count": "count",
        "min": "min",
        "max": "max",
    }[args.stat]
    agg = getattr(g2, stat_fn)()
    rows = [{"group": str(k), args.stat: (None if v is pd.NA else float(v))} for k, v in agg.items()]
    rows, trunc = truncate_records(rows, limit=50)
    return df, {"ok": True, "tool": "group_by_summary", "result": rows, "truncated": trunc}


class CorrelationArgs(BaseModel):
    column_a: str
    column_b: str


def correlation_analysis(df: pd.DataFrame, args: CorrelationArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, CorrelationArgs):
        args = CorrelationArgs.model_validate(args)
    for c in (args.column_a, args.column_b):
        if c not in df.columns:
            return df, {"ok": False, "tool": "correlation_analysis", "error": f"列不存在: {c}"}
    a = pd.to_numeric(df[args.column_a], errors="coerce")
    b = pd.to_numeric(df[args.column_b], errors="coerce")
    m = a.notna() & b.notna()
    if m.sum() < 2:
        return df, {"ok": False, "tool": "correlation_analysis", "error": "有效样本不足"}
    r = float(a[m].corr(b[m]))
    return df, {"ok": True, "tool": "correlation_analysis", "pearson": r, "n": int(m.sum())}


class TopKValuesArgs(BaseModel):
    column: str
    k: int = Field(default=10, ge=1, le=100)


def top_k_values(df: pd.DataFrame, args: TopKValuesArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, TopKValuesArgs):
        args = TopKValuesArgs.model_validate(args)
    if args.column not in df.columns:
        return df, {"ok": False, "tool": "top_k_values", "error": f"列不存在: {args.column}"}
    vc = df[args.column].value_counts(dropna=False).head(args.k)
    rows = [{"value": str(k), "count": int(v)} for k, v in vc.items()]
    return df, {"ok": True, "tool": "top_k_values", "top": rows}

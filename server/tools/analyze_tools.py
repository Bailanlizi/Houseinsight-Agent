from __future__ import annotations

import re
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


def coerce_filter_rows_arguments(raw: dict[str, Any]) -> dict[str, Any]:
    """将 LLM 常见别名（filter_conditions / structured_filter）转为 FilterRowsArgs 所需结构。"""
    if not isinstance(raw, dict):
        raise TypeError("filter_rows 参数须为对象")
    if "filters" in raw:
        return {"filters": raw["filters"], "logic": raw.get("logic", "and")}
    if "structured_filter" in raw:
        inner = raw["structured_filter"]
        if isinstance(inner, dict):
            return coerce_filter_rows_arguments(inner)
        raise ValueError("structured_filter 须为对象")
    if "filter_conditions" in raw:
        fc = raw["filter_conditions"]
        logic = raw.get("logic", "and")
        if logic not in ("and", "or"):
            logic = "and"
        if not isinstance(fc, dict):
            raise ValueError("filter_conditions 须为列名到条件的字典")
        filters: list[dict[str, Any]] = []
        for col, val in fc.items():
            col_s = str(col)
            if isinstance(val, dict):
                op = str(val.get("op", "contains"))
                if op not in ("==", "!=", "<", ">", "<=", ">=", "in", "contains"):
                    op = "contains"
                filters.append({"column": col_s, "op": op, "value": val.get("value")})
            elif isinstance(val, (list, tuple, set)):
                filters.append({"column": col_s, "op": "in", "value": list(val)})
            else:
                filters.append({"column": col_s, "op": "contains", "value": str(val)})
        return {"filters": filters, "logic": logic}
    raise ValueError(
        "filter_rows 必须使用 filters 数组，例如："
        '{"filters":[{"column":"描述","op":"contains","value":"地铁"}],"logic":"and"}；'
        "也允许使用 filter_conditions 简写（自动转为 contains/in）。"
    )


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
    try:
        if isinstance(args, FilterRowsArgs):
            validated = args
        else:
            coerced = coerce_filter_rows_arguments(dict(args))
            validated = FilterRowsArgs.model_validate(coerced)
    except Exception as e:  # noqa: BLE001
        return df, {"ok": False, "tool": "filter_rows", "error": str(e)}
    try:
        masks = [_apply_one(df, f) for f in validated.filters]
        if not masks:
            sub = df
        elif validated.logic == "and":
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


HowMatch = Literal["any_term_any_column", "all_terms_concat"]


class SearchTextArgs(BaseModel):
    """在多个文本列上做子串检索；用于卖点/交通/采光等非结构化表述（多同义词 OR、多列 OR）。"""

    columns: list[str] = Field(min_length=1, max_length=32)
    terms: list[str] = Field(min_length=1, max_length=32)
    how: HowMatch = "any_term_any_column"
    case_insensitive: bool = True


def _normalize_terms(terms: list[str]) -> list[str]:
    out: list[str] = []
    for t in terms:
        s = str(t).strip()
        if s and s not in out:
            out.append(s)
    return out


def search_text(df: pd.DataFrame, args: SearchTextArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """通用文本检索：不绑定具体业务词，由调用方传入列名与同义词列表。"""
    try:
        if isinstance(args, SearchTextArgs):
            validated = args
        else:
            validated = SearchTextArgs.model_validate(dict(args))
    except Exception as e:  # noqa: BLE001
        return df, {"ok": False, "tool": "search_text", "error": str(e)}

    terms = _normalize_terms(list(validated.terms))
    if not terms:
        return df, {"ok": False, "tool": "search_text", "error": "terms 去空后须至少包含一个非空关键词"}

    cols = [str(c) for c in validated.columns]
    for c in cols:
        if c not in df.columns:
            return df, {"ok": False, "tool": "search_text", "error": f"列不存在: {c}"}

    try:
        if validated.how == "any_term_any_column":
            m = pd.Series(False, index=df.index)
            for c in cols:
                s = df[c].astype(str)
                for t in terms:
                    pat = re.escape(t) if t else ""
                    if not pat:
                        continue
                    m = m | s.str.contains(pat, case=not validated.case_insensitive, na=False, regex=True)
            sub = df.loc[m]
        else:
            # all_terms_concat：行内拼接所选列后，须同时包含每一个关键词（适合「地铁+阳台」等 AND）
            parts = [df[c].astype(str) for c in cols]
            blob = parts[0]
            for p in parts[1:]:
                blob = blob + " " + p
            text = blob
            m = pd.Series(True, index=df.index)
            for t in terms:
                pat = re.escape(t)
                m = m & text.str.contains(pat, case=not validated.case_insensitive, na=False, regex=True)
            sub = df.loc[m]

        recs, trunc = truncate_records(sub.to_dict(orient="records"), limit=50)
        return df, {
            "ok": True,
            "tool": "search_text",
            "matched_rows": int(len(sub)),
            "rows_preview": recs,
            "truncated": trunc,
            "how": validated.how,
            "columns_used": cols,
            "terms_used": terms,
        }
    except Exception as e:  # noqa: BLE001
        return df, {"ok": False, "tool": "search_text", "error": str(e)}


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

from __future__ import annotations

import re
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field


class RemoveDuplicatesArgs(BaseModel):
    subset: list[str]


def remove_duplicates(df: pd.DataFrame, args: RemoveDuplicatesArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, RemoveDuplicatesArgs):
        args = RemoveDuplicatesArgs.model_validate(args)
    miss = [c for c in args.subset if c not in df.columns]
    if miss:
        return df, {"ok": False, "tool": "remove_duplicates", "error": f"列不存在: {miss}"}
    before = len(df)
    out = df.drop_duplicates(subset=args.subset, keep="first").reset_index(drop=True)
    return out, {
        "ok": True,
        "tool": "remove_duplicates",
        "rows_before": before,
        "rows_after": len(out),
        "removed": before - len(out),
    }


class FilterOutliersArgs(BaseModel):
    column: str
    method: str = Field(default="iqr", pattern="^(iqr|clip)$")
    iqr_k: float = 1.5
    lower: float | None = None
    upper: float | None = None


def filter_outliers(df: pd.DataFrame, args: FilterOutliersArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, FilterOutliersArgs):
        args = FilterOutliersArgs.model_validate(args)
    if args.column not in df.columns:
        return df, {"ok": False, "tool": "filter_outliers", "error": f"列不存在: {args.column}"}
    s = pd.to_numeric(df[args.column], errors="coerce")
    before = int(len(df))
    mask = s.notna()
    if args.method == "clip" and args.lower is not None and args.upper is not None:
        clipped = s.clip(lower=args.lower, upper=args.upper)
        out = df.copy()
        out[args.column] = clipped
        return out, {"ok": True, "tool": "filter_outliers", "method": "clip", "rows": len(out)}
    q1 = float(s[mask].quantile(0.25))
    q3 = float(s[mask].quantile(0.75))
    iqr = q3 - q1
    lo = q1 - args.iqr_k * iqr
    hi = q3 + args.iqr_k * iqr
    keep = (s >= lo) & (s <= hi) | s.isna()
    out = df.loc[keep].reset_index(drop=True)
    return out, {
        "ok": True,
        "tool": "filter_outliers",
        "method": "iqr",
        "rows_before": before,
        "rows_after": len(out),
        "bounds": {"lower": lo, "upper": hi},
    }


class FillMissingArgs(BaseModel):
    column: str
    method: str = Field(pattern="^(mean|median|mode|constant)$")
    constant: str | float | None = None


def fill_missing(df: pd.DataFrame, args: FillMissingArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, FillMissingArgs):
        args = FillMissingArgs.model_validate(args)
    if args.column not in df.columns:
        return df, {"ok": False, "tool": "fill_missing", "error": f"列不存在: {args.column}"}
    out = df.copy()
    col = out[args.column]
    if args.method == "constant":
        if args.constant is None:
            return df, {"ok": False, "tool": "fill_missing", "error": "constant 方法需要 constant 值"}
        out[args.column] = col.fillna(args.constant)
    elif args.method == "mean":
        v = pd.to_numeric(col, errors="coerce").mean()
        out[args.column] = pd.to_numeric(col, errors="coerce").fillna(v)
    elif args.method == "median":
        v = pd.to_numeric(col, errors="coerce").median()
        out[args.column] = pd.to_numeric(col, errors="coerce").fillna(v)
    else:
        mode = col.mode()
        fill_v = mode.iloc[0] if len(mode) else None
        out[args.column] = col.fillna(fill_v)
    return out, {"ok": True, "tool": "fill_missing", "filled": int(col.isna().sum())}


class ParseNumericColumnArgs(BaseModel):
    column: str
    unit_wan_multiplier: float = Field(default=10_000.0, description="「万」换算倍数")


def _parse_money_like(val: Any, wan_mult: float) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    s = str(val).strip()
    if not s:
        return None
    s = s.replace(",", "").replace("，", "")
    mult = 1.0
    if "万" in s:
        mult = wan_mult
        s = s.replace("万", "")
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    try:
        return float(m.group()) * mult
    except ValueError:
        return None


def parse_numeric_column(
    df: pd.DataFrame, args: ParseNumericColumnArgs | dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, ParseNumericColumnArgs):
        args = ParseNumericColumnArgs.model_validate(args)
    if args.column not in df.columns:
        return df, {"ok": False, "tool": "parse_numeric_column", "error": f"列不存在: {args.column}"}
    out = df.copy()
    parsed = out[args.column].map(lambda v: _parse_money_like(v, args.unit_wan_multiplier))
    out[args.column] = pd.to_numeric(parsed, errors="coerce")
    non_null = int(out[args.column].notna().sum())
    return out, {"ok": True, "tool": "parse_numeric_column", "non_null": non_null}

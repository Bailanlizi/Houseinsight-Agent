from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from server.tools._dataframe import truncate_records


class GetDataProfileArgs(BaseModel):
    sample_rows: int = Field(default=5, ge=1, le=50)


def get_data_profile(df: pd.DataFrame, args: GetDataProfileArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, GetDataProfileArgs):
        args = GetDataProfileArgs.model_validate(args)
    rows, truncated = truncate_records(df.head(args.sample_rows).to_dict(orient="records"), limit=args.sample_rows)
    missing_pct = {c: float(df[c].isna().mean()) for c in df.columns}
    profile = {
        "ok": True,
        "tool": "get_data_profile",
        "n_rows": int(len(df)),
        "n_columns": int(len(df.columns)),
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "missing_rate": missing_pct,
        "sample_rows": rows,
        "truncated": truncated,
    }
    return df, profile


class GetBasicStatsArgs(BaseModel):
    columns: list[str] | None = None


def get_basic_stats(df: pd.DataFrame, args: GetBasicStatsArgs | dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, GetBasicStatsArgs):
        args = GetBasicStatsArgs.model_validate(args)
    cols = args.columns
    if cols is None:
        cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        return df, {"ok": False, "tool": "get_basic_stats", "error": f"列不存在: {missing}"}
    stats: dict[str, Any] = {}
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        stats[c] = {
            "count": int(s.count()),
            "mean": float(s.mean()) if s.count() else None,
            "median": float(s.median()) if s.count() else None,
            "min": float(s.min()) if s.count() else None,
            "max": float(s.max()) if s.count() else None,
        }
    return df, {"ok": True, "tool": "get_basic_stats", "stats": stats}

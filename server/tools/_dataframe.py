from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd


def ensure_row_fingerprint(df: pd.DataFrame) -> pd.DataFrame:
    """若无 id 列则注入 _hi_row_fp（SPEC）。"""
    if "id" in df.columns or "_hi_row_fp" in df.columns:
        return df
    out = df.copy()

    def fp_for_row(row: pd.Series) -> str:
        blob = "|".join(str(v) for v in row.values)
        return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()[:16]

    out["_hi_row_fp"] = out.apply(fp_for_row, axis=1)
    return out


def truncate_records(records: list[dict[str, Any]], limit: int = 50) -> tuple[list[dict[str, Any]], bool]:
    if len(records) <= limit:
        return records, False
    return records[:limit], True

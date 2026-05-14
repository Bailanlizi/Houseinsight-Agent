from __future__ import annotations

import re
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

# 常见「房屋信息」管道串：2室1厅 | 85.46平米 | 南 北 | 简装 | 低楼层(共4层) | 2012年建 | 板塔结合
_ROOM_HALL = re.compile(r"(\d+)\s*室\s*(\d+)\s*厅")
_AREA = re.compile(r"([\d.]+)\s*平米")
_YEAR = re.compile(r"(\d{4})\s*年建")
_FLOOR_WORD = re.compile(r"(低楼层|中楼层|高楼层|顶层|底层)")
_ORIENT = re.compile(r"(东|南|西|北|东南|东北|西南|西北)(?:\s+(东|南|西|北))?")
_FITMENTS = ("精装", "简装", "毛坯", "其他")
_STRUCTS = ("板塔结合", "塔楼", "板楼", "平房", "别墅")


class ParseHouseInfoColumnArgs(BaseModel):
    column: str = Field(default="房屋信息", description="待解析的复合描述列名")
    prefix: str = Field(default="hi_", description="新列名前缀，避免与原始列冲突")


def _parse_cell(val: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "rooms": None,
        "halls": None,
        "area_m2": None,
        "fitment": None,
        "floor_tag": None,
        "build_year": None,
        "structure": None,
        "orientation": None,
    }
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return out
    s = str(val).strip()
    if not s:
        return out

    m = _ROOM_HALL.search(s)
    if m:
        out["rooms"] = int(m.group(1))
        out["halls"] = int(m.group(2))

    m = _AREA.search(s)
    if m:
        try:
            out["area_m2"] = float(m.group(1))
        except ValueError:
            pass

    m = _YEAR.search(s)
    if m:
        try:
            out["build_year"] = int(m.group(1))
        except ValueError:
            pass

    m = _FLOOR_WORD.search(s)
    if m:
        out["floor_tag"] = m.group(1)

    for f in _FITMENTS:
        if f in s:
            out["fitment"] = f
            break

    for st in _STRUCTS:
        if st in s:
            out["structure"] = st
            break

    m = _ORIENT.search(s)
    if m:
        parts = [g for g in m.groups() if g]
        out["orientation"] = " ".join(parts) if parts else None

    return out


def parse_house_info_column(
    df: pd.DataFrame, args: ParseHouseInfoColumnArgs | dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(args, ParseHouseInfoColumnArgs):
        args = ParseHouseInfoColumnArgs.model_validate(args)
    if args.column not in df.columns:
        return df, {"ok": False, "tool": "parse_house_info_column", "error": f"列不存在: {args.column}"}

    p = args.prefix
    parsed = df[args.column].map(_parse_cell)
    out = df.copy()
    out[f"{p}室"] = parsed.map(lambda x: x["rooms"])
    out[f"{p}厅"] = parsed.map(lambda x: x["halls"])
    out[f"{p}建面"] = parsed.map(lambda x: x["area_m2"])
    out[f"{p}装修"] = parsed.map(lambda x: x["fitment"])
    out[f"{p}楼层类型"] = parsed.map(lambda x: x["floor_tag"])
    out[f"{p}建筑年代"] = parsed.map(lambda x: x["build_year"])
    out[f"{p}结构"] = parsed.map(lambda x: x["structure"])
    out[f"{p}朝向"] = parsed.map(lambda x: x["orientation"])

    non_null = int(out[f"{p}建面"].notna().sum())
    return out, {
        "ok": True,
        "tool": "parse_house_info_column",
        "source_column": args.column,
        "added_columns": [
            f"{p}室",
            f"{p}厅",
            f"{p}建面",
            f"{p}装修",
            f"{p}楼层类型",
            f"{p}建筑年代",
            f"{p}结构",
            f"{p}朝向",
        ],
        "rows_with_area": non_null,
    }

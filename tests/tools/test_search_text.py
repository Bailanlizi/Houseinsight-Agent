import pandas as pd

from server.tools.analyze_tools import search_text


def test_search_text_any_term_hits_description_not_location():
    df = pd.DataFrame(
        {
            "描述": ["武侯立交 地铁三号线", "无交通词"],
            "位置信息": ["保利花园一期 ", "双楠三区 "],
            "区域": ["武侯", "武侯"],
        }
    )
    _, out = search_text(
        df,
        {
            "columns": ["描述", "位置信息"],
            "terms": ["地铁", "号线"],
            "how": "any_term_any_column",
        },
    )
    assert out["ok"]
    assert out["matched_rows"] == 1
    assert "地铁三号线" in str(out["rows_preview"][0].get("描述", ""))


def test_search_text_location_only_would_miss():
    df = pd.DataFrame(
        {
            "描述": ["地铁3号线口 大悦城旁"],
            "位置信息": ["华宇楠苑 "],
        }
    )
    _, out_loc = search_text(df, {"columns": ["位置信息"], "terms": ["地铁"], "how": "any_term_any_column"})
    assert out_loc["ok"] and out_loc["matched_rows"] == 0

    _, out_multi = search_text(
        df,
        {"columns": ["描述", "位置信息"], "terms": ["地铁", "号线"], "how": "any_term_any_column"},
    )
    assert out_multi["matched_rows"] == 1


def test_search_text_all_terms_concat():
    df = pd.DataFrame({"描述": ["带大阳台 地铁旁", "仅阳台"], "区域": ["武侯", "武侯"]})
    _, out = search_text(
        df,
        {"columns": ["描述"], "terms": ["阳台", "地铁"], "how": "all_terms_concat"},
    )
    assert out["ok"] and out["matched_rows"] == 1

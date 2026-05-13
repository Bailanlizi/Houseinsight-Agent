import pandas as pd

from server.tools.explore_tools import get_basic_stats, get_data_profile


def test_get_data_profile_basic():
    df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "z"]})
    _, prof = get_data_profile(df, {})
    assert prof["ok"] is True
    assert prof["n_rows"] == 3
    assert "a" in prof["columns"]


def test_get_basic_stats_missing_column():
    df = pd.DataFrame({"a": [1, 2, 3]})
    _, out = get_basic_stats(df, {"columns": ["missing"]})
    assert out["ok"] is False

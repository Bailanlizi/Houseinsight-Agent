import pandas as pd

from server.tools.analyze_tools import filter_rows


def test_filter_rows_and():
    df = pd.DataFrame({"price": [100, 200, 300], "rooms": [2, 3, 2]})
    _, out = filter_rows(
        df,
        {
            "filters": [
                {"column": "price", "op": "<=", "value": 250},
                {"column": "rooms", "op": "==", "value": 2},
            ],
            "logic": "and",
        },
    )
    assert out["ok"] is True
    assert out["matched_rows"] == 1

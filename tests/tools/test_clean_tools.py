import pandas as pd

from server.tools.clean_tools import parse_numeric_column


def test_parse_numeric_wan():
    df = pd.DataFrame({"price": ["153万", "200.5万", None]})
    out_df, payload = parse_numeric_column(df, {"column": "price"})
    assert payload["ok"] is True
    assert int(out_df.loc[0, "price"]) == 1_530_000

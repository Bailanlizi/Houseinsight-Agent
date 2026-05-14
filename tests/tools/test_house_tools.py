import pandas as pd
import pytest

from server.tools.house_tools import parse_house_info_column


def test_parse_house_info_pipe_string():
    df = pd.DataFrame(
        {
            "房屋信息": [
                "2室1厅 | 85.46平米 | 南 北 | 其他 | 低楼层(共4层) | 2012年建 | 平房",
            ]
        }
    )
    out, payload = parse_house_info_column(df, {"column": "房屋信息"})
    assert payload["ok"]
    assert int(out.loc[0, "hi_室"]) == 2
    assert int(out.loc[0, "hi_厅"]) == 1
    assert float(out.loc[0, "hi_建面"]) == pytest.approx(85.46)
    assert int(out.loc[0, "hi_建筑年代"]) == 2012
    assert out.loc[0, "hi_结构"] == "平房"

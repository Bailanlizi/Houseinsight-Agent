import uuid

import pandas as pd

from server.core.session_store import SessionStore, get_session_store


def test_session_store_roundtrip():
    s = SessionStore()
    sid = str(uuid.uuid4())
    df = pd.DataFrame({"a": [1]})
    s.put(sid, df)
    out = s.get(sid)
    assert out is not None
    assert list(out.columns) == ["a"]
    s.delete(sid)
    assert s.get(sid) is None


def test_global_store_singleton():
    a = get_session_store()
    b = get_session_store()
    assert a is b

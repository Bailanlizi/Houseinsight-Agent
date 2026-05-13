from __future__ import annotations

import threading

import pandas as pd


class SessionStore:
    """进程内会话级 DataFrame 存储（SPEC：整表不进 checkpoint）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frames: dict[str, pd.DataFrame] = {}

    def put(self, session_id: str, df: pd.DataFrame) -> None:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("expected pandas.DataFrame")
        with self._lock:
            self._frames[session_id] = df

    def get(self, session_id: str) -> pd.DataFrame | None:
        with self._lock:
            return self._frames.get(session_id)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._frames.pop(session_id, None)


_store = SessionStore()


def get_session_store() -> SessionStore:
    return _store

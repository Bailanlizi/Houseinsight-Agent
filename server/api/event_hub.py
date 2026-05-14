"""会话级 WebSocket 事件总线：订阅者 asyncio.Queue，publish 线程安全投递到事件循环。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_MAX = 500


class SessionEventHub:
    """每个 session_id 对应多个订阅队列；publish 时广播。队列满则丢弃最旧一条再尝试。"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

    async def register(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_DEFAULT_MAX)
        async with self._lock:
            self._queues.setdefault(session_id, []).append(q)
        return q

    async def unregister(self, session_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            lst = self._queues.get(session_id)
            if not lst:
                return
            try:
                lst.remove(q)
            except ValueError:
                return
            if not lst:
                self._queues.pop(session_id, None)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._queues.get(session_id, ()))
        for q in queues:
            await self._put_drop_oldest(q, event)

    @staticmethod
    async def _put_drop_oldest(q: asyncio.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("event hub queue still full after drop, event skipped")


_hub: SessionEventHub | None = None


def get_event_hub() -> SessionEventHub:
    global _hub
    if _hub is None:
        _hub = SessionEventHub()
    return _hub


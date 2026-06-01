"""TelegramSource — реализация JobSource поверх backend (Telethon).

Capabilities: can_scan=True, can_search=True, can_apply=False (read-only, всегда).

Источник тонкий: backend отдаёт сырые объекты Telethon, source маппит их в модели
(mapping.py) и добавляет вежливые задержки между запросами. Backend инъектируется —
в проде это TelethonBackend (client.py), в тестах — фейк.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol

from core.interfaces import Capabilities
from core.models import Dialog, RawMessage
from sources.telegram import mapping


class Backend(Protocol):
    """Низкоуровневый поставщик сырых объектов Telethon."""

    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    def iter_dialogs(self, include_archived: bool) -> AsyncIterator[Any]: ...
    def iter_messages(self, dialog_id: int, min_id: int | None) -> AsyncIterator[Any]: ...


async def _default_sleeper(seconds: float) -> None:
    await asyncio.sleep(seconds)


class TelegramSource:
    """Источник вакансий из Telegram (личные чаты, группы, каналы, сообщества + архив)."""

    name = "telegram"

    def __init__(
        self,
        config: dict[str, Any],
        backend: Backend | None = None,
        sleeper: Callable[[float], Awaitable[None] | None] | None = None,
    ) -> None:
        self._config = config or {}
        self._backend = backend
        self._sleeper = sleeper or _default_sleeper

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(can_scan=True, can_search=True, can_apply=False)

    @property
    def _delay(self) -> float:
        return float(
            self._config.get("sources", {}).get("telegram", {}).get("delay_between_requests", 0.5)
        )

    async def _sleep(self, seconds: float) -> None:
        result = self._sleeper(seconds)
        if asyncio.iscoroutine(result):
            await result

    async def connect(self) -> None:
        if self._backend is None:
            raise RuntimeError("TelegramSource: backend не инициализирован")
        await self._backend.connect()

    async def close(self) -> None:
        if self._backend is not None:
            await self._backend.close()

    async def iter_dialogs(self, include_archived: bool = True) -> AsyncIterator[Dialog]:
        """Перебрать диалоги, включая архив (folder_id 1)."""
        async for raw in self._backend.iter_dialogs(include_archived=include_archived):
            yield mapping.map_dialog(raw)

    async def iter_new_messages(
        self, dialog: Dialog, cursor: str | None
    ) -> AsyncIterator[RawMessage]:
        """Новые сообщения с cursor (min_id). None = глубина первого прохода (по дате на стороне backend)."""
        min_id = int(cursor) if cursor is not None else None
        async for raw in self._backend.iter_messages(int(dialog.id), min_id):
            await self._sleep(self._delay)
            yield mapping.map_message(raw, dialog)

    async def search(self, query: str) -> AsyncIterator[RawMessage]:  # pragma: no cover
        raise NotImplementedError("Поиск по Telegram — опционально, не требуется для дайджеста")
        yield

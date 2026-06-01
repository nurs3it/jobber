"""WebBoardsSource — ЗАГЛУШКА по интерфейсу JobSource (Фаза 7).

Обобщённый источник для веб-досок вакансий (через их публичные API/RSS, где это разрешено).
Сейчас — каркас, демонстрирующий контракт.

ПРАВОВОЕ/ToS: у каждой доски свои условия и rate limits. Предпочитать официальные API/RSS,
а не скрейпинг. Подробнее — .claude/docs/adding-a-source.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from core.interfaces import Capabilities
from core.models import Dialog, RawMessage


class WebBoardsSource:
    """Заглушка. Включается через config.sources.webboards.enabled (по умолчанию false)."""

    name = "webboards"

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(can_scan=False, can_search=True, can_apply=False)

    async def connect(self) -> None:
        raise NotImplementedError("TODO Фаза 7")

    async def close(self) -> None:
        raise NotImplementedError("TODO Фаза 7")

    async def iter_dialogs(self, include_archived: bool = True) -> AsyncIterator[Dialog]:
        raise NotImplementedError("TODO Фаза 7")
        yield  # pragma: no cover

    async def iter_new_messages(
        self, dialog: Dialog, cursor: str | None
    ) -> AsyncIterator[RawMessage]:
        raise NotImplementedError("TODO Фаза 7")
        yield  # pragma: no cover

    async def search(self, query: str) -> AsyncIterator[RawMessage]:
        raise NotImplementedError("TODO Фаза 7: поиск через официальные API/RSS досок")
        yield  # pragma: no cover

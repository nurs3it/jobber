"""LinkedInSource — ЗАГЛУШКА по интерфейсу JobSource (Фаза 7).

Реализуется в будущем. Сейчас — каркас, демонстрирующий контракт.

ПРАВОВОЕ/ToS: автоматизированный сбор данных LinkedIn ограничен их Условиями использования.
Перед реализацией свериться с ToS и официальным API. Подробнее — .claude/docs/security.md,
.claude/docs/adding-a-source.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from core.interfaces import Capabilities
from core.models import Dialog, RawMessage


class LinkedInSource:
    """Заглушка. Включается через config.sources.linkedin.enabled (по умолчанию false)."""

    name = "linkedin"

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    @property
    def capabilities(self) -> Capabilities:
        # Уточнить при реализации с учётом официального API.
        return Capabilities(can_scan=False, can_search=True, can_apply=False)

    async def connect(self) -> None:
        raise NotImplementedError("TODO Фаза 7: LinkedIn — учесть ToS и официальный API")

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
        raise NotImplementedError("TODO Фаза 7: поиск через официальный API LinkedIn")
        yield  # pragma: no cover

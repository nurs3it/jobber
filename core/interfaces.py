"""Интерфейс источника вакансий `JobSource` + capability-флаги.

Provider-agnostic контракт. Ядро работает только с этим интерфейсом и не знает,
Telegram перед ним, LinkedIn или веб-доска.

Как добавить источник — см. .claude/docs/adding-a-source.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from core.models import Dialog, RawMessage


class Capabilities(BaseModel):
    """Что источник умеет. Telegram — только чтение (can_apply=False всегда)."""

    can_scan: bool = False      # перебирать диалоги и читать новые сообщения
    can_search: bool = False    # серверный поиск по запросу
    can_apply: bool = False     # откликаться (у нас НИКОГДА не используется автоматически)


@runtime_checkable
class JobSource(Protocol):
    """Источник вакансий. Реализации — в sources/<name>/.

    Курсор (cursor) — непрозрачная для ядра строка: источник сам решает, что это
    (id последнего сообщения, дата и т.п.). Хранится в storage/ per-dialog.
    """

    name: str

    @property
    def capabilities(self) -> Capabilities:
        """Флаги возможностей источника."""
        ...

    async def connect(self) -> None:
        """Установить соединение/сессию. Для Telegram — Telethon login."""
        ...

    async def close(self) -> None:
        """Закрыть соединение."""
        ...

    def iter_dialogs(self, include_archived: bool = True) -> AsyncIterator[Dialog]:
        """Перебрать все диалоги, включая архив (для Telegram — folder_id 1)."""
        ...

    def iter_new_messages(
        self, dialog: Dialog, cursor: str | None
    ) -> AsyncIterator[RawMessage]:
        """Новые сообщения в диалоге начиная с cursor (None = с начала/глубина первого прохода)."""
        ...

    async def search(self, query: str) -> AsyncIterator[RawMessage]:  # опционально
        """Серверный поиск, если can_search. Иначе можно не реализовывать."""
        ...

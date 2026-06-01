"""TelethonBackend — реальный low-level доступ к Telegram (Telethon, user session).

ВАЖНО:
  - User session (MTProto), НЕ Bot API. Бот не видит личные чаты, подписки, группы и архив.
  - Файл сессии = полный доступ к аккаунту. Только локально, в .gitignore, как секрет.
  - Только чтение. Никаких отправок/вступлений/рассылок.
  - flood_sleep_threshold: при FloodWait Telethon сам подождёт (до порога); большие — пробрасываются.

Это интеграционный слой (реальная сеть/сессия), поэтому он не покрыт юнит-тестами.
Логика маппинга/задержек/фильтра архива протестирована в TelegramSource с фейковым backend.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from core.paths import jobber_home


class TelethonBackend:
    """Обёртка над telethon.TelegramClient с безопасными дефолтами (read-only)."""

    def __init__(self, config: dict[str, Any], secrets: dict[str, Any]) -> None:
        self._config = config or {}
        self._secrets = secrets or {}
        self._client = None  # telethon.TelegramClient

    # --- соединение ---

    async def connect(self) -> None:
        """Подключиться/залогиниться. Первый логин — интерактивно (код + 2FA-пароль).

        Сессия хранится в файле <session_name>.session (локальный секрет).
        """
        from telethon import TelegramClient

        api_id = self._secrets.get("api_id")
        api_hash = self._secrets.get("api_hash")
        phone = self._secrets.get("phone")
        session_name = self._secrets.get("session_name", "jobber")
        if not (api_id and api_hash):
            raise RuntimeError(
                "Нет TG_API_ID/TG_API_HASH в .env. Заполните их (см. /onboard, my.telegram.org)."
            )

        home = jobber_home()
        home.mkdir(parents=True, exist_ok=True)
        session_path = str(home / session_name)
        # flood_sleep_threshold: автоматически переждать небольшие FloodWait.
        self._client = TelegramClient(
            session_path, int(api_id), str(api_hash), flood_sleep_threshold=120
        )
        # start() сам запросит код из Telegram и пароль 2FA при первом логине (интерактивно).
        await self._client.start(phone=phone)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    # --- чтение (read-only) ---

    async def iter_dialogs(self, include_archived: bool) -> AsyncIterator[Any]:
        """Сырые Telethon-диалоги из основной папки и (опц.) из архива (folder_id 1)."""
        assert self._client is not None, "Сначала connect()"
        async for d in self._client.iter_dialogs():          # основная папка (folder 0)
            yield d
        if include_archived:
            async for d in self._client.iter_dialogs(folder=1):  # архив
                yield d

    async def iter_messages(self, dialog_id: int, min_id: int | None) -> AsyncIterator[Any]:
        """Сырые сообщения диалога новее min_id.

        Если min_id is None (первый проход без курсора) — ограничиваем глубину
        first_pass.max_messages_per_dialog, чтобы не тянуть всю историю.
        """
        assert self._client is not None, "Сначала connect()"
        if min_id is not None:
            async for m in self._client.iter_messages(dialog_id, min_id=min_id):
                yield m
        else:
            cap = int(self._config.get("first_pass", {}).get("max_messages_per_dialog", 300))
            async for m in self._client.iter_messages(dialog_id, limit=cap):
                yield m

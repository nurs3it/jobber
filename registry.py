"""Реестр источников вакансий.

Собирает включённые в config.yaml источники и отдаёт их ядру как список `JobSource`.
Включение/выключение — через секцию `sources` в config.yaml.

Фаза 0: только каркас. Реальная регистрация источников появится в Фазах 2 и 7.
"""

from __future__ import annotations

from typing import Any

from core.config import load_secrets
from core.interfaces import JobSource


def build_sources(config: dict[str, Any], secrets: dict[str, Any] | None = None) -> list[JobSource]:
    """Вернуть список включённых источников по конфигу.

    Telegram подключается с реальным TelethonBackend. linkedin/webboards — заглушки (Фаза 7),
    включаются только если явно enabled в config.yaml.
    """
    sources: list[JobSource] = []
    enabled = config.get("sources", {})
    secrets = secrets if secrets is not None else load_secrets()

    if enabled.get("telegram", {}).get("enabled"):
        from sources.telegram.client import TelethonBackend
        from sources.telegram.source import TelegramSource

        backend = TelethonBackend(config, secrets)
        sources.append(TelegramSource(config, backend=backend))

    if enabled.get("linkedin", {}).get("enabled"):
        from sources.linkedin.source import LinkedInSource

        sources.append(LinkedInSource(config))

    if enabled.get("webboards", {}).get("enabled"):
        from sources.webboards.source import WebBoardsSource

        sources.append(WebBoardsSource(config))

    return sources

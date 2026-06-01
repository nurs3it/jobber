"""CLI Telegram-источника. Используется командой /onboard для первого логина.

  python -m sources.telegram login    # интерактивный вход (код из Telegram + пароль 2FA)

Первый запуск создаёт файл сессии (<TG_SESSION_NAME>.session) — 🔒 локальный секрет.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from core.config import load_config, load_secrets
from sources.telegram.client import TelethonBackend


async def _login() -> int:
    config = load_config()
    secrets = load_secrets()
    if not (secrets.get("api_id") and secrets.get("api_hash")):
        print("Нет TG_API_ID/TG_API_HASH в .env. Заполните их (my.telegram.org).", file=sys.stderr)
        return 1
    backend = TelethonBackend(config, secrets)
    await backend.connect()
    # Проверим, что сессия рабочая: посчитаем пару диалогов.
    count = 0
    async for _ in backend.iter_dialogs(include_archived=False):
        count += 1
        if count >= 1:
            break
    await backend.close()
    print("✅ Логин успешен, сессия создана. Telegram доступен. Дальше: /scan")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sources.telegram")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="Первый интерактивный логин в Telegram (код + 2FA)")
    args = parser.parse_args(argv)
    if args.cmd == "login":
        return asyncio.run(_login())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

# Настройка (setup)

Пошаговая первичная настройка Jobber.

## 1. Установка (npm / yarn)

```bash
npm i -g @nurs3it/jobber           # или из GitHub: npm i -g github:nurs3it/jobber
jobber setup                       # venv, зависимости, регистрация в Claude Code
```

`jobber setup` создаёт `~/.jobber` (venv, `config.yaml`, `.env`, vault, storage), ставит slash-команды
в `~/.claude/commands` и регистрирует MCP-сервер `jobber` в Claude Code (user scope).

> Альтернатива (dev из исходников): `git clone … && npm link && jobber setup`.
> Старый локальный путь без npm: `bash scripts/install.sh` (ставит в папку проекта).

Управление версиями: `jobber update` / `jobber downdate` / `jobber install-version <v>` / `jobber versions`.
Диагностика: `jobber status`. Удаление: `jobber remove [--purge]`.

## 2. Получение api_id / api_hash

1. Зайдите на https://my.telegram.org под своим Telegram-аккаунтом.
2. **API development tools** → создайте приложение (любое название).
3. Скопируйте **api_id** и **api_hash**.

> Это ключи доступа к Telegram API. Храните как секрет.

## 3. Заполнение .env

Откройте `.env` и заполните:

```
TG_API_ID=...
TG_API_HASH=...
TG_PHONE=+7...
```

`.env` в `.gitignore` — не коммитится.

## 4. Онбординг и импорт CV

В Claude Code выполните `/onboard`:
- приложите резюме (**pdf / docx / png / jpg**) — оно распарсится в `profile/cv.md` без потерь фактов;
- подтвердите роль, грейд, зарплату, локацию, удалёнку, стоп-факторы;
- укажите глубину первого прохода (7 / 14 / 30 дней) и время дайджеста.

## 5. Первый логин в Telegram

Во время `/onboard` (Фаза 2) произойдёт логин user-session (Telethon):
- введите **код** из Telegram;
- при включённой **2FA** — пароль.

Создастся файл сессии. 🔒 Это полный доступ к аккаунту — он локальный и в `.gitignore`.

## 6. Первый scan

```
/scan 14        # проход по всем диалогам и архиву за 14 дней
/digest         # собрать дайджест в Obsidian
```

## Подключение MCP-сервера к Claude Code

В корне проекта есть `.mcp.json` — Claude Code подхватывает MCP-сервер `jobber` автоматически,
когда вы работаете в этой папке (он запускает `scripts/mcp-server.sh` → `python -m mcp_server`).
При первом обнаружении Claude Code попросит подтвердить доверие проектному MCP-серверу.

Инструменты сервера: `sources`, `get_profile`, `scan_candidates`, `write_digest`, `seen_reset`.
LLM-шаги (классификация, скоринг, письма) делает сам Claude Code по `cv.md` — отдельный API-ключ не нужен.

Проверить вручную: `python -m mcp_server` (stdio-сервер; Ctrl+C для выхода).

> Подробнее об архитектуре — `architecture.md`; о безопасности — `security.md`.

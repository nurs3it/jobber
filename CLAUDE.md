# Jobber — персональный ассистент поиска работы по Telegram

Локальный продукт. Пользователь один раз настраивает проект (отдаёт резюме + Telegram-ключи),
дальше одной командой получает свежие подходящие вакансии из своих чатов, групп, сообществ
и каналов (**включая архив**) — каждая с готовым черновиком сопроводительного письма и скором релевантности.

**Главный приоритет — минимум времени пользователя.** Настройка один раз, потом «сканируй» или дайджест по расписанию.

> HeadHunter не используем (соискательский API закрыт с 15.12.2025). Источник — Telegram.
> Архитектура **provider-agnostic**: в будущем LinkedIn, веб-доски и т.п. Telegram — первый и пока единственный источник.

---

## Целевой user-flow

1. Пользователь ставит проект, запускает `/onboard`.
2. Прикладывает резюме (**pdf / docx / img**) и вводит Telegram `api_id` / `api_hash` + телефон.
3. Резюме парсится → `profile/cv.md`. Ключи → `.env`. Первый логин в Telegram (код + 2FA).
4. Пользователь: «сканируй и найди свежие вакансии».
5. Система проходит по диалогам (включая архив), находит и оценивает вакансии.
6. По **каждой** вакансии: ссылка · кому писать (контакт или «не указан») · черновик сопроводительного · скор 0–100 с причиной.

---

## Архитектура (карта проекта)

```
core/              Ядро. НЕ знает о Telegram. Интерфейс JobSource + доменные модели (pydantic).
ingest/            Импорт CV из pdf/docx/img → profile/cv.md.
sources/
  telegram/        Полная реализация (Telethon, user session). Маппинг сообщений + извлечение контакта.
  linkedin/        Заглушка по интерфейсу (Фаза 7).
  webboards/       Заглушка по интерфейсу (Фаза 7).
registry.py        Реестр источников, вкл/выкл через config.yaml.
pipeline.py        Оркестратор: collect_candidates / run_scan / run_digest (DI, тестируется на фейках).
matching/          Предфильтр (regex/keywords) + LLM-классификация/скоринг по профилю.
cover/             Генерация сопроводительных писем (тон из конфига). Только черновики.
digest/            Дедуп, агрегация, рендер дайджеста в Obsidian (Markdown).
storage/           Курсоры (per-dialog), seen-store, кэш (SQLite/JSON, gitignored).
profile/           cv.md (резюме пользователя, gitignored).
mcp_server/        MCP-сервер (stdio). Объявляет инструменты, роутит через ядро. Подключаем к Claude Code.
.claude/           Slash-команды, агенты, документация (docs/).
scripts/           install.sh, install-schedule.sh, uninstall-schedule.sh.
tests/             pytest + моки.
config.yaml        Единый источник правды конфигурации (не секреты).
.env               Секреты: TG_API_ID/HASH/PHONE. Gitignored.
vault/             Obsidian vault по умолчанию (gitignored).
```

Поток данных: `источник → предфильтр → LLM-классификация/скоринг → дедуп → сопроводительное → дайджест`.

---

## Запуск и команды

Среда — Python 3.11+ через `uv` (или venv). Установка: `bash scripts/install.sh`.

Slash-команды (в Claude Code, см. `.claude/commands/`):

| Команда | Что делает |
|---|---|
| `/onboard` | Импорт CV (pdf/docx/img) → `cv.md`, ввод/сохранение TG-ключей, первый логин. |
| `/scan` | Разовый проход (напр. «за 7 дней по всем диалогам, включая архив»). |
| `/digest` | Собрать дайджест за период (новое с прошлого запуска) → Obsidian + отчёт в чат. |
| `/cover <id>` | Перегенерировать сопроводительное для вакансии. |
| `/profile-edit` | Отредактировать `cv.md` вместе с пользователем. |
| `/sources` | Показать источники и их capability-флаги. |
| `/seen-reset` | Сбросить виденные сообщения / курсоры. |

Автозапуск: `claude -p "/digest"` из папки проекта по расписанию (launchd на macOS / cron на Linux),
ставится через `scripts/install-schedule.sh`.

---

## Переменные окружения (.env)

| Переменная | Назначение |
|---|---|
| `TG_API_ID`, `TG_API_HASH` | Ключи приложения с my.telegram.org. |
| `TG_PHONE` | Телефон аккаунта (международный формат). |
| `TG_SESSION_NAME` | Имя файла сессии Telethon (локальный секрет). |
| `ANTHROPIC_API_KEY` | Опционально, только для автономного запуска конвейера вне Claude Code. |

---

## Конвенции

- **Provider-agnostic.** `core/` не импортирует ничего из `sources/`. Источники реализуют интерфейс `JobSource`.
- **Read-only по Telegram.** Никаких отправок, вступлений, рассылок. Сопроводительные — только черновики.
- **Мягкие задержки**, обработка `FloodWaitError` (ждать указанное время).
- Доменные модели — `pydantic`. Конфиг — `config.yaml`. Секреты — `.env`.
- Документация (`CLAUDE.md` в каждой папке + `.claude/docs/`) держится актуальной после каждой фазы.

---

## 🔒 Безопасность — файл сессии

**Файл сессии Telethon (`*.session`) = полный доступ к аккаунту пользователя.**

- Только локально. В `.gitignore`. Никогда не коммитить, не логировать, не выводить в дайджест.
- Секреты (`.env`), сессия и загруженные CV — только на машине пользователя.
- Скомпрометированная сессия = угнанный Telegram. Относиться как к паролю.
- Подробнее: `.claude/docs/security.md`.

---

## Статус по фазам

- [x] **Фаза 0** — каркас, конфиги, скелеты документации, шаблон cv.md, install.sh.
- [x] **Фаза 1** — импорт CV (pdf/docx/img/txt) → текст; запись cv.md (атомарно+бэкап); сохранение ключей (`update_env`); CLI `python -m ingest extract`. Тесты с реальными файлами.
- [x] **Фаза 2** — Telethon-backend (логин код+2FA, архив folder=1, FloodWait); `TelegramSource` (маппинг, задержки); MCP-сервер (stdio, `.mcp.json`); CLI `python -m sources.telegram login`.
- [x] **Фаза 3** — предфильтр (RU/EN keywords/hashtags); seen-store + per-dialog курсоры (SQLite); fuzzy-дедуп.
- [x] **Фаза 4** — LLM-классификация/скоринг (`matching/classifier.py`, абстракция `core/llm.py`); извлечение контакта (`mapping.extract_contact`); загрузка профиля (`core/profile.py`).
- [x] **Фаза 5** — сопроводительные (`cover/`, тон/язык из конфига); рендер дайджеста в Obsidian (`digest/render.py`); оркестратор `pipeline.py`; команды под MCP.
- [x] **Фаза 6** — автозапуск: `scripts/{run-digest,install-schedule,uninstall-schedule}.sh` (launchd на macOS, cron на Linux).
- [x] **Фаза 7** — заглушки `linkedin`/`webboards` по интерфейсу (read-only, `adding-a-source.md`).

Все фазы реализованы. Тесты: `python -m pytest tests/` (84 passed, 1 skip — OCR без tesseract). Линт: `ruff check .`.

Документация: `README.md` · `.claude/docs/{setup,architecture,adding-a-source,runbook,security,troubleshooting}.md`.

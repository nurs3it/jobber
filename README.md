# Jobber

[![CI](https://github.com/nurs3it/jobber/actions/workflows/ci.yml/badge.svg)](https://github.com/nurs3it/jobber/actions/workflows/ci.yml)

Локальный персональный ассистент поиска работы по **Telegram**. Отдаёшь резюме и Telegram-ключи —
получаешь свежие подходящие вакансии из своих чатов, групп, сообществ и каналов (**включая архив**),
каждую с готовым черновиком сопроводительного письма и скором релевантности 0–100.

- **Минимум времени.** Настройка один раз (`/onboard`), дальше `/scan` или дайджест по расписанию.
- **Read-only.** Ничего не отправляется автоматически. Сопроводительные — только черновики под ревью.
- **Provider-agnostic.** Telegram сейчас; LinkedIn и веб-доски — заложены на будущее.

> Почему не HeadHunter: соискательский API закрыт с 15.12.2025. Источник — Telegram (user-session, MTProto).

## Установка (npm / yarn)

Jobber ставится как глобальный CLI. Данные и Python-движок живут в `~/.jobber` (отдельно от кода).

```bash
# из GitHub (рекомендуется):
npm  i -g github:nurs3it/jobber        #  или: yarn global add github:nurs3it/jobber
# конкретная версия (git-тег):
npm  i -g github:nurs3it/jobber#v1.0.0
# если опубликовано в npm registry:
npm  i -g jobber                       #  или: jobber@1.0.0

jobber setup                           # venv, зависимости, регистрация в Claude Code
```

Затем в **Claude Code**:

```
/onboard      # резюме (pdf/docx/img) + Telegram-ключи + первый логин
/scan         # разовый проход по диалогам и архиву
/digest       # дайджест в Obsidian + отчёт в чат
```

## Команды CLI

| Команда | Назначение |
|---|---|
| `jobber install [версия]` | Установить/настроить (опц. конкретную версию). |
| `jobber update` | Обновить до последней версии. |
| `jobber downdate` | Откатить на предыдущую версию. |
| `jobber install-version <v>` · `use <v>` | Поставить конкретную версию. |
| `jobber versions` | Список доступных версий (git-теги / npm). |
| `jobber remove [--purge]` | Удалить (с `--purge` — вместе с данными `~/.jobber`). |
| `jobber login` | Вход в Telegram (код + 2FA). |
| `jobber extract <файл>` | Извлечь текст из резюме. |
| `jobber schedule on\|off` | Ежедневный дайджест по расписанию. |
| `jobber status` · `version` | Диагностика и версия. |

> Канал версий определяется при установке (GitHub-теги или npm). Переопределить: `--github` / `--npm`.

### Установка из исходников (dev)

```bash
git clone https://github.com/nurs3it/jobber && cd jobber
npm link        # делает доступным CLI `jobber` из репозитория
jobber setup
```

## Документация

- **Настройка:** [`.claude/docs/setup.md`](.claude/docs/setup.md) — api_id/api_hash, первый логин, импорт CV, первый scan.
- **Архитектура:** [`.claude/docs/architecture.md`](.claude/docs/architecture.md) — ядро, источники, конвейер, диаграмма.
- **Добавить источник:** [`.claude/docs/adding-a-source.md`](.claude/docs/adding-a-source.md) — интерфейс, capability-флаги, маппинг.
- **Эксплуатация:** [`.claude/docs/runbook.md`](.claude/docs/runbook.md) — расписание, где файлы.
- **Безопасность:** [`.claude/docs/security.md`](.claude/docs/security.md) — модель угроз, файл сессии, read-only.
- **Проблемы:** [`.claude/docs/troubleshooting.md`](.claude/docs/troubleshooting.md) — flood-wait, протухшая сессия, OCR, дубликаты, пустой дайджест.

## 🔒 Безопасность

Файл сессии Telethon (`*.session`) = полный доступ к Telegram-аккаунту. Только локально, в `.gitignore`,
никогда не коммитить и не логировать. Подробнее — `.claude/docs/security.md` и `CLAUDE.md`.
